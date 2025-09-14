from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from app.core.deps import get_items_service
from app.schemas import ItemSchemas as schemas
from app.services.ItemsService.ItemsService import ItemsService


router = APIRouter()


@router.get("/", response_model=list[schemas.Item])
async def list_items(items_service: get_items_service):
    return await items_service.get_items()


@router.post("/", response_model=schemas.Item, status_code=201)
async def create_item(
    item_create: schemas.ItemCreate,
    items_service: get_items_service,
):
    return await items_service.create_item(item_create)


@router.get("/{item_id}", response_model=schemas.Item)
async def get_item(
    item_id: int,
    items_service: get_items_service,
):
    item = await items_service.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.put("/{item_id}", response_model=schemas.Item)
async def update_item(
    item_id: int,
    item_update: schemas.ItemUpdate,
    items_service: get_items_service,
):
    updated_item = await items_service.update_item(item_id, item_update)
    if updated_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return updated_item


@router.delete("/{item_id}", status_code=204)
async def delete_item(
    item_id: int,
    items_service: get_items_service,
):
    success = await items_service.delete_item(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Item not found")
    return None
