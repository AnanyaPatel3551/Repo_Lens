import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.database.session import Base
from src.models.report import Report
from src.models.chunk import KnowledgeChunk, Embedding
from src.services.retrieval_service import RetrievalService


class MockLLMProvider:
    """
    Mock LLM provider returning mock embedding vectors based on keyword contents.
    """
    async def generate_embedding(self, text: str) -> list:
        if "auth" in text.lower():
            # Align with authentication search query
            return [1.0, 0.0, 0.0]
        else:
            return [0.0, 1.0, 0.0]

    async def generate_response(self, prompt: str, system_instruction: str = None) -> str:
        return "Grounded mock response description."


@pytest.mark.asyncio
async def test_sqlite_fallback_retrieval():
    """
    Validates that RetrievalService queries, computes cosine similarity,
    and returns matches sorted by relevance on SQLite fallback databases.
    """
    # Initialize in-memory SQLite engine
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_local = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_local() as db:
        # 1. Create a mockup repository report
        report = Report(
            id="test-repo-id",
            github_url="https://github.com/owner/repo",
            status="completed"
        )
        db.add(report)
        await db.flush()

        # 2. Seed knowledge chunks
        chunk_auth = KnowledgeChunk(
            id="c1",
            repository_id="test-repo-id",
            file_path="src/auth.py",
            language="Python",
            chunk_type="function",
            chunk_content="def handle_auth(): pass",
            start_line=1,
            end_line=2
        )
        chunk_utils = KnowledgeChunk(
            id="c2",
            repository_id="test-repo-id",
            file_path="src/utils.py",
            language="Python",
            chunk_type="function",
            chunk_content="def format_date(): pass",
            start_line=1,
            end_line=2
        )
        db.add(chunk_auth)
        db.add(chunk_utils)
        await db.flush()

        # 3. Seed embeddings
        emb_auth = Embedding(chunk_id="c1", vector=[1.0, 0.0, 0.0])
        emb_utils = Embedding(chunk_id="c2", vector=[0.0, 1.0, 0.0])
        db.add(emb_auth)
        db.add(emb_utils)
        await db.commit()

        # 4. Perform retrieval with query containing 'auth'
        provider = MockLLMProvider()
        results = await RetrievalService.retrieve(
            db=db,
            repository_id="test-repo-id",
            question="How does auth work?",
            provider=provider,
            limit=2
        )

        # 5. Assert sorting correctness
        assert len(results) == 2
        
        # 'src/auth.py' should be retrieved first (highest cosine similarity)
        assert results[0]["file_path"] == "src/auth.py"
        assert results[0]["relevance_score"] > 0.99  # Cosine similarity is 1.0
        
        # 'src/utils.py' should be second (orthogonal vector [0, 1, 0])
        assert results[1]["file_path"] == "src/utils.py"
        assert abs(results[1]["relevance_score"]) < 1e-5  # Cosine similarity is 0.0

    await engine.dispose()
