"""Weaviate database wrapper for hybrid semantic and lexical search.

Provides vector database functionality using Weaviate v4 client API.
"""

import time
from typing import List, Optional

import weaviate
from weaviate.classes.config import Configure, DataType, Property, VectorDistances
from weaviate.classes.query import Filter, MetadataQuery
from weaviate.exceptions import WeaviateConnectionError

from backend.database.chunker import Chunk
from backend.database.embeddings import EmbeddingModel


def list_collections(url: Optional[str] = None) -> List[str]:
    """
    List all available collections in Weaviate.

    Args:
        url: Optional URL for remote Weaviate instance (default: http://localhost:8080)

    Returns:
        List of collection names
    """
    try:
        if url is not None:
            import urllib.parse

            parsed = urllib.parse.urlparse(url)
            host = parsed.hostname or "localhost"
            port = parsed.port or 8080
            client = weaviate.connect_to_local(host=host, port=port)
        else:
            # Default: connect to local Docker container
            client = weaviate.connect_to_local(
                host="localhost", port=8080, grpc_port=50051
            )
        try:
            # In Weaviate v4, list_all() returns a list of collection names
            collections = client.collections.list_all()
            return list(collections) if collections else []
        finally:
            client.close()
    except Exception as e:
        # If connection fails, return empty list
        print(f"Warning: Could not connect to Weaviate: {e}")
        return []


class WeaviateDatabase:
    """
    Weaviate database wrapper for storing and searching chunks.

    Supports hybrid search (semantic + keyword) with metadata filtering.
    """

    def __init__(
        self,
        collection_name: str,
        url: Optional[str] = None,
        embedded_options: Optional[weaviate.embedded.EmbeddedOptions] = None,
        auth_client_secret: Optional[weaviate.auth.AuthCredentials] = None,
        additional_headers: Optional[dict] = None,
        embedding_model: Optional[EmbeddingModel] = None,
        device: Optional[str] = None,
    ):
        """
        Initialize Weaviate database.

        Args:
            collection_name: Name of Weaviate collection
            url: Optional URL for remote Weaviate instance (default: http://localhost:8080 for Docker)
            embedded_options: Optional embedded Weaviate options (use if you want embedded instead of Docker)
            auth_client_secret: Optional authentication for remote instances
            additional_headers: Optional additional headers
            embedding_model: Embedding model instance (creates new if None)
            device: Device to use for embedding model ('cpu', 'cuda', 'mps', or None for auto-detect)
        """
        self.collection_name = collection_name

        # Initialize Weaviate client
        try:
            if embedded_options is not None:
                # Use embedded Weaviate if explicitly requested
                self.client = weaviate.WeaviateClient(embedded_options=embedded_options)
                self.client.connect()
            elif url is not None:
                # Custom URL provided - use connect_to_local helper
                import urllib.parse

                parsed = urllib.parse.urlparse(url)
                host = parsed.hostname or "localhost"
                port = parsed.port or 8080
                self.client = weaviate.connect_to_local(
                    host=host,
                    port=port,
                    headers=additional_headers,
                    auth_credentials=auth_client_secret,
                )
            else:
                # Default: connect to local Docker container (http://localhost:8080)
                self.client = weaviate.connect_to_local(
                    host="localhost",
                    port=8080,
                    grpc_port=50051,
                    headers=additional_headers,
                    auth_credentials=auth_client_secret,
                )
        except WeaviateConnectionError as e:
            raise ConnectionError(
                "Cannot connect to Weaviate Database.\n"
                "Is it running?\n"
                "If using Docker, ensure daemon and container are running and are reachable."
            ) from e

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
        if not self.client.collections.exists(self.collection_name):
            print(f"Creating collection: {self.collection_name}")
            self.client.collections.create(
                name=self.collection_name,
                vector_config=Configure.Vectors.self_provided(
                    vector_index_config=Configure.VectorIndex.hnsw(
                        distance_metric=VectorDistances.COSINE,
                    ),
                ),
                properties=[
                    Property(name="text", data_type=DataType.TEXT),
                    Property(name="page", data_type=DataType.INT),
                    Property(name="source_book", data_type=DataType.TEXT),
                    Property(name="section", data_type=DataType.TEXT_ARRAY),
                    Property(name="chunk_index", data_type=DataType.INT),
                ],
            )
            print(
                f"Collection '{self.collection_name}' created with dimension {self.embedding_dim}"
            )
        # else:
        #     print(f"Using existing collection: {self.collection_name}")

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
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            embeddings = self.embedding_model.embed(batch, show_progress=False)
            all_embeddings.extend(embeddings)

        # Prepare data objects
        collection = self.client.collections.get(self.collection_name)
        with collection.batch.dynamic() as batch:
            for chunk, embedding in zip(chunks, all_embeddings):
                data_object = {
                    "text": chunk.text,
                    "page": chunk.page,
                    "source_book": chunk.source_book,
                    "section": chunk.section if chunk.section is not None else [],
                    "chunk_index": chunk.chunk_index,
                }
                batch.add_object(
                    properties=data_object,
                    vector=embedding,
                )

        print(f"Added {len(chunks)} chunks to database")

    def add_from_json(
        self,
        json_path,
        source_book: str,
        min_char_len: int = 1000,
        batch_size: int = 32,
    ):
        """
        Load JSON dump, chunk it, and add chunks to database.

        Args:
            json_path: Path to JSON file containing page transcriptions
            source_book: Source book identifier (e.g., 'heroes', 'monsters')
            min_char_len: Minimum character length for chunks before concatenation
            batch_size: Batch size for embedding generation
        """
        import json
        from pathlib import Path

        json_path_obj = Path(json_path)
        if not json_path_obj.exists():
            raise FileNotFoundError(f"JSON file not found: {json_path_obj}")

        print(f"Loading JSON dump from: {json_path_obj}")
        with open(json_path_obj, "r") as f:
            json_dump = json.load(f)

        from backend.database.chunker import chunk_json_dump

        print(f"Chunking {len(json_dump)} pages...")
        chunks = chunk_json_dump(
            json_dump=json_dump,
            source_book=source_book,
            min_char_len=min_char_len,
        )

        print(f"Created {len(chunks)} chunks")
        if chunks:
            avg_chars = sum(len(c.text) for c in chunks) / len(chunks)
            print(f"Average chunk size: {avg_chars:.0f} characters")

        # Add chunks to database
        self.add_chunks(chunks, batch_size=batch_size)

    def search(
        self,
        query: str,
        limit: int = 10,
        page_filter: Optional[int] = None,
        section_filter: Optional[str] = None,
        use_hybrid: bool = True,
        alpha: float = 0.5,
    ) -> List[dict]:
        """
        Search database with semantic and/or keyword search.

        Args:
            query: Search query text
            limit: Maximum number of results
            page_filter: Filter by page number (optional)
            section_filter: Filter by section name (optional)
            use_hybrid: Use hybrid search (semantic + keyword), else semantic only
            alpha: Weight for vector search in hybrid (0.0 = pure BM25, 1.0 = pure vector, default: 0.5)

        Returns:
            List of result dictionaries with text, page, source_book, section, chunk_index, score
        """
        if use_hybrid:
            return self.hybrid_search(
                query=query,
                limit=limit,
                page_filter=page_filter,
                section_filter=section_filter,
                alpha=alpha,
            )
        else:
            return self.vector_search(
                query=query,
                limit=limit,
                page_filter=page_filter,
                section_filter=section_filter,
            )

    def vector_search(
        self,
        query: str,
        limit: int = 10,
        page_filter: Optional[int] = None,
        section_filter: Optional[str] = None,
    ) -> List[dict]:
        """
        Semantic search using query embedding.

        Args:
            query: Search query text
            limit: Maximum number of results
            page_filter: Filter by page number (optional)
            section_filter: Filter by section name (optional)

        Returns:
            List of result dictionaries with text, page, source_book, section, chunk_index, score
        """
        # Generate query embedding
        query_vector = self.embedding_model.embed_single(query)

        # Build filter
        filters = None
        if page_filter is not None or section_filter is not None:
            conditions = []
            if page_filter is not None:
                conditions.append(Filter.by_property("page").equal(page_filter))
            if section_filter is not None:
                conditions.append(
                    Filter.by_property("section").contains_any([section_filter])
                )
            if len(conditions) == 1:
                filters = conditions[0]
            else:
                filters = Filter.all_of(conditions)

        # Perform vector search
        collection = self.client.collections.get(self.collection_name)
        response = collection.query.near_vector(
            near_vector=query_vector,
            limit=limit,
            filters=filters,
            return_metadata=MetadataQuery(distance=True),
        )

        # Format results
        formatted_results = []
        for obj in response.objects:
            props = obj.properties
            formatted_results.append(
                {
                    "text": props.get("text", ""),
                    "page": props.get("page"),
                    "source_book": props.get("source_book", ""),
                    "section": props.get("section", []),
                    "chunk_index": props.get("chunk_index", 0),
                    "score": 1.0 - obj.metadata.distance
                    if obj.metadata.distance is not None
                    else 0.0,
                }
            )

        return formatted_results

    def text_search(
        self,
        query: str,
        limit: int = 10,
        page_filter: Optional[int] = None,
        section_filter: Optional[str] = None,
    ) -> List[dict]:
        """
        Keyword/text search using BM25.

        Args:
            query: Search query text
            limit: Maximum number of results
            page_filter: Filter by page number (optional)
            section_filter: Filter by section name (optional)

        Returns:
            List of result dictionaries with text, page, source_book, section, chunk_index, score
        """
        # Build filter
        filters = None
        if page_filter is not None or section_filter is not None:
            conditions = []
            if page_filter is not None:
                conditions.append(Filter.by_property("page").equal(page_filter))
            if section_filter is not None:
                conditions.append(
                    Filter.by_property("section").contains_any([section_filter])
                )
            if len(conditions) == 1:
                filters = conditions[0]
            else:
                filters = Filter.all_of(conditions)

        # Perform BM25 search
        collection = self.client.collections.get(self.collection_name)
        response = collection.query.bm25(
            query=query,
            limit=limit,
            filters=filters,
            return_metadata=MetadataQuery(score=True),
        )

        # Format results
        formatted_results = []
        for obj in response.objects:
            props = obj.properties
            formatted_results.append(
                {
                    "text": props.get("text", ""),
                    "page": props.get("page"),
                    "source_book": props.get("source_book", ""),
                    "section": props.get("section", []),
                    "chunk_index": props.get("chunk_index", 0),
                    "score": obj.metadata.score
                    if obj.metadata.score is not None
                    else 0.0,
                }
            )

        return formatted_results

    def hybrid_search(
        self,
        query: str,
        limit: int = 10,
        page_filter: Optional[int] = None,
        section_filter: Optional[str] = None,
        alpha: float = 0.5,
    ) -> List[dict]:
        """
        Hybrid search combining vector and text search.

        Args:
            query: Search query text
            limit: Maximum number of results
            page_filter: Filter by page number (optional)
            section_filter: Filter by section name (optional)
            alpha: Weight for vector search (0.0 = pure BM25, 1.0 = pure vector, default: 0.5)

        Returns:
            List of result dictionaries with text, page, source_book, section, chunk_index, score
        """
        # Generate query embedding
        query_vector = self.embedding_model.embed_single(query)

        # Build filter
        filters = None
        if page_filter is not None or section_filter is not None:
            conditions = []
            if page_filter is not None:
                conditions.append(Filter.by_property("page").equal(page_filter))
            if section_filter is not None:
                conditions.append(
                    Filter.by_property("section").contains_any([section_filter])
                )
            if len(conditions) == 1:
                filters = conditions[0]
            else:
                filters = Filter.all_of(conditions)

        # Perform hybrid search
        collection = self.client.collections.get(self.collection_name)
        response = collection.query.hybrid(
            query=query,
            vector=query_vector,
            alpha=alpha,
            limit=limit,
            filters=filters,
            return_metadata=MetadataQuery(score=True),
        )

        # Format results
        formatted_results = []
        for obj in response.objects:
            props = obj.properties
            formatted_results.append(
                {
                    "text": props.get("text", ""),
                    "page": props.get("page"),
                    "source_book": props.get("source_book", ""),
                    "section": props.get("section", []),
                    "chunk_index": props.get("chunk_index", 0),
                    "score": obj.metadata.score
                    if obj.metadata.score is not None
                    else 0.0,
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
            collection = self.client.collections.get(self.collection_name)
            collection.query.near_vector(
                near_vector=query_vector,
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
        collection = self.client.collections.get(self.collection_name)

        # Get object count
        aggregate_result = collection.aggregate.over_all(total_count=True)
        points_count = (
            aggregate_result.total_count
            if hasattr(aggregate_result, "total_count")
            else 0
        )

        return {
            "name": self.collection_name,
            "points_count": points_count,
            "vectors_count": points_count,  # In Weaviate, each object has one vector
            "status": "ready",  # Weaviate doesn't have status field like Qdrant
            "config": {
                "vector_size": self.embedding_dim,
                "distance": "cosine",
            },
        }

    def close(self):
        """Close the Weaviate client and release resources."""
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
