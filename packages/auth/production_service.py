"""Production-ready JWT authentication service with PostgreSQL persistence."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import bcrypt
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.auth import (
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_REFRESH_TOKEN_EXPIRE_DAYS,
    JWT_SECRET_KEY,
    DuplicateUserError,
    InactiveUserError,
    InvalidCredentialsError,
    LoginRequest,
    RegisterRequest,
    TokenExpiredError,
    TokenInvalidError,
    TokenPayload,
    TokenResponse,
    User,
    UserNotFoundError,
    UserRole,
)
from services.api.database import RefreshTokenORM, UserORM


class AuthService:
    """Production-ready authentication service with PostgreSQL."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Password handling
    # ------------------------------------------------------------------

    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def _verify_password(self, plain: str, hashed: str) -> bool:
        """Verify a password against its hash."""
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

    # ------------------------------------------------------------------
    # Token handling
    # ------------------------------------------------------------------

    def _create_access_token(self, user: User) -> str:
        """Create JWT access token."""
        expire = datetime.now(UTC) + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = TokenPayload(
            sub=str(user.id),
            username=user.username,
            role=user.role,
            exp=int(expire.timestamp()),
            iat=int(datetime.now(UTC).timestamp()),
            jti=secrets.token_hex(16),  # Add jti to satisfy PyJWT validation
            type="access",
        )
        return jwt.encode(payload.model_dump(), JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    def _create_refresh_token(self, user: User) -> tuple[str, str]:
        """Create refresh token and return (token, jti)."""
        jti = secrets.token_hex(16)
        expire = datetime.now(UTC) + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        payload = {
            "sub": str(user.id),
            "username": user.username,
            "type": "refresh",
            "jti": jti,
            "exp": int(expire.timestamp()),
            "iat": int(datetime.now(UTC).timestamp()),
        }
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return token, jti

    def _decode_token(self, token: str) -> dict:
        """Decode and validate JWT."""
        try:
            return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError as exc:
            raise TokenExpiredError("Token has expired") from exc
        except jwt.InvalidTokenError as exc:
            raise TokenInvalidError(f"Invalid token: {exc}") from exc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def register(self, req: RegisterRequest) -> User:
        """Register a new user."""
        if not req.username.strip():
            raise ValueError("Username required")
        if not req.password or len(req.password) < 8:
            raise ValueError("Password must be at least 8 characters")

        # Check for duplicates
        existing = await self._db.execute(
            select(UserORM).where(UserORM.username == req.username)
        )
        if existing.scalar_one_or_none():
            raise DuplicateUserError(f"User '{req.username}' already exists")

        hashed = self._hash_password(req.password)
        user_id = str(uuid4())

        orm_user = UserORM(
            id=user_id,
            username=req.username,
            email=req.email,
            hashed_password=hashed,
            role=req.role,
            is_active=True,
            created_at=datetime.now(UTC),
        )
        self._db.add(orm_user)
        await self._db.commit()

        return User(
            id=UUID(user_id),
            username=req.username,
            email=req.email,
            role=UserRole(req.role),
            is_active=True,
            created_at=orm_user.created_at,
        )

    async def login(self, req: LoginRequest) -> TokenResponse:
        """Authenticate and return tokens."""
        result = await self._db.execute(
            select(UserORM).where(UserORM.username == req.username)
        )
        orm_user = result.scalar_one_or_none()

        if not orm_user or not self._verify_password(req.password, orm_user.hashed_password):
            raise InvalidCredentialsError("Invalid username or password")

        if not orm_user.is_active:
            raise InactiveUserError("User account is deactivated")

        # Update last login
        orm_user.last_login = datetime.now(UTC)
        await self._db.commit()

        user = User(
            id=UUID(orm_user.id),
            username=orm_user.username,
            email=orm_user.email,
            role=UserRole(orm_user.role),
            is_active=orm_user.is_active,
            last_login=orm_user.last_login,
        )

        access_token = self._create_access_token(user)
        refresh_token, jti = self._create_refresh_token(user)

        # Store refresh token in DB
        rt = RefreshTokenORM(
            jti=jti,
            user_id=str(user.id),
            username=user.username,
            expires_at=datetime.now(UTC) + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        )
        self._db.add(rt)
        await self._db.commit()

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token=refresh_token,
        )

    async def refresh_token(self, refresh_token_str: str) -> TokenResponse:
        """Refresh access token."""
        payload = self._decode_token(refresh_token_str)

        if payload.get("type") != "refresh":
            raise TokenInvalidError("Not a refresh token")

        jti = payload.get("jti")
        result = await self._db.execute(
            select(RefreshTokenORM).where(
                RefreshTokenORM.jti == jti,
                RefreshTokenORM.revoked == False,
            )
        )
        rt = result.scalar_one_or_none()

        if not rt:
            raise TokenInvalidError("Refresh token not found")
        # Handle both timezone-aware and naive datetimes
        expires_at = rt.expires_at
        now = datetime.now(UTC)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < now:
            raise TokenInvalidError("Refresh token expired or revoked")

        # Get user
        user_result = await self._db.execute(
            select(UserORM).where(UserORM.id == rt.user_id, UserORM.is_active == True)
        )
        orm_user = user_result.scalar_one_or_none()
        if not orm_user:
            raise TokenInvalidError("User not found or inactive")

        user = User(
            id=UUID(orm_user.id),
            username=orm_user.username,
            email=orm_user.email,
            role=UserRole(orm_user.role),
            is_active=orm_user.is_active,
        )

        # Revoke old refresh token
        rt.revoked = True

        # Generate new tokens
        access_token = self._create_access_token(user)
        new_refresh_token, new_jti = self._create_refresh_token(user)

        new_rt = RefreshTokenORM(
            jti=new_jti,
            user_id=str(user.id),
            username=user.username,
            expires_at=datetime.now(UTC) + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        )
        self._db.add(new_rt)
        await self._db.commit()

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token=new_refresh_token,
        )

    async def get_current_user(self, token: str) -> User:
        """Get user from access token."""
        payload = self._decode_token(token)

        if payload.get("type") != "access":
            raise TokenInvalidError("Not an access token")

        user_id = payload.get("sub")
        result = await self._db.execute(
            select(UserORM).where(UserORM.id == user_id, UserORM.is_active == True)
        )
        orm_user = result.scalar_one_or_none()
        if not orm_user:
            raise UserNotFoundError("User not found")

        return User(
            id=orm_user.id,
            username=orm_user.username,
            email=orm_user.email,
            role=orm_user.role,
            is_active=orm_user.is_active,
            last_login=orm_user.last_login.isoformat() if orm_user.last_login else None,
        )

    async def logout(self, refresh_token: str) -> None:
        """Revoke refresh token."""
        try:
            payload = self._decode_token(refresh_token)
            jti = payload.get("jti")
            if jti:
                await self._db.execute(
                    select(RefreshTokenORM)
                    .where(RefreshTokenORM.jti == jti)
                    .update({"revoked": True})
                )
                await self._db.commit()
        except TokenInvalidError:
            pass  # Already invalid, ignore

    async def cleanup_expired_tokens(self) -> int:
        """Delete expired tokens. Returns count deleted."""
        result = await self._db.execute(
            select(RefreshTokenORM)
            .where(RefreshTokenORM.expires_at < datetime.now(UTC))
            .delete()
        )
        await self._db.commit()
        return result.rowcount if hasattr(result, 'rowcount') else 0

    async def get_user(self, username: str) -> User:
        """Get user by username."""
        result = await self._db.execute(
            select(UserORM).where(UserORM.username == username)
        )
        orm_user = result.scalar_one_or_none()
        if not orm_user:
            raise UserNotFoundError(f"User '{username}' not found")

        return User(
            id=orm_user.id,
            username=orm_user.username,
            email=orm_user.email,
            role=orm_user.role,
            is_active=orm_user.is_active,
            last_login=orm_user.last_login.isoformat() if orm_user.last_login else None,
        )

    async def list_users(self) -> list[User]:
        """List all users."""
        result = await self._db.execute(select(UserORM))
        orm_users = result.scalars().all()

        return [
            User(
                id=u.id,
                username=u.username,
                email=u.email,
                role=u.role,
                is_active=u.is_active,
                last_login=u.last_login.isoformat() if u.last_login else None,
            )
            for u in orm_users
        ]

    async def change_password(
        self,
        username: str,
        current_password: str,
        new_password: str,
    ) -> None:
        """Change user's password."""
        result = await self._db.execute(
            select(UserORM).where(UserORM.username == username)
        )
        orm_user = result.scalar_one_or_none()
        if not orm_user:
            raise UserNotFoundError(f"User '{username}' not found")

        if not self._verify_password(current_password, orm_user.hashed_password):
            raise InvalidCredentialsError("Current password is incorrect")

        if len(new_password) < 8:
            raise ValueError("Password must be at least 8 characters")

        orm_user.hashed_password = self._hash_password(new_password)
        await self._db.commit()

    async def change_role(self, username: str, new_role: str) -> User:
        """Change user role."""
        result = await self._db.execute(
            select(UserORM).where(UserORM.username == username)
        )
        orm_user = result.scalar_one_or_none()
        if not orm_user:
            raise UserNotFoundError(f"User '{username}' not found")

        orm_user.role = new_role
        await self._db.commit()

        return User(
            id=UUID(orm_user.id),
            username=orm_user.username,
            email=orm_user.email,
            role=UserRole(orm_user.role),
            is_active=orm_user.is_active,
            last_login=orm_user.last_login,
        )

    async def deactivate_user(self, username: str) -> User:
        """Deactivate a user."""
        result = await self._db.execute(
            select(UserORM).where(UserORM.username == username)
        )
        orm_user = result.scalar_one_or_none()
        if not orm_user:
            raise UserNotFoundError(f"User '{username}' not found")

        orm_user.is_active = False
        await self._db.commit()

        return User(
            id=orm_user.id,
            username=orm_user.username,
            email=orm_user.email,
            role=orm_user.role,
            is_active=orm_user.is_active,
            last_login=orm_user.last_login.isoformat() if orm_user.last_login else None,
        )
