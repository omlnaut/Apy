from typing import List, Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.item import ItemModel
from app.schemas.ItemSchemas import ItemCreate, ItemUpdate


class ItemsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(self) -> Sequence[ItemModel]:
        result = await self.session.execute(select(ItemModel))
        return result.scalars().all()

    async def get(self, item_id: int) -> Optional[ItemModel]:
        return await self.session.get(ItemModel, item_id)

    async def create(self, data: ItemCreate) -> ItemModel:
        item = ItemModel(**data.model_dump())
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def update(self, item_id: int, data: ItemUpdate) -> Optional[ItemModel]:
        item = await self.get(item_id)
        if not item:
            return None
        for field, value in data.model_dump().items():
            setattr(item, field, value)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def delete(self, item_id: int) -> bool:
        item = await self.get(item_id)
        if not item:
            return False
        await self.session.delete(item)
        await self.session.commit()
        return True
