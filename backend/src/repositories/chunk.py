from typing import List, Tuple, Any
import math
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete

from src.models.chunk import KnowledgeChunk, Embedding
from src.repositories.base import BaseRepository


class ChunkRepository(BaseRepository[KnowledgeChunk]):
    """
    Repository class handling database interactions for the KnowledgeChunk and Embedding models.
    """
    def __init__(self, db: AsyncSession):
        super().__init__(KnowledgeChunk, db)

    async def bulk_create_chunks(self, chunks: List[KnowledgeChunk]) -> List[KnowledgeChunk]:
        """
        Inserts multiple knowledge chunks in bulk.
        """
        for chunk in chunks:
            self.db.add(chunk)
        await self.db.flush()
        return chunks

    async def bulk_create_embeddings(self, embeddings: List[Embedding]) -> List[Embedding]:
        """
        Inserts multiple embeddings in bulk.
        """
        for embedding in embeddings:
            self.db.add(embedding)
        await self.db.flush()
        return embeddings

    async def delete_by_repository_id(self, repository_id: str) -> None:
        """
        Deletes all chunks and embeddings for a given repository.
        """
        await self.db.execute(
            delete(KnowledgeChunk).where(KnowledgeChunk.repository_id == repository_id)
        )
        await self.db.flush()

    async def get_by_repository_id(self, repository_id: str) -> List[KnowledgeChunk]:
        """
        Fetches all knowledge chunks for a repository.
        """
        result = await self.db.execute(
            select(KnowledgeChunk)
            .where(KnowledgeChunk.repository_id == repository_id)
        )
        return list(result.scalars().all())

    async def search_similarity(
        self, repository_id: str, query_vector: List[float], limit: int = 10
    ) -> List[Tuple[KnowledgeChunk, float]]:
        """
        Retrieves the top semantically similar chunks for a query vector.
        Uses native pgvector distance operator on Postgres, and Python-based fallback on SQLite.
        """
        # Determine database dialect
        dialect_name = self.db.bind.dialect.name

        if dialect_name == "postgresql":
            # PostgreSQL pgvector similarity search
            # We use .op("<=>") to perform cosine distance (1 - cosine similarity)
            # Relevance = 1 - cosine distance = 1 - (v1 <=> v2)
            stmt = (
                select(
                    KnowledgeChunk, 
                    (1.0 - Embedding.vector.op("<=>")(query_vector)).label("relevance")
                )
                .join(Embedding, KnowledgeChunk.id == Embedding.chunk_id)
                .where(KnowledgeChunk.repository_id == repository_id)
                .order_by(Embedding.vector.op("<=>")(query_vector))
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            return [(row[0], float(row[1])) for row in result.all()]
        else:
            # SQLite / Fallback in-memory cosine similarity search
            # 1. Fetch all chunks and embeddings for the repository
            stmt = (
                select(KnowledgeChunk, Embedding.vector)
                .join(Embedding, KnowledgeChunk.id == Embedding.chunk_id)
                .where(KnowledgeChunk.repository_id == repository_id)
            )
            result = await self.db.execute(stmt)
            rows = result.all()

            if not rows:
                return []

            # 2. Compute similarity in-memory
            matches = []
            for chunk, vector in rows:
                if not vector:
                    continue
                similarity = self._cosine_similarity(query_vector, vector)
                matches.append((chunk, similarity))

            # 3. Sort by similarity descending and limit
            matches.sort(key=lambda x: x[1], reverse=True)
            return matches[:limit]

    async def search_lexical(
        self, repository_id: str, question: str, limit: int = 10
    ) -> List[Tuple[KnowledgeChunk, float]]:
        """
        Retrieves matching chunks using keyword matching on the chunk_content.
        Supports both PostgreSQL and SQLite.
        """
        import re
        from sqlalchemy import or_
        
        # Split question into words and search for chunks containing any of the keywords
        words = [w.strip() for w in re.split(r'\W+', question) if len(w.strip()) > 2]
        if not words:
            # Fallback to returning the first few chunks
            result = await self.db.execute(
                select(KnowledgeChunk)
                .where(KnowledgeChunk.repository_id == repository_id)
                .limit(limit)
            )
            return [(chunk, 0.5) for chunk in result.scalars().all()]

        # Construct a search query: match chunks where content contains keywords
        clauses = [KnowledgeChunk.chunk_content.ilike(f"%{word}%") for word in words]
        
        stmt = (
            select(KnowledgeChunk)
            .where(KnowledgeChunk.repository_id == repository_id, or_(*clauses))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return [(chunk, 0.8) for chunk in result.scalars().all()]

    @staticmethod
    def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """
        Computes cosine similarity between two vectors.
        """
        if len(v1) != len(v2) or not v1:
            return 0.0
            
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm_a = math.sqrt(sum(a * a for a in v1))
        norm_b = math.sqrt(sum(b * b for b in v2))
        
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
            
        return dot_product / (norm_a * norm_b)
