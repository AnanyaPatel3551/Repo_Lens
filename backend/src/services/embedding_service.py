import asyncio
from typing import List

from src.models.chunk import KnowledgeChunk, Embedding
from src.services.llm_provider import BaseLLMProvider


class EmbeddingService:
    """
    Service to generate vector embeddings for repository chunks.
    """

    @staticmethod
    async def generate_embeddings_for_chunks(
        chunks: List[KnowledgeChunk], provider: BaseLLMProvider
    ) -> List[Embedding]:
        """
        Generates vector embeddings for a list of KnowledgeChunk records.
        Executes concurrently with a semaphore limit of 10 to avoid HTTP 429 rate limiting.
        """
        if not chunks:
            return []

        semaphore = asyncio.Semaphore(10)
        quota_exceeded = False

        async def embed_chunk(chunk: KnowledgeChunk) -> Embedding:
            nonlocal quota_exceeded
            if quota_exceeded:
                return None

            async with semaphore:
                if quota_exceeded:
                    return None
                try:
                    vector = await provider.generate_embedding(chunk.chunk_content)
                    return Embedding(
                        chunk_id=chunk.id,
                        vector=vector,
                        meta={}
                    )
                except Exception as e:
                    err_msg = str(e).lower()
                    if "quota" in err_msg or "429" in err_msg or "exhausted" in err_msg:
                        if not quota_exceeded:
                            quota_exceeded = True
                            import sys
                            print(f"Warning: Gemini Embedding Quota Exceeded. Skipping remaining embeddings for this repository run. Error: {e}", file=sys.stderr)
                    else:
                        import sys
                        print(f"Warning: Failed to generate embedding for chunk {chunk.id} in file {chunk.file_path}: {e}", file=sys.stderr)
                    return None

        tasks = [embed_chunk(c) for c in chunks]
        results = await asyncio.gather(*tasks)
        
        return [r for r in results if r is not None]
