# Engineering Resolution Report: MED-01 through MED-05

**Project:** Legal Analyzer Web Application  
**Execution Date:** 2026-10-04  
**Scope:** Medium-Severity Reliability, Observability, Scalability, and Database Performance Fixes (MED-01 to MED-05)  
**Status:** All 5 Issues Resolved, Verified & Tested  

---

## 1. Executive Summary

| Issue ID | Architecture Label | Category | Target Component | Status |
| :--- | :--- | :--- | :--- | :--- |
| **MED-01** | `DATA-DB-003-CONNECTION-POOLING` | Database Infrastructure | SQLAlchemy Engine Configuration | **Resolved** |
| **MED-02** | `OBS-LOG-001-STRUCTURED-LOGGING` | Observability & Reliability | Logging & Stream Handlers | **Resolved** |
| **MED-03** | `API-REST-001-PAGINATION` | API Design & Scalability | Document & Audit Log List Endpoints | **Resolved** |
| **MED-04** | `PERF-DB-001-RELATIONSHIP-EAGER-LOAD` | Database Performance | Clause & RiskFlag ORM Relationships | **Resolved** |
| **MED-05** | `DATA-DB-004-INDEX-OPTIMIZATION` | Database Performance | Foreign Key & Filter Column Indexing | **Resolved** |

---

## 2. Detailed Bug Resolutions

### Bug 1: [PROMPT MED-01] Production Connection Pooling on SQLAlchemy Engine

- **Label:** `DATA-DB-003-CONNECTION-POOLING`
- **Target Files:**
  - `backend/app/core/database.py`
  - `backend/tests/test_database_pooling.py` *(New Test Suite)*
- **Problem Statement:**
  The database engine was instantiated without explicit pool parameters (`create_engine(settings.DATABASE_URL)`), defaulting to 5 connections with no recycle timeout. Under concurrent web traffic or background tasks, PostgreSQL dropped stale idle connections, causing connection timeouts, dropped queries, and pool exhaustion.
- **Root Cause & Technical Resolution:**
  - Configured driver-adaptive connection pooling in `backend/app/core/database.py`:
    - Dialect detection via `is_sqlite = settings.DATABASE_URL.startswith("sqlite")`.
    - Set `pool_size=10` for PostgreSQL (`5` for SQLite).
    - Set `max_overflow=20` for PostgreSQL (`10` for SQLite).
    - Enabled `pool_pre_ping=True` to test connections for liveness before dispatching queries.
    - Set `pool_recycle=1800` (30 minutes) to recycle connections before backend timeouts disconnect them.
    - Preserved `connect_args={"check_same_thread": False}` for SQLite compatibility.
    - Explicitly typed `get_db() -> Generator[Session, None, None]`.
- **Code Changes:**
  ```python
  is_sqlite = settings.DATABASE_URL.startswith("sqlite")
  connect_args = {"check_same_thread": False} if is_sqlite else {}

  engine = create_engine(
      settings.DATABASE_URL,
      connect_args=connect_args,
      pool_size=10 if not is_sqlite else 5,
      max_overflow=20 if not is_sqlite else 10,
      pool_pre_ping=True,
      pool_recycle=1800,
  )
  ```
- **Verification & Testing:**
  Implemented `backend/tests/test_database_pooling.py`:
  - Validates `pool_size == 10`, `max_overflow == 20`, and `pool_recycle == 1800` under PostgreSQL URLs.
  - Validates `pool_pre_ping` flag is set on the engine pool.
  - Verifies SQLite configuration compatibility.
  - Result: 4 tests passed.

---

### Bug 2: [PROMPT MED-02] Application Structured Logging & Print Statement Elimination

- **Label:** `OBS-LOG-001-STRUCTURED-LOGGING`
- **Target Files:**
  - `backend/app/main.py`
  - `backend/app/core/logging.py`
  - `backend/app/workers/tasks.py`
  - `backend/app/services/storage_service.py`
  - `backend/app/services/ocr_service.py`
  - `backend/tests/test_logging.py` *(New Test Suite)*
- **Problem Statement:**
  `setup_logging()` in `logging.py` was defined but never invoked in `main.py`. The backend relied on raw `print()` statements across background tasks, storage, and OCR services, preventing log-level filtering, structured JSON ingestion in production, and Sentry breadcrumbs.
- **Root Cause & Technical Resolution:**
  - Enhanced `backend/app/core/logging.py`:
    - Added `JSONLogFormatter` outputting timestamp, log level, module name, message, and exception tracebacks in production mode.
    - Standardized console formatting for development mode.
  - Activated logging in `backend/app/main.py`:
    - Called `setup_logging()` immediately before instantiating the `FastAPI` application.
  - Replaced all raw `print()` calls across:
    - Background task worker (`backend/app/workers/tasks.py`)
    - Storage service (`backend/app/services/storage_service.py`)
    - OCR processing service (`backend/app/services/ocr_service.py`)
  - Enforced document confidentiality rules: logged strictly `document_id` references, never untrusted or raw legal document content.
- **Code Changes:**
  ```python
  class JSONLogFormatter(logging.Formatter):
      """Format log records as structured JSON for production ingestion."""
      def format(self, record: logging.LogRecord) -> str:
          log_data: dict[str, Any] = {
              "timestamp": datetime.now(timezone.utc).isoformat(),
              "level": record.levelname,
              "name": record.name,
              "message": record.getMessage(),
              "module": record.module,
              "line": record.lineno,
          }
          if record.exc_info:
              log_data["exception"] = self.formatException(record.exc_info)
          return json.dumps(log_data)
  ```
- **Verification & Testing:**
  Implemented `backend/tests/test_logging.py`:
  - Verifies production JSON log structure with expected keys (`timestamp`, `level`, `message`, `module`).
  - Implemented an automated AST walker scanning all Python files in `backend/app/` to assert that zero `print(...)` function calls exist in application code.
  - Result: 5 tests passed.

---

### Bug 3: [PROMPT MED-03] Limit/Offset Pagination on List Endpoints

- **Label:** `API-REST-001-PAGINATION`
- **Target Files:**
  - `backend/app/models/schemas.py`
  - `backend/app/api/v1/routers/documents/crud.py`
  - `backend/app/api/v1/routers/admin.py`
  - `frontend/lib/api/client.ts`
  - `frontend/app/(dashboard)/dashboard/page.tsx`
  - `frontend/app/(dashboard)/review/page.tsx`
  - `frontend/app/(dashboard)/admin/page.tsx`
  - `backend/tests/test_pagination.py` *(New Test Suite)*
- **Problem Statement:**
  `GET /api/v1/documents` and `GET /api/v1/admin/audit-logs` returned unbounded arrays in a single query. With hundreds of uploaded contracts or thousands of audit logs, this caused query timeouts, bandwidth waste, and frontend browser performance drops.
- **Root Cause & Technical Resolution:**
  - Created standardized pagination response schemas in `backend/app/models/schemas.py`:
    - `PaginatedDocumentList`: `{ items: list[DocumentListItemResponse], total: int, limit: int, offset: int }`
    - `PaginatedAuditLogList`: `{ items: list[AuditLogResponse], total: int, limit: int, offset: int }`
  - Updated API routers with validated query parameters:
    - `limit: int = Query(default=50, ge=1, le=100, description="Max records to return")`
    - `offset: int = Query(default=0, ge=0, description="Number of records to skip")`
    - Executed count queries alongside sliced `.offset(offset).limit(limit)` queries.
  - Updated Frontend:
    - Added TypeScript interfaces `PaginatedDocumentList` and `PaginatedAuditLogList`.
    - Updated `client.ts` methods `getDocuments(limit = 50, offset = 0)` and `getAuditLogs(limit = 50, offset = 0)`.
    - Updated dashboard, review, and admin pages to unpack `.items` with backward-compatible array fallbacks.
- **Code Changes:**
  ```python
  @router.get("", response_model=PaginatedDocumentList)
  def list_documents(
      limit: int = Query(default=50, ge=1, le=100, description="Max records to return"),
      offset: int = Query(default=0, ge=0, description="Number of records to skip"),
      current_user: User = Depends(get_current_user),
      db: Session = Depends(get_db),
  ) -> PaginatedDocumentList:
      base_query = db.query(Document).filter(Document.user_id == current_user.id)
      total = base_query.count()
      docs = (
          base_query.order_by(Document.created_at.desc())
          .offset(offset)
          .limit(limit)
          .all()
      )
      return PaginatedDocumentList(
          items=[DocumentListItemResponse.model_validate(doc) for doc in docs],
          total=total,
          limit=limit,
          offset=offset,
      )
  ```
- **Verification & Testing:**
  Implemented `backend/tests/test_pagination.py`:
  - Verified default limit (50) and offset (0).
  - Verified slicing logic with custom `limit` and `offset`.
  - Verified validation error handling for `limit > 100`, `limit < 1`, and `offset < 0`.
  - Verified frontend with `npx tsc --noEmit` (0 errors).
  - Result: 6 tests passed.

---

### Bug 4: [PROMPT MED-04] Fix N+1 Query Anti-Pattern in get_document

- **Label:** `PERF-DB-001-RELATIONSHIP-EAGER-LOAD`
- **Target Files:**
  - `backend/app/models/database_models.py`
  - `backend/app/api/v1/routers/documents/crud.py`
  - `backend/tests/test_eager_loading.py` *(New Test Suite)*
- **Problem Statement:**
  `get_document` queried all clauses for a contract and then iterated over each clause in a Python `for` loop, querying `RiskFlag` individually (`db.query(RiskFlag).filter(RiskFlag.clause_id == c_db.id).all()`). For a contract with 60 clauses, this caused 61 sequential database round-trips.
- **Root Cause & Technical Resolution:**
  - Defined explicit bidirectional ORM relationships in `backend/app/models/database_models.py`:
    ```python
    # In Clause:
    risk_flags = relationship(
        "RiskFlag",
        back_populates="clause",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # In RiskFlag:
    clause = relationship("Clause", back_populates="risk_flags")
    ```
  - Updated `get_document` in `crud.py`:
    - Applied `joinedload(Clause.risk_flags)` during clause retrieval.
    - Read `c_db.risk_flags` directly from in-memory objects rather than issuing manual SQL queries.
- **Code Changes:**
  ```python
  clauses_db = (
      db.query(Clause)
      .options(joinedload(Clause.risk_flags))
      .filter(Clause.document_id == document_id)
      .order_by(Clause.clause_number.asc())
      .all()
  )

  for c_db in clauses_db:
      risk_flags_db = c_db.risk_flags  # In-memory evaluation; no extra SQL query
  ```
- **Verification & Testing:**
  Implemented `backend/tests/test_eager_loading.py`:
  - Registered a SQLAlchemy `before_cursor_execute` event listener.
  - Seeded a test document containing 10 clauses each with risk flags.
  - Verified that accessing risk flags across all 10 clauses executed 0 additional SQL queries.
  - Result: 3 tests passed.

---

### Bug 5: [PROMPT MED-05] Add Database Indexes to All Foreign Key and Filtering Columns

- **Label:** `DATA-DB-004-INDEX-OPTIMIZATION`
- **Target Files:**
  - `backend/app/models/database_models.py`
  - `backend/alembic/versions/791aa19f3d22_add_foreign_key_indexes.py` *(Alembic Migration)*
  - `backend/tests/test_model_indexes.py` *(New Test Suite)*
- **Problem Statement:**
  Foreign key columns and high-cardinality filter fields lacked B-tree indexes across 8+ tables, forcing PostgreSQL to perform sequential table scans during document clause resolution, audit log queries, and chat lookups.
- **Root Cause & Technical Resolution:**
  - Added `index=True` to 14 foreign key and filtering columns in `backend/app/models/database_models.py`:
    1. `Document.user_id`
    2. `Clause.document_id`
    3. `RiskFlag.clause_id`
    4. `ExtractedText.document_id`
    5. `ComplianceCheck.document_id`
    6. `LegalReference.document_id`
    7. `Report.document_id`
    8. `AuditLog.document_id`
    9. `AutomationRun.document_id`
    10. `ClauseReview.document_id`
    11. `ClauseReview.clause_id`
    12. `DocumentChunk.document_id`
    13. `ChatMessage.document_id`
    14. `ChatMessage.conversation_id`
  - Created Alembic migration `791aa19f3d22_add_foreign_key_indexes.py` using `op.create_index` and `op.drop_index`.
- **Code Changes:**
  ```python
  # Example of index additions in backend/app/models/database_models.py:
  class Clause(Base):
      ...
      document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)

  class RiskFlag(Base):
      ...
      clause_id = Column(UUID(as_uuid=True), ForeignKey("clauses.id", ondelete="CASCADE"), nullable=False, index=True)
  ```
- **Verification & Testing:**
  Implemented `backend/tests/test_model_indexes.py`:
  - Verified `column.index is True` on all 14 model fields.
  - Verified SQLAlchemy Table metadata reflection includes indexes on target columns.
  - Result: 2 tests passed.

---

## 3. Complete File Modification Registry

### Modified Backend Source Files:
- `backend/app/core/database.py` (MED-01)
- `backend/app/core/logging.py` (MED-02)
- `backend/app/main.py` (MED-02)
- `backend/app/workers/tasks.py` (MED-02)
- `backend/app/services/storage_service.py` (MED-02)
- `backend/app/services/ocr_service.py` (MED-02)
- `backend/app/models/schemas.py` (MED-03)
- `backend/app/api/v1/routers/documents/crud.py` (MED-03, MED-04)
- `backend/app/api/v1/routers/admin.py` (MED-03)
- `backend/app/models/database_models.py` (MED-04, MED-05)

### New Database Migration:
- `backend/alembic/versions/791aa19f3d22_add_foreign_key_indexes.py` (MED-05)

### Modified Frontend Source Files:
- `frontend/lib/api/client.ts` (MED-03)
- `frontend/app/(dashboard)/dashboard/page.tsx` (MED-03)
- `frontend/app/(dashboard)/review/page.tsx` (MED-03)
- `frontend/app/(dashboard)/admin/page.tsx` (MED-03)

### New Automated Test Suites:
- `backend/tests/test_database_pooling.py` (4 tests)
- `backend/tests/test_logging.py` (5 tests)
- `backend/tests/test_pagination.py` (6 tests)
- `backend/tests/test_eager_loading.py` (3 tests)
- `backend/tests/test_model_indexes.py` (2 tests)

---

## 4. Test Suite Execution Summary

```
============================= test session starts =============================
platform win32 -- Python 3.13.9, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\legal\backend
configfile: pyproject.toml
plugins: anyio-4.14.1
collected 20 items

tests\test_database_pooling.py ....                                      [ 20%]
tests\test_logging.py .....                                              [ 45%]
tests\test_pagination.py ......                                          [ 75%]
tests\test_eager_loading.py ...                                          [ 90%]
tests\test_model_indexes.py ..                                           [100%]

======================== 20 passed, 1 warning in 2.13s ========================
```

- **Backend Linting:** Clean (`ruff check app tests` returned 0 errors).
- **Frontend Type Checking:** Clean (`npx tsc --noEmit` returned 0 errors).
- **Engineering Rules Adherence:**
  - Zero raw `print()` statements in application code.
  - Only `document_id` references logged; raw document contents remain confidential.
  - Strict type hints on Python and TypeScript.
  - Zero hardcoded secrets or production credentials.
