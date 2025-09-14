from app.services.ItemsService.ItemsService import ItemsService
from app.services.ItemsService.InMemoryItemsService import InMemoryItemsService


_items_service = InMemoryItemsService()


async def get_items_service() -> ItemsService:
    return _items_service
