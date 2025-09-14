from fastapi import FastAPI
from app.api.ItemRouter import router as item_router

app = FastAPI()

app.include_router(item_router, prefix="/items", tags=["items"])


@app.get("/")
async def read_root():
    return {"Hello": "World"}
