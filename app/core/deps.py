from typing import Annotated

from fastapi import Depends
from app.services.ItemsService.ItemsService import ItemsService
from app.services.ItemsService.InMemoryItemsService import InMemoryItemsService


_items_service = InMemoryItemsService()


async def _get_items_service() -> ItemsService:
    return _items_service


get_items_service = Annotated[ItemsService, Depends(_get_items_service)]
