from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.chunk import ChunkRepository
from src.services.llm_provider import BaseLLMProvider


class RetrievalService:
    """
    Service to retrieve relevant code chunks for a given query.
    """

    @staticmethod
    async def retrieve(
        db: AsyncSession,
        repository_id: str,
        question: str,
        provider: BaseLLMProvider,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieves the most relevant code chunks for a repository ID and user query.
        """
        if not question.strip():
            return []

        # 1. Generate embedding for the query string
        query_vector = await provider.generate_embedding(question)

        # 2. Search database for matching chunks using the repository
        chunk_repo = ChunkRepository(db)
        matches = await chunk_repo.search_similarity(repository_id, query_vector, limit=limit)

        # 3. Format matches
        results = []
        for chunk, score in matches:
            results.append({
                "chunk_content": chunk.chunk_content,
                "file_path": chunk.file_path,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "relevance_score": score
            })

        return results
