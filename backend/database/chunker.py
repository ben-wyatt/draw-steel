"""
Markdown chunker that respects document structure.

Chunks markdown files intelligently, preserving paragraph boundaries,
keeping related content together, and tracking page numbers and section headers.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import tiktoken


@dataclass
class Chunk:
    """Represents a chunk of text with metadata."""

    text: str
    page: Optional[int]
    source: str
    section: List[str]  # Header hierarchy
    chunk_index: int
    token_count: int


class MarkdownChunker:
    """
    Intelligently chunks markdown files respecting document structure.

    Chunking strategy:
    - Target size: ~500-800 tokens (configurable)
    - Never break within paragraphs, lists, or tables
    - Prefer breaking at headers (##, ###)
    - Keep related content together (e.g., Benefit/Drawback pairs)
    - Preserve markdown formatting
    """

    def __init__(
        self,
        target_tokens: int = 600,
        min_tokens: int = 200,
        max_tokens: int = 1000,
        encoding_name: str = "cl100k_base",
    ):
        """
        Initialize chunker.

        Args:
            target_tokens: Target chunk size in tokens
            min_tokens: Minimum chunk size (only break if exceeded)
            max_tokens: Maximum chunk size (force break if exceeded)
            encoding_name: Tiktoken encoding to use
        """
        self.target_tokens = target_tokens
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self.encoding = tiktoken.get_encoding(encoding_name)

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.encoding.encode(text))

    def parse_page_marker(self, line: str) -> Optional[int]:
        """Extract page number from [[Begin Page N]] marker."""
        match = re.match(r"\[\[Begin Page (\d+)\]\]", line.strip())
        if match:
            return int(match.group(1))
        return None

    def is_header(self, line: str) -> tuple[bool, int, str]:
        """
        Check if line is a header and return level and text.

        Returns:
            (is_header, level, text) where level is 1-6, text is header text
        """
        line = line.rstrip()
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            return True, level, text
        return False, 0, ""

    def is_list_item(self, line: str) -> bool:
        """Check if line is a list item."""
        stripped = line.strip()
        return bool(re.match(r"^[-*+]\s+", stripped)) or bool(
            re.match(r"^\d+\.\s+", stripped)
        )

    def is_table_row(self, line: str) -> bool:
        """Check if line is a table row."""
        stripped = line.strip()
        return bool(re.match(r"^\|.+\|$", stripped))

    def is_empty(self, line: str) -> bool:
        """Check if line is empty or whitespace."""
        return not line.strip()

    def should_keep_together(self, prev_lines: List[str], next_line: str) -> bool:
        """
        Determine if next_line should be kept with previous lines.

        Keeps together:
        - Benefit/Drawback pairs
        - List items in same list
        - Table rows
        - Paragraphs that are part of same section
        """
        if not prev_lines:
            return False

        # Check if previous block ends with Benefit: or Drawback:
        last_line = prev_lines[-1].strip()
        if last_line.startswith("**Benefit:**") or last_line.startswith(
            "**Drawback:**"
        ):
            # Keep next line if it's a continuation or related content
            next_stripped = next_line.strip()
            if (
                not self.is_header(next_line)
                and not self.is_empty(next_line)
                and not next_stripped.startswith("**Benefit:**")
                and not next_stripped.startswith("**Drawback:**")
            ):
                return True

        # Keep list items together
        if self.is_list_item(prev_lines[-1]) and self.is_list_item(next_line):
            return True

        # Keep table rows together
        if self.is_table_row(prev_lines[-1]) and self.is_table_row(next_line):
            return True

        return False

    def chunk_markdown(self, markdown_text: str, source: str = "") -> List[Chunk]:
        """
        Chunk markdown text respecting structure.

        Args:
            markdown_text: Full markdown text to chunk
            source: Source file path or identifier

        Returns:
            List of Chunk objects
        """
        lines = markdown_text.split("\n")
        chunks: List[Chunk] = []
        current_chunk_lines: List[str] = []
        current_page: Optional[int] = None
        current_section: List[str] = []  # Header hierarchy
        chunk_index = 0
        page_chunk_index = 0

        i = 0
        while i < len(lines):
            line = lines[i]

            # Check for page marker
            page_num = self.parse_page_marker(line)
            if page_num is not None:
                # Save current chunk if it has content
                if current_chunk_lines:
                    chunk_text = "\n".join(current_chunk_lines).strip()
                    if chunk_text:
                        token_count = self.count_tokens(chunk_text)
                        chunks.append(
                            Chunk(
                                text=chunk_text,
                                page=current_page,
                                source=source,
                                section=current_section.copy(),
                                chunk_index=page_chunk_index,
                                token_count=token_count,
                            )
                        )
                        page_chunk_index += 1
                    current_chunk_lines = []

                current_page = page_num
                page_chunk_index = 0
                i += 1
                continue

            # Check for header
            is_header, header_level, header_text = self.is_header(line)
            if is_header:
                # Check if we should break before this header
                if current_chunk_lines:
                    chunk_text = "\n".join(current_chunk_lines).strip()
                    token_count = self.count_tokens(chunk_text)

                    # If current chunk is large enough, break before header
                    if token_count >= self.min_tokens:
                        chunks.append(
                            Chunk(
                                text=chunk_text,
                                page=current_page,
                                source=source,
                                section=current_section.copy(),
                                chunk_index=page_chunk_index,
                                token_count=token_count,
                            )
                        )
                        page_chunk_index += 1
                        current_chunk_lines = []

                # Update section hierarchy
                # Truncate to current level, then add new header
                current_section = current_section[: header_level - 1]
                current_section.append(header_text)

            # Add line to current chunk
            current_chunk_lines.append(line)

            # Check if we need to break
            chunk_text = "\n".join(current_chunk_lines).strip()
            token_count = self.count_tokens(chunk_text)

            # Force break if exceeds max_tokens
            if token_count > self.max_tokens:
                # Try to break at a good point
                # Find last header or paragraph boundary
                break_point = len(current_chunk_lines)
                for j in range(len(current_chunk_lines) - 1, 0, -1):
                    test_chunk = "\n".join(current_chunk_lines[:j]).strip()
                    test_tokens = self.count_tokens(test_chunk)
                    if test_tokens >= self.min_tokens:
                        # Check if this is a good break point
                        if j < len(current_chunk_lines) - 1:
                            # Check if next line is header or empty
                            next_line = (
                                current_chunk_lines[j]
                                if j < len(current_chunk_lines)
                                else ""
                            )
                            if self.is_empty(next_line) or self.is_header(next_line):
                                break_point = j
                                break

                # Extract chunk up to break point
                chunk_text = "\n".join(current_chunk_lines[:break_point]).strip()
                if chunk_text:
                    token_count = self.count_tokens(chunk_text)
                    chunks.append(
                        Chunk(
                            text=chunk_text,
                            page=current_page,
                            source=source,
                            section=current_section.copy(),
                            chunk_index=page_chunk_index,
                            token_count=token_count,
                        )
                    )
                    page_chunk_index += 1

                # Keep remaining lines
                current_chunk_lines = current_chunk_lines[break_point:]
                # Skip empty lines at start
                while current_chunk_lines and self.is_empty(current_chunk_lines[0]):
                    current_chunk_lines.pop(0)

            # Check if we should break after this line
            elif token_count >= self.target_tokens:
                # Look ahead to see if next line is a good break point
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    # Break if next line is header or empty (end of paragraph)
                    if self.is_header(next_line) or self.is_empty(next_line):
                        # Don't break if we should keep together
                        if not self.should_keep_together(
                            current_chunk_lines, next_line
                        ):
                            chunks.append(
                                Chunk(
                                    text=chunk_text,
                                    page=current_page,
                                    source=source,
                                    section=current_section.copy(),
                                    chunk_index=page_chunk_index,
                                    token_count=token_count,
                                )
                            )
                            page_chunk_index += 1
                            current_chunk_lines = []

            i += 1

        # Add final chunk
        if current_chunk_lines:
            chunk_text = "\n".join(current_chunk_lines).strip()
            if chunk_text:
                token_count = self.count_tokens(chunk_text)
                chunks.append(
                    Chunk(
                        text=chunk_text,
                        page=current_page,
                        source=source,
                        section=current_section.copy(),
                        chunk_index=page_chunk_index,
                        token_count=token_count,
                    )
                )

        return chunks

    def chunk_file(self, file_path: Path) -> List[Chunk]:
        """
        Chunk a markdown file.

        Args:
            file_path: Path to markdown file

        Returns:
            List of Chunk objects
        """
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        source = str(file_path)
        return self.chunk_markdown(content, source=source)
