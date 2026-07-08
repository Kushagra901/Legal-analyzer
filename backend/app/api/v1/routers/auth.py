"""
Authentication router.
Handles user registration, login, and token verification stubs.
"""

from fastapi import APIRouter

router = APIRouter()


@router.post("/login")
def login() -> dict[str, str]:
    """
    User login endpoint placeholder.

    Returns:
        dict[str, str]: Stated login response.
    """
    return {"message": "login successful"}


@router.post("/signup")
def signup() -> dict[str, str]:
    """
    User signup endpoint placeholder.

    Returns:
        dict[str, str]: Stated signup response.
    """
    return {"message": "signup successful"}
