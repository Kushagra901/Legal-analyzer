"""
Pydantic v2 validation and serialization schemas for API requests and responses.
"""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check endpoint response schema."""
    status: str = Field(..., description="Current system operational status")


class AuthMessageResponse(BaseModel):
    """Authentication endpoints response schema."""
    message: str = Field(..., description="Status message for authentication operation")


class CitationResponse(BaseModel):
    """Legal citation reference schema."""
    source: str = Field(..., description="Legal authority or source document")
    citation: str = Field(..., description="Citation excerpt or rule reference")


class ClauseResponse(BaseModel):
    """Extracted contract clause schema."""
    id: str | None = Field(default=None, description="Unique clause UUID")
    type: str = Field(..., description="Category/type of contract clause")
    text: str = Field(..., description="Verbatim clause text")
    explanation: str = Field(..., description="Plain-English explanation or risk context")
    severity: str = Field(..., description="Risk severity level: LOW, MEDIUM, or HIGH")


class AnalysisDetailResponse(BaseModel):
    """Detailed contract AI analysis schema."""
    safety_score: int = Field(..., description="Safety score from 0 (unsafe) to 100 (fully safe)")
    risk_level: str = Field(..., description="Overall document risk level: LOW, MEDIUM, or HIGH")
    summary: str = Field(..., description="Plain-English summary of contract terms")
    clauses: list[ClauseResponse] = Field(default_factory=list, description="Extracted clause objects")
    citations: list[CitationResponse] = Field(default_factory=list, description="Legal reference citations")
    recommendations: list[str] = Field(default_factory=list, description="Actionable review recommendations")
    compliance_violations: list[str] = Field(default_factory=list, description="Policy violation descriptions")


class UploadResponse(BaseModel):
    """Document upload action response schema."""
    document_id: str = Field(..., description="UUID of the uploaded document")
    filename: str = Field(..., description="Original filename of the document")
    status: str = Field(..., description="Current processing status")
    uploaded_at: str = Field(..., description="ISO 8601 upload timestamp")
    storage_path: str = Field(..., description="Cloud storage object reference key")


class DocumentListItemResponse(BaseModel):
    """Summary item schema for document listings."""
    document_id: str = Field(..., description="UUID of the document")
    filename: str = Field(..., description="Original filename")
    status: str = Field(..., description="Processing status")
    uploaded_at: str | None = Field(default=None, description="ISO 8601 upload timestamp")


type DocumentListResponse = list[DocumentListItemResponse]


class DocumentResponse(BaseModel):
    """Full detail response schema for a document."""
    document_id: str = Field(..., description="UUID of the document")
    filename: str = Field(..., description="Original filename")
    status: str = Field(..., description="Processing status")
    uploaded_at: str | None = Field(default=None, description="ISO 8601 upload timestamp")
    original_text: str | None = Field(default=None, description="Extracted raw text content")
    analysis: AnalysisDetailResponse | None = Field(default=None, description="AI analysis details")


class ReportResponse(BaseModel):
    """Memorandum report output response schema."""
    document_id: str = Field(..., description="UUID of the document")
    filename: str = Field(..., description="Original filename")
    uploaded_at: str | None = Field(default=None, description="ISO 8601 upload timestamp")
    report_url: str = Field(..., description="URL path to generated PDF report")
    safety_score: int = Field(..., description="Safety score from 0 to 100")
    risk_level: str = Field(..., description="Overall document risk level")
    summary: str = Field(..., description="Plain-English summary of contract terms")
    recommendations: list[str] = Field(default_factory=list, description="Actionable review recommendations")
    citations: list[CitationResponse] = Field(default_factory=list, description="Legal reference citations")


class AnalysisStatusResponse(BaseModel):
    """Status update response schema for pipeline actions."""
    status: str = Field(..., description="Updated processing or pipeline status")
    progress: int | float | None = Field(default=100, description="Processing progress percentage from 0 to 100")
    error: str | None = Field(default=None, description="Error detail message if processing failed")
    message: str | None = Field(default=None, description="Action detail message")
    document_id: str | None = Field(default=None, description="UUID of target document")
    filename: str | None = Field(default=None, description="Original document filename")
    summary: str | None = Field(default=None, description="Generated summary if available")
    report_url: str | None = Field(default=None, description="Generated report URL if available")
    safety_score: int | None = Field(default=None, description="Safety score if available")
    risk_level: str | None = Field(default=None, description="Risk level if available")
    violations: list[str] | None = Field(default=None, description="Compliance violations if available")


class AuditLogItemResponse(BaseModel):
    """Individual audit log entry schema."""
    id: str = Field(..., description="Audit log entry UUID")
    action: str = Field(..., description="Recorded audit action description")
    document_id: str = Field(..., description="Associated document UUID")
    user: str = Field(..., description="Email or entity performing action")
    timestamp: str = Field(..., description="Formatted event timestamp")


type AuditLogResponse = list[AuditLogItemResponse]


class ClauseReviewCreate(BaseModel):
    """Schema for submitting or updating a clause review decision."""
    decision: str = Field(..., description="Review decision: pending, approved, or redline_flagged")
    note: str | None = Field(default=None, description="Optional attorney review note")


class ClauseReviewResponse(BaseModel):
    """Schema for returning a clause review record."""
    id: str = Field(..., description="UUID of the clause review record")
    clause_id: str = Field(..., description="UUID of the reviewed clause")
    document_id: str = Field(..., description="UUID of the document")
    user_id: str = Field(..., description="UUID of the reviewing user")
    decision: str = Field(..., description="Review decision: pending, approved, or redline_flagged")
    note: str | None = Field(default=None, description="Attorney review note")
    reviewed_at: str = Field(..., description="ISO 8601 timestamp of review")

