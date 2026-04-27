from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.storage.minio_client import ensure_bucket_exists


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_bucket_exists()
    yield


app = FastAPI(title="wcaleniepracujpl-backend", lifespan=lifespan)
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
