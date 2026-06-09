from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.database.session import engine, Base
from src.api.routes import router
from src.utils.config import settings
from src.models.chunk import KnowledgeChunk, Embedding

async def run_migrations(engine_obj):
    """
    Ensure the reports table exists and run migrations dynamically
    to append new columns if they are missing.
    """
    from sqlalchemy import inspect, text
    async with engine_obj.begin() as conn:
        # Enable pgvector if postgresql
        if engine_obj.dialect.name == "postgresql":
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            
        # Enable WAL mode if SQLite to prevent database locking during concurrent reads/writes
        if engine_obj.dialect.name == "sqlite":
            await conn.execute(text("PRAGMA journal_mode=WAL;"))
            await conn.execute(text("PRAGMA synchronous=NORMAL;"))
            
        # Create base tables
        await conn.run_sync(Base.metadata.create_all)
        
        # Check column definitions and execute ALTER TABLE statements if necessary
        def migrate(connection):
            inspector = inspect(connection)
            existing_cols = [c["name"] for c in inspector.get_columns("reports")]
            
            new_columns = {
                "summary": "JSON",
                "architecture_report": "JSON",
                "important_files": "JSON",
                "onboarding_guide": "JSON",
                "repository_tour": "JSON",
                "architecture_walkthrough": "JSON"
            }
            
            for name, col_type in new_columns.items():
                if name not in existing_cols:
                    print(f"Database Migration: Adding column '{name}' to 'reports' table.")
                    connection.execute(text(f"ALTER TABLE reports ADD COLUMN {name} {col_type}"))
                    
        await conn.run_sync(migrate)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events: handles DB tables creation on startup
    and clean connection pools release on shutdown.
    Attempts PostgreSQL first; falls back to SQLite if database is offline.
    """
    try:
        # Try running migrations on PostgreSQL
        await run_migrations(engine)
        print("PostgreSQL database tables initialized and migrated successfully.")
    except Exception as e:
        print(f"\n[WARNING] Failed to connect to PostgreSQL: {e}")
        print("Falling back to local SQLite database: ./repolens.db\n")
        
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        import src.database.session as db_session
        
        # Override connection engine mappings dynamically at runtime
        sqlite_url = "sqlite+aiosqlite:///./repolens.db"
        db_session.engine = create_async_engine(
            sqlite_url,
            echo=False
        )
        db_session.SessionLocal = async_sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=db_session.engine,
            expire_on_commit=False
        )
        
        # Create database tables and migrate in SQLite fallback
        await run_migrations(db_session.engine)
        print("Local SQLite database initialized and migrated successfully.")
        
    yield
    
    # Dispose of active connection pools on shutdown
    import src.database.session as db_session
    await db_session.engine.dispose()
    print("Database connections closed.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-grade API analyzing public GitHub repositories for code metrics and structures.",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for Next.js web application communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(router)

@app.get("/", summary="Health check endpoint")
async def root():
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "version": "1.0.0"
    }
