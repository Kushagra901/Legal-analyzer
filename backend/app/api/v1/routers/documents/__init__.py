"""
Documents router package.
Consolidates CRUD, analysis, clause review, and document chat sub-routers into a master router.
"""

import logging

from fastapi import APIRouter

from app.api.v1.routers.documents.analysis import (
    router as analysis_router,
)
from app.api.v1.routers.documents.analysis import (
    run_report,
)
from app.api.v1.routers.documents.chat import router as chat_router
from app.api.v1.routers.documents.crud import (
    ensure_test_user_exists,
    trigger_n8n_webhook,
)
from app.api.v1.routers.documents.crud import (
    router as crud_router,
)
from app.api.v1.routers.documents.review import router as review_router
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

router = APIRouter()

router.include_router(crud_router)
router.include_router(analysis_router)
router.include_router(review_router)
router.include_router(chat_router)

__all__ = [
    "logger",
    "router",
    "crud_router",
    "analysis_router",
    "review_router",
    "chat_router",
    "ensure_test_user_exists",
    "trigger_n8n_webhook",
    "run_report",
    "LLMService",
]


