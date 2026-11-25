"""Shared text chunking utilities for document ingestion."""
import re


def chunk(body: str, max_chars: int = 800) -> list[str]:
    """Pack paragraphs into chunks of at most max_chars (a single longer paragraph stays whole)."""
    chunks: list[str] = []
    for para in re.split(r"\n\s*\n", body):
        para = para.strip()
        if not para:
            continue
        if chunks and len(chunks[-1]) + len(para) < max_chars:
            chunks[-1] += "\n\n" + para
        else:
            chunks.append(para)
    return chunks
