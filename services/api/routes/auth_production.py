"""Production authentication API routes with PostgreSQL persistence."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from packages.auth import (
    InvalidCredentialsError,
    LoginRequest,
    RegisterRequest,
    TokenExpiredError,
    TokenInvalidError,
    TokenResponse,
    User,
)
from packages.auth.production_service import AuthService
from services.api.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()


async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Dependency to get AuthService with database session."""
    return AuthService(db)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth: AuthService = Depends(get_auth_service),
) -> User:
    """Dependency to get current user from JWT token."""
    token = credentials.credentials
    try:
        return await auth.get_current_user(token)
    except TokenExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except TokenInvalidError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_admin(
    user: User = Depends(get_current_user),
) -> User:
    """Dependency to require admin role."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------


@router.post("/register", response_model=User)
async def register(
    req: RegisterRequest,
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    """Register a new user."""
    try:
        return await auth.register(req)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Login and get JWT tokens."""
    try:
        return await auth.login(req)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    req: dict[str, str],
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Refresh access token using refresh token."""
    refresh = req.get("refresh_token", "")
    try:
        return await auth.refresh_token(refresh)
    except TokenInvalidError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from exc


# ---------------------------------------------------------------------------
# Protected endpoints
# ---------------------------------------------------------------------------


@router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Get current user info."""
    return current_user


@router.post("/logout")
async def logout(
    req: dict[str, str],
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> dict[str, str]:
    """Logout and revoke refresh token."""
    refresh = req.get("refresh_token", "")
    await auth.logout(refresh)
    return {"message": "Logged out successfully"}


@router.post("/change-password")
async def change_password(
    req: dict[str, str],
    auth: Annotated[AuthService, Depends(get_auth_service)],
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Change current user's password."""
    from packages.auth import InvalidCredentialsError

    current = req.get("current_password", "")
    new_pass = req.get("new_password", "")

    try:
        await auth.change_password(current_user.username, current, new_pass)
        return {"message": "Password changed successfully"}
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        ) from exc


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------


@router.get("/users", response_model=list[User])
async def list_users(
    auth: Annotated[AuthService, Depends(get_auth_service)],
    admin: User = Depends(get_current_admin),
) -> list[User]:
    """List all users (admin only)."""
    return await auth.list_users()


@router.patch("/users/{username}/role")
async def change_user_role(
    username: str,
    req: dict[str, str],
    auth: Annotated[AuthService, Depends(get_auth_service)],
    admin: User = Depends(get_current_admin),
) -> User:
    """Change user role (admin only)."""
    from packages.auth import UserNotFoundError

    new_role = req.get("role", "")
    try:
        return await auth.change_role(username, new_role)
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.delete("/users/{username}")
async def deactivate_user(
    username: str,
    auth: Annotated[AuthService, Depends(get_auth_service)],
    admin: User = Depends(get_current_admin),
) -> User:
    """Deactivate a user (admin only)."""
    from packages.auth import UserNotFoundError

    try:
        return await auth.deactivate_user(username)
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
