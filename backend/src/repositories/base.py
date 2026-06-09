from typing import Generic, TypeVar, Type, Optional, List, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

ModelType = TypeVar("ModelType")

class BaseRepository(Generic[ModelType]):
    """
    Generic Base Repository that provides basic CRUD operations for database models.
    """
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get(self, id: Any) -> Optional[ModelType]:
        """
        Fetch a single database record by primary key id.
        """
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalars().first()

    async def get_multi(self, *, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """
        Fetch multiple records with offset pagination.
        """
        result = await self.db.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def create(self, obj_in: ModelType) -> ModelType:
        """
        Insert a new model record.
        """
        self.db.add(obj_in)
        await self.db.flush()  # Populates id without full commit
        return obj_in

    async def update(self, db_obj: ModelType, update_data: Dict[str, Any]) -> ModelType:
        """
        Update fields on an existing model record.
        """
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        self.db.add(db_obj)
        await self.db.flush()
        return db_obj

    async def remove(self, id: Any) -> Optional[ModelType]:
        """
        Delete a database record by id.
        """
        obj = await self.get(id)
        if obj:
            await self.db.delete(obj)
            await self.db.flush()
        return obj
