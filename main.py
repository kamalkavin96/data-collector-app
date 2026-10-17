from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

import app.models
from app.api.routes import locations, upload
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title= settings.APP_TITLE , version="1.0.0", lifespan=lifespan)
app.include_router(upload.router)
app.include_router(locations.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_RELOAD,
        log_level=settings.LOG_LEVEL,
    )
