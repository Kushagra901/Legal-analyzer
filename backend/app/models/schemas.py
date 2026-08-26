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


DocumentListResponse = list[DocumentListItemResponse]


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
    clauses: list[ClauseResponse] = Field(default_factory=list, description="Categorized clauses and risk flags")
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


AuditLogResponse = list[AuditLogItemResponse]


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


class ChatRequest(BaseModel):
    """Request schema for document Q&A chat."""
    query: str = Field(..., description="User's question about the document", min_length=1, max_length=2000)
    conversation_id: str | None = Field(default=None, description="Optional conversation UUID for multi-turn threads")


class ChatCitationResponse(BaseModel):
    """Citation reference within a chat answer."""
    clause_id: str | None = Field(default=None, description="UUID of the referenced clause")
    clause_type: str = Field(..., description="Type/category of the cited clause")
    snippet: str = Field(..., description="Relevant text excerpt from the clause")
    section_reference: str | None = Field(default=None, description="Section number reference (e.g. Section 8.2)")


class ChatResponse(BaseModel):
    """Response schema for document Q&A chat."""
    answer: str = Field(..., description="Grounded answer based on document content")
    citations: list[ChatCitationResponse] = Field(default_factory=list, description="Clause citations supporting the answer")
    confidence: str = Field(default="MEDIUM", description="Answer confidence: HIGH, MEDIUM, or LOW")
    disclaimer: str = Field(default="This AI response assists document review and is not legal advice.", description="Legal disclaimer")


class ChatHistoryItemResponse(BaseModel):
    """Individual chat message in conversation history."""
    id: str = Field(..., description="Message UUID")
    role: str = Field(..., description="Message sender role: user or assistant")
    content: str = Field(..., description="Message text content")
    citations: list[ChatCitationResponse] = Field(default_factory=list, description="Citations if assistant message")
    confidence: str | None = Field(default=None, description="Confidence level if assistant message")
    created_at: str = Field(..., description="ISO 8601 timestamp")


class ObligationItem(BaseModel):
    """Individual obligation extracted from document."""
    party: str = Field(..., description="Party responsible for the obligation")
    obligation: str = Field(..., description="Description of the obligation")
    deadline: str | None = Field(default=None, description="Deadline or timeframe")
    trigger: str | None = Field(default=None, description="Event that triggers the obligation")
    penalty: str | None = Field(default=None, description="Consequence of non-compliance")


class RiskFlagItem(BaseModel):
    """Individual risk flag from deep extraction."""
    clause_type: str = Field(..., description="Type of the flagged clause")
    severity: str = Field(..., description="Risk severity: LOW, MEDIUM, or HIGH")
    issue: str = Field(..., description="Description of the risk issue")
    original_text: str | None = Field(default=None, description="Original clause text")
    page_reference: str | None = Field(default=None, description="Section or page reference")


class RedlineItem(BaseModel):
    """Individual redline suggestion from deep extraction."""
    clause_type: str = Field(..., description="Type of clause being redlined")
    original_text: str = Field(..., description="Original clause text")
    suggested_replacement: str = Field(..., description="Suggested replacement clause text")
    rationale: str = Field(..., description="Business rationale for the change")


class DealTermsResponse(BaseModel):
    """Extracted deal terms from the document."""
    parties: list[str] = Field(default_factory=list, description="Contracting party names")
    effective_date: str | None = Field(default=None, description="Contract effective date")
    expiration_date: str | None = Field(default=None, description="Contract expiration date")
    auto_renewal: bool | None = Field(default=None, description="Whether auto-renewal is present")
    renewal_notice_days: int | None = Field(default=None, description="Days of notice required before renewal")
    governing_law: str | None = Field(default=None, description="Governing law jurisdiction")
    jurisdiction: str | None = Field(default=None, description="Court jurisdiction")
    document_type: str | None = Field(default=None, description="Type of legal document")


class DeepExtractionResponse(BaseModel):
    """Full deep extraction response schema."""
    document_id: str = Field(..., description="UUID of the document")
    deal_terms: DealTermsResponse = Field(default_factory=DealTermsResponse, description="Extracted deal terms")
    obligations: list[ObligationItem] = Field(default_factory=list, description="Extracted obligations")
    risk_flags: list[RiskFlagItem] = Field(default_factory=list, description="Identified risk flags")
    missing_protections: list[str] = Field(default_factory=list, description="Missing standard protective clauses")
    redline_suggestions: list[RedlineItem] = Field(default_factory=list, description="Suggested clause replacements")
    executive_summary: str = Field(default="", description="Plain-English executive summary")
    confidence: str = Field(default="MEDIUM", description="Overall extraction confidence")
    disclaimer: str = Field(default="This analysis assists document review and is not legal advice.", description="Legal disclaimer")
