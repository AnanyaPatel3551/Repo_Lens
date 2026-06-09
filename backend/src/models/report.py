import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import String, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database.session import Base

class Report(Base):
    """
    SQLAlchemy model representing a GitHub Repository Analysis Report.
    """
    __tablename__ = "reports"

    # UUID primary key represented as string
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        index=True
    )
    
    github_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    repo_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    repo_owner: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    
    # Status can be: "pending", "cloning", "analyzing", "completed", "failed"
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    
    # Analysis metrics stored as JSON objects
    metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    languages: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    frameworks: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    entry_points: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    dependencies: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    architecture_report: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    important_files: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    onboarding_guide: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    repository_tour: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    architecture_walkthrough: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )
