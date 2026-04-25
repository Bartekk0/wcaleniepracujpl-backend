from fastapi import FastAPI

from app.api.router import api_router

app = FastAPI(title="wcaleniepracujpl-backend")
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
