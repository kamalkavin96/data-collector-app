import sys
from pathlib import Path

# Lets both `python app/main.py` and `python -m app.main` work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from contextlib import asynccontextmanager  # noqa: E402

import uvicorn  # noqa: E402
from fastapi import FastAPI  # noqa: E402

import app.models  # noqa: E402, F401  (register models)
from app.api.routes import postal, upload  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)  # use Alembic for migrations in production
    yield


app = FastAPI(title="Department of Posts API", version="1.0.0", lifespan=lifespan)
app.include_router(upload.router)
app.include_router(postal.router)


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
