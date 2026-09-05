from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import demo, health, metrics, payments, recovery


app = FastAPI(
    title="Recovery Governor API",
    version="1.0.0",
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
