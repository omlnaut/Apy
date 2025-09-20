# Section 3 – Database Integration (PostgreSQL) — Devcontainer + Zero‑manual Tests

In this section, we add a **real PostgreSQL** database. You’ll have:

* A **local Postgres** running automatically as a devcontainer *service* for manual API use.
* **Zero‑manual test DB** using **Testcontainers** (pytest spins a disposable Postgres for the test run). No `docker run` steps.
* Same repository/DI structure as before; only the implementation changes.

---

## Why this / Big picture

* **Local == Prod:** Postgres in dev and prod reduces surprises.
* **No manual steps in tests:** Testcontainers creates/tears down a clean DB for the suite → reproducible, isolated tests.
* **Clean architecture preserved:** Routers and services remain decoupled from persistence details via repositories and DI.

---

## 1) Dependencies

Add to `requirements.txt` (or `pyproject.toml`):

```
sqlalchemy[asyncio]==2.0.30
alembic==1.13.1
asyncpg==0.29.0
pytest-asyncio==0.23.8
testcontainers[postgresql]==4.9.0
```

---

## 2) Devcontainer with Postgres service (manual API use)

Use docker‑compose to run a DB **alongside** your devcontainer.

**.devcontainer/docker-compose.yml**

```yaml
version: "3.9"
services:
  app:
    build:
      context: ..
      dockerfile: .devcontainer/Dockerfile
    volumes:
      - ..:/workspace:cached
    command: sleep infinity
    depends_on:
      - db
    environment:
      # Inside the container, reach Postgres by service name `db`
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/fastapi_dev
    ports:
      - "8000:8000"   # FastAPI
  db:
    image: postgres:16
    restart: unless-stopped
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: fastapi_dev
    ports:
      - "5432:5432"   # Optional: expose to host (psql/GUI)
    volumes:
      - pgdata:/var/lib/postgresql/data
volumes:
  pgdata:
```

**.devcontainer/devcontainer.json**

```json
{
  "name": "fastapi-svc",
  "dockerComposeFile": ["docker-compose.yml"],
  "service": "app",
  "workspaceFolder": "/workspace",
  "customizations": {
    "vscode": {
      "extensions": ["ms-python.python", "ms-python.vscode-pylance"]
    }
  },
  "postCreateCommand": "pip install -r requirements.txt",
  "forwardPorts": [8000, 5432]
}
```

**.devcontainer/Dockerfile** (example)

```dockerfile
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /workspace
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates git \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
```

Now when you **Reopen in Container**, a Postgres server is already available at `db:5432` for your API.

---

## 3) Database config (`app/core/database.py`)

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    # Default matches the devcontainer compose setup
    "postgresql+asyncpg://postgres:postgres@db:5432/fastapi_dev"
)

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
```

---

## 4) Models (`app/models/item.py`)

```python
from sqlalchemy.orm import Mapped, mapped_column, declarative_base

Base = declarative_base()

class ItemModel(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str]
    description: Mapped[str | None]
```

---

## 5) Repository (`app/services/items_db.py`)

```python
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.item import ItemModel
from app.schemas.items import ItemCreate, ItemUpdate

class ItemsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(self) -> List[ItemModel]:
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
```

---

## 6) DI provider (`app/core/deps.py`)

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.services.items_db import ItemsRepository

async def get_items_service(session: AsyncSession = Depends(get_session)):
    return ItemsRepository(session)
```

Routers pick up the DB‑backed repo automatically.

---

## 7) Alembic migrations

Initialize Alembic once:

```bash
alembic init migrations
```

* In `alembic.ini`, set sqlalchemy.url to something like `${DATABASE_URL}` (or leave empty and supply env var at runtime).
* In `migrations/env.py`, import your metadata: `from app.models.item import Base as target_metadata`.
* Generate & apply:

```bash
alembic revision --autogenerate -m "create items table"
alembic upgrade head
```

---

## 8) Zero‑manual Postgres for tests (Testcontainers)

**Docker socket access in devcontainer**

* Testcontainers needs to talk to Docker. Inside a devcontainer, this works if you mount the host’s Docker socket into the container.
* Add to your `docker-compose.yml` service definition for `app`:

  ```yaml
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
  ```
* This way the devcontainer shares the host’s Docker daemon and can start sibling containers (like ephemeral Postgres).
* Ensure your user in the container has permission (often add to `docker` group or run as root).

Pytest will spin a disposable Postgres and inject its URL via dependency overrides.

**tests/conftest.py**

```python
import asyncio
import os
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

from app.main import app
from app.core.database import get_session
from app.models.item import Base

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def pg_container():
    with PostgresContainer("postgres:16") as pg:
        # Convert sync URL to asyncpg URL
        sync_url = pg.get_connection_url()  # e.g., postgresql://user:pass@host:port/db
        async_url = sync_url.replace("postgresql://", "postgresql+asyncpg://")
        yield async_url

@pytest.fixture(scope="session", autouse=True)
def create_schema(pg_container, event_loop):
    engine = create_async_engine(pg_container, echo=False, future=True)
    async def init_models():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    event_loop.run_until_complete(init_models())

@pytest.fixture()
def override_get_session(pg_container):
    engine = create_async_engine(pg_container, echo=False, future=True)
    SessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def _override():
        async with SessionLocal() as session:
            yield session
    app.dependency_overrides[get_session] = _override
    yield
    app.dependency_overrides.clear()
```

> Your existing async endpoint tests from Section 2 work unchanged. They now run against an ephemeral Postgres with **no manual setup**.

Run:

```bash
pytest -q
```

---

## 9) Manual API usage in devcontainer

* Start the app inside the container:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

* The app uses the compose‑provided DB at `db:5432` (via `DATABASE_URL`).
* Use `/docs` to CRUD items; data persists in the `pgdata` volume.

---

## Verification

* `alembic upgrade head` runs successfully inside the container.
* `/docs` works and persists data between restarts.
* `pytest` runs without any manual DB start/stop.

---

## Outcome

* **Local Postgres for manual dev** (via devcontainer service).
* **Disposable Postgres for tests** (via Testcontainers).
* Same DI/repository abstractions; no router changes.
* Ready for Azure Postgres by swapping `DATABASE_URL` in prod env.
