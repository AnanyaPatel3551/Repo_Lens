# RepoLens AI - Repository Intelligence Platform

RepoLens AI is a production-grade repository intelligence platform. It analyzes any public GitHub repository, generating comprehensive metrics on languages, frameworks, entry points, files, and project dependencies.

The project is architected as a modular monorepo, separating a FastAPI python backend (employing SOLID principles, clean database repositories, and decoupled analysis components) from a modern Next.js/TypeScript/Tailwind CSS dashboard styled with a Vercel/Linear dark theme.

---

## Architecture Overview

RepoLens AI follows **Clean Architecture** and **SOLID** principles:
- **Presentation Layer (FastAPI)**: Validates input schemas using Pydantic, maps endpoints, and initiates processing.
- **Service Layer (Orchestrator)**: Coordinates repository downloading, analysis triggers, and database writing.
- **Scanners & Analyzers (Domain)**: Independent, specialized components scanning files, mapping languages, extracting dependencies, scoring framework confidence, and finding codebase start triggers.
- **Repository Pattern (Database)**: Isolates SQL code and database access from business logic.
- **Asynchronous Execution**: Uses FastAPI's asynchronous event loops and PostgreSQL connection pools. It delegates analysis pipelines to background workers to ensure instant HTTP response times (HTTP 202).

---

## Project Structure

```
c:/Repo_Lens/
├── backend/
│   ├── src/
│   │   ├── api/          # Request validation models (Pydantic) and endpoints
│   │   ├── services/     # Core services (Git cloning, analysis coordinator)
│   │   ├── analyzers/    # Specific scanners (Language, Dependencies, Frameworks, Entrypoints)
│   │   ├── models/       # Database schemas (SQLAlchemy)
│   │   ├── repositories/ # Database CRUD abstractions (Repository pattern)
│   │   ├── database/     # Async session configs and DB engine
│   │   ├── utils/        # Configuration management (Pydantic Settings)
│   │   └── workers/      # Workers interface (for future Celery/Redis integrations)
│   ├── tests/            # Pytest suite
│   ├── requirements.txt  # Python packages
│   └── main.py           # FastAPI entrypoint
├── frontend/
│   ├── app/              # Next.js App Router layout and pages (Overview & Dependencies)
│   ├── components/       # UI visual elements
│   ├── lib/              # Async API Client utility
│   ├── types/            # TypeScript interfaces
│   ├── package.json      # Node scripts and dependencies
│   ├── tailwind.config.ts# Tailwind CSS settings
│   └── tsconfig.json     # TypeScript config
├── docker-compose.yml    # Development PostgreSQL database container config
└── README.md             # Platform Documentation
```

---

## Local Setup

### 1. Database (Docker Setup)
Spin up the development PostgreSQL database using Docker Compose:
```bash
docker-compose up -d
```
This launches a PostgreSQL container on port `5432` with username `postgres`, password `postgrespassword`, and database name `repolens`.

### 2. Backend Setup
Create a virtual environment, install python libraries, and run the FastAPI server:
```bash
cd backend
# Create environment
python -m venv venv
# Activate on Windows
.\venv\Scripts\activate
# Install libraries
pip install -r requirements.txt
# Launch with Uvicorn
uvicorn main:app --reload --port 8000
```
- API Docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/`

*Note: Database tables are automatically initialized on backend startup.*

### 3. Frontend Setup
Install dependencies and run the Next.js dev server:
```bash
cd frontend
npm install
npm run dev
```
- Web Application dashboard: `http://localhost:3000`

---

## Scan Engine Pipeline Details

When a user submits a URL:
1. **Validation**: Pydantic validates that the string is a valid GitHub URL format.
2. **Sandbox Allocation**: The cloning engine creates a randomized, unique folder under `temp_workspaces/`.
3. **Cloning**: Clones with `--depth 1` to optimize bandwidth and speed.
4. **Scan**: Runs the file walker, checking file sizes and performing a null-byte test to ignore binary files.
5. **Code Intelligence**:
   - **Language Classifier**: Assigns file sizes and lines to languages, ranking them.
   - **Dependency Parser**: Reads packages from manifests (`package.json`, `Cargo.toml`, etc.) extracting package versions.
   - **Framework Resolver**: Computes confidence values (React, Vue, Spring Boot, etc.) using file structures and dependency arrays.
   - **Entrypoint Discovery**: Discovers probable app start files.
6. **Persistence**: Saves the data model in PostgreSQL.
7. **Cleanup**: Deletes the sandbox environment.
