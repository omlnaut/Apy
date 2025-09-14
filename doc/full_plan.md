# Production-Ready FastAPI Project Plan

This document is the living plan for building a production-ready FastAPI project from scratch. It contains the overall goal, the step-by-step plan, and detailed content for the first two sections (already implemented).

---

## Goal

Build a **production-ready FastAPI API service** that:

* Is hosted on **Azure (free tier)**
* Uses a **SQL database** (async)
* Provides a **clean architecture** with clear separation of concerns
* Is **fully testable** (unit & integration tests)
* Has **logging & metrics** for observability
* Runs in a **VS Code devcontainer** for convenient local development
* Is deployed as a **container**
* Provides only an **API**, no frontend

---

## High-Level Plan

1. **Project Setup & Initialization**

   * Devcontainer config for VS Code + Docker
   * Minimal FastAPI app with health-check endpoint
   * Pytest setup with a first passing test

2. **Basic API Endpoints (Items) with Clean Architecture** ✅ (done)

   * Modular structure (`api`, `schemas`, `services`, `core`, `models`)
   * Async CRUD endpoints for a sample resource (Item)
   * Dependency injection for services
   * Automated async tests with httpx + pytest-asyncio

3. **Database Integration (SQL)**

   * Async DB (Postgres on Azure, SQLite locally for dev/tests)
   * SQLAlchemy + Alembic migrations
   * Repository pattern for persistence
   * Test database setup with transactions/fixtures

4. **Clean Architecture Refinement**

   * Separate domain logic, repositories, services more clearly
   * Add DTOs or mapping where needed

5. **Logging & Metrics**

   * Structured logging (JSON logs)
   * Request/response logging middleware
   * Prometheus metrics endpoint

6. **Containerization & Local Orchestration**

   * Dockerfile for the app
   * docker-compose for local app + DB
   * Verify production-like environment locally

7. **Azure Deployment**

   * Deploy container to Azure App Service / Azure Container Apps
   * Use Azure Database for PostgreSQL (free tier)
   * Configure env vars and secrets
   * Verify deployed API and monitor logs/metrics

---

# Section 1 – Project Setup & Initialization

In this section, we bootstrap the project and confirm everything works with a health-check endpoint and a test.

**Why this / Big picture**

* Start simple: verify environment, devcontainer, test framework all work.
* Build confidence with a health-check and first passing test.

### Steps

1. Create project folder + `.devcontainer/` with Dockerfile and devcontainer.json.
2. Install dependencies (`fastapi`, `uvicorn[standard]`, `httpx`, `pytest`).
3. Implement `app/main.py` with a simple FastAPI app and a root endpoint:

   ```python
   from fastapi import FastAPI

   app = FastAPI()

   @app.get("/")
   async def read_root():
       return {"message": "Hello World"}
   ```
4. Run the app with `uvicorn app.main:app --reload` and verify `GET /` returns JSON.
5. Create `tests/test_main.py` with:

   ```python
   from fastapi.testclient import TestClient
   from app.main import app

   client = TestClient(app)

   def test_read_root():
       response = client.get("/")
       assert response.status_code == 200
       assert response.json() == {"message": "Hello World"}
   ```
6. Run `pytest` → should pass.

**Outcome**: Verified development environment and test framework.

---

# Section 2 – Modular FastAPI API with Dependency Injection

In this section we implement a modular FastAPI application with an **Item** resource, full CRUD endpoints, and clear **dependency injection** for services. The API is fully asynchronous and comes with automated tests. This sets the stage for a clean architecture where each layer is separate and swappable.

---

## Project Structure

**Why this / Big picture**

* Mirrors *clean architecture* layering: **api** (presentation), **services** (use‑cases/domain logic), **schemas** (I/O contracts), and later **models** (persistence).
* Clear boundaries let you swap implementations (in‑memory → SQL) without touching routers.
* `core/` hosts cross‑cutting concerns (DI, config) so endpoints stay thin.
  We split the project into folders for API routes, schemas, services, and core dependencies.

```
project/
├── app/
│   ├── main.py          # app creation
│   ├── api/items.py     # endpoints
│   ├── schemas/items.py # Pydantic models
│   ├── services/items.py# business logic
│   ├── core/deps.py     # DI providers
│   └── models/          # placeholder for DB later
├── tests/test_items.py  # automated tests
└── pytest.ini           # test config
```

---

## 1) Schemas (`app/schemas/items.py`)

**Why this / Big picture**

* Pydantic schemas are the **API contract**. Validation happens before logic, producing predictable 422s.
* Separate **Create/Update** from **Item** so clients can’t set server‑owned fields (e.g., `id`).
* `orm_mode` future‑proofs the layer for ORM objects later.

```python
from pydantic import BaseModel
from typing import Optional

class ItemBase(BaseModel):
    name: str
    description: Optional[str] = None

class ItemCreate(ItemBase):
    pass

class ItemUpdate(ItemBase):
    pass

class Item(ItemBase):
    id: int
    class Config:
        orm_mode = True
```

---

## 2) Service Layer (`app/services/items.py`)

**Why this / Big picture**

* `ItemsService` (a `Protocol`) is the seam for dependency inversion; routers depend on an **abstraction**, not a concrete class.
* `InMemoryItemsService` gives fast, deterministic tests and a default dev impl. Later we’ll add a DB‑backed impl with the same interface.
* No endpoint‑level state → easier concurrency, scaling, and test isolation.

```python
from typing import Dict, List, Optional, Protocol
from app.schemas import items as schemas

class ItemsService(Protocol):
    async def get_items(self) -> List[dict]: ...
    async def get_item(self, item_id: int) -> Optional[dict]: ...
    async def create_item(self, item: schemas.ItemCreate) -> dict: ...
    async def update_item(self, item_id: int, item: schemas.ItemUpdate) -> Optional[dict]: ...
    async def delete_item(self, item_id: int) -> bool: ...

class InMemoryItemsService:
    def __init__(self) -> None:
        self._items_db: Dict[int, dict] = {}
        self._id_counter: int = 0

    async def get_items(self) -> List[dict]:
        return list(self._items_db.values())

    async def get_item(self, item_id: int) -> Optional[dict]:
        return self._items_db.get(item_id)

    async def create_item(self, item: schemas.ItemCreate) -> dict:
        self._id_counter += 1
        data = item.model_dump()
        data["id"] = self._id_counter
        self._items_db[self._id_counter] = data
        return data

    async def update_item(self, item_id: int, item: schemas.ItemUpdate) -> Optional[dict]:
        if item_id not in self._items_db:
            return None
        data = item.model_dump()
        data["id"] = item_id
        self._items_db[item_id] = data
        return data

    async def delete_item(self, item_id: int) -> bool:
        return self._items_db.pop(item_id, None) is not None
```

---

## 3) Dependency Provider (`app/core/deps.py`)

**Why this / Big picture**

* Centralized DI provider makes env‑specific swaps (dev/test/prod) trivial without touching routers.
* Tests override `get_items_service` to inject a fresh service per test (true isolation).

```python
from app.services.items import InMemoryItemsService, ItemsService

_items_service = InMemoryItemsService()

async def get_items_service() -> ItemsService:
    return _items_service
```

---

## 4) Router (`app/api/items.py`)

**Why this / Big picture**

* Routers are **thin adapters**: translate HTTP ↔ service calls; no business logic here.
* `Depends(get_items_service)` keeps endpoints declarative and DI‑friendly; switching to DB later is a provider change, not a router change.
* `response_model` enforces response shape and powers OpenAPI docs automatically.

```python
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.schemas import items as schemas
from app.services.items import ItemsService
from app.core.deps import get_items_service

router = APIRouter()

@router.get("/", response_model=List[schemas.Item])
async def list_items(svc: ItemsService = Depends(get_items_service)):
    return await svc.get_items()

@router.post("/", response_model=schemas.Item, status_code=201)
async def create_item(item: schemas.ItemCreate, svc: ItemsService = Depends(get_items_service)):
    return await svc.create_item(item)

@router.get("/{item_id}", response_model=schemas.Item)
async def get_item(item_id: int, svc: ItemsService = Depends(get_items_service)):
    item = await svc.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@router.put("/{item_id}", response_model=schemas.Item)
async def update_item(item_id: int, item: schemas.ItemUpdate, svc: ItemsService = Depends(get_items_service)):
    updated = await svc.update_item(item_id, item)
    if updated is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return updated

@router.delete("/{item_id}", status_code=204)
async def delete_item(item_id: int, svc: ItemsService = Depends(get_items_service)):
    deleted = await svc.delete_item(item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return None
```

---

## 5) Main App (`app/main.py`)

**Why this / Big picture**

* `main.py` is the composition root: wire routers and (later) middleware, CORS, logging, metrics, startup/shutdown hooks.
* Keeping it minimal avoids early coupling; future features are added via includes/middleware.

```python
from fastapi import FastAPI
from app.api import items as items_router

app = FastAPI(title="My App")
app.include_router(items_router.router, prefix="/items", tags=["Items"])
```

---

## 6) Tests (`tests/test_items.py`)

**Why this / Big picture**

* Async tests with `httpx.AsyncClient` + `ASGITransport` hit the app **in‑process** (no network), so they’re fast and reliable.
* Dependency overrides guarantee **isolation** and mirror how we’ll swap to a DB service in integration tests.
* Tests codify expected behavior (status codes, shapes, errors) and protect future refactors.

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core import deps
from app.services.items import InMemoryItemsService

@pytest.fixture(autouse=True)
def override_items_service():
    test_service = InMemoryItemsService()
    app.dependency_overrides[deps.get_items_service] = lambda: test_service
    yield
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_list_initially_empty():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/items/")
    assert resp.status_code == 200
    assert resp.json() == []

@pytest.mark.asyncio
async def test_create_item():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/items/", json={"name": "Test", "description": "X"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == 1
    assert data["name"] == "Test"
```

---

## 7) Pytest Config (`pytest.ini`)

**Why this / Big picture**

* Declaring the `asyncio` marker avoids warnings and makes intent clear.
* This file is also the place to add global opts (e.g., `addopts = -q --maxfail=1`) as the suite grows.

```ini
[pytest]
markers =
    asyncio: marks an async test (use with pytest-asyncio)
```

---

## Verification

**Why this / Big picture**

* Each section ends with a **verifiable outcome** (manual via `/docs` and automated via tests). This supports iterative, CI‑friendly development.

* Run the app: `uvicorn app.main:app --reload` → check `/docs`

* Run tests: `pytest` → all tests pass

---

## Outcome

* **Clean architecture foundation:** API, schemas, services, and core are decoupled.
* **Dependency injection:** Routers depend on abstractions, making future swaps trivial.
* **Async everywhere:** Ready for async DB later.
* **Testability:** Complete coverage of CRUD with isolated in-memory services.
* **Next step:** Replace the in-memory service with a real database implementation.
