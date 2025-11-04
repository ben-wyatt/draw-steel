# Chunking Strategy Analysis Summary

## Overview

Analysis of chunking strategy for `all_pages_v1.md` (Delian Tomb adventure) using the current `MarkdownChunker` with `target_tokens=600`.

## Key Findings

### Chunk Size Distribution

- **Total chunks**: 186
- **Total pages**: 70
- **Mean chunk size**: 262.7 tokens (significantly below target of 600)
- **Median chunk size**: 246 tokens
- **Size range**: 31 - 613 tokens
- **Standard deviation**: 118 tokens

**Percentiles**:
- P25: 206 tokens
- P75: 309 tokens
- P90: 415 tokens
- P95: 518 tokens

### Why Chunks Are Smaller Than Target

The chunker is **correctly prioritizing document structure over size**. When it encounters a header after reaching `min_tokens` (200), it breaks the chunk to maintain semantic coherence. This is actually **good behavior** for retrieval quality.

The analysis shows that increasing `target_tokens` beyond 600 has no effect - chunks are still breaking at ~260 tokens on average because the document structure (headers) takes precedence.

### Boundary Quality

- **90.9%** of chunks start with headers (excellent!)
- **0%** end with headers (chunks contain content after headers)
- **4.3%** start mid-paragraph (very low - good)
- **26.9%** end mid-paragraph (but these are mostly valid breaks at list items, after punctuation, or before headers)

### Chunks Per Page

- **Mean**: 2.7 chunks/page
- **Median**: 3 chunks/page
- **Range**: 1-5 chunks/page
- **22 pages** have only 1 chunk (likely short pages or single cohesive sections)
- **0 pages** have >5 chunks

### Problematic Chunks

- **39 small chunks** (< 200 tokens, 21% of total)
  - Many are legitimate short sections (e.g., page titles, brief subsections)
  - Some may benefit from merging with adjacent chunks for better context
- **0 large chunks** (> 1000 tokens)
  - Max chunk size is 613 tokens - well within reasonable limits

## Semantic Coherence Assessment

### Strengths

1. **Excellent header alignment**: 90.9% of chunks start with headers, ensuring clear topic boundaries
2. **Structure preservation**: Chunks respect document hierarchy and section boundaries
3. **No oversized chunks**: Maximum chunk size (613 tokens) is reasonable for retrieval
4. **Consistent breaking**: Chunks break at logical points (headers, empty lines)

### Areas for Improvement

1. **Small chunks**: 21% of chunks are < 200 tokens. While many are legitimate short sections, some could potentially be merged for better context in retrieval.

2. **End-of-chunk boundaries**: Some chunks end in ways that might split related content:
   - List items that span multiple lines
   - Test outcomes that are part of larger descriptions
   - However, inspection shows most "mid-paragraph" breaks are actually at valid points

## Comparison Across Configurations

Testing different `target_tokens` values shows:

| Target Tokens | Total Chunks | Mean Tokens | Median Tokens | Small Chunks |
|---------------|--------------|-------------|---------------|--------------|
| 400           | 192          | 254.5       | 246           | 40           |
| 600           | 186          | 262.7       | 246           | 39           |
| 800           | 186          | 262.7       | 246           | 39           |
| 1000          | 186          | 262.7       | 246           | 39           |

**Key Insight**: Changing `target_tokens` beyond 400 has minimal effect because the chunker prioritizes structure over size. The document naturally breaks into ~260 token chunks due to header frequency.

## Recommendations

### 1. Current Strategy is Generally Good

The chunker is working as designed - prioritizing semantic coherence (headers) over strict size targets. This is **appropriate** for adventure/module content where sections are meaningful units.

### 2. Consider Adjusting `min_tokens`

- **Current**: `min_tokens=200`
- **Consider**: Reducing to `min_tokens=150` or `min_tokens=100` to allow more aggressive merging of very short sections
- **Trade-off**: Fewer very small chunks vs. potentially less granular retrieval

### 3. Consider `target_tokens` Reduction

- **Current**: `target_tokens=600` (not being reached anyway)
- **Consider**: Set to `target_tokens=300` to better match actual output (~260 tokens mean)
- **Rationale**: Aligns expectations with actual behavior, though it won't change output significantly

### 4. Optional: Merge Very Small Chunks

For chunks < 150 tokens that don't start with a major header (H1/H2), consider merging with adjacent chunks if combined size < `max_tokens`.

### 5. No Changes Needed for `max_tokens`

- **Current**: `max_tokens=1000`
- **Status**: Appropriate - no chunks exceed this, and max is 613 tokens

## Sample Chunk Quality

### Good Examples

**Page 15, Chunk 1 (542 tokens)** - "Minions" section:
- Starts with header
- Contains complete concept (minions, squads, shared stamina)
- Good semantic coherence
- Appropriate size for retrieval

**Page 7, Chunk 1 (516 tokens)** - "A Mother's Plea":
- Complete narrative section
- Contains all related dialogue and context
- Good for answering questions about this scene

### Areas to Review

**Page 1, Chunk 1 (53 tokens)** - Title page:
- Very short but semantically complete
- Could potentially be merged with next chunk, but standalone is also fine

**Small chunks (< 200 tokens)**:
- Most are legitimate short sections
- Review specific cases where context might be lost

## Conclusion

The current chunking strategy is **functioning well** for this type of content. The chunker correctly prioritizes document structure over strict size targets, resulting in semantically coherent chunks that align with section boundaries.

**Primary recommendation**: Consider reducing `min_tokens` from 200 to 100-150 to allow more aggressive merging of very short sections, potentially reducing the 21% of small chunks while maintaining semantic coherence.

**Secondary recommendation**: Adjust `target_tokens` to 300 to align with actual output, though this is primarily for clarity/documentation as it won't significantly change behavior.

The strategy respects document structure well and produces chunks suitable for semantic search retrieval.

