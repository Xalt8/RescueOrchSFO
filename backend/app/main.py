"""Rescue Command Center - FastAPI Backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import mavic, tiago

app = FastAPI(
    title="Rescue Command Center API",
    description="API for controlling Mavic drone and Tiago robot in rescue operations",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mavic.router)
app.include_router(tiago.router)


@app.get("/")
def root():
    return {"message": "Rescue Command Center API", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}
