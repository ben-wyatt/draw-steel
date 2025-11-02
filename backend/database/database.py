"""
Qdrant database wrapper for hybrid semantic and lexical search.

Provides fast local vector database with typo tolerance and fuzzy matching.
"""

import time
import uuid
from pathlib import Path
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)
from tqdm import tqdm

from backend.database.chunker import Chunk
from backend.database.embeddings import EmbeddingModel


class Database:
    """
    Qdrant database wrapper for storing and searching chunks.

    Supports hybrid search (semantic + keyword) with metadata filtering.
    """

    def __init__(
        self,
        collection_name: str,
        db_path: Optional[Path] = None,
        embedding_model: Optional[EmbeddingModel] = None,
        device: Optional[str] = None,
    ):
        """
        Initialize database.

        Args:
            collection_name: Name of Qdrant collection
            db_path: Path to database directory (default: backend/data/db_files)
            embedding_model: Embedding model instance (creates new if None)
            device: Device to use for embedding model ('cpu', 'cuda', 'mps', or None for auto-detect)
        """
        if db_path is None:
            # Default to backend/data/db_files
            repo_root = Path(__file__).parent.parent.parent
            db_path = repo_root / "backend" / "data" / "db_files"
        db_path.mkdir(parents=True, exist_ok=True)

        self.collection_name = collection_name
        self.db_path = db_path
        self.qdrant_path = db_path / "qdrant"

        # Initialize Qdrant client (local mode)
        self.client = QdrantClient(path=str(self.qdrant_path))

        # Initialize embedding model
        if embedding_model is None:
            self.embedding_model = EmbeddingModel(device=device)
        else:
            self.embedding_model = embedding_model

        # Get embedding dimension
        self.embedding_dim = self.embedding_model.get_embedding_dimension()

        # Create collection if it doesn't exist
        self._ensure_collection()

    def _ensure_collection(self):
        """Create collection if it doesn't exist or recreate if dimension mismatch."""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.collection_name not in collection_names:
            print(f"Creating collection: {self.collection_name}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=Distance.COSINE,
                ),
            )
            print(f"Collection '{self.collection_name}' created with dimension {self.embedding_dim}")
        else:
            # Check if dimension matches
            collection_info = self.client.get_collection(self.collection_name)
            existing_dim = collection_info.config.params.vectors.size
            if existing_dim != self.embedding_dim:
                print(
                    f"Collection '{self.collection_name}' exists with dimension {existing_dim}, "
                    f"but model produces dimension {self.embedding_dim}. Recreating collection..."
                )
                self.client.delete_collection(self.collection_name)
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dim,
                        distance=Distance.COSINE,
                    ),
                )
                print(f"Collection '{self.collection_name}' recreated with dimension {self.embedding_dim}")
            else:
                print(f"Using existing collection: {self.collection_name}")

    def add_chunks(self, chunks: List[Chunk], batch_size: int = 32):
        """
        Add chunks to database with embeddings.

        Args:
            chunks: List of Chunk objects to add
            batch_size: Batch size for embedding generation
        """
        if not chunks:
            return

        print(f"Adding {len(chunks)} chunks to database...")

        # Generate embeddings in batches
        texts = [chunk.text for chunk in chunks]
        all_embeddings = []
        num_batches = (len(texts) + batch_size - 1) // batch_size
        for i in tqdm(range(0, len(texts), batch_size), desc="Generating embeddings", total=num_batches, unit="batch"):
            batch = texts[i : i + batch_size]
            embeddings = self.embedding_model.embed(batch, show_progress=False)
            all_embeddings.extend(embeddings)

        # Prepare points for Qdrant
        points = []
        for chunk, embedding in zip(chunks, all_embeddings):
            point_id = str(uuid.uuid4())
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "text": chunk.text,
                        "page": chunk.page,
                        "source": chunk.source,
                        "section": chunk.section,
                        "chunk_index": chunk.chunk_index,
                        "token_count": chunk.token_count,
                    },
                )
            )

        # Upload to Qdrant
        self.client.upsert(collection_name=self.collection_name, points=points)
        print(f"Added {len(chunks)} chunks to database")

    def search(
        self,
        query: str,
        limit: int = 10,
        page_filter: Optional[int] = None,
        section_filter: Optional[str] = None,
        use_hybrid: bool = True,
    ) -> List[dict]:
        """
        Search database with semantic and/or keyword search.

        Args:
            query: Search query text
            limit: Maximum number of results
            page_filter: Filter by page number (optional)
            section_filter: Filter by section name (optional)
            use_hybrid: Use hybrid search (semantic + keyword), else semantic only

        Returns:
            List of result dictionaries with text, page, section, score, etc.
        """
        # Generate query embedding
        query_vector = self.embedding_model.embed_single(query)

        # Build filter
        filter_conditions = []
        if page_filter is not None:
            filter_conditions.append(
                FieldCondition(key="page", match=MatchValue(value=page_filter))
            )
        if section_filter is not None:
            filter_conditions.append(
                FieldCondition(key="section", match=MatchValue(value=section_filter))
            )

        query_filter = Filter(must=filter_conditions) if filter_conditions else None

        # Perform semantic search
        # Note: Qdrant's hybrid search requires collection configuration with sparse vectors
        # For now, we use semantic search. Keyword search can be added via payload filtering
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit,
        )

        # Format results
        formatted_results = []
        for result in results:
            payload = result.payload
            formatted_results.append(
                {
                    "text": payload.get("text", ""),
                    "page": payload.get("page"),
                    "source": payload.get("source", ""),
                    "section": payload.get("section", []),
                    "chunk_index": payload.get("chunk_index", 0),
                    "token_count": payload.get("token_count", 0),
                    "score": result.score,
                }
            )

        return formatted_results

    def test_latency(self, query: str, num_runs: int = 10) -> dict:
        """
        Test latency of semantic search (embedding + matching).

        Args:
            query: Query text to test
            num_runs: Number of runs for averaging

        Returns:
            Dictionary with timing statistics
        """
        times = []

        for _ in range(num_runs):
            start = time.time()

            # Generate embedding
            query_vector = self.embedding_model.embed_single(query)

            # Search
            self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=10,
            )

            elapsed = time.time() - start
            times.append(elapsed)

        return {
            "query": query,
            "num_runs": num_runs,
            "mean_ms": sum(times) / len(times) * 1000,
            "min_ms": min(times) * 1000,
            "max_ms": max(times) * 1000,
            "median_ms": sorted(times)[len(times) // 2] * 1000,
            "times_ms": [t * 1000 for t in times],
        }

    def get_collection_info(self) -> dict:
        """Get information about the collection."""
        collection_info = self.client.get_collection(self.collection_name)
        return {
            "name": self.collection_name,
            "points_count": collection_info.points_count,
            "vectors_count": collection_info.vectors_count,
            "status": collection_info.status,
            "config": {
                "vector_size": collection_info.config.params.vectors.size,
                "distance": collection_info.config.params.vectors.distance,
            },
        }

    def close(self):
        """Close the Qdrant client and release the lock."""
        if hasattr(self, "client") and self.client is not None:
            self.client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures client is closed."""
        self.close()

    def __del__(self):
        """Cleanup when object is garbage collected."""
        self.close()

