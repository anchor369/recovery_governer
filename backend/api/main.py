from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import demo, health, metrics, payments, recovery
from backend.db import close_connection_pool, open_connection_pool


@asynccontextmanager
async def lifespan(_app):
    open_connection_pool()
    try:
        yield
    finally:
        close_connection_pool()


app = FastAPI(
    title="Recovery Governor API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(health.router)
app.include_router(payments.router)
app.include_router(demo.router)
app.include_router(recovery.router)
app.include_router(metrics.router)
