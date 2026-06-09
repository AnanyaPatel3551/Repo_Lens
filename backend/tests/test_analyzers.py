import os
import pytest
from src.services.clone import parse_github_url
from src.analyzers.languages import LanguageAnalyzer
from src.analyzers.frameworks import FrameworkAnalyzer
from src.analyzers.entrypoints import EntryPointAnalyzer
from src.analyzers.dependencies import DependencyAnalyzer
from src.analyzers.architecture_detector import ArchitectureDetector
from src.analyzers.important_file_ranker import ImportantFileRanker
from src.analyzers.summary_generator import SummaryGenerator

def test_parse_github_url():
    # Test valid URLs
    assert parse_github_url("https://github.com/fastapi/fastapi") == ("fastapi", "fastapi")
    assert parse_github_url("http://github.com/owner/repo-name.git") == ("owner", "repo-name")
    assert parse_github_url("https://www.github.com/owner/repo.name") == ("owner", "repo.name")
    
    # Test invalid URLs
    with pytest.raises(ValueError):
        parse_github_url("https://github.com/owner")
    with pytest.raises(ValueError):
        parse_github_url("https://gitlab.com/owner/repo")
    with pytest.raises(ValueError):
        parse_github_url("https://github.com/owner/repo/extra")

def test_language_analyzer():
    records = [
        {"path": "main.py", "extension": ".py", "size": 100, "line_count": 50},
        {"path": "utils.py", "extension": ".py", "size": 200, "line_count": 150},
        {"path": "app.ts", "extension": ".ts", "size": 150, "line_count": 100},
        {"path": "styles.css", "extension": ".css", "size": 50, "line_count": 20},
    ]
    
    result = LanguageAnalyzer.analyze(records)
    
    assert "Python" in result
    assert "TypeScript" in result
    assert "CSS" not in result
    
    assert result["Python"]["files"] == 2
    assert result["Python"]["lines"] == 200
    assert result["TypeScript"]["files"] == 1
    assert result["TypeScript"]["lines"] == 100
    
    assert result["Python"]["percentage"] == 66.67
    assert result["TypeScript"]["percentage"] == 33.33

def test_framework_analyzer(tmp_path):
    file_records = [
        {"path": "src/App.tsx", "extension": ".tsx", "size": 100, "line_count": 20},
        {"path": "main.py", "extension": ".py", "size": 100, "line_count": 50},
    ]
    
    dependencies = {
        "package.json": [
            {"name": "react", "version": "18.2.0", "scope": "prod"},
            {"name": "next", "version": "14.1.0", "scope": "prod"}
        ],
        "requirements.txt": [
            {"name": "fastapi", "version": "0.110.0", "scope": "prod"}
        ]
    }
    
    result = FrameworkAnalyzer.analyze(file_records, dependencies, str(tmp_path))
    
    assert result["React"] == 1.0
    assert result["Next.js"] == 1.0
    assert result["FastAPI"] == 1.0
    assert "Django" not in result

def test_entrypoint_analyzer(tmp_path):
    file_records = [
        {"path": "src/index.js", "extension": ".js", "size": 100, "line_count": 5},
        {"path": "app.py", "extension": ".py", "size": 100, "line_count": 10},
        {"path": "App.test.tsx", "extension": ".tsx", "size": 50, "line_count": 10},
    ]
    
    result = EntryPointAnalyzer.analyze(file_records, str(tmp_path))
    
    paths = [ep["path"] for ep in result]
    assert "src/index.js" in paths
    assert "app.py" in paths
    assert "App.test.tsx" not in paths

# ==========================================
# PHASE 2 - PLATFORM INTELLIGENCE TESTS
# ==========================================

def test_architecture_detector():
    # 1. Clean Architecture Detection
    clean_files = [
        {"path": "src/domain/entities/user.py"},
        {"path": "src/domain/usecases/auth.py"},
        {"path": "src/infrastructure/db/connection.py"},
    ]
    res_clean = ArchitectureDetector.analyze(clean_files)
    assert res_clean["architecture_type"] == "Clean Architecture"
    assert res_clean["confidence_score"] >= 0.70
    assert any("domain" in e.lower() for e in res_clean["evidence"])

    # 2. Layered Architecture Detection
    layered_files = [
        {"path": "src/services/user_service.py"},
        {"path": "src/repositories/user_repo.py"},
        {"path": "src/database/session.py"},
    ]
    res_layer = ArchitectureDetector.analyze(layered_files)
    assert res_layer["architecture_type"] == "Layered Architecture"
    assert res_layer["confidence_score"] >= 0.70

    # 3. MVC Detection
    mvc_files = [
        {"path": "src/controllers/home.py"},
        {"path": "src/models/user.py"},
        {"path": "src/views/index.html"},
    ]
    res_mvc = ArchitectureDetector.analyze(mvc_files)
    assert res_mvc["architecture_type"] == "MVC"

    # 4. Monolith Fallback
    mono_files = [
        {"path": "app.py"},
        {"path": "utils.py"},
        {"path": "package.json"},
    ]
    res_mono = ArchitectureDetector.analyze(mono_files)
    assert res_mono["architecture_type"] == "Monolith"
    assert res_mono["confidence_score"] == 0.80

def test_important_file_ranker():
    files = [
        {"path": "README.md", "extension": ".md", "size": 500, "line_count": 10},
        {"path": "main.py", "extension": ".py", "size": 500, "line_count": 25},
        {"path": "requirements.txt", "extension": ".txt", "size": 100, "line_count": 5},
        {"path": "schema.sql", "extension": ".sql", "size": 300, "line_count": 12},
        {"path": "next.config.js", "extension": ".js", "size": 200, "line_count": 8},
        {"path": "routes.py", "extension": ".py", "size": 400, "line_count": 15},
        {"path": "services/user_service.py", "extension": ".py", "size": 900, "line_count": 45},
        {"path": "regular_file.py", "extension": ".py", "size": 300, "line_count": 50},
    ]
    entry_points = [{"path": "main.py", "language": "Python", "description": "Entry point"}]
    
    ranked = ImportantFileRanker.rank(files, entry_points)
    
    # Assert README is ranked first (score 100)
    assert ranked[0]["path"] == "README.md"
    assert ranked[0]["importance_score"] == 100
    
    # Assert main.py is ranked next (score 99)
    assert ranked[1]["path"] == "main.py"
    
    # Assert requirements.txt (score 99)
    assert any(f["path"] == "requirements.txt" and f["importance_score"] == 99 for f in ranked)

    # Assert total ranked files returned is within cap limits (top 10)
    assert len(ranked) <= 10

@pytest.mark.asyncio
async def test_summary_generator():
    files = [
        {"path": "README.md", "extension": ".md", "size": 1000, "line_count": 30},
        {"path": "main.py", "extension": ".py", "size": 500, "line_count": 10},
        {"path": "src/api/routes.py", "extension": ".py", "size": 300, "line_count": 10},
        {"path": "src/services/db.py", "extension": ".py", "size": 200, "line_count": 10},
    ]
    languages = {"Python": {"files": 3, "lines": 30, "percentage": 100.0}}
    frameworks = {"FastAPI": 1.0}
    entry_points = [{"path": "main.py", "language": "Python", "description": "Startup bootstrap entry point."}]
    dependencies = {"requirements.txt": [{"name": "fastapi", "version": "0.100", "scope": "prod"}]}
    architecture = {"architecture_type": "Layered Architecture", "confidence_score": 0.85, "evidence": ["Detected API routes"]}
    important_files = [
        {"path": "README.md", "importance_score": 98, "explanation": "Documentation"},
        {"path": "main.py", "importance_score": 95, "explanation": "Entrypoint"}
    ]

    res = await SummaryGenerator.generate(
        files,
        languages,
        frameworks,
        entry_points,
        dependencies,
        architecture,
        important_files
    )

    assert "summary" in res
    assert "onboarding_guide" in res
    
    # Assert summary facts mapping
    assert "FastAPI" in res["summary"]["project_purpose"]
    assert "Python" in res["summary"]["main_technologies"]
    assert "Layered Architecture" in res["summary"]["architecture_overview"]
    
    # Assert onboarding guide mapping
    assert "README.md" in res["onboarding_guide"]["where_to_start"]
    assert res["onboarding_guide"]["entry_points"][0]["path"] == "main.py"
