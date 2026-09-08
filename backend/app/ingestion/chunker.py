from dataclasses import dataclass, field
from typing import Any, Dict, List
from app.ingestion.parsers import ParsedPage


@dataclass
class DocumentChunk:
    chunk_index: int
    content: str
    page_number: int
    token_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class SemanticChunker:
    """
    Intelligent text chunker splitting documents into semantically coherent
    segments with sliding overlap, preserving document and page provenance.
    """

    def __init__(self, target_chunk_size: int = 600, overlap_chars: int = 80):
        self.target_chunk_size = target_chunk_size
        self.overlap_chars = overlap_chars

    def chunk_pages(self, pages: List[ParsedPage]) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        global_index = 0

        for page in pages:
            text = page.text.strip()
            if not text:
                continue

            # Split text by double newlines (paragraphs), or sentences if paragraph is large
            raw_paragraphs = text.split("\n\n")
            paragraphs = []
            for p in raw_paragraphs:
                p = p.strip()
                if not p:
                    continue
                if len(p) > self.target_chunk_size:
                    # Split on sentence boundaries
                    sentences = [s.strip() for s in p.replace(". ", ".\n").split("\n") if s.strip()]
                    paragraphs.extend(sentences)
                else:
                    paragraphs.append(p)

            current_buffer = []
            current_len = 0

            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue

                if current_len + len(para) > self.target_chunk_size and current_buffer:
                    chunk_text = "\n\n".join(current_buffer)
                    approx_tokens = max(1, len(chunk_text) // 4)
                    chunks.append(
                        DocumentChunk(
                            chunk_index=global_index,
                            content=chunk_text,
                            page_number=page.page_number,
                            token_count=approx_tokens,
                            metadata={**page.metadata, "char_length": len(chunk_text)},
                        )
                    )
                    global_index += 1

                    # Retain last paragraph for contextual overlap if small
                    if len(current_buffer[-1]) <= self.overlap_chars * 2:
                        current_buffer = [current_buffer[-1], para]
                        current_len = len(current_buffer[0]) + len(para)
                    else:
                        current_buffer = [para]
                        current_len = len(para)
                else:
                    current_buffer.append(para)
                    current_len += len(para)

            if current_buffer:
                chunk_text = "\n\n".join(current_buffer)
                approx_tokens = max(1, len(chunk_text) // 4)
                chunks.append(
                    DocumentChunk(
                        chunk_index=global_index,
                        content=chunk_text,
                        page_number=page.page_number,
                        token_count=approx_tokens,
                        metadata={**page.metadata, "char_length": len(chunk_text)},
                    )
                )
                global_index += 1

        return chunks
