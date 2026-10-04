"""WhistleDrop FastAPI Application Entrypoint.

Provides a confidential, anonymous misconduct reporting REST API.
"""

from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from app.config import get_settings
from app.database import init_db
from app.routers import moderator, reports

# Setup privacy-preserving logging: do not log request bodies, case codes, or auth tokens
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("whistledrop")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown events."""
    logger.info("Starting WhistleDrop Backend...")
    # Automatically initialize SQLite tables for development/testing
    init_db()
    logger.info("Database tables initialized successfully.")
    yield
    logger.info("WhistleDrop Backend shutting down.")


app = FastAPI(
    title="WhistleDrop API",
    description=(
        "Confidential, anonymous reporting backend system. "
        "Allows individuals to submit reports and track their status using cryptographic case codes "
        "without disclosing identity, collecting tracking telemetry, or requiring account registration."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


@app.middleware("http")
async def privacy_and_security_headers_middleware(request: Request, call_next):
    """Add defensive privacy and security headers to every HTTP response."""
    response: Response = await call_next(request)
    # Prevent caching of confidential case information in intermediate proxies
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


# Register API Routers
app.include_router(reports.router, prefix=f"{settings.API_V1_STR}/reports")
app.include_router(moderator.router, prefix=f"{settings.API_V1_STR}/moderator")


@app.get(
    "/",
    tags=["General"],
    summary="API Root Information",
    description="Returns service status and link to interactive documentation.",
)
def root():
    """Service status and documentation entrypoint."""
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "status": "online",
        "documentation": "/docs",
        "redoc": "/redoc",
    }


@app.get(
    "/health",
    tags=["General"],
    summary="Health check",
    description="Returns healthy status for load balancers or uptime monitoring.",
)
def health_check():
    """Service health check."""
    return {"status": "healthy"}
