# Image Parsing

This directory contains tools for parsing structured data from PDF images using vision models.

## Directory Structure

- **`stat-blocks/`**: Parses monster stat block images from the PDFs using vision models (GPT-5 via OpenRouter) to extract structured Monster data including stats, defenses, abilities, and traits.
- **`whole-image-parsing/`**: Converts entire PDF pages to images and can process them with vision models.

## PDF to Image Conversion

The `whole-image-parsing/pdf-to-page-image.py` script converts PDF pages to PNG images for vision model processing.

### Usage

```bash
# Convert a single page
uv run python pdf-parsing/image-parsing/whole-image-parsing/pdf-to-page-image.py --page 1

# Convert a page range
uv run python pdf-parsing/image-parsing/whole-image-parsing/pdf-to-page-image.py --start-page 1 --end-page 10

# Convert all pages
uv run python pdf-parsing/image-parsing/whole-image-parsing/pdf-to-page-image.py
```

### Options

- `--pdf`: Path to PDF file (default: local `pdf/Draw_Steel_Heroes_v1.pdf`)
- `--page`: Single page number to convert (1-indexed)
- `--start-page` / `--end-page`: Page range (1-indexed, inclusive)
- `--output-dir`: Output directory (default: `images/` relative to script)
- `--dpi`: Resolution in DPI (default: 150)

### Output

- Images are saved as `page_0001.png`, `page_0002.png`, etc. in the `images/` directory
- Each page image is approximately 1238×1632 pixels (at 150 DPI)
- Average file size: ~0.89MB per page

## Vision Model Cost Estimation

### Image Specifications

- **Dimensions**: 1238×1632 pixels
- **Tiles**: 12 tiles (3×4 tiles of 512×512)
- **Image tokens**: 2,125 tokens (85 base + 12×170 per tile)
- **Text prompt tokens**: ~50 tokens
- **Total input tokens**: ~2,175 tokens
- **Output tokens**: 200-500 tokens (estimated average: 350 for structured JSON)

### Cost per Page (USD)

| Model | Input Cost | Total Cost (min) | Total Cost (avg) | Total Cost (max) |
|-------|------------|------------------|------------------|------------------|
| **GPT-5 Standard** | $0.0027 | $0.0047 | **$0.0062** | $0.0077 |
| **GPT-5 Mini** | $0.0005 | $0.0009 | **$0.0012** | $0.0015 |
| **GPT-5 Nano** | $0.0001 | $0.0002 | **$0.0002** | $0.0003 |
| **GPT-5 Pro** | $0.0326 | $0.0566 | **$0.0746** | $0.0926 |

### Total Cost for All 417 Pages (using average output)

- **GPT-5 Standard**: $2.59
- **GPT-5 Mini**: $0.52 ⭐ (recommended for cost/quality balance)
- **GPT-5 Nano**: $0.10 (cheapest, but may have lower accuracy)
- **GPT-5 Pro**: $31.12

### Notes

- Image tokens calculated using OpenAI vision formula:
  - Base: 85 tokens + (12 tiles × 170 tokens/tile) = 2,125 tokens
- Output tokens vary based on response complexity
- Actual costs may vary based on:
  - Actual response length
  - Model availability and pricing changes
  - OpenRouter pricing (if different from OpenAI direct)

### Pricing Sources

- GPT-5 pricing: $1.25/$10.00 per million tokens (input/output) for Standard
- GPT-5 Mini: $0.25/$2.00 per million tokens
- GPT-5 Nano: $0.05/$0.40 per million tokens
- GPT-5 Pro: $15.00/$120.00 per million tokens

## Base64 Encoding Utility

The `pdf-to-page-image.py` script includes an `encode_image()` function for converting images to base64 format for vision model API calls:

```python
from pdf_to_page_image import encode_image

image_path = Path("images/page_0001.png")
base64_image = encode_image(image_path)
```

This matches the pattern used in `stat-blocks/parse_image.py` for OpenRouter API integration.

