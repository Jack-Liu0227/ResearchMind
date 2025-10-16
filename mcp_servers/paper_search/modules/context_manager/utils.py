"""
Data Layer Utilities
Helper functions for data processing.
"""

from typing import List


def chunk_text(text: str, max_chunk_bytes: int = 25000, min_chunk_chars: int = 200) -> List[str]:
    """
    Split text into chunks that fit within byte limit.

    Args:
        text: Input text to chunk
        max_chunk_bytes: Maximum bytes per chunk (default: 25000)
        min_chunk_chars: Minimum characters per chunk (default: 200)

    Returns:
        List of text chunks
    """
    chunks = []

    # First split by paragraphs
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

    current_chunk = ""
    current_bytes = 0

    for para in paragraphs:
        para_bytes = len(para.encode('utf-8'))

        # If single paragraph exceeds limit, split it further
        if para_bytes > max_chunk_bytes:
            # Save current chunk if exists
            if current_chunk and len(current_chunk) >= min_chunk_chars:
                chunks.append(current_chunk)
                current_chunk = ""
                current_bytes = 0

            # Split long paragraph by sentences
            sentences = para.replace('! ', '!|').replace('? ', '?|').replace('. ', '.|').split('|')
            for sent in sentences:
                sent = sent.strip()
                if not sent:
                    continue

                sent_bytes = len(sent.encode('utf-8'))

                # If adding this sentence exceeds limit, save current chunk
                if current_bytes + sent_bytes > max_chunk_bytes:
                    if current_chunk and len(current_chunk) >= min_chunk_chars:
                        chunks.append(current_chunk)
                    current_chunk = sent
                    current_bytes = sent_bytes
                else:
                    current_chunk += (" " + sent if current_chunk else sent)
                    current_bytes += sent_bytes
        else:
            # If adding this paragraph exceeds limit, save current chunk
            if current_bytes + para_bytes > max_chunk_bytes:
                if current_chunk and len(current_chunk) >= min_chunk_chars:
                    chunks.append(current_chunk)
                current_chunk = para
                current_bytes = para_bytes
            else:
                current_chunk += ("\n\n" + para if current_chunk else para)
                current_bytes += para_bytes

    # Add remaining chunk
    if current_chunk and len(current_chunk) >= min_chunk_chars:
        chunks.append(current_chunk)

    return chunks

