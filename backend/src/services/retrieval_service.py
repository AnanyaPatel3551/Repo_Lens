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

        chunk_repo = ChunkRepository(db)
        
        # 1. Try to generate embedding and perform similarity search
        try:
            query_vector = await provider.generate_embedding(question)
            if query_vector and any(v != 0.0 for v in query_vector):
                matches = await chunk_repo.search_similarity(repository_id, query_vector, limit=limit)
            else:
                raise ValueError("Embedding provider returned a zero vector.")
        except Exception as e:
            import sys
            print(f"Warning: Semantic search failed ({e}). Falling back to lexical keyword search.", file=sys.stderr)
            matches = await chunk_repo.search_lexical(repository_id, question, limit=limit)

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
