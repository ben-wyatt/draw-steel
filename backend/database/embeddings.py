"""
Embedding generation using local HuggingFace model.

Uses google/embeddinggemma-300m for fast local semantic embeddings.
"""

import time
from typing import List, Optional

from sentence_transformers import SentenceTransformer

from backend.utils.keys import get_hf_token


class EmbeddingModel:
    """
    Wrapper for local embedding model.

    Uses google/embeddinggemma-300m for generating semantic vectors.
    """

    def __init__(self, model_name: str = "google/embeddinggemma-300m"):
        """
        Initialize embedding model.

        Args:
            model_name: HuggingFace model name (default: google/embeddinggemma-300m)
        """
        self.model_name = model_name
        self.model: Optional[SentenceTransformer] = None
        self._load_model()

    def _load_model(self):
        """Load the embedding model."""
        print(f"Loading embedding model: {self.model_name}...")
        
        # Get HuggingFace token for gated models
        hf_token = get_hf_token()
        if hf_token:
            # Use token for authentication
            self.model = SentenceTransformer(
                self.model_name,
                token=hf_token,
            )
        else:
            # Try without token (for non-gated models)
            self.model = SentenceTransformer(self.model_name)
        
        print("Model loaded successfully.")

    def embed(self, texts: List[str], show_progress: bool = False) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed
            show_progress: Whether to show progress bar

        Returns:
            List of embedding vectors (each is a list of floats)
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")

        if not texts:
            return []

        # Batch encode
        embeddings = self.model.encode(
            texts, show_progress_bar=show_progress, convert_to_numpy=True
        )

        # Convert to list of lists
        return embeddings.tolist()

    def embed_single(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text string to embed

        Returns:
            Embedding vector as list of floats
        """
        return self.embed([text])[0]

    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model."""
        if self.model is None:
            raise RuntimeError("Model not loaded")
        # Get dimension by embedding a dummy text
        test_embedding = self.embed_single("test")
        return len(test_embedding)

