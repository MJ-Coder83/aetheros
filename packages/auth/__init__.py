"""Basic JWT-based authentication and authorization for InkosAI.

This module provides simple, stateless JWT authentication with:
- User registration and login
- Password hashing with bcrypt
- JWT token generation and validation
- Role-based access control (RBAC)
- Integration with the Intelligence Profile system

Design principles:
- All auth events are logged to the Tape
- Passwords are never stored in plaintext
- JWT tokens are stateless (no session store needed)
- Roles control API endpoint access
- User IDs map to Intelligence Profile user_ids

Usage::

    from packages.auth.service import AuthService

    svc = AuthService(tape_service=tape_svc)
    user = await svc.register("alice", "password123", role="admin")
    token = await svc.login("alice", "password123")
    # token.access_token can be used in Authorization: Bearer <token>
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID, uuid4

import bcrypt as _bcrypt
import jwt
from pydantic import BaseModel, Field

from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

JWT_SECRET_KEY = "inkosai-dev-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60
JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class UserRole(StrEnum):
    """User roles for RBAC."""

    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class AuthEventType(StrEnum):
    """Auth event types for Tape logging."""

    REGISTERED = "auth.registered"
    LOGIN = "auth.login"
    LOGIN_FAILED = "auth.login_failed"
    TOKEN_REFRESHED = "auth.token_refreshed"
    PASSWORD_CHANGED = "auth.password_changed"
    ROLE_CHANGED = "auth.role_changed"
    USER_DEACTIVATED = "auth.user_deactivated"
    USER_REACTIVATED = "auth.user_reactivated"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class User(BaseModel):
    """A registered user."""

    id: UUID = Field(default_factory=uuid4)
    username: str
    email: str = ""
    role: UserRole = UserRole.VIEWER
    is_active: bool = True
    profile_id: UUID | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_login: datetime | None = None


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str  # user ID
    username: str
    role: str
    exp: int  # POSIX integer timestamp — PyJWT requires int for exp
    iat: int  # POSIX integer timestamp — PyJWT requires int for iat
    jti: str = Field(default_factory=lambda: secrets.token_hex(8))


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = 0
    refresh_token: str | None = None


class LoginRequest(BaseModel):
    """Login request body."""

    username: str
    password: str


class RegisterRequest(BaseModel):
    """Registration request body."""

    username: str
    password: str
    email: str = ""
    role: str = "viewer"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class AuthError(Exception):
    """Base exception for auth operations."""


class UserNotFoundError(AuthError):
    """Raised when a user does not exist."""


class DuplicateUserError(AuthError):
    """Raised when a username already exists."""


class InvalidCredentialsError(AuthError):
    """Raised when login credentials are invalid."""


class InactiveUserError(AuthError):
    """Raised when trying to authenticate an inactive user."""


class TokenExpiredError(AuthError):
    """Raised when a JWT token has expired."""


class TokenInvalidError(AuthError):
    """Raised when a JWT token is invalid."""


class InsufficientPermissionError(AuthError):
    """Raised when a user lacks the required role."""


# ---------------------------------------------------------------------------
# User store (in-memory; Postgres later)
# ---------------------------------------------------------------------------


class UserStore:
    """In-memory store for users and their hashed passwords."""

    def __init__(self) -> None:
        self._users: dict[str, User] = {}  # username -> User
        self._passwords: dict[str, str] = {}  # username -> hashed_password
        self._refresh_tokens: dict[str, str] = {}  # jti -> username

    def add_user(self, user: User, hashed_password: str) -> None:
        self._users[user.username] = user
        self._passwords[user.username] = hashed_password

    def get_user(self, username: str) -> User | None:
        return self._users.get(username)

    def get_user_by_id(self, user_id: UUID) -> User | None:
        for user in self._users.values():
            if user.id == user_id:
                return user
        return None

    def get_hashed_password(self, username: str) -> str | None:
        return self._passwords.get(username)

    def update_user(self, user: User) -> None:
        if user.username not in self._users:
            raise UserNotFoundError(f"User '{user.username}' not found")
        self._users[user.username] = user

    def update_password(self, username: str, hashed_password: str) -> None:
        if username not in self._passwords:
            raise UserNotFoundError(f"User '{username}' not found")
        self._passwords[username] = hashed_password

    def list_users(self) -> list[User]:
        return list(self._users.values())

    def store_refresh_token(self, jti: str, username: str) -> None:
        self._refresh_tokens[jti] = username

    def get_refresh_token_user(self, jti: str) -> str | None:
        return self._refresh_tokens.get(jti)

    def revoke_refresh_token(self, jti: str) -> None:
        self._refresh_tokens.pop(jti, None)


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def _hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return _bcrypt.hashpw(
        password.encode("utf-8"), _bcrypt.gensalt()
    ).decode("utf-8")


def _verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bool(
        _bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    )


# ---------------------------------------------------------------------------
# JWT token utilities
# ---------------------------------------------------------------------------


def _create_access_token(
    user: User,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token."""
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = TokenPayload(
        sub=str(user.id),
        username=user.username,
        role=user.role.value,
        exp=int(expire.timestamp()),
        iat=int(datetime.now(UTC).timestamp()),
    )
    return jwt.encode(payload.model_dump(), JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def _create_refresh_token(user: User) -> tuple[str, str]:
    """Create a refresh token. Returns (token, jti)."""
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


def _decode_token(token: str) -> dict[str, object]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM]
        )
        return dict(payload)
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenInvalidError(f"Invalid token: {exc}") from exc


# ---------------------------------------------------------------------------
# Auth Service -- the main public API
# ---------------------------------------------------------------------------


class AuthService:
    """JWT-based authentication and authorization service.

    AuthService provides:
    - User registration with password hashing
    - Login with JWT token generation
    - Token validation and user extraction
    - Role-based access control
    - Integration with Intelligence Profile user_ids
    - Full audit logging to the Tape

    Usage::

        svc = AuthService(tape_service=tape_svc)
        user = await svc.register("alice", "password123")
        token = await svc.login("alice", "password123")
        decoded = await svc.validate_token(token.access_token)
    """

    def __init__(
        self,
        tape_service: TapeService | None = None,
        store: UserStore | None = None,
    ) -> None:
        self._tape = tape_service
        self._store = store or UserStore()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    async def register(
        self,
        username: str,
        password: str,
        email: str = "",
        role: str = "viewer",
    ) -> User:
        """Register a new user.

        Args:
            username: Unique username.
            password: Plaintext password (will be hashed).
            email: Optional email address.
            role: User role (admin, operator, viewer).

        Returns:
            The newly created User.

        Raises:
            DuplicateUserError: if the username already exists.
            ValueError: if the username or password is empty.
        """
        if not username.strip():
            raise ValueError("Username must not be empty")
        if not password.strip():
            raise ValueError("Password must not be empty")
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters")

        if self._store.get_user(username) is not None:
            raise DuplicateUserError(f"User '{username}' already exists")

        user_role = UserRole(role)
        hashed = _hash_password(password)
        user = User(
            username=username,
            email=email,
            role=user_role,
        )
        self._store.add_user(user, hashed)

        if self._tape is not None:
            await self._tape.log_event(
                event_type=AuthEventType.REGISTERED.value,
                payload={
                    "user_id": str(user.id),
                    "username": username,
                    "role": user_role.value,
                },
                agent_id="auth-service",
            )

        return user

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    async def login(
        self,
        username: str,
        password: str,
    ) -> TokenResponse:
        """Authenticate a user and return JWT tokens.

        Args:
            username: The username.
            password: The plaintext password.

        Returns:
            A TokenResponse with access and refresh tokens.

        Raises:
            InvalidCredentialsError: if the credentials are invalid.
            InactiveUserError: if the user is deactivated.
        """
        user = self._store.get_user(username)
        if user is None:
            if self._tape is not None:
                await self._tape.log_event(
                    event_type=AuthEventType.LOGIN_FAILED.value,
                    payload={"username": username, "reason": "user_not_found"},
                    agent_id="auth-service",
                )
            raise InvalidCredentialsError("Invalid credentials")

        hashed = self._store.get_hashed_password(username)
        if hashed is None or not _verify_password(password, hashed):
            if self._tape is not None:
                await self._tape.log_event(
                    event_type=AuthEventType.LOGIN_FAILED.value,
                    payload={"username": username, "reason": "wrong_password"},
                    agent_id="auth-service",
                )
            raise InvalidCredentialsError("Invalid credentials")

        if not user.is_active:
            raise InactiveUserError(f"User '{username}' is deactivated")

        # Update last login
        user = user.model_copy(update={"last_login": datetime.now(UTC)})
        self._store.update_user(user)

        # Generate tokens
        access_token = _create_access_token(user)
        refresh_token, jti = _create_refresh_token(user)
        self._store.store_refresh_token(jti, username)

        if self._tape is not None:
            await self._tape.log_event(
                event_type=AuthEventType.LOGIN.value,
                payload={
                    "user_id": str(user.id),
                    "username": username,
                },
                agent_id="auth-service",
            )

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token=refresh_token,
        )

    # ------------------------------------------------------------------
    # Token validation
    # ------------------------------------------------------------------

    async def validate_token(self, token: str) -> dict[str, object]:
        """Validate a JWT access token and return its payload.

        Raises:
            TokenExpiredError: if the token has expired.
            TokenInvalidError: if the token is invalid.
        """
        return _decode_token(token)

    async def get_current_user(self, token: str) -> User:
        """Get the current user from a JWT token.

        Raises:
            TokenInvalidError: if the token is invalid.
            UserNotFoundError: if the user no longer exists.
            InactiveUserError: if the user is deactivated.
        """
        payload = _decode_token(token)
        user_id = UUID(str(payload.get("sub", "")))
        user = self._store.get_user_by_id(user_id)
        if user is None:
            raise UserNotFoundError(f"User {user_id} not found")
        if not user.is_active:
            raise InactiveUserError(f"User '{user.username}' is deactivated")
        return user

    async def require_role(
        self,
        token: str,
        required_role: UserRole,
    ) -> User:
        """Validate token and require a minimum role.

        Admins can access everything; operators can access operator+viewer;
        viewers can only access viewer endpoints.

        Raises:
            InsufficientPermissionError: if the user lacks the required role.
        """
        user = await self.get_current_user(token)

        role_hierarchy = {
            UserRole.ADMIN: 3,
            UserRole.OPERATOR: 2,
            UserRole.VIEWER: 1,
        }
        user_level = role_hierarchy.get(user.role, 0)
        required_level = role_hierarchy.get(required_role, 0)

        if user_level < required_level:
            raise InsufficientPermissionError(
                f"User '{user.username}' has role '{user.role.value}' "
                f"but requires '{required_role.value}'"
            )

        return user

    # ------------------------------------------------------------------
    # Token refresh
    # ------------------------------------------------------------------

    async def refresh_token(self, refresh_token_str: str) -> TokenResponse:
        """Refresh an access token using a refresh token.

        Args:
            refresh_token_str: The refresh token.

        Returns:
            A new TokenResponse with fresh access and refresh tokens.

        Raises:
            TokenInvalidError: if the refresh token is invalid.
        """
        payload = _decode_token(refresh_token_str)

        if str(payload.get("type", "")) != "refresh":
            raise TokenInvalidError("Not a refresh token")

        jti = str(payload.get("jti", ""))
        username = self._store.get_refresh_token_user(jti)
        if username is None:
            raise TokenInvalidError("Refresh token not found or revoked")

        user = self._store.get_user(username)
        if user is None or not user.is_active:
            self._store.revoke_refresh_token(jti)
            raise TokenInvalidError("User not found or inactive")

        # Revoke old refresh token
        self._store.revoke_refresh_token(jti)

        # Generate new tokens
        access_token = _create_access_token(user)
        new_refresh_token, new_jti = _create_refresh_token(user)
        self._store.store_refresh_token(new_jti, username)

        if self._tape is not None:
            await self._tape.log_event(
                event_type=AuthEventType.TOKEN_REFRESHED.value,
                payload={"username": username},
                agent_id="auth-service",
            )

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token=new_refresh_token,
        )

    # ------------------------------------------------------------------
    # User management
    # ------------------------------------------------------------------

    async def change_password(
        self,
        username: str,
        current_password: str,
        new_password: str,
    ) -> None:
        """Change a user's password.

        Args:
            username: The username.
            current_password: Current password for verification.
            new_password: New password to set.

        Raises:
            InvalidCredentialsError: if current password is wrong.
            ValueError: if new password is too short.
        """
        if len(new_password) < 6:
            raise ValueError("New password must be at least 6 characters")

        hashed = self._store.get_hashed_password(username)
        if hashed is None or not _verify_password(current_password, hashed):
            raise InvalidCredentialsError("Current password is incorrect")

        self._store.update_password(username, _hash_password(new_password))

        if self._tape is not None:
            await self._tape.log_event(
                event_type=AuthEventType.PASSWORD_CHANGED.value,
                payload={"username": username},
                agent_id="auth-service",
            )

    async def change_role(
        self,
        username: str,
        new_role: str,
    ) -> User:
        """Change a user's role.

        Args:
            username: The username.
            new_role: New role (admin, operator, viewer).

        Raises:
            UserNotFoundError: if the user does not exist.
        """
        user = self._store.get_user(username)
        if user is None:
            raise UserNotFoundError(f"User '{username}' not found")

        role = UserRole(new_role)
        user = user.model_copy(update={"role": role})
        self._store.update_user(user)

        if self._tape is not None:
            await self._tape.log_event(
                event_type=AuthEventType.ROLE_CHANGED.value,
                payload={"username": username, "new_role": role.value},
                agent_id="auth-service",
            )

        return user

    async def deactivate_user(self, username: str) -> User:
        """Deactivate a user account."""
        user = self._store.get_user(username)
        if user is None:
            raise UserNotFoundError(f"User '{username}' not found")

        user = user.model_copy(update={"is_active": False})
        self._store.update_user(user)

        if self._tape is not None:
            await self._tape.log_event(
                event_type=AuthEventType.USER_DEACTIVATED.value,
                payload={"username": username},
                agent_id="auth-service",
            )

        return user

    async def reactivate_user(self, username: str) -> User:
        """Reactivate a deactivated user account."""
        user = self._store.get_user(username)
        if user is None:
            raise UserNotFoundError(f"User '{username}' not found")

        user = user.model_copy(update={"is_active": True})
        self._store.update_user(user)

        if self._tape is not None:
            await self._tape.log_event(
                event_type=AuthEventType.USER_REACTIVATED.value,
                payload={"username": username},
                agent_id="auth-service",
            )

        return user

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def get_user(self, username: str) -> User:
        """Get a user by username."""
        user = self._store.get_user(username)
        if user is None:
            raise UserNotFoundError(f"User '{username}' not found")
        return user

    async def list_users(self) -> list[User]:
        """List all users."""
        return self._store.list_users()

    def get_store(self) -> UserStore:
        """Return the user store (for FastAPI dependency injection)."""
        return self._store
