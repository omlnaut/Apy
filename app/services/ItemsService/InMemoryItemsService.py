from app.schemas.ItemSchemas import ItemCreate


class InMemoryItemsService:
    def __init__(self) -> None:
        self._items_db: dict[int, dict] = {}
        self._id_counter: int = 0

    async def get_items(self) -> list[dict]:
        return list(self._items_db.values())

    async def get_item(self, item_id: int, user_id: int) -> dict | None:
        return self._items_db.get(item_id)

    async def create_item(self, item_create: ItemCreate) -> dict:
        self._id_counter += 1

        item = item_create.model_dump()
        item["id"] = self._id_counter

        self._items_db[self._id_counter] = item
        return item

    async def update_item(self, item_id: int, item_update: ItemCreate) -> dict | None:
        if item_id not in self._items_db:
            return None

        updated_item = item_update.model_dump()
        updated_item["id"] = item_id
        self._items_db[item_id] = updated_item

        return updated_item

    async def delete_item(self, item_id: int) -> bool:
        return self._items_db.pop(item_id, None) is not None
