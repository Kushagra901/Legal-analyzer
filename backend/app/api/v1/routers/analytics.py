from typing import Any, Dict, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

from app.core.database import get_db
from app.core.auth import get_current_user
from app.services.analytics_etl_service import AnalyticsETLService

router = APIRouter(prefix="/analytics", tags=["analytics"])

class RiskTrendResponse(BaseModel):
    document_id: UUID
    user_id: UUID
    uploaded_at: Any
    safety_score: int
    risk_level: str
    upload_sequence: int
    rolling_avg_3: float | None
    prev_score: int | None
    score_change: int | None
    risk_rank: int

class ClauseDistributionResponse(BaseModel):
    category: str | None
    category_total: int
    grand_total: int
    category_pct: float
    popularity_rank: int

class UserMetricsResponse(BaseModel):
    user_id: UUID
    total_documents: int
    high_risk_count: int
    latest_document: str | None
    activity_quartile: int

class ETLResponse(BaseModel):
    document_id: str | None = None
    fact_document_analyses_created: bool | None = None
    fact_clause_risks_count: int | None = None
    status: str | None = None
    documents_processed: int | None = None
    clauses_processed: int | None = None
    error: str | None = None
    message: str | None = None

@router.get("/risk-trends", response_model=List[RiskTrendResponse])
def get_risk_trends(db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    """Get document risk trends from the v_document_risk_trends view (current user only)."""
    query = text("SELECT * FROM v_document_risk_trends WHERE user_id = :user_id")
    result = db.execute(query, {"user_id": current_user.id}).mappings().all()
    return result

@router.get("/clause-distribution", response_model=List[ClauseDistributionResponse])
def get_clause_distribution(db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    """Get clause category distribution from v_clause_category_distribution."""
    query = text("SELECT * FROM v_clause_category_distribution")
    result = db.execute(query).mappings().all()
    return result

@router.get("/user-metrics", response_model=List[UserMetricsResponse])
def get_user_metrics(db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    """Get user activity metrics from v_user_activity_metrics (current user only)."""
    query = text("SELECT * FROM v_user_activity_metrics WHERE user_id = :user_id")
    result = db.execute(query, {"user_id": current_user.id}).mappings().all()
    return result

@router.post("/etl/{document_id}", response_model=ETLResponse)
def trigger_etl(document_id: UUID, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    """Trigger ETL for a specific document. Admin only."""
    if not getattr(current_user, "is_superuser", False):
         raise HTTPException(status_code=403, detail="Admin access required")
    
    service = AnalyticsETLService(db)
    result = service.run_full_etl(document_id)
    return result

@router.post("/backfill", response_model=ETLResponse)
def trigger_backfill(db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    """Trigger full backfill. Admin only."""
    if not getattr(current_user, "is_superuser", False):
         raise HTTPException(status_code=403, detail="Admin access required")
         
    service = AnalyticsETLService(db)
    result = service.backfill_all_documents()
    return result
