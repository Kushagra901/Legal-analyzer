"""
Main entry point for the FastAPI application.
Configures middleware, registers routers, and initializes the status handler.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routers import admin, auth, documents, reports
from app.core.config import settings

app = FastAPI(
    title="Legal Analyzer API",
    description="Backend API for Legal Analyzer legal contract audit service",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers under /api/v1 prefix
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Administration"])


@app.get("/health")
def health_check() -> dict[str, str]:
    """
    Retrieves the service health status.

    Returns:
        dict[str, str]: A dictionary showing the current server status.
    """
    return {"status": "healthy"}
