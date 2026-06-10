import os
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.chunk import KnowledgeChunk
from src.repositories.chunk import ChunkRepository
from src.services.chunking_service import ChunkingService
from src.services.embedding_service import EmbeddingService
from src.services.llm_provider import get_provider


class IndexingService:
    """
    Orchestration service to generate semantic chunks and embeddings for a analyzed repository.
    """

    @staticmethod
    async def index_repository(db: AsyncSession, repository_id: str, cloned_dir: str, files: List[Dict[str, Any]]) -> None:
        """
        Clears existing chunks, scans, chunks, embeds, and persists all repository content.
        """
        # 1. Clear any prior indexes (for idempotency and retries)
        chunk_repo = ChunkRepository(db)
        await chunk_repo.delete_by_repository_id(repository_id)

        # 2. Extract semantic chunks
        chunks_to_create = []
        for file_record in files:
            rel_path = file_record["path"]
            full_path = os.path.join(cloned_dir, rel_path)
            
            if not os.path.isfile(full_path):
                continue

            from src.analyzers.scanner import is_binary_file
            if is_binary_file(full_path):
                continue

            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if "\x00" in content:
                    continue  # Skip files containing null characters (binary/corrupted)
            except Exception:
                continue  # Skip unreadable/binary files

            ext = file_record.get("extension", "").lower()
            language = "Unknown"
            if ext == ".py":
                language = "Python"
            elif ext in (".ts", ".tsx"):
                language = "TypeScript"
            elif ext in (".js", ".jsx"):
                language = "JavaScript"
            elif ext == ".java":
                language = "Java"
            elif ext == ".go":
                language = "Go"
            elif ext == ".md":
                language = "Markdown"
            elif ext in (".json", ".yaml", ".yml", ".toml"):
                language = "Config"

            file_chunks = ChunkingService.chunk_file(rel_path, content, language)
            
            for fc in file_chunks:
                chunks_to_create.append(KnowledgeChunk(
                    repository_id=repository_id,
                    file_path=fc["file_path"],
                    language=fc["language"],
                    chunk_type=fc["chunk_type"],
                    chunk_content=fc["chunk_content"],
                    start_line=fc["start_line"],
                    end_line=fc["end_line"],
                    meta=fc["metadata"]
                ))

        if not chunks_to_create:
            return

        # Commit chunks to database to obtain IDs
        saved_chunks = await chunk_repo.bulk_create_chunks(chunks_to_create)
        await db.commit()

        # 3. Generate and save embeddings
        try:
            provider = get_provider()
            embeddings = await EmbeddingService.generate_embeddings_for_chunks(saved_chunks, provider)
            if embeddings:
                await chunk_repo.bulk_create_embeddings(embeddings)
                await db.commit()
        except Exception as e:
            # If embedding fails (e.g. invalid API key or model download error),
            # we keep the text-based chunks index and log a warning.
            import sys
            print(f"Warning: Embedding pipeline failed for repository {repository_id}: {e}. Chunks remain indexed in text-only mode.", file=sys.stderr)
