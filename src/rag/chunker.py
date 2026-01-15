"""Semantic text chunking for RAG pipeline."""

import re
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """A text chunk with metadata."""
    
    text: str
    index: int
    start_char: int
    end_char: int


class SemanticChunker:
    """Split text into semantic chunks based on document structure.
    
    Uses paragraph and section boundaries for more meaningful chunks.
    Falls back to sentence-based splitting for long paragraphs.
    """

    def __init__(
        self,
        max_chunk_size: int = 512,
        min_chunk_size: int = 100,
        overlap_sentences: int = 1,
    ):
        """Initialize semantic chunker.
        
        Args:
            max_chunk_size: Maximum chunk size in characters.
            min_chunk_size: Minimum chunk size (smaller chunks merged with neighbors).
            overlap_sentences: Number of sentences to overlap between chunks.
        """
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap_sentences = overlap_sentences
        
        # Patterns for section detection
        self.section_patterns = [
            r"^(?:Abstract|Introduction|Related Work|Background|Method|Methodology|"
            r"Approach|Experiments?|Results?|Discussion|Conclusion|References|"
            r"Appendix|Acknowledgements?)[\s:]*$",
            r"^\d+\.?\s+[A-Z]",  # Numbered sections like "1. Introduction"
            r"^[A-Z][A-Z\s]+$",  # ALL CAPS headers
        ]
        self.section_regex = re.compile(
            "|".join(self.section_patterns), 
            re.IGNORECASE | re.MULTILINE
        )

    def chunk_text(self, text: str) -> list[Chunk]:
        """Split text into semantic chunks.
        
        Args:
            text: Full document text.
            
        Returns:
            List of Chunk objects with text and metadata.
        """
        logger.info(f"Chunking text of {len(text)} characters...")
        
        # First, split by sections
        sections = self._split_by_sections(text)
        
        # Then process each section
        chunks = []
        char_offset = 0
        
        for section in sections:
            section_chunks = self._chunk_section(section, len(chunks), char_offset)
            chunks.extend(section_chunks)
            char_offset += len(section)
        
        # Apply overlap between chunks
        if self.overlap_sentences > 0:
            chunks = self._add_overlap(chunks)
        
        logger.info(f"Created {len(chunks)} chunks")
        return chunks

    def _split_by_sections(self, text: str) -> list[str]:
        """Split text by section headers.
        
        Args:
            text: Full document text.
            
        Returns:
            List of section texts.
        """
        # Find all section boundaries
        matches = list(self.section_regex.finditer(text))
        
        if not matches:
            # No sections found, treat as single section
            return [text]
        
        sections = []
        prev_end = 0
        
        for match in matches:
            # Add text before this section header
            if match.start() > prev_end:
                section_text = text[prev_end:match.start()].strip()
                if section_text:
                    sections.append(section_text)
            prev_end = match.start()
        
        # Add remaining text
        if prev_end < len(text):
            section_text = text[prev_end:].strip()
            if section_text:
                sections.append(section_text)
        
        return sections if sections else [text]

    def _chunk_section(
        self, 
        section: str, 
        start_index: int,
        char_offset: int
    ) -> list[Chunk]:
        """Chunk a single section.
        
        Args:
            section: Section text.
            start_index: Starting chunk index.
            char_offset: Character offset in original text.
            
        Returns:
            List of chunks from this section.
        """
        # Split by paragraphs first
        paragraphs = self._split_paragraphs(section)
        
        chunks = []
        current_chunk = ""
        current_start = char_offset
        chunk_index = start_index
        
        for para in paragraphs:
            # Check if adding this paragraph exceeds max size
            if len(current_chunk) + len(para) + 2 > self.max_chunk_size:
                # Save current chunk if large enough
                if len(current_chunk) >= self.min_chunk_size:
                    chunks.append(Chunk(
                        text=current_chunk.strip(),
                        index=chunk_index,
                        start_char=current_start,
                        end_char=current_start + len(current_chunk)
                    ))
                    chunk_index += 1
                    current_start += len(current_chunk)
                    current_chunk = ""
                
                # Handle paragraphs that are too long
                if len(para) > self.max_chunk_size:
                    # Split by sentences
                    sentence_chunks = self._split_long_paragraph(
                        para, chunk_index, current_start
                    )
                    chunks.extend(sentence_chunks)
                    chunk_index += len(sentence_chunks)
                    current_start += len(para)
                    continue
            
            # Add paragraph to current chunk
            if current_chunk:
                current_chunk += "\n\n"
            current_chunk += para
        
        # Don't forget the last chunk
        if current_chunk.strip() and len(current_chunk) >= self.min_chunk_size:
            chunks.append(Chunk(
                text=current_chunk.strip(),
                index=chunk_index,
                start_char=current_start,
                end_char=current_start + len(current_chunk)
            ))
        elif current_chunk.strip() and chunks:
            # Merge small trailing chunk with previous
            last = chunks[-1]
            chunks[-1] = Chunk(
                text=last.text + "\n\n" + current_chunk.strip(),
                index=last.index,
                start_char=last.start_char,
                end_char=current_start + len(current_chunk)
            )
        
        return chunks

    def _split_paragraphs(self, text: str) -> list[str]:
        """Split text into paragraphs.
        
        Args:
            text: Text to split.
            
        Returns:
            List of paragraph strings.
        """
        # Split by double newlines or more
        paragraphs = re.split(r"\n\s*\n", text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _split_long_paragraph(
        self, 
        paragraph: str, 
        start_index: int,
        char_offset: int
    ) -> list[Chunk]:
        """Split a long paragraph by sentences.
        
        Args:
            paragraph: Long paragraph text.
            start_index: Starting chunk index.
            char_offset: Character offset in original text.
            
        Returns:
            List of chunks.
        """
        # Simple sentence splitting
        sentences = re.split(r"(?<=[.!?])\s+", paragraph)
        
        chunks = []
        current_chunk = ""
        current_start = char_offset
        chunk_index = start_index
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 > self.max_chunk_size:
                if current_chunk.strip():
                    chunks.append(Chunk(
                        text=current_chunk.strip(),
                        index=chunk_index,
                        start_char=current_start,
                        end_char=current_start + len(current_chunk)
                    ))
                    chunk_index += 1
                    current_start += len(current_chunk)
                    current_chunk = ""
            
            if current_chunk:
                current_chunk += " "
            current_chunk += sentence
        
        if current_chunk.strip():
            chunks.append(Chunk(
                text=current_chunk.strip(),
                index=chunk_index,
                start_char=current_start,
                end_char=current_start + len(current_chunk)
            ))
        
        return chunks

    def _add_overlap(self, chunks: list[Chunk]) -> list[Chunk]:
        """Add sentence overlap between consecutive chunks.
        
        Args:
            chunks: List of chunks without overlap.
            
        Returns:
            List of chunks with overlap added.
        """
        if len(chunks) <= 1:
            return chunks
        
        overlapped = [chunks[0]]
        
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            curr_chunk = chunks[i]
            
            # Get last N sentences from previous chunk
            prev_sentences = re.split(r"(?<=[.!?])\s+", prev_chunk.text)
            overlap_text = " ".join(prev_sentences[-self.overlap_sentences:])
            
            # Prepend to current chunk
            new_text = overlap_text + " " + curr_chunk.text
            overlapped.append(Chunk(
                text=new_text,
                index=curr_chunk.index,
                start_char=curr_chunk.start_char,
                end_char=curr_chunk.end_char
            ))
        
        return overlapped

    def get_chunk_texts(self, text: str) -> list[str]:
        """Convenience method to get just the text of chunks.
        
        Args:
            text: Full document text.
            
        Returns:
            List of chunk text strings.
        """
        chunks = self.chunk_text(text)
        return [c.text for c in chunks]
