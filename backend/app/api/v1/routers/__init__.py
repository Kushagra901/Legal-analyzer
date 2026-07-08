"""
Package initialization for API v1 routers.
Imports all routers to make them accessible by the main app configuration.
"""

from app.api.v1.routers import admin, auth, documents, reports

__all__ = ["admin", "auth", "documents", "reports"]
