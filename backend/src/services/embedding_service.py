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
        Generates vector embeddings for a list of KnowledgeChunk records in batch.
        """
        if not chunks:
            return []

        try:
            # Extract text content from all chunks
            texts = [chunk.chunk_content for chunk in chunks]
            
            # Generate embeddings in batch
            vectors = await provider.generate_embeddings(texts)
            
            # Construct and return Embedding objects matching the generated vectors
            embeddings = []
            for idx, vector in enumerate(vectors):
                if idx < len(chunks):
                    embeddings.append(Embedding(
                        chunk_id=chunks[idx].id,
                        vector=vector,
                        meta={}
                    ))
            return embeddings
        except Exception as e:
            err_msg = str(e).lower()
            import sys
            if "quota" in err_msg or "429" in err_msg or "exhausted" in err_msg:
                print(f"Warning: Gemini Embedding Quota Exceeded. Skipping remaining embeddings for this repository run. Error: {e}", file=sys.stderr)
            else:
                print(f"Warning: Failed to generate embeddings: {e}", file=sys.stderr)
            return []
