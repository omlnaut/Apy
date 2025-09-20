from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.services.ItemsService.ItemsService import ItemsService
from app.services.ItemsService.InMemoryItemsService import InMemoryItemsService
from app.services.items_db import ItemsRepository


async def _get_items_service(session: AsyncSession = Depends(get_session)):
    return ItemsRepository(session)


get_items_service = Annotated[ItemsService, Depends(_get_items_service)]
