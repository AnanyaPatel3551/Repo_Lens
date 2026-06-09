from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.models.report import Report
from src.repositories.base import BaseRepository

class ReportRepository(BaseRepository[Report]):
    """
    Repository class handling database interactions for the Report model.
    """
    def __init__(self, db: AsyncSession):
        super().__init__(Report, db)

    async def get_by_github_url(self, github_url: str) -> Optional[Report]:
        """
        Fetch the most recent report generated for a specific GitHub URL.
        """
        result = await self.db.execute(
            select(self.model)
            .where(self.model.github_url == github_url)
            .order_by(self.model.created_at.desc())
        )
        return result.scalars().first()
