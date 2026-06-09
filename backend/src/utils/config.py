import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "RepoLens AI"
    API_V1_STR: str = "/api"
    
    # Database configuration (defaults to local docker postgres instance using asyncpg)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgrespassword@localhost:5432/repolens"
    
    # Directory to store temporary workspace clones inside the project workspace
    TEMP_DIR: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
        "temp_workspaces"
    )

    # Provider settings
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
