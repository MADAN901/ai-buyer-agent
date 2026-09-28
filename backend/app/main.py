"""FastAPI application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings
from app.db.database import Base, engine

settings = get_settings()
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Purchasing Agent",
    description="Investigate → decide → act → validate → recover purchasing agent",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "llm_provider": settings.llm_provider}
