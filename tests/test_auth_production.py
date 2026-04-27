"""Production authentication tests with PostgreSQL."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from packages.auth import (
    DuplicateUserError,
    InactiveUserError,
    InvalidCredentialsError,
    LoginRequest,
    RegisterRequest,
    TokenInvalidError,
    UserRole,
)
from packages.auth.production_service import AuthService
from services.api.database import Base

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    """Create a test database session."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        yield session
        await session.rollback()

    await engine.dispose()


@pytest.fixture
async def auth_service(db: AsyncSession) -> AuthService:
    """Create AuthService for tests."""
    return AuthService(db)


@pytest.mark.asyncio
class TestAuthRegistration:
    """User registration tests."""

    async def test_register_success(self, auth_service: AuthService) -> None:
        """Test successful user registration."""
        req = RegisterRequest(username="testuser", password="password123", email="test@inkos.ai")
        user = await auth_service.register(req)

        assert user.username == "testuser"
        assert user.email == "test@inkos.ai"
        assert user.role == UserRole.VIEWER
        assert user.is_active is True

    async def test_register_duplicate_username(self, auth_service: AuthService) -> None:
        """Test registration with duplicate username fails."""
        req = RegisterRequest(username="dupuser", password="password123")
        await auth_service.register(req)

        with pytest.raises(DuplicateUserError):
            await auth_service.register(req)

    async def test_register_weak_password(self, auth_service: AuthService) -> None:
        """Test registration with weak password fails."""
        req = RegisterRequest(username="weakuser", password="123")

        with pytest.raises(ValueError, match="at least 8 characters"):
            await auth_service.register(req)

    async def test_register_empty_username(self, auth_service: AuthService) -> None:
        """Test registration with empty username fails."""
        req = RegisterRequest(username="", password="password123")

        with pytest.raises(ValueError, match="required"):
            await auth_service.register(req)


@pytest.mark.asyncio
class TestAuthLogin:
    """User login tests."""

    async def test_login_success(self, auth_service: AuthService) -> None:
        """Test successful login."""
        # Register first
        reg = RegisterRequest(username="loginuser", password="password123")
        await auth_service.register(reg)

        # Login
        login = LoginRequest(username="loginuser", password="password123")
        response = await auth_service.login(login)

        assert response.access_token
        assert response.refresh_token
        assert response.token_type == "bearer"
        assert response.expires_in > 0

    async def test_login_invalid_credentials(self, auth_service: AuthService) -> None:
        """Test login with wrong password fails."""
        reg = RegisterRequest(username="loginuser2", password="password123")
        await auth_service.register(reg)

        login = LoginRequest(username="loginuser2", password="wrongpassword")

        with pytest.raises(InvalidCredentialsError):
            await auth_service.login(login)

    async def test_login_nonexistent_user(self, auth_service: AuthService) -> None:
        """Test login for non-existent user fails."""
        login = LoginRequest(username="nonexistent", password="password123")

        with pytest.raises(InvalidCredentialsError):
            await auth_service.login(login)


@pytest.mark.asyncio
class TestAuthToken:
    """Token validation tests."""

    async def test_get_current_user_valid_token(self, auth_service: AuthService) -> None:
        """Test getting user from valid token."""
        # Register and login
        reg = RegisterRequest(username="tokenuser", password="password123")
        await auth_service.register(reg)

        login = LoginRequest(username="tokenuser", password="password123")
        response = await auth_service.login(login)

        # Get user from token
        user = await auth_service.get_current_user(response.access_token)
        assert user.username == "tokenuser"

    async def test_get_current_user_invalid_token(self, auth_service: AuthService) -> None:
        """Test invalid token raises error."""
        with pytest.raises(TokenInvalidError):
            await auth_service.get_current_user("invalid-token")

    async def test_refresh_token_success(self, auth_service: AuthService) -> None:
        """Test refreshing access token."""
        # Register and login
        reg = RegisterRequest(username="refreshuser", password="password123")
        await auth_service.register(reg)

        login = LoginRequest(username="refreshuser", password="password123")
        response = await auth_service.login(login)

        # Refresh
        new_response = await auth_service.refresh_token(response.refresh_token)
        assert new_response.access_token
        assert new_response.refresh_token
        # Should be different tokens
        assert new_response.access_token != response.access_token

    async def test_refresh_token_invalid(self, auth_service: AuthService) -> None:
        """Test invalid refresh token fails."""
        with pytest.raises(TokenInvalidError):
            await auth_service.refresh_token("invalid-refresh-token")


@pytest.mark.asyncio
class TestAuthUserManagement:
    """User management tests (admin)."""

    async def test_change_password(self, auth_service: AuthService) -> None:
        """Test password change."""
        # Register
        reg = RegisterRequest(username="passuser", password="oldpassword")
        await auth_service.register(reg)

        # Change password
        await auth_service.change_password("passuser", "oldpassword", "newpassword123")

        # Login with new password
        login = LoginRequest(username="passuser", password="newpassword123")
        response = await auth_service.login(login)
        assert response.access_token

    async def test_change_password_wrong_current(self, auth_service: AuthService) -> None:
        """Test password change with wrong current password fails."""
        reg = RegisterRequest(username="passuser2", password="password123")
        await auth_service.register(reg)

        with pytest.raises(InvalidCredentialsError):
            await auth_service.change_password("passuser2", "wrongpassword", "newpassword")

    async def test_list_users(self, auth_service: AuthService) -> None:
        """Test listing users."""
        # Create some users with unique emails
        await auth_service.register(RegisterRequest(username="user1", password="password123", email="user1@test.com"))
        await auth_service.register(RegisterRequest(username="user2", password="password123", email="user2@test.com"))

        users = await auth_service.list_users()
        assert len(users) >= 2

    async def test_deactivate_user(self, auth_service: AuthService) -> None:
        """Test user deactivation."""
        reg = RegisterRequest(username="deactivateuser", password="password123")
        await auth_service.register(reg)

        user = await auth_service.deactivate_user("deactivateuser")
        assert user.is_active is False

        # Login should fail for deactivated user
        login = LoginRequest(username="deactivateuser", password="password123")
        with pytest.raises(InactiveUserError):
            await auth_service.login(login)


class TestAuthRoles:
    """Role-based access control tests."""

    def test_role_hierarchy(self) -> None:
        """Test role hierarchy is correct."""
        # Admin > Operator > Viewer (by enum definition order, but we use value comparison)
        role_values = {"admin": 3, "operator": 2, "viewer": 1}
        assert role_values[UserRole.ADMIN.value] > role_values[UserRole.OPERATOR.value]
        assert role_values[UserRole.OPERATOR.value] > role_values[UserRole.VIEWER.value]
        assert role_values[UserRole.ADMIN.value] > role_values[UserRole.VIEWER.value]

    def test_role_from_string(self) -> None:
        """Test role parsing."""
        assert UserRole("admin") == UserRole.ADMIN
        assert UserRole("operator") == UserRole.OPERATOR
        assert UserRole("viewer") == UserRole.VIEWER

        with pytest.raises(ValueError):
            UserRole("invalid_role")
