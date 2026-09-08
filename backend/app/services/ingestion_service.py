import uuid
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import EntityNotFoundError
from app.ingestion.chunker import SemanticChunker
from app.ingestion.embeddings import embedding_engine
from app.ingestion.parsers import parse_document
from app.models.file import FileChunk
from app.repositories.file_repository import FileRepository
from app.schemas.file import FileChunkCreateDTO, FileChunkResponseDTO, VectorFilterDTO


class IngestionService:
    """
    Ingestion Service dedicated to text extraction, chunking,
    vector embedding generation, and semantic retrieval.
    Decoupled from core File business lifecycle management.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.file_repo = FileRepository(session)

    async def ingest_document(
        self,
        file_id: uuid.UUID,
        content: bytes,
        filename: str,
        mime_type: Optional[str] = None,
    ) -> List[FileChunkResponseDTO]:
        """
        Full end-to-end multi-modal ingestion pipeline:
        1. Multi-modal parsing (PDF, DOCX, XLSX, CSV, TXT)
        2. Semantic chunking with page and provenance metadata
        3. High-dimensional vector embedding generation
        4. Bulk insertion into pgvector file_chunks table
        """
        pages = parse_document(content, filename, mime_type)
        chunker = SemanticChunker()
        doc_chunks = chunker.chunk_pages(pages)

        chunks_data: List[FileChunkCreateDTO] = []
        for c in doc_chunks:
            embedding = embedding_engine.embed_text(c.content)
            chunks_data.append(
                FileChunkCreateDTO(
                    file_id=file_id,
                    chunk_index=c.chunk_index,
                    content=c.content,
                    page_number=c.page_number,
                    token_count=c.token_count,
                    embedding=embedding,
                    metadata=c.metadata,
                )
            )

        return await self.ingest_chunks(file_id, chunks_data)

    async def ingest_chunks(
        self,
        file_id: uuid.UUID,
        chunks_data: List[FileChunkCreateDTO],
    ) -> List[FileChunkResponseDTO]:
        file_obj = await self.file_repo.get_by_id(file_id)
        if not file_obj:
            raise EntityNotFoundError("File", file_id)

        # Transition status to chunking / embedding
        file_obj.status = "embedding"
        await self.file_repo.update(file_obj)

        chunk_models = [
            FileChunk(
                file_id=file_id,
                chunk_index=item.chunk_index,
                content=item.content,
                page_number=item.page_number,
                token_count=item.token_count,
                embedding=item.embedding,
                metadata_=item.metadata or {},
            )
            for item in chunks_data
        ]

        inserted = await self.file_repo.create_chunks(chunk_models)

        # Mark file as ready
        file_obj.status = "ready"
        file_obj.page_count = max([c.page_number or 1 for c in chunks_data], default=1)
        await self.file_repo.update(file_obj)

        return [FileChunkResponseDTO.model_validate(c) for c in inserted]

    async def search_evidence(
        self,
        filters: VectorFilterDTO,
        query_vector: List[float],
    ) -> List[Tuple[FileChunkResponseDTO, float]]:
        """Performs vector search with rich metadata filtering across project documents."""
        results = await self.file_repo.similarity_search(filters, query_vector)
        return [(FileChunkResponseDTO.model_validate(chunk), score) for chunk, score in results]
