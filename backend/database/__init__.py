"""Natural language database system for Draw Steel TTRPG rules retrieval."""

from backend.database.chunker import Chunk, chunk_json_dump, construct_chunk
from backend.database.embeddings import EmbeddingModel
from backend.database.weaviate_db import WeaviateDatabase, list_collections

# For backward compatibility, alias WeaviateDatabase as Database
Database = WeaviateDatabase

__all__ = [
    "Chunk",
    "chunk_json_dump",
    "construct_chunk",
    "Database",
    "WeaviateDatabase",
    "EmbeddingModel",
    "list_collections",
]
