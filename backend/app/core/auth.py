"""
Authentication utilities for Supabase.
Handles verifying JWT access tokens and managing user sessions.
"""

import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from supabase import create_client, Client

from app.core.config import settings
from app.core.database import get_db
from app.models import User, Organization

security_scheme = HTTPBearer()


def get_supabase_client() -> Client:
    """
    Dependency injection helper to yield initialized Supabase Client.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase credentials are not configured in environment settings."
        )
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
    supabase_client: Client = Depends(get_supabase_client)
) -> User:
    """
    FastAPI dependency that decodes the Bearer token, gets the user info from Supabase,
    and returns/provisions the corresponding user profile in the local database.
    """
    token = credentials.credentials
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
