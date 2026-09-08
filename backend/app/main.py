from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    demo_router,
    health_router,
    operations_router,
    workflows_router,
)
from app.core.config import get_settings
from app.db.session import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Initialize SQLite tables if using local fallback database
    init_db()
    from app.db.seed_helper import seed_demo_data
    from app.db.session import SessionLocal
    with SessionLocal() as db:
        seed_demo_data(db)
    yield


app = FastAPI(
    title=get_settings().app_name,
    version="2.0.0",
    description="Production-grade AI Operations Agent with Google Cloud MySQL and SQL Guardrail Engine.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", get_settings().frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(workflows_router, prefix="/api", tags=["workflows"])
app.include_router(operations_router, prefix="/api", tags=["operations"])
app.include_router(demo_router, prefix="/api", tags=["demo"])

# Instrument FastAPI backend with langgraph-observe universal client SDK
from langgraph_observe import instrument_fastapi
instrument_fastapi(
    app,
    server_url=get_settings().observe_server_url,
    project=get_settings().observe_project,
    environment=get_settings().observe_environment,
    trace_id_header="X-LangGraph-Trace-ID",
)


