import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core import deps
from app.services.ItemsService.InMemoryItemsService import InMemoryItemsService


@pytest.fixture(autouse=True)
def override_items_service():
    test_service = InMemoryItemsService()
    app.dependency_overrides[deps._get_items_service] = lambda: test_service
    yield
    app.dependency_overrides.clear()


async def test_list_initially_empty():
    async with test_client() as client:
        resp = await client.get("/items/")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_create_item():
    async with test_client() as client:
        resp = await client.post("/items/", json={"name": "Test", "description": "X"})

    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == 1
    assert data["name"] == "Test"
    assert data["description"] == "X"


def test_client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
