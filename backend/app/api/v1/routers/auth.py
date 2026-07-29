"""
Authentication router.
Handles user registration, login, and token verification stubs.
"""

from fastapi import APIRouter, Request

from app.core.limiter import limiter
from app.models.schemas import AuthMessageResponse

router = APIRouter()


@router.post("/login", response_model=AuthMessageResponse)
@limiter.limit("10/minute")
def login(request: Request) -> AuthMessageResponse:
    """
    User login endpoint placeholder.

    Returns:
        AuthMessageResponse: Stated login response.
    """
    return AuthMessageResponse(message="login successful")


@router.post("/signup", response_model=AuthMessageResponse)
@limiter.limit("10/minute")
def signup(request: Request) -> AuthMessageResponse:
    """
    User signup endpoint placeholder.

    Returns:
        AuthMessageResponse: Stated signup response.
    """
    return AuthMessageResponse(message="signup successful")
