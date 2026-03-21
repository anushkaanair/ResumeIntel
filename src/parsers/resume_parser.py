"""Resume Parser — Extracts text from PDF and DOCX resume files."""

from __future__ import annotations

import io
from pathlib import Path
from typing import BinaryIO

import structlog

from src.exceptions import ParsingError

logger = structlog.get_logger()


class ResumeParser:
    """Parses resume files (PDF, DOCX, TXT) into plain text."""

    SUPPORTED_FORMATS = {".pdf", ".docx", ".doc", ".txt"}

    def parse(self, file: BinaryIO, filename: str) -> str:
        """Parse a resume file into plain text.

        Args:
            file: File-like binary object.
            filename: Original filename (used to determine format).

        Returns:
            Extracted text content.
        """
        ext = Path(filename).suffix.lower()
        if ext not in self.SUPPORTED_FORMATS:
            raise ParsingError(
                f"Unsupported format: {ext}",
                context={"supported": list(self.SUPPORTED_FORMATS)},
            )

        logger.info("resume_parser.parsing", filename=filename, format=ext)

        if ext == ".pdf":
            return self._parse_pdf(file)
        elif ext in (".docx", ".doc"):
            return self._parse_docx(file)
        elif ext == ".txt":
            return self._parse_txt(file)
        else:
            raise ParsingError(f"No parser for format: {ext}")

    def parse_text(self, text: str) -> str:
        """Parse raw text input (already extracted)."""
        cleaned = text.strip()
        if len(cleaned) < 50:
            raise ParsingError("Resume text too short (minimum 50 characters)")
        return cleaned

    def _parse_pdf(self, file: BinaryIO) -> str:
        """Extract text from PDF."""
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(file)
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n".join(pages).strip()

            if not text:
                raise ParsingError("No text extracted from PDF — may be image-based")

            logger.info("resume_parser.pdf_parsed", pages=len(reader.pages), chars=len(text))
            return text

        except ImportError:
            raise ParsingError("PyPDF2 not installed — cannot parse PDF")
        except Exception as e:
            raise ParsingError(f"PDF parsing failed: {e}")

    def _parse_docx(self, file: BinaryIO) -> str:
        """Extract text from DOCX."""
        try:
            from docx import Document

            doc = Document(file)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            text = "\n".join(paragraphs).strip()

            if not text:
                raise ParsingError("No text extracted from DOCX")

            logger.info("resume_parser.docx_parsed", paragraphs=len(paragraphs), chars=len(text))
            return text

        except ImportError:
            raise ParsingError("python-docx not installed — cannot parse DOCX")
        except Exception as e:
            raise ParsingError(f"DOCX parsing failed: {e}")

    def _parse_txt(self, file: BinaryIO) -> str:
        """Read plain text file."""
        content = file.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        return content.strip()
