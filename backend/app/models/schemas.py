"""
Pydantic v2 validation and serialization schemas for API requests and responses.
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class ClauseCategory(StrEnum):
    """
    Standard 41 clause categories defined by the CUAD (Contract Understanding Atticus Dataset) taxonomy.
    """
    DOCUMENT_NAME = "Document Name"
    PARTIES = "Parties"
    AGREEMENT_DATE = "Agreement Date"
    EFFECTIVE_DATE = "Effective Date"
    EXPIRATION_DATE = "Expiration Date"
    RENEWAL_TERM = "Renewal Term"
    NOTICE_PERIOD_TO_TERMINATE_RENEWAL = "Notice Period To Terminate Renewal"
    GOVERNING_LAW = "Governing Law"
    MOST_FAVORED_NATION = "Most Favored Nation"
    NON_COMPETE = "Non-Compete"
    EXCLUSIVITY = "Exclusivity"
    NO_SOLICIT_OF_CUSTOMERS = "No-Solicit Of Customers"
    NO_SOLICIT_OF_EMPLOYEES = "No-Solicit Of Employees"
    NON_DISPARAGEMENT = "Non-Disparagement"
    TERMINATION_FOR_CONVENIENCE = "Termination For Convenience"
    ROFR_ROFO_ROFN = "Rofr/Rofo/Rofn"
    CHANGE_OF_CONTROL = "Change Of Control"
    ANTI_ASSIGNMENT = "Anti-Assignment"
    REVENUE_PROFIT_SHARING = "Revenue/Profit Sharing"
    PRICE_RESTRICTIONS = "Price Restrictions"
    MINIMUM_COMMITMENT = "Minimum Commitment"
    VOLUME_RESTRICTION = "Volume Restriction"
    IP_OWNERSHIP_ASSIGNMENT = "Ip Ownership Assignment"
    JOINTLY_OWNED_PROPERTY = "Jointly Owned Property"
    LICENSE_GRANT = "License Grant"
    NON_TRANSFERABLE_LICENSE = "Non-Transferable License"
    AFFILIATE_LICENSE_LICENSOR = "Affiliate License-Licensor"
    AFFILIATE_LICENSE_LICENSEE = "Affiliate License-Licensee"
    UNLIMITED_ALL_YOU_CAN_EAT_LICENSE = "Unlimited/All-You-Can-Eat-License"
    IRREVOCABLE_OR_PERPETUAL_LICENSE = "Irrevocable Or Perpetual License"
    SOURCE_CODE_ESCROW = "Source Code Escrow"
    POST_TERMINATION_SERVICES = "Post-Termination Services"
    AUDIT_RIGHTS = "Audit Rights"
    UNCAPPED_LIABILITY = "Uncapped Liability"
    CAP_ON_LIABILITY = "Cap On Liability"
    LIQUIDATED_DAMAGES = "Liquidated Damages"
    WARRANTY_DURATION = "Warranty Duration"
    INSURANCE = "Insurance"
    COVENANT_NOT_TO_SUE = "Covenant Not To Sue"
    THIRD_PARTY_BENEFICIARY = "Third Party Beneficiary"
    DOUBLE_CAP = "Double Cap"

    @classmethod
    def from_str(cls, value: str | None) -> "ClauseCategory | None":
        """
        Normalize a raw category string or key to a canonical CUAD ClauseCategory member.
        Handles case insensitivity, underscores, hyphens, and common variations.
        """
        if not value or not isinstance(value, str) or not value.strip():
            return None
        cleaned = value.strip().lower().replace("_", " ").replace("-", " ")
        if cleaned in ("notice period", "notice period to terminate renewal"):
            return cls.NOTICE_PERIOD_TO_TERMINATE_RENEWAL
        for member in cls:
            if member.value.lower() == cleaned:
                return member
            member_norm = member.value.lower().replace("_", " ").replace("-", " ")
            if member_norm == cleaned:
                return member
            if member.name.lower() == value.strip().lower():
                return member
        return None


# Module-level alias matching lowercase naming request
clause_category = ClauseCategory


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
    category: str | None = Field(default=None, description="Category classification of the clause")
    clause_category: ClauseCategory | str | None = Field(
        default=None, description="CUAD 41 standard clause category classification"
    )
    confidence_score: float | None = Field(default=None, description="Model confidence score for clause extraction")

    @model_validator(mode="before")
    @classmethod
    def normalize_clause_categories(cls, data: Any) -> Any:
        """
        Normalize and synchronize clause_category and category fields.
        """
        if isinstance(data, dict):
            raw = data.get("clause_category") or data.get("category")
            if raw is not None:
                matched = ClauseCategory.from_str(str(raw))
                if matched:
                    data["clause_category"] = matched
                    if not data.get("category"):
                        data["category"] = matched.value
        return data


class AnalysisDetailResponse(BaseModel):
    """Detailed contract AI analysis schema."""
    safety_score: int = Field(..., description="Safety score from 0 (unsafe) to 100 (fully safe)")
    risk_level: str = Field(..., description="Overall document risk level: LOW, MEDIUM, or HIGH")
    summary: str = Field(..., description="Plain-English summary of contract terms")
    clauses: list[ClauseResponse] = Field(default_factory=list, description="Extracted clause objects")
    citations: list[CitationResponse] = Field(default_factory=list, description="Legal reference citations")
    recommendations: list[str] = Field(default_factory=list, description="Actionable review recommendations")
    compliance_violations: list[str] = Field(default_factory=list, description="Policy violation descriptions")
    document_overview: str | None = Field(default=None, description="Executive overview of document")
    parties: list[str] | list[dict] | dict | None = Field(default=None, description="Identified contract parties")
    key_dates: dict | list[dict] | list[str] | None = Field(default=None, description="Identified key contract dates")
    missing_sections: list[str] | None = Field(default=None, description="Missing standard sections/protections")
    key_terms: list[str] | list[dict] | dict | None = Field(default=None, description="Identified key contract terms")
    plain_english_summary: str | None = Field(default=None, description="Plain-English explanation of contract terms")
    extracted_text: str | None = Field(default=None, description="Extracted raw contract text")
    original_text: str | None = Field(default=None, description="Extracted raw contract text alias")


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


class PaginatedDocumentList(BaseModel):
    """Paginated document listing response schema."""
    items: list[DocumentListItemResponse] = Field(..., description="List of document items")
    total: int = Field(..., description="Total count of matching documents")
    limit: int = Field(..., description="Maximum items per page")
    offset: int = Field(..., description="Pagination offset")


class DocumentResponse(BaseModel):
    """Full detail response schema for a document."""
    document_id: str = Field(..., description="UUID of the document")
    filename: str = Field(..., description="Original filename")
    status: str = Field(..., description="Processing status")
    uploaded_at: str | None = Field(default=None, description="ISO 8601 upload timestamp")
    error_message: str | None = Field(default=None, description="Processing error message if failed")
    original_text: str | None = Field(default=None, description="Extracted raw text content")
    extracted_text: str | None = Field(default=None, description="Extracted raw text content alias")
    analysis: AnalysisDetailResponse | None = Field(default=None, description="AI analysis details")


class ReportResponse(BaseModel):
    """Memorandum report output response schema."""
    document_id: str = Field(..., description="UUID of the document")
    filename: str = Field(..., description="Original filename")
    uploaded_at: str | None = Field(default=None, description="ISO 8601 upload timestamp")
    report_url: str = Field(..., description="URL path to generated PDF report")
    format: str | None = Field(default="pdf", description="Report format: pdf or docx")
    safety_score: int = Field(..., description="Safety score from 0 to 100")
    risk_level: str = Field(..., description="Overall document risk level")
    summary: str = Field(..., description="Plain-English summary of contract terms")
    recommendations: list[str] = Field(default_factory=list, description="Actionable review recommendations")
    clauses: list[ClauseResponse] = Field(default_factory=list, description="Categorized clauses and risk flags")
    citations: list[CitationResponse] = Field(default_factory=list, description="Legal reference citations")
    document_overview: str | None = Field(default=None, description="Executive overview of document")
    parties: list[str] | list[dict] | dict | None = Field(default=None, description="Identified contract parties")
    key_dates: dict | list[dict] | list[str] | None = Field(default=None, description="Identified key contract dates")
    missing_sections: list[str] | None = Field(default=None, description="Missing standard sections/protections")
    key_terms: list[str] | list[dict] | dict | None = Field(default=None, description="Identified key contract terms")
    plain_english_summary: str | None = Field(default=None, description="Plain-English explanation of contract terms")


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


class PaginatedAuditLogList(BaseModel):
    """Paginated audit log listing response schema."""
    items: list[AuditLogItemResponse] = Field(..., description="List of audit log items")
    total: int = Field(..., description="Total count of matching audit logs")
    limit: int = Field(..., description="Maximum items per page")
    offset: int = Field(..., description="Pagination offset")


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
    question: str | None = Field(default=None, description="User's question about the document", min_length=1, max_length=2000)
    query: str | None = Field(default=None, description="User's question about the document (alias for backwards compatibility)", min_length=1, max_length=2000)
    conversation_id: str | None = Field(default=None, description="Optional conversation UUID for multi-turn threads")

    @model_validator(mode="before")
    @classmethod
    def validate_question_or_query(cls, values):
        if isinstance(values, dict):
            q = values.get("question") or values.get("query")
            if not q or not str(q).strip():
                raise ValueError("A 'question' or 'query' must be provided.")
            values["question"] = str(q).strip()
            values["query"] = str(q).strip()
        return values


class SourceChunkResponse(BaseModel):
    """Details of a document chunk used as context for answering."""
    chunk_id: str = Field(..., description="UUID of the chunk")
    chunk_index: int = Field(..., description="Index of the chunk in the document")
    chunk_text: str = Field(..., description="Content text of the chunk")
    similarity: float | None = Field(default=None, description="Cosine similarity score (0.0 to 1.0)")


class ChatCitationResponse(BaseModel):
    """Citation reference within a chat answer."""
    clause_id: str | None = Field(default=None, description="UUID of the referenced clause")
    clause_type: str = Field(..., description="Type/category of the cited clause")
    snippet: str = Field(..., description="Relevant text excerpt from the clause")
    section_reference: str | None = Field(default=None, description="Section number reference (e.g. Section 8.2)")


class ChatResponse(BaseModel):
    """Response schema for document Q&A chat."""
    answer: str = Field(..., description="Grounded answer based on document content")
    source_chunks: list[SourceChunkResponse] = Field(default_factory=list, description="Source chunks used to answer the question")
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


class QuickSummaryResponse(BaseModel):
    """Response schema for fast 2-3 sentence document overview."""
    document_id: str = Field(..., description="UUID of the document")
    filename: str = Field(..., description="Original filename")
    quick_summary: str = Field(..., description="2-3 sentence immediate document overview")
    document_type: str = Field(default="Legal Agreement", description="Identified document category or contract type")
    key_points: list[str] = Field(default_factory=list, description="Immediate 2-3 key takeaways")
    estimated_risk_level: str = Field(default="LOW", description="Estimated risk level: LOW, MEDIUM, HIGH, or NEUTRAL")
    disclaimer: str = Field(default="This initial AI overview assists legal review and is not legal advice.", description="Legal disclaimer")


class ComplianceAuditRequest(BaseModel):
    """Request model for document compliance check."""
    rule_set: str | None = Field(
        default=None,
        description="Target rule-set (e.g. 'standard_nda', 'gdpr_privacy', 'employment_agreement', 'franchise_agreement', 'commercial_lease', 'saas_service_agreement'). If omitted, auto-detected from content."
    )


class ComplianceResponse(BaseModel):
    """Response model for compliance check result."""
    document_id: str = Field(..., description="UUID of the document")
    filename: str = Field(..., description="Document filename")
    rule_set: str = Field(..., description="The applied rule-set (either requested or auto-detected)")
    auto_detected: bool = Field(default=False, description="Whether rule-set was auto-detected based on content")
    status: str = Field(..., description="Compliance status: 'compliant' | 'non-compliant' | 'compliance_checked'")
    violations: list[str] = Field(default_factory=list, description="List of detected policy violations or missing required clauses")
    safety_score: int | None = Field(default=None, description="Current safety score of the document")
    risk_level: str | None = Field(default=None, description="Risk level (LOW, MEDIUM, HIGH)")
class ProcessPipelineResponse(BaseModel):
    """Document pipeline processing response schema."""
    document_id: str = Field(..., description="UUID of the processed document")
    status: str = Field(..., description="Processing status of the pipeline")
