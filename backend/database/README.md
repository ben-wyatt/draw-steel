# Natural Language Database

Database system for storing and retrieving Draw Steel TTRPG rules using semantic search.

MOST UP TO DATE DATABASE: `heroes-full-v1`

**Note:** This codebase has been migrated from Qdrant to Weaviate. The `Database` class is now an alias for `WeaviateDatabase` for backward compatibility.

## Components

### Chunker

Processes JSON transcription files into semantic chunks for database storage. Filters image-only pages, splits content by markdown headers, and concatenates small chunks to meet minimum size requirements. Extracts structured blocks (abilities, monsters, items) using `[[Name|type]]` patterns and maintains metadata including page numbers, section hierarchies, and token counts.

**Usage:**
```python
from backend.database import chunk_json_dump, Chunk
import json

# Load JSON transcription file
with open("transcription.json") as f:
    json_dump = json.load(f)

# Chunk the data
chunks = chunk_json_dump(
    json_dump=json_dump,
    source_book="heroes",
    min_char_len=1000
)
```

Each chunk contains:
 - text: Chunk content (markdown)
 - page: Page number
 - source_book: Source book identifier
 - ability_blocks: List of ability references
 - monster_blocks: List of monster block references
 - item_blocks: List of item references
 - section: List of section headers (hierarchy)
 - chunk_index: Order within page
 - token_count: Estimated token count


### EmbeddingModel

Generates semantic embeddings using local `gemma-300m`

**Usage:**
```python
from backend.database import EmbeddingModel

model = EmbeddingModel()
embeddings = model.embed(["text 1", "text 2"])
```

### Database

Weaviate-based database for storing and searching chunks.

Uses Weaviate v4 client API. By default, connects to a local Weaviate instance running on `http://localhost:8080` (typically via Docker). Can also use embedded Weaviate or connect to remote instances.

**Usage:**
```python
from backend.database import Database, WeaviateDatabase

# Initialize database (connects to local Weaviate by default)
db = Database(collection_name="draw_steel_rules")
# Or explicitly use WeaviateDatabase
db = WeaviateDatabase(collection_name="draw_steel_rules")

# Add chunks
db.add_chunks(chunks)

# Search (hybrid search by default)
results = db.search("surprise round", limit=10)

# Test latency
stats = db.test_latency("surprise round", num_runs=10)

# List all collections
from backend.database import list_collections
collections = list_collections()
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

### Usage


```bash
# single search
uv run python -m backend.database.cli search --query "surprise round" --limit 5

# latency
uv run python -m backend.database.cli latency --query "surprise round" --num-runs 10

# interactive search
uv run python -m backend.database.cli interactive --limit 5
```






## Future Enhancements

- Add hybrid search with keyword matching (requires Qdrant sparse vectors)
- Support for structured data retrieval (abilities, monsters)
- PDF page linking functionality
- API endpoint for retrieval

