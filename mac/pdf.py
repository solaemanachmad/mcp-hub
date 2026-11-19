"""PDF text extraction and overlapping sentence-friendly chunking."""

from __future__ import annotations

import io
from pypdf import PdfReader


def extract_text(pdf_bytes: bytes) -> tuple[str, int]:
    """Extract clean text and page count from raw PDF bytes."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    text = "\n\n".join(p for p in pages if p)
    return text, len(reader.pages)


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 180) -> list[str]:
    """Split text into overlapping chunks suitable for RAG embeddings."""
    clean = " ".join((text or "").split())
    if not clean:
        return []
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap.")

    chunks: list[str] = []
    start = 0
    total = len(clean)
    while start < total:
        end = min(total, start + chunk_size)
        if end < total:
            # Prefer breaking on a sentence or word boundary
            split_at = clean.rfind(". ", start + chunk_size // 2, end)
            if split_at == -1:
                split_at = clean.rfind(" ", start + chunk_size // 2, end)
            if split_at != -1:
                end = split_at + 1
        piece = clean[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= total:
            break
        start = max(0, end - overlap)
    return chunks
