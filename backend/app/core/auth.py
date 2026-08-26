"""
Authentication utilities for Supabase.
Handles verifying JWT access tokens and managing user sessions.
Supports X-Internal-Token for internal service bypass.
"""

import uuid

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from supabase import Client, create_client

from app.core.config import settings
from app.core.database import get_db
from app.models import Document, Organization, User

# Disable auto_error so we can manually handle absent user-JWTs when X-Internal-Token is provided
security_scheme = HTTPBearer(auto_error=False)


def get_supabase_client() -> Client | None:
    """
    Dependency injection helper to yield initialized Supabase Client.
    Returns None if Supabase credentials are not set (for local dev / offline mode).
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        return None
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: Session = Depends(get_db),
    supabase_client: Client | None = Depends(get_supabase_client)
) -> User:
    """
    FastAPI dependency that decodes either:
    1. A valid X-Internal-Token header matching INTERNAL_SERVICE_TOKEN (returns an admin system user)
    2. A Bearer token decoded via Supabase and validated locally (or mock token in dev/testing).
    """
    # 1. Inspect for internal service header authentication
    internal_token = request.headers.get("x-internal-token")
    if internal_token is not None:
        if not settings.INTERNAL_SERVICE_TOKEN or internal_token != settings.INTERNAL_SERVICE_TOKEN:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid internal service token."
            )
        # Yield a transient Mock User with Admin Role to bypass tenant segregation
        system_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")
        system_user = User(
            id=system_uuid,
            org_id=system_uuid,
            email="system-internal@service.local",
            role="admin"
        )
        return system_user

    # 2. Enforce standard User JWT token verification if internal token was not provided
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials are required."
        )

    token = credentials.credentials

    # Fallback to local dev / test mock user if Supabase is unconfigured or token is a mock token
    if token in ("test-token", "mock-token", settings.AUTH_MOCK_TOKEN) or supabase_client is None:
        test_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")
        org = db.query(Organization).filter(Organization.id == test_uuid).first()
        if not org:
            org = Organization(id=test_uuid, name="Default Organization", plan="free")
            db.add(org)
            db.flush()
        user = db.query(User).filter(User.id == test_uuid).first()
        if not user:
            user = User(id=test_uuid, org_id=org.id, email="test@example.com", role="user")
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    try:
        # Fetch user info using token to check validity
        response = supabase_client.auth.get_user(token)
        supabase_user = response.user
        if not supabase_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication session."
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )

    user_uuid = uuid.UUID(supabase_user.id)
    user_email = supabase_user.email or ""

    # Find or provision user in local PostgreSQL
    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        # Associate user with a default organization, or create one if none exists
        org = db.query(Organization).first()
        if not org:
            org = Organization(
                id=uuid.uuid4(),
                name="Default Organization",
                plan="free"
            )
            db.add(org)
            db.flush()

        user = User(
            id=user_uuid,
            org_id=org.id,
            email=user_email,
            role="user"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return user


def get_accessible_document(
    db: Session,
    document_uuid: uuid.UUID | str,
    current_user: User
) -> Document:
    """
    Resolves document access control for a given user.
    - Administrators (including internal services running under admin bypass)
      have full access to any document.
    - Regular users are strictly restricted to documents where document.user_id == current_user.id.
    Raises HTTPException(404) if document does not exist.
    Raises HTTPException(403) if regular user tries to access another user's document.
    Returns the Document instance if authorized.
    """
    if isinstance(document_uuid, str):
        try:
            doc_uuid = uuid.UUID(document_uuid)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid document ID format."
            )
    else:
        doc_uuid = document_uuid

    doc = db.query(Document).filter(Document.id == doc_uuid).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )

    if current_user.role != "admin" and doc.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You do not have permission to access this document."
        )

    return doc
