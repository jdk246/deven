from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401
from app.config import get_settings
from app.db import Base, engine
from app.routers.admin import router as admin_router
from app.routers.agent import router as agent_router
from app.routers.chat import router as chat_router
from app.routers.insights import router as insights_router
from app.routers.kols import router as kols_router
from app.routers.tokens import router as tokens_router
from app.schemas import HealthResponse

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="trust-trace backend",
    version="0.2.0",
    description="Core FastAPI service for the trust-trace monorepo.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router)
app.include_router(agent_router)
app.include_router(chat_router)
app.include_router(insights_router)
app.include_router(kols_router)
app.include_router(tokens_router)


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health_check() -> HealthResponse:
    return HealthResponse()
