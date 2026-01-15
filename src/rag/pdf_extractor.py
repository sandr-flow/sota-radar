"""PDF download and text extraction for arXiv papers."""

import io
import logging
from typing import Optional

import fitz  # PyMuPDF

from src.infrastructure.http_client import get_client

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Download and extract text from arXiv PDFs.
    
    Uses PyMuPDF (fitz) for fast and accurate text extraction.
    PDFs are processed in memory without temporary files.
    """

    async def download_pdf(self, pdf_url: str) -> bytes:
        """Download PDF from arXiv.
        
        Args:
            pdf_url: URL to the PDF file (e.g., https://arxiv.org/pdf/2301.12345.pdf).
            
        Returns:
            Raw PDF bytes.
            
        Raises:
            httpx.HTTPError: If download fails.
        """
        logger.info(f"Downloading PDF: {pdf_url}")
        client = get_client()
        response = await client.get(pdf_url, timeout=60.0, follow_redirects=True)
        response.raise_for_status()
        logger.info(f"Downloaded {len(response.content)} bytes")
        return response.content

    def extract_text(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF using PyMuPDF.
        
        Args:
            pdf_bytes: Raw PDF file content.
            
        Returns:
            Extracted text with preserved paragraph structure.
        """
        logger.info("Extracting text from PDF...")
        
        # Open PDF from memory
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        text_parts = []
        for page_num, page in enumerate(doc):
            # Extract text with layout preservation
            page_text = page.get_text("text")
            if page_text.strip():
                text_parts.append(page_text)
        
        doc.close()
        
        full_text = "\n\n".join(text_parts)
        logger.info(f"Extracted {len(full_text)} characters from {len(text_parts)} pages")
        
        return self._clean_text(full_text)

    def _clean_text(self, text: str) -> str:
        """Clean extracted text by removing artifacts.
        
        Args:
            text: Raw extracted text.
            
        Returns:
            Cleaned text.
        """
        # Remove excessive whitespace while preserving paragraph breaks
        lines = text.split("\n")
        cleaned_lines = []
        
        for line in lines:
            # Strip trailing whitespace
            line = line.rstrip()
            # Skip lines that are just page numbers or headers
            if line.strip().isdigit() and len(line.strip()) <= 3:
                continue
            cleaned_lines.append(line)
        
        # Join and normalize whitespace
        result = "\n".join(cleaned_lines)
        
        # Remove multiple consecutive blank lines
        while "\n\n\n" in result:
            result = result.replace("\n\n\n", "\n\n")
        
        return result.strip()

    async def download_and_extract(self, pdf_url: str) -> str:
        """Download PDF and extract text in one operation.
        
        Args:
            pdf_url: URL to the PDF file.
            
        Returns:
            Extracted text.
        """
        pdf_bytes = await self.download_pdf(pdf_url)
        return self.extract_text(pdf_bytes)
