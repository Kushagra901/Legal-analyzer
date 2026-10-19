"""
Services package initialization.
Contains modules for OCR processing, LLM analysis, risk checking, compliance audits, storage, and report generation.
"""
from app.services.audit_service import AuditService, audit_service
from app.services.chat_service import ChatService
from app.services.compliance_service import ComplianceService
from app.services.deep_extraction_service import DeepExtractionService
from app.services.embedding_service import EmbeddingService
from app.services.legal_chunker import LegalChunker, split_legal_clauses
from app.services.llm_service import LLMService
from app.services.ocr_service import OCRService
from app.services.ollama_service import OllamaService
from app.services.report_generator_service import ReportGeneratorService
from app.services.risk_service import RiskService
from app.services.storage_service import StorageService

__all__ = [
    "AuditService",
    "audit_service",
    "ChatService",
    "ComplianceService",
    "DeepExtractionService",
    "EmbeddingService",
    "LegalChunker",
    "LLMService",
    "OCRService",
    "OllamaService",
    "ReportGeneratorService",
    "RiskService",
    "StorageService",
    "split_legal_clauses",
]
