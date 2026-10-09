"""
Main entry point for the FastAPI application.
Configures middleware, registers routers, and initializes the status handler.
"""

from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.routers import admin, analytics, auth, documents, reports, system
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import setup_logging
from app.core.request_id import RequestIDMiddleware
from app.core.security_headers import SecurityHeadersMiddleware
from app.models.schemas import HealthResponse
from app.services.mcp_server import create_mcp_router

# Validate production secrets on startup/module load
settings.validate_production_secrets()

if settings.SENTRY_DSN:
    sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=0.1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Enforce production secrets check during application lifespan startup
    settings.validate_production_secrets()
    yield


setup_logging()

app = FastAPI(
    title="Legal Analyzer API",
    description="Backend API for Legal Analyzer legal contract audit service",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure Rate Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Configure Security Headers
app.add_middleware(SecurityHeadersMiddleware)

# Configure Request ID Correlation
app.add_middleware(RequestIDMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Internal-Token"],
    expose_headers=["X-Request-ID"],
    max_age=600,
)

# Register API Routers under /api/v1 prefix
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Administration"])
app.include_router(system.router, prefix="/api/v1/system", tags=["System"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(create_mcp_router(), prefix="/mcp", tags=["MCP"])


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """
    Retrieves the service health status.

    Returns:
        HealthResponse: The operational health status schema.
    """
    return HealthResponse(status="healthy")
