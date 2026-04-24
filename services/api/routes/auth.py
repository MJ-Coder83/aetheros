"""Authentication API routes."""

from fastapi import APIRouter, HTTPException, Query

from packages.auth import (
    InvalidCredentialsError,
    LoginRequest,
    RegisterRequest,
    TokenExpiredError,
    TokenInvalidError,
    UserNotFoundError,
)
from services.api.dependencies import AuthServiceDep

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register_user(
    body: RegisterRequest,
    svc: AuthServiceDep,
) -> dict[str, object]:
    """Register a new user."""
    user = await svc.register(
        username=body.username,
        password=body.password,
        email=body.email,
        role=body.role,
    )
    return user.model_dump()


@router.post("/login")
async def login_user(
    body: LoginRequest,
    svc: AuthServiceDep,
) -> dict[str, object]:
    """Login and get JWT tokens."""
    token = await svc.login(body.username, body.password)
    return token.model_dump()


@router.post("/refresh")
async def refresh_token(
    svc: AuthServiceDep,
    refresh_token: str = "",
) -> dict[str, object]:
    """Refresh an access token."""
    try:
        token = await svc.refresh_token(refresh_token)
        return token.model_dump()
    except (TokenInvalidError, TokenExpiredError) as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get("/me")
async def get_current_user(
    svc: AuthServiceDep,
    token: str = Query(...),
) -> dict[str, object]:
    """Get the current user from a JWT token."""
    try:
        user = await svc.get_current_user(token)
        return user.model_dump()
    except (TokenInvalidError, TokenExpiredError, UserNotFoundError) as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.post("/change-password")
async def change_password(
    svc: AuthServiceDep,
    username: str = "",
    current_password: str = "",
    new_password: str = "",
) -> dict[str, object]:
    """Change a user's password."""
    try:
        await svc.change_password(username, current_password, new_password)
        return {"message": "Password changed successfully"}
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get("/users")
async def list_users(
    svc: AuthServiceDep,
) -> list[dict[str, object]]:
    """List all users."""
    users = await svc.list_users()
    return [u.model_dump() for u in users]


@router.post("/users/{username}/role")
async def change_role(
    username: str,
    svc: AuthServiceDep,
    new_role: str = "",
) -> dict[str, object]:
    """Change a user's role."""
    try:
        user = await svc.change_role(username, new_role)
        return user.model_dump()
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/users/{username}/deactivate")
async def deactivate_user(
    username: str,
    svc: AuthServiceDep,
) -> dict[str, object]:
    """Deactivate a user account."""
    try:
        user = await svc.deactivate_user(username)
        return user.model_dump()
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/users/{username}/reactivate")
async def reactivate_user(
    username: str,
    svc: AuthServiceDep,
) -> dict[str, object]:
    """Reactivate a deactivated user account."""
    try:
        user = await svc.reactivate_user(username)
        return user.model_dump()
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
