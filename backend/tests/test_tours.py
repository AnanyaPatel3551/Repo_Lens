import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from unittest.mock import patch

from src.database.session import Base
from src.models.report import Report
from src.models.chunk import KnowledgeChunk, Embedding
from src.services.repository_tour_service import RepositoryTourService
from src.services.architecture_walkthrough_service import ArchitectureWalkthroughService
from src.services.ask_service import AskService


class MockServiceLLMProvider:
    """
    Mock LLM provider returned for Q&A, tours, and walkthrough generation tests.
    """
    async def generate_embedding(self, text: str) -> list:
        return [0.1, 0.2, 0.3]

    async def generate_response(self, prompt: str, system_instruction: str = None) -> str:
        sys_inst_lower = system_instruction.lower() if system_instruction else ""
        prompt_lower = prompt.lower()
        
        if "tour" in sys_inst_lower:
            return (
                "Step 1\n"
                "File: src/main.py\n"
                "Reason: Application startup entrypoint.\n\n"
                "Step 2\n"
                "File: src/auth/service.py\n"
                "Reason: Implements user session authentication."
            )
        elif "walkthrough" in sys_inst_lower:
            return "# Codebase Architecture Walkthrough\n\n## Request Flow\nRequests hit `routes.py` first."
        elif "onboarding" in sys_inst_lower:
            if "missing" in prompt_lower or "unknown" in prompt_lower:
                return "Information not found in analyzed repository."
            return "This project handles authentication using OAuth [File: src/auth/service.py (10-80)] and JWT security checks."
        return "Generic response."


@pytest.mark.asyncio
async def test_repository_tour_parsing():
    """
    Verifies that RepositoryTourService correctly requests and parses the LLM output into step structures.
    """
    report = Report(
        entry_points=[{"path": "src/main.py", "language": "Python", "description": "Startup"}],
        important_files=[{"path": "src/main.py", "importance_score": 95, "explanation": "Startup"}],
        architecture_report={"architecture_type": "Layered", "evidence": ["routes"]}
    )
    provider = MockServiceLLMProvider()

    result = await RepositoryTourService.generate_tour(report, provider)

    assert "tour_steps" in result
    assert len(result["tour_steps"]) == 2
    assert result["tour_steps"][0]["step"] == 1
    assert result["tour_steps"][0]["file"] == "src/main.py"
    assert "startup" in result["tour_steps"][0]["reason"].lower()
    assert result["tour_steps"][1]["step"] == 2
    assert result["tour_steps"][1]["file"] == "src/auth/service.py"
    assert "authentication" in result["tour_steps"][1]["reason"].lower()


@pytest.mark.asyncio
async def test_architecture_walkthrough():
    """
    Verifies that ArchitectureWalkthroughService properly queries the LLM.
    """
    report = Report(
        entry_points=[],
        important_files=[],
        architecture_report={}
    )
    provider = MockServiceLLMProvider()

    result = await ArchitectureWalkthroughService.generate_walkthrough(report, provider)

    assert "walkthrough" in result
    assert "# Codebase Architecture Walkthrough" in result["walkthrough"]


@pytest.mark.asyncio
async def test_ask_service_citation_parsing():
    """
    Verifies that AskService executes similarity retrieval, compiles context,
    queries the LLM, extracts citation maps, and reformats output.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_local = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_local() as db:
        report = Report(
            id="test-ask-id",
            github_url="https://github.com/owner/repo",
            status="completed"
        )
        db.add(report)
        await db.flush()

        # Seed a dummy chunk/embedding so retrieval succeeds
        chunk = KnowledgeChunk(
            id="c1",
            repository_id="test-ask-id",
            file_path="src/auth/service.py",
            language="Python",
            chunk_type="function",
            chunk_content="def auth(): pass",
            start_line=10,
            end_line=80
        )
        db.add(chunk)
        await db.flush()

        emb = Embedding(chunk_id="c1", vector=[0.1, 0.2, 0.3])
        db.add(emb)
        await db.commit()

        provider = MockServiceLLMProvider()

        with patch("src.services.ask_service.get_provider", return_value=provider):
            res = await AskService.ask(db, report, "How does auth work?")

            assert "answer" in res
            assert "citations" in res
            assert len(res["citations"]) == 1
            assert res["citations"][0]["file_path"] == "src/auth/service.py"
            assert res["citations"][0]["start_line"] == 10
            assert res["citations"][0]["end_line"] == 80
            
            # The bracket citation tag should be reformatted to clean output
            assert "(src/auth/service.py:10-80)" in res["answer"]
            assert "[File:" not in res["answer"]

    await engine.dispose()


@pytest.mark.asyncio
async def test_ask_service_hallucination_prevention():
    """
    Verifies that AskService falls back and clears citations when information is not found in codebase.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_local = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_local() as db:
        report = Report(
            id="test-ask-id",
            github_url="https://github.com/owner/repo",
            status="completed"
        )
        db.add(report)
        await db.commit()

        provider = MockServiceLLMProvider()

        with patch("src.services.ask_service.get_provider", return_value=provider):
            res = await AskService.ask(db, report, "What unknown database tables are used?")

            assert res["answer"] == "Information not found in analyzed repository."
            assert len(res["citations"]) == 0

    await engine.dispose()
