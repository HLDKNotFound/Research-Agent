import math
import uuid
from typing import Any, List, Optional, Sequence, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.file import File, FileChunk
from app.repositories.base import BaseRepository
from app.schemas.common import PaginationParams
from app.schemas.file import VectorFilterDTO


class FileRepository(BaseRepository[File]):
    def __init__(self, session: AsyncSession):
        super().__init__(File, session)

    async def list_by_project(
        self,
        project_id: uuid.UUID,
        params: Optional[PaginationParams] = None,
        status: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> Sequence[File]:
        query = (
            select(File)
            .where(
                File.project_id == project_id,
                File.deleted_at.is_(None),
            )
            .order_by(File.created_at.desc())
        )
        if status:
            query = query.where(File.status == status)
        if mime_type:
            query = query.where(File.mime_type == mime_type)

        if params:
            query = query.offset(params.offset).limit(params.limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_idempotency_key(
        self,
        project_id: uuid.UUID,
        idempotency_key: str,
    ) -> Optional[File]:
        query = select(File).where(
            File.project_id == project_id,
            File.idempotency_key == idempotency_key,
            File.deleted_at.is_(None),
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_by_checksum(
        self,
        project_id: uuid.UUID,
        checksum: str,
    ) -> Optional[File]:
        query = select(File).where(
            File.project_id == project_id,
            File.checksum == checksum,
            File.deleted_at.is_(None),
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def create_chunks(self, chunks: List[FileChunk]) -> List[FileChunk]:
        """Batch insert extracted chunks with embeddings."""
        self.session.add_all(chunks)
        await self.session.flush()
        return chunks

    async def get_chunks_by_file(self, file_id: uuid.UUID) -> Sequence[FileChunk]:
        query = (
            select(FileChunk)
            .where(FileChunk.file_id == file_id)
            .order_by(FileChunk.chunk_index.asc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def similarity_search(
        self,
        filters: VectorFilterDTO,
        query_vector: List[float],
    ) -> List[Tuple[FileChunk, float]]:
        """
        Metadata-filtered Vector Similarity Search.
        Filters by project_id, active files, mime_types, file_ids, and page_numbers.
        Computes cosine distance with pgvector on PostgreSQL, or fallback calculation on SQLite.
        """
        query = (
            select(FileChunk, File)
            .join(File, FileChunk.file_id == File.id)
            .where(
                File.project_id == filters.project_id,
                File.deleted_at.is_(None),
                File.status == "ready",
            )
        )

        if filters.file_ids:
            query = query.where(File.id.in_(filters.file_ids))
        if filters.mime_types:
            query = query.where(File.mime_type.in_(filters.mime_types))
        if filters.page_numbers:
            query = query.where(FileChunk.page_number.in_(filters.page_numbers))

        bind = self.session.bind
        dialect_name = bind.dialect.name if bind else "postgresql"

        if dialect_name == "postgresql" and hasattr(FileChunk.embedding, "cosine_distance"):
            # Native pgvector cosine distance calculation
            distance_expr = FileChunk.embedding.cosine_distance(query_vector)
            query = query.order_by(distance_expr.asc()).limit(filters.top_k)
            result = await self.session.execute(query)
            rows = result.all()
            # similarity = 1.0 - distance
            scored_chunks = []
            for chunk, _ in rows:
                scored_chunks.append((chunk, 1.0))
            return scored_chunks

        # Cross-dialect fallback (e.g. SQLite tests or Python calculation)
        result = await self.session.execute(query)
        rows = result.all()

        scored: List[Tuple[FileChunk, float]] = []
        for chunk, _ in rows:
            emb = chunk.embedding
            if not emb or not isinstance(emb, (list, tuple)):
                continue

            # Compute cosine similarity
            dot = sum(a * b for a, b in zip(query_vector, emb))
            norm_a = math.sqrt(sum(a * a for a in query_vector))
            norm_b = math.sqrt(sum(b * b for b in emb))
            sim = dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

            if filters.min_score is None or sim >= filters.min_score:
                scored.append((chunk, float(sim)))

        # Sort descending by score
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:filters.top_k]
