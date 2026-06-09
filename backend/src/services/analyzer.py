import sys
import traceback
from typing import List, Dict, Any
import src.database.session as db_session
from src.repositories.report import ReportRepository
from src.services.clone import CloneService, cleanup_workspace
from src.analyzers.scanner import FileScanner
from src.analyzers.languages import LanguageAnalyzer
from src.analyzers.dependencies import DependencyAnalyzer
from src.analyzers.frameworks import FrameworkAnalyzer
from src.analyzers.entrypoints import EntryPointAnalyzer
from src.analyzers.architecture_detector import ArchitectureDetector
from src.analyzers.important_file_ranker import ImportantFileRanker
from src.analyzers.summary_generator import SummaryGenerator
from src.services.indexing_service import IndexingService

class AnalysisService:
    @staticmethod
    async def run_analysis(report_id: str) -> None:
        """
        Runs the full repository intelligence analysis flow in the background.
        Opens its own isolated DB session to avoid session sharing conflicts.
        """
        db = db_session.SessionLocal()
        repo = ReportRepository(db)
        
        # 1. Fetch current pending report
        report = await repo.get(report_id)
        if not report:
            await db.close()
            return

        cloned_dir = None
        import time
        start_total = time.perf_counter()
        try:
            # 2. Update status: cloning
            await repo.update(report, {"status": "cloning"})
            await db.commit()
            
            # 3. Clone Repository
            start_clone = time.perf_counter()
            cloned_dir, owner, repo_name = CloneService.clone_repository(report.github_url)
            clone_time = time.perf_counter() - start_clone
            
            # Update repo metadata in DB
            await repo.update(report, {
                "repo_owner": owner,
                "repo_name": repo_name,
                "status": "analyzing"
            })
            await db.commit()

            start_analyze = time.perf_counter()
            # 4. Scan files recursively
            files = FileScanner.scan(cloned_dir)
            
            # 5. Extract Dependencies
            dependencies = DependencyAnalyzer.analyze(cloned_dir)
            
            # 6. Detect Languages
            languages = LanguageAnalyzer.analyze(files)
            
            # 7. Detect Frameworks
            frameworks = FrameworkAnalyzer.analyze(files, dependencies, cloned_dir)
            
            # 8. Detect Entry Points
            entry_points = EntryPointAnalyzer.analyze(files, cloned_dir)
            
            # 9. Detect Architecture Heuristics
            architecture_report = ArchitectureDetector.analyze(files)
            
            # 10. Rank High Signal Files
            important_files = ImportantFileRanker.rank(files, entry_points)
            
            # 11. Generate Grounded Summary & Onboarding
            summary_onboarding = await SummaryGenerator.generate(
                files,
                languages,
                frameworks,
                entry_points,
                dependencies,
                architecture_report,
                important_files
            )
            analyze_time = time.perf_counter() - start_analyze
            
            # 12. Index the repository semantic chunks and embeddings
            start_index = time.perf_counter()
            await IndexingService.index_repository(db, report_id, cloned_dir, files)
            indexing_time = time.perf_counter() - start_index

            total_time = time.perf_counter() - start_total
            
            # 12. Compute Metrics
            total_files = len(files)
            total_lines = sum(rec["line_count"] for rec in files)
            
            # Sort files by size descending, pick top 10
            sorted_by_size = sorted(files, key=lambda x: x["size"], reverse=True)
            largest_files = sorted_by_size[:10]
            
            metrics = {
                "total_files": total_files,
                "total_lines": total_lines,
                "largest_files": largest_files,
                "latency": {
                    "clone_time": round(clone_time, 2),
                    "analyze_time": round(analyze_time, 2),
                    "indexing_time": round(indexing_time, 2),
                    "total_time": round(total_time, 2)
                }
            }

            # 13. Update report to completed in database
            await repo.update(report, {
                "status": "completed",
                "metrics": metrics,
                "languages": languages,
                "frameworks": frameworks,
                "entry_points": entry_points,
                "dependencies": dependencies,
                "summary": summary_onboarding["summary"],
                "architecture_report": architecture_report,
                "important_files": important_files,
                "onboarding_guide": summary_onboarding["onboarding_guide"]
            })
            await db.commit()

        except Exception as e:
            # Capture error logs
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            print(f"Error during analysis of report {report_id}: {error_msg}", file=sys.stderr)
            
            # Mark database job as failed
            try:
                # Refresh report in case of session mismatch
                report = await repo.get(report_id)
                if report:
                    await repo.update(report, {
                        "status": "failed",
                        "error_message": str(e)
                    })
                    await db.commit()
            except Exception as db_err:
                print(f"Failed to record error state to DB: {db_err}", file=sys.stderr)
                
        finally:
            # 11. Strictly clean up temporary cloned files
            if cloned_dir:
                cleanup_workspace(cloned_dir)
            
            # Close db session
            await db.close()
