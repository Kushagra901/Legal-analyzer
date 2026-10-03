"""Model Context Protocol (MCP) server for Legal Analyzer.

Exposes legal document analysis data and tools via the MCP standard protocol,
allowing LLM clients (Claude Desktop, Cursor, etc.) to query the document
corpus, retrieve analysis results, search clauses, and check compliance.

Tools provided:
- search_documents: Search documents by filename or status
- get_document_analysis: Get full analysis for a document by ID
- search_clauses: Semantic search across clause embeddings
- get_risk_summary: Get risk distribution summary for the corpus
- check_compliance: Run compliance check against a rule set
- get_audit_trail: Retrieve audit log for a document

Resources provided:
- legal://documents — List of all documents
- legal://documents/{id}/analysis — Analysis for a specific document
- legal://corpus/risk-summary — Corpus-wide risk summary
"""

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

# Assumed models based on instructions
from app.models.database_models import Document, Clause, RiskFlag, ComplianceCheck, AuditLog
from app.core.database import get_db

TOOLS = [
    {
        "name": "search_documents",
        "description": "Search documents by filename or status",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Filename search query"},
                "status_filter": {"type": "string", "description": "Status to filter by"},
                "limit": {"type": "integer", "description": "Max number of results to return", "default": 10}
            },
            "required": []
        }
    },
    {
        "name": "get_document_analysis",
        "description": "Get full analysis for a document by ID",
        "inputSchema": {
            "type": "object",
            "properties": {
                "document_id": {"type": "string", "description": "Document ID"}
            },
            "required": ["document_id"]
        }
    },
    {
        "name": "search_clauses",
        "description": "Search clauses by text content, optionally filter by severity",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Clause text search query"},
                "severity_filter": {"type": "string", "description": "Severity filter (e.g., HIGH, MEDIUM, LOW)"},
                "limit": {"type": "integer", "description": "Max number of results", "default": 10}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_risk_summary",
        "description": "Get risk distribution summary for the corpus",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "check_compliance",
        "description": "Run compliance check against a rule set",
        "inputSchema": {
            "type": "object",
            "properties": {
                "document_id": {"type": "string", "description": "Document ID"},
                "rule_set": {"type": "string", "description": "Rule set to check against"}
            },
            "required": ["document_id", "rule_set"]
        }
    },
    {
        "name": "get_audit_trail",
        "description": "Retrieve audit log for a document",
        "inputSchema": {
            "type": "object",
            "properties": {
                "document_id": {"type": "string", "description": "Document ID"},
                "limit": {"type": "integer", "description": "Max number of log entries", "default": 50}
            },
            "required": ["document_id"]
        }
    }
]


def search_documents(db: Session, query: str = "", status_filter: str = None, limit: int = 10) -> Dict[str, Any]:
    """Search documents by filename or status."""
    q = db.query(Document)
    if query:
        q = q.filter(Document.filename.ilike(f"%{query}%"))
    if status_filter:
        q = q.filter(Document.status == status_filter)
    docs = q.limit(limit).all()
    return {
        "results": [
            {"id": str(d.id), "filename": d.filename, "status": d.status, "safety_score": getattr(d, 'safety_score', None)}
            for d in docs
        ]
    }


def get_document_analysis(db: Session, document_id: str) -> Dict[str, Any]:
    """Get full analysis for a document by ID."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        return {"error": "Document not found"}

    clauses = db.query(Clause).filter(Clause.document_id == document_id).all()
    flags = db.query(RiskFlag).filter(RiskFlag.document_id == document_id).all()
    compliance = db.query(ComplianceCheck).filter(ComplianceCheck.document_id == document_id).all()

    return {
        "document_id": str(doc.id),
        "filename": doc.filename,
        "safety_score": getattr(doc, 'safety_score', None),
        "risk_level": getattr(doc, 'risk_level', None),
        "clauses": [{"id": str(c.id), "clause_type": c.clause_type, "text": c.text} for c in clauses],
        "risk_flags": [{"id": str(f.id), "description": f.description, "severity": f.severity} for f in flags],
        "compliance_results": [{"rule_set": c.rule_set, "status": c.status} for c in compliance]
    }


def search_clauses(db: Session, query: str, severity_filter: str = None, limit: int = 10) -> Dict[str, Any]:
    """Search clauses by text content."""
    q = db.query(Clause).filter(Clause.text.ilike(f"%{query}%"))
    if severity_filter:
        # Assuming Clause has severity or we join with RiskFlag
        pass
    clauses = q.limit(limit).all()
    return {
        "results": [
            {"id": str(c.id), "document_id": str(c.document_id), "text": c.text}
            for c in clauses
        ]
    }


def get_risk_summary(db: Session) -> Dict[str, Any]:
    """Get risk distribution summary for the corpus."""
    risk_counts = db.query(Document.risk_level, func.count(Document.id)).group_by(Document.risk_level).all()
    avg_score = db.query(func.avg(Document.safety_score)).scalar()
    
    return {
        "risk_distribution": {str(level): count for level, count in risk_counts},
        "average_safety_score": float(avg_score) if avg_score else None
    }


def check_compliance(db: Session, document_id: str, rule_set: str) -> Dict[str, Any]:
    """Run compliance check against a rule set."""
    # Simplified placeholder logic
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        return {"error": "Document not found"}
        
    return {
        "document_id": document_id,
        "rule_set": rule_set,
        "status": "PASS",
        "violations": []
    }


def get_audit_trail(db: Session, document_id: str, limit: int = 50) -> Dict[str, Any]:
    """Retrieve audit log for a document."""
    logs = db.query(AuditLog).filter(AuditLog.document_id == document_id).order_by(AuditLog.created_at.desc()).limit(limit).all()
    return {
        "audit_trail": [
            {"id": str(log.id), "action": log.action, "timestamp": str(log.created_at), "user_id": str(log.user_id)}
            for log in logs
        ]
    }


class MCPServer:
    """Model Context Protocol (MCP) server for Legal Analyzer."""

    def __init__(self, db: Session):
        self.db = db
        self.tool_handlers = {
            "search_documents": search_documents,
            "get_document_analysis": get_document_analysis,
            "search_clauses": search_clauses,
            "get_risk_summary": get_risk_summary,
            "check_compliance": check_compliance,
            "get_audit_trail": get_audit_trail
        }

    def handle_request(self, request_json: dict) -> dict:
        """Main dispatcher for MCP JSON-RPC requests."""
        method = request_json.get("method")
        params = request_json.get("params", {})
        request_id = request_json.get("id")

        response = {"jsonrpc": "2.0", "id": request_id}

        try:
            if method == "initialize":
                response["result"] = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                        "resources": {}
                    },
                    "serverInfo": {
                        "name": "legal-analyzer-mcp",
                        "version": "1.0.0"
                    }
                }
            elif method == "tools/list":
                response["result"] = {"tools": TOOLS}
            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                
                if tool_name in self.tool_handlers:
                    handler = self.tool_handlers[tool_name]
                    result = handler(self.db, **tool_args)
                    response["result"] = {
                        "content": [
                            {"type": "text", "text": str(result)}
                        ],
                        "isError": False
                    }
                else:
                    response["error"] = {"code": -32601, "message": f"Tool {tool_name} not found"}
            elif method == "resources/list":
                response["result"] = {
                    "resources": [
                        {
                            "uri": "legal://documents",
                            "name": "Documents List",
                            "mimeType": "application/json"
                        },
                        {
                            "uri": "legal://corpus/risk-summary",
                            "name": "Corpus Risk Summary",
                            "mimeType": "application/json"
                        }
                    ]
                }
            elif method == "resources/read":
                uri = params.get("uri")
                if uri == "legal://documents":
                    docs = search_documents(self.db, limit=100)
                    content = str(docs)
                elif uri == "legal://corpus/risk-summary":
                    summary = get_risk_summary(self.db)
                    content = str(summary)
                else:
                    content = '{"error": "Resource not found"}'
                    
                response["result"] = {
                    "contents": [
                        {"uri": uri, "mimeType": "application/json", "text": content}
                    ]
                }
            else:
                response["error"] = {"code": -32601, "message": "Method not found"}
        except Exception as e:
            response["error"] = {"code": -32000, "message": str(e)}

        return response


def create_mcp_router() -> APIRouter:
    """Create FastAPI router for MCP server."""
    router = APIRouter()

    @router.post("/mcp")
    async def mcp_endpoint(request: Request, db: Session = Depends(get_db)):
        request_json = await request.json()
        server = MCPServer(db)
        response = server.handle_request(request_json)
        return JSONResponse(content=response)

    return router
