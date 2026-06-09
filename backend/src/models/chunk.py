import uuid
from typing import Optional, List
from sqlalchemy import String, Integer, ForeignKey, Text, JSON, TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.session import Base

# Dynamic import check for pgvector
try:
    from pgvector.sqlalchemy import Vector as PGVector
except ImportError:
    PGVector = None


class SafeVector(TypeDecorator):
    """
    A custom TypeDecorator that compiles to the pgvector VECTOR type
    when using PostgreSQL, and falls back to a JSON column when using SQLite.
    """
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql" and PGVector is not None:
            # VECTOR type with dynamic dimension
            return dialect.type_descriptor(PGVector())
        else:
            return dialect.type_descriptor(JSON)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        # Ensure the vector is a list of floats
        return [float(x) for x in value]

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            # SQLite or Postgres driver might return a string representation like '[1.0, 2.0]'
            import re
            return [float(x) for x in re.findall(r"[-+]?\d*\.\d+|\d+", value)]
        return [float(x) for x in value]


class KnowledgeChunk(Base):
    """
    SQLAlchemy model representing a semantic code chunk within the repository knowledge index.
    """
    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True
    )
    
    repository_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    language: Mapped[str] = mapped_column(String(64), nullable=False)
    chunk_type: Mapped[str] = mapped_column(String(64), nullable=False)
    chunk_content: Mapped[str] = mapped_column(Text, nullable=False)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    meta: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    # Relationships
    embedding = relationship(
        "Embedding", 
        back_populates="chunk", 
        cascade="all, delete-orphan", 
        uselist=False
    )


class Embedding(Base):
    """
    SQLAlchemy model representing the vector embedding of a knowledge chunk.
    """
    __tablename__ = "embeddings"

    chunk_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("knowledge_chunks.id", ondelete="CASCADE"),
        primary_key=True,
        index=True
    )
    
    vector: Mapped[List[float]] = mapped_column(SafeVector, nullable=False)
    meta: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    # Relationships
    chunk = relationship("KnowledgeChunk", back_populates="embedding")
