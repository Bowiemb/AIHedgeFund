"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.api.core.config import settings
from apps.api.core.logging import setup_logging
from apps.api.v1.router import api_router
from packages.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan events."""
    # Startup
    setup_logging()

    # TODO: Initialize S3 buckets, Redis connections, etc.

    yield

    # Shutdown
    await engine.dispose()


app = FastAPI(
    title="AIHedgeFund API",
    description="AI-powered hedge fund platform with SEC data API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoints
@app.get("/healthz", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/readyz", tags=["health"])
async def readiness_check():
    """Readiness check endpoint."""
    # TODO: Check database, Redis, S3 connectivity
    return {"status": "ready"}


# Include API routers
app.include_router(api_router, prefix="/v1")


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
            }
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )
