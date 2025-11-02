# Natural Language Database

Database system for storing and retrieving Draw Steel TTRPG rules using semantic search.

MOST UP TO DATE DATABASE: `heroes-full-v1`

## Overview

This module provides:
- **Markdown Chunker**: Intelligently chunks markdown files respecting document structure
- **Embedding Model**: Local HuggingFace model (`google/embeddinggemma-300m`) for semantic embeddings
- **Qdrant Database**: Fast local vector database with hybrid search capabilities

## Components

### MarkdownChunker

Chunks markdown files while preserving:
- Paragraph boundaries
- List and table integrity
- Related content (e.g., Benefit/Drawback pairs)
- Page numbers from `[[Begin Page N]]` markers
- Section header hierarchy

**Usage:**
```python
from backend.database import MarkdownChunker

chunker = MarkdownChunker(target_tokens=600)
chunks = chunker.chunk_file(Path("content.md"))
```

### EmbeddingModel

Generates semantic embeddings using local HuggingFace model.

**Usage:**
```python
from backend.database import EmbeddingModel

model = EmbeddingModel()
embeddings = model.embed(["text 1", "text 2"])
```

### Database

Qdrant-based database for storing and searching chunks.

**Usage:**
```python
from backend.database import Database

# Initialize database
db = Database(collection_name="draw_steel_rules")

# Add chunks
db.add_chunks(chunks)

# Search
results = db.search("surprise round", limit=10)

# Test latency
stats = db.test_latency("surprise round", num_runs=10)
```

## CLI Usage

### Build Database

Process a markdown file and build the database:

```bash
uv run python -m backend.database.cli build --markdown-file backend/data/heroes/natural_language/pages_0260-0270_v2.md
```

Options:
- `--collection-name`: Name of collection (default: `draw_steel_natural_language`)
- `--target-tokens`: Target chunk size (default: 600)
- `--batch-size`: Batch size for embeddings (default: 32)

### Test Search

Test search functionality:

```bash
uv run python -m backend.database.cli search --query "surprise round" --limit 5
```

### Test Latency

Measure search latency:

```bash
uv run python -m backend.database.cli latency --query "surprise round" --num-runs 10
```

### Interactive Search

Interactive search mode with live latency display:

```bash
uv run python -m backend.database.cli interactive --limit 5
```

This will:
- Prompt you for queries using `input()`
- Display results immediately with latency in milliseconds
- Show page numbers, sections, and text previews
- Continue until you type `exit`, `quit`, or `q` (or Ctrl+C)

## Database Storage

Database files are stored in `backend/data/db_files/` (gitignored).

The database directory structure:
```
backend/data/db_files/
└── qdrant/
    └── [collection data]
```

## Example

```python
from pathlib import Path
from backend.database import MarkdownChunker, Database

# Chunk markdown file
chunker = MarkdownChunker(target_tokens=600)
chunks = chunker.chunk_file(Path("rules.md"))

# Build database
db = Database(collection_name="rules")
db.add_chunks(chunks)

# Search
results = db.search("combat mechanics", limit=5)
for result in results:
    print(f"Page {result['page']}: {result['text'][:100]}...")
    print(f"Score: {result['score']:.4f}\n")

# Test latency
stats = db.test_latency("combat mechanics")
print(f"Mean latency: {stats['mean_ms']:.2f} ms")
```

## Database Schema

Each chunk is stored with:
- `text`: Chunk content (markdown)
- `page`: Page number (from `[[Begin Page N]]` markers)
- `source`: Source file path
- `section`: List of section headers (hierarchy)
- `chunk_index`: Order within page
- `token_count`: Approximate token count

## Future Enhancements

- Add hybrid search with keyword matching (requires Qdrant sparse vectors)
- Support for structured data retrieval (abilities, monsters)
- PDF page linking functionality
- API endpoint for retrieval

