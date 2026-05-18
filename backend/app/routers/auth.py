"""
Authentication endpoints.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.auth import create_access_token
from backend.app.config import settings

router = APIRouter(tags=["Auth"])


class TokenRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


@router.post("/auth/token")
async def issue_token(payload: TokenRequest):
    """Issue a JWT access token for admin dashboard endpoints."""
    if (
        payload.username != settings.ADMIN_USERNAME
        or payload.password != settings.ADMIN_PASSWORD
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    token = create_access_token({"sub": payload.username, "role": "admin"})
    return {"access_token": token, "token_type": "bearer"}
