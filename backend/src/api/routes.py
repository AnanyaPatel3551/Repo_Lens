from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.session import get_db
from src.api.schemas import (
    AnalyzeRequest, AnalyzeResponse, ReportResponse,
    AskRequest, AskResponse, TourResponse, WalkthroughResponse,
    GraphResponse, ExplanationResponse
)
from src.repositories.report import ReportRepository
from src.models.report import Report
from src.services.analyzer import AnalysisService

# Platform Intelligence Services
from src.services.ask_service import AskService
from src.services.repository_tour_service import RepositoryTourService
from src.services.architecture_walkthrough_service import ArchitectureWalkthroughService
from src.services.relationship_graph_service import RelationshipGraphService
from src.services.explanation_service import ExplanationService
from src.services.architecture_diagram_service import ArchitectureDiagramService
from src.services.llm_provider import get_provider

router = APIRouter(prefix="/api")

@router.post(
    "/analyze", 
    response_model=AnalyzeResponse, 
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger repository analysis",
    description="Submits a public GitHub URL to be cloned and analyzed in the background."
)
async def analyze_repository(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    repo = ReportRepository(db)
    
    # 1. Create a new Report in pending state
    new_report = Report(
        github_url=request.github_url,
        status="pending"
    )
    
    try:
        saved_report = await repo.create(new_report)
        # Flush/commit changes to obtain ID
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record analysis job in database: {str(e)}"
        )
    
    # 2. Add full analysis workflow to FastAPI BackgroundTasks queue
    background_tasks.add_task(AnalysisService.run_analysis, saved_report.id)
    
    # 3. Respond immediately with status code 202
    return AnalyzeResponse(
        report_id=saved_report.id,
        status=saved_report.status,
        message="Repository analysis has been queued in the background."
    )

@router.get(
    "/reports/{id}", 
    response_model=ReportResponse,
    summary="Retrieve repository intelligence report",
    description="Gets the results of a repo analysis by UUID. Returns current processing status or compiled details."
)
async def get_report(
    id: str,
    db: AsyncSession = Depends(get_db)
):
    repo = ReportRepository(db)
    report = await repo.get(id)
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis report not found."
        )
        
    return report

@router.post(
    "/repositories/{id}/ask",
    response_model=AskResponse,
    summary="Ask a question about the repository",
    description="Answers developer questions by retrieving relevant codebase snippets and querying the configured LLM."
)
async def ask_repository(
    id: str,
    request: AskRequest,
    db: AsyncSession = Depends(get_db)
):
    repo_model = ReportRepository(db)
    report = await repo_model.get(id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository analysis report not found."
        )
    if report.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Repository analysis is not completed (current status: {report.status})."
        )

    try:
        ans = await AskService.ask(db, report, request.question)
        return ans
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate answer: {str(e)}"
        )

@router.get(
    "/repositories/{id}/tour",
    response_model=TourResponse,
    summary="Retrieve 60 second repository tour",
    description="Lazily generates and caches a step-by-step interactive onboarding tour."
)
async def get_repository_tour(
    id: str,
    db: AsyncSession = Depends(get_db)
):
    repo_model = ReportRepository(db)
    report = await repo_model.get(id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository analysis report not found."
        )
    if report.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Repository analysis is not completed (current status: {report.status})."
        )

    # If cached, return it
    if report.repository_tour:
        return report.repository_tour

    try:
        provider = get_provider()
        tour_data = await RepositoryTourService.generate_tour(report, provider)
        await repo_model.update(report, {"repository_tour": tour_data})
        await db.commit()
        return tour_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate repository tour: {str(e)}"
        )

@router.get(
    "/repositories/{id}/architecture-walkthrough",
    response_model=WalkthroughResponse,
    summary="Retrieve repository architecture walkthrough",
    description="Lazily generates and caches an onboarding architecture flow walkthrough."
)
async def get_architecture_walkthrough(
    id: str,
    db: AsyncSession = Depends(get_db)
):
    repo_model = ReportRepository(db)
    report = await repo_model.get(id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository analysis report not found."
        )
    if report.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Repository analysis is not completed (current status: {report.status})."
        )

    # If cached, return it
    if report.architecture_walkthrough:
        return report.architecture_walkthrough

    try:
        provider = get_provider()
        walkthrough_data = await ArchitectureWalkthroughService.generate_walkthrough(report, provider)
        await repo_model.update(report, {"architecture_walkthrough": walkthrough_data})
        await db.commit()
        return walkthrough_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate architecture walkthrough: {str(e)}"
        )

@router.get(
    "/repositories/{id}/file",
    summary="Retrieve file content from index",
    description="Reconstructs and returns the content of a file from its indexed chunks."
)
async def get_indexed_file(
    id: str,
    path: str,
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy.future import select
    from src.models.chunk import KnowledgeChunk
    
    # Query all chunks for this file path
    stmt = (
        select(KnowledgeChunk)
        .where(KnowledgeChunk.repository_id == id, KnowledgeChunk.file_path == path)
        .order_by(KnowledgeChunk.start_line.asc())
    )
    result = await db.execute(stmt)
    chunks = result.scalars().all()

    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File '{path}' not found in the indexed repository."
        )

    # Reconstruct the file content line-by-line using chunk bounds to resolve overlap
    lines_map = {}
    for chunk in chunks:
        chunk_lines = chunk.chunk_content.splitlines()
        for idx, line in enumerate(chunk_lines):
            line_no = chunk.start_line + idx
            # If line_no is already in map, we check if it is longer or matches (keep only unique lines)
            lines_map[line_no] = line

    sorted_lines = [lines_map[l] for l in sorted(lines_map.keys())]
    file_content = "\n".join(sorted_lines)

    return {
        "file_path": path,
        "content": file_content,
        "lines": sorted_lines
    }


@router.get(
    "/repositories/{id}/graph",
    response_model=GraphResponse,
    summary="Retrieve repository intelligence relationship graph",
    description="Returns node-link representation of entrypoints, routers, services, and databases."
)
async def get_repository_graph(
    id: str,
    db: AsyncSession = Depends(get_db)
):
    repo_model = ReportRepository(db)
    report = await repo_model.get(id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository analysis report not found."
        )
    if report.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Repository analysis is not completed (current status: {report.status})."
        )
    return RelationshipGraphService.generate_graph(report)


@router.get(
    "/repositories/{id}/explain-file",
    response_model=ExplanationResponse,
    summary="Dynamically explain codebase file",
    description="Queries the LLM provider to explain the purpose, responsibilities, functions, and coupling dependencies of a file."
)
async def explain_codebase_file(
    id: str,
    path: str,
    db: AsyncSession = Depends(get_db)
):
    repo_model = ReportRepository(db)
    report = await repo_model.get(id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository analysis report not found."
        )
    if report.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Repository analysis is not completed (current status: {report.status})."
        )
    try:
        provider = get_provider()
        return await ExplanationService.explain_file(db, id, path, provider)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate file explanation: {str(e)}"
        )


@router.get(
    "/repositories/{id}/explain-folder",
    response_model=ExplanationResponse,
    summary="Dynamically explain codebase directory",
    description="Queries the LLM provider to explain the purpose, responsibilities, functions, and coupling dependencies of a folder."
)
async def explain_codebase_folder(
    id: str,
    path: str,
    db: AsyncSession = Depends(get_db)
):
    repo_model = ReportRepository(db)
    report = await repo_model.get(id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository analysis report not found."
        )
    if report.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Repository analysis is not completed (current status: {report.status})."
        )
    try:
        provider = get_provider()
        return await ExplanationService.explain_folder(db, id, path, provider)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate folder explanation: {str(e)}"
        )


@router.get(
    "/repositories/{id}/diagrams",
    summary="Retrieve repository intelligence architecture diagrams",
    description="Lazily generates and caches three Mermaid diagrams (request flow, services, and folder structure)."
)
async def get_repository_diagrams(
    id: str,
    db: AsyncSession = Depends(get_db)
):
    repo_model = ReportRepository(db)
    report = await repo_model.get(id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository analysis report not found."
        )
    if report.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Repository analysis is not completed (current status: {report.status})."
        )
    try:
        provider = get_provider()
        diagrams = await ArchitectureDiagramService.get_diagrams(db, report, provider)
        return diagrams
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate architecture diagrams: {str(e)}"
        )

