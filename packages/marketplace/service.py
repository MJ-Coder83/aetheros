"""InkosAI Plugin Marketplace Service.

Implements the full marketplace lifecycle:
- Plugin publishing and discovery
- Search with category, tag, and full-text filters
- Installation with permission approval flow
- Rating system (1-5 stars)
- Audit logging to Tape

All operations are async and logged to the Tape for full auditability.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PluginCategory(StrEnum):
    """Plugin categories for classification."""

    AGENT = "agent"
    SKILL = "skill"
    WORKFLOW = "workflow"
    INTEGRATION = "integration"
    ANALYTICS = "analytics"
    UTILITY = "utility"
    TEMPLATE = "template"


class PluginSortOrder(StrEnum):
    """Sort order for marketplace listings."""

    NEWEST = "newest"
    POPULAR = "popular"
    HIGHEST_RATED = "highest_rated"
    MOST_INSTALLED = "most_installed"
    NAME_ASC = "name_asc"


class PluginInstallationStatus(StrEnum):
    """Status of a plugin installation."""

    PENDING_PERMISSIONS = "pending_permissions"
    INSTALLING = "installing"
    ACTIVE = "active"
    DISABLED = "disabled"
    UNINSTALLED = "uninstalled"


class PluginPermissionLevel(StrEnum):
    """Permission levels required by a plugin."""

    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    NETWORK = "network"
    FILESYSTEM = "filesystem"
    ADMIN = "admin"


class PermissionRequestStatus(StrEnum):
    """Status of a permission approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class MarketplaceEventType(StrEnum):
    """Marketplace event types for Tape logging."""

    PUBLISHED = "marketplace.plugin_published"
    UPDATED = "marketplace.plugin_updated"
    UNPUBLISHED = "marketplace.plugin_unpublished"
    SEARCHED = "marketplace.searched"
    DISCOVERED = "marketplace.discovered"
    INSTALLED = "marketplace.plugin_installed"
    UNINSTALLED = "marketplace.plugin_uninstalled"
    RATED = "marketplace.plugin_rated"
    PERMISSIONS_APPROVED = "marketplace.permissions_approved"
    PERMISSIONS_REJECTED = "marketplace.permissions_rejected"
    PERMISSIONS_REQUESTED = "marketplace.permissions_requested"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class PluginListing(BaseModel):
    """A published plugin in the marketplace."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    display_name: str
    description: str
    version: str
    author: str
    category: PluginCategory
    tags: list[str] = []
    permissions: list[PluginPermissionLevel] = []
    config_schema: dict[str, object] = {}
    homepage_url: str = ""
    repository_url: str = ""
    icon_url: str = ""
    downloads: int = 0
    average_rating: float = 0.0
    rating_count: int = 0
    is_verified: bool = False
    is_featured: bool = False
    min_platform_version: str = "0.1.0"
    published_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PluginInstallation(BaseModel):
    """An installed plugin in a domain."""

    id: UUID = Field(default_factory=uuid4)
    plugin_id: UUID
    domain_id: str
    installed_by: str
    status: PluginInstallationStatus = PluginInstallationStatus.PENDING_PERMISSIONS
    version: str = ""
    config: dict[str, object] = {}
    permissions_granted: list[PluginPermissionLevel] = []
    installed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PluginRating(BaseModel):
    """A user rating for a plugin."""

    id: UUID = Field(default_factory=uuid4)
    plugin_id: UUID
    user_id: str
    score: int
    review: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PermissionRequest(BaseModel):
    """A pending permission approval request for a plugin installation."""

    id: UUID = Field(default_factory=uuid4)
    installation_id: UUID
    plugin_id: UUID
    domain_id: str
    permissions: list[PluginPermissionLevel]
    status: PermissionRequestStatus = PermissionRequestStatus.PENDING
    requested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    resolved_at: datetime | None = None
    resolved_by: str | None = None


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class MarketplaceError(Exception):
    """Base exception for marketplace operations."""


class PluginNotFoundError(MarketplaceError):
    """Raised when a requested plugin listing does not exist."""


class DuplicateListingError(MarketplaceError):
    """Raised when a plugin with the same name and author already exists."""


class InstallationNotFoundError(MarketplaceError):
    """Raised when a plugin installation record does not exist."""


class DuplicateInstallationError(MarketplaceError):
    """Raised when a plugin is already installed in a domain."""


class InvalidPermissionError(MarketplaceError):
    """Raised when invalid permissions are specified."""


class InsufficientPermissionLevelError(MarketplaceError):
    """Raised when a permission request tries to approve more than requested."""


class PermissionRequestNotFoundError(MarketplaceError):
    """Raised when a permission request does not exist."""


class AlreadyRatedError(MarketplaceError):
    """Raised when a user tries to rate a plugin they already rated."""


class RatingValidationError(MarketplaceError):
    """Raised when a rating score is out of range."""


class SelfRatingError(MarketplaceError):
    """Raised when a plugin author tries to rate their own plugin."""


# ---------------------------------------------------------------------------
# In-memory stores
# ---------------------------------------------------------------------------


class PublishedPluginStore:
    """In-memory store for published plugin listings."""

    def __init__(self) -> None:
        self._listings: dict[UUID, PluginListing] = {}

    def add(self, listing: PluginListing) -> None:
        self._listings[listing.id] = listing

    def get(self, plugin_id: UUID) -> PluginListing | None:
        return self._listings.get(plugin_id)

    def update(self, listing: PluginListing) -> None:
        self._listings[listing.id] = listing

    def remove(self, plugin_id: UUID) -> PluginListing | None:
        return self._listings.pop(plugin_id, None)

    def list_all(self) -> list[PluginListing]:
        return list(self._listings.values())

    def find_by_name_and_author(self, name: str, author: str) -> PluginListing | None:
        for listing in self._listings.values():
            if listing.name == name and listing.author == author:
                return listing
        return None


class InstallationStore:
    """In-memory store for plugin installations."""

    def __init__(self) -> None:
        self._installations: dict[UUID, PluginInstallation] = {}

    def add(self, installation: PluginInstallation) -> None:
        self._installations[installation.id] = installation

    def get(self, installation_id: UUID) -> PluginInstallation | None:
        return self._installations.get(installation_id)

    def update(self, installation: PluginInstallation) -> None:
        self._installations[installation.id] = installation

    def remove(self, installation_id: UUID) -> PluginInstallation | None:
        return self._installations.pop(installation_id, None)

    def list_for_domain(self, domain_id: str) -> list[PluginInstallation]:
        return [
            inst
            for inst in self._installations.values()
            if inst.domain_id == domain_id
            and inst.status != PluginInstallationStatus.UNINSTALLED
        ]

    def find_active(self, plugin_id: UUID, domain_id: str) -> PluginInstallation | None:
        for inst in self._installations.values():
            if (
                inst.plugin_id == plugin_id
                and inst.domain_id == domain_id
                and inst.status != PluginInstallationStatus.UNINSTALLED
            ):
                return inst
        return None


class RatingStore:
    """In-memory store for plugin ratings."""

    def __init__(self) -> None:
        self._ratings: dict[UUID, PluginRating] = {}

    def add(self, rating: PluginRating) -> None:
        self._ratings[rating.id] = rating

    def get(self, rating_id: UUID) -> PluginRating | None:
        return self._ratings.get(rating_id)

    def list_for_plugin(self, plugin_id: UUID) -> list[PluginRating]:
        return [r for r in self._ratings.values() if r.plugin_id == plugin_id]

    def find_by_user_and_plugin(self, user_id: str, plugin_id: UUID) -> PluginRating | None:
        for r in self._ratings.values():
            if r.user_id == user_id and r.plugin_id == plugin_id:
                return r
        return None


class PermissionRequestStore:
    """In-memory store for permission requests."""

    def __init__(self) -> None:
        self._requests: dict[UUID, PermissionRequest] = {}

    def add(self, request: PermissionRequest) -> None:
        self._requests[request.id] = request

    def get(self, request_id: UUID) -> PermissionRequest | None:
        return self._requests.get(request_id)

    def update(self, request: PermissionRequest) -> None:
        self._requests[request.id] = request

    def list_for_domain(self, domain_id: str) -> list[PermissionRequest]:
        return [
            r for r in self._requests.values()
            if r.domain_id == domain_id and r.status == PermissionRequestStatus.PENDING
        ]

    def find_by_installation(self, installation_id: UUID) -> PermissionRequest | None:
        for r in self._requests.values():
            if r.installation_id == installation_id and r.status == PermissionRequestStatus.PENDING:
                return r
        return None


# ---------------------------------------------------------------------------
# Marketplace Service
# ---------------------------------------------------------------------------


class MarketplaceService:
    """Plugin Marketplace service — discovery, search, installation, rating, and permissions.

    All operations are logged to the Tape for full auditability.

    Usage::

        svc = MarketplaceService(tape_service=tape_svc)
        listing = await svc.publish_plugin(...)
        results = await svc.search("analytics")
        installation = await svc.install(plugin_id, domain_id, user_id)
    """

    def __init__(
        self,
        tape_service: TapeService,
        plugin_store: PublishedPluginStore | None = None,
        installation_store: InstallationStore | None = None,
        rating_store: RatingStore | None = None,
        permission_store: PermissionRequestStore | None = None,
    ) -> None:
        self._tape = tape_service
        self._plugins = plugin_store or PublishedPluginStore()
        self._installations = installation_store or InstallationStore()
        self._ratings = rating_store or RatingStore()
        self._permissions = permission_store or PermissionRequestStore()

    # ------------------------------------------------------------------
    # Plugin publishing
    # ------------------------------------------------------------------

    async def publish_plugin(
        self,
        name: str,
        display_name: str,
        description: str,
        version: str,
        author: str,
        category: PluginCategory,
        tags: list[str] | None = None,
        permissions: list[PluginPermissionLevel] | None = None,
        config_schema: dict[str, object] | None = None,
        homepage_url: str = "",
        repository_url: str = "",
        icon_url: str = "",
        is_featured: bool = False,
        min_platform_version: str = "0.1.0",
    ) -> PluginListing:
        """Publish a new plugin to the marketplace.

        Args:
            name: Unique plugin identifier (slug).
            display_name: Human-readable name.
            description: Plugin description.
            version: Semantic version string.
            author: Plugin author identifier.
            category: Plugin category.
            tags: Optional tags for discovery.
            permissions: Permissions required by the plugin.
            config_schema: Optional JSON schema for plugin configuration.
            homepage_url: Optional homepage URL.
            repository_url: Optional repository URL.
            icon_url: Optional icon URL.
            is_featured: Whether the plugin is featured.
            min_platform_version: Minimum platform version required.

        Returns:
            The newly created PluginListing.

        Raises:
            DuplicateListingError: if a plugin with the same name and author exists.
            ValueError: if required fields are empty.
        """
        if not name.strip():
            raise ValueError("Plugin name must not be empty")
        if not display_name.strip():
            raise ValueError("Display name must not be empty")
        if not version.strip():
            raise ValueError("Version must not be empty")
        if not author.strip():
            raise ValueError("Author must not be empty")

        existing = self._plugins.find_by_name_and_author(name, author)
        if existing is not None:
            raise DuplicateListingError(
                f"Plugin '{name}' by '{author}' already exists"
            )

        listing = PluginListing(
            name=name,
            display_name=display_name,
            description=description,
            version=version,
            author=author,
            category=category,
            tags=tags or [],
            permissions=permissions or [],
            config_schema=config_schema or {},
            homepage_url=homepage_url,
            repository_url=repository_url,
            icon_url=icon_url,
            is_featured=is_featured,
            min_platform_version=min_platform_version,
        )
        self._plugins.add(listing)

        await self._tape.log_event(
            event_type=MarketplaceEventType.PUBLISHED.value,
            payload={
                "plugin_id": str(listing.id),
                "name": name,
                "version": version,
                "author": author,
                "category": category.value,
            },
            agent_id="marketplace-service",
        )

        return listing

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    async def discover(
        self,
        category: PluginCategory | None = None,
        tags: list[str] | None = None,
        featured_only: bool = False,
        sort: PluginSortOrder = PluginSortOrder.NEWEST,
        limit: int = 20,
        offset: int = 0,
    ) -> list[PluginListing]:
        """Browse plugins with optional category/tag filters.

        Args:
            category: Filter by plugin category.
            tags: Filter by tags (match any).
            featured_only: Only return featured plugins.
            sort: Sort order for results.
            limit: Maximum results to return.
            offset: Pagination offset.

        Returns:
            Filtered and sorted list of PluginListings.
        """
        results = self._plugins.list_all()

        if category is not None:
            results = [p for p in results if p.category == category]

        if tags:
            tag_set = set(tags)
            results = [p for p in results if tag_set.intersection(p.tags)]

        if featured_only:
            results = [p for p in results if p.is_featured]

        results = self._sort_listings(results, sort)

        paginated = results[offset : offset + limit]

        await self._tape.log_event(
            event_type=MarketplaceEventType.DISCOVERED.value,
            payload={
                "category": category.value if category else None,
                "tags": tags or [],
                "featured_only": featured_only,
                "sort": sort.value,
                "result_count": len(paginated),
            },
            agent_id="marketplace-service",
        )

        return paginated

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        category: PluginCategory | None = None,
        sort: PluginSortOrder = PluginSortOrder.NEWEST,
        limit: int = 20,
        offset: int = 0,
    ) -> list[PluginListing]:
        """Full-text search across plugin metadata.

        Searches name, display_name, description, author, and tags.

        Args:
            query: Search query (case-insensitive).
            category: Optional category filter.
            sort: Sort order for results.
            limit: Maximum results.
            offset: Pagination offset.

        Returns:
            Matching and sorted list of PluginListings.
        """
        q = query.lower()
        all_plugins = self._plugins.list_all()

        scored: list[tuple[int, PluginListing]] = []
        for plugin in all_plugins:
            score = 0
            if q in plugin.name.lower():
                score += 10
            if q in plugin.display_name.lower():
                score += 8
            if q in plugin.description.lower():
                score += 5
            if q in plugin.author.lower():
                score += 3
            for tag in plugin.tags:
                if q in tag.lower():
                    score += 4
                    break
            if score > 0:
                scored.append((score, plugin))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [plugin for _, plugin in scored]

        if category is not None:
            results = [p for p in results if p.category == category]

        results = self._sort_listings(results, sort)
        paginated = results[offset : offset + limit]

        await self._tape.log_event(
            event_type=MarketplaceEventType.SEARCHED.value,
            payload={
                "query": query,
                "category": category.value if category else None,
                "result_count": len(paginated),
            },
            agent_id="marketplace-service",
        )

        return paginated

    # ------------------------------------------------------------------
    # Get plugin
    # ------------------------------------------------------------------

    async def get_plugin(self, plugin_id: UUID) -> PluginListing:
        """Get detailed plugin information by ID.

        Args:
            plugin_id: The plugin's UUID.

        Returns:
            The PluginListing.

        Raises:
            PluginNotFoundError: if the plugin does not exist.
        """
        listing = self._plugins.get(plugin_id)
        if listing is None:
            raise PluginNotFoundError(f"Plugin '{plugin_id}' not found")
        return listing

    # ------------------------------------------------------------------
    # Installation
    # ------------------------------------------------------------------

    async def install(
        self,
        plugin_id: UUID,
        domain_id: str,
        user_id: str,
        config: dict[str, object] | None = None,
    ) -> tuple[PluginInstallation, PermissionRequest | None]:
        """Install a plugin into a domain.

        If the plugin requires permissions, a PermissionRequest is created
        and the installation stays in PENDING_PERMISSIONS status until
        the permissions are approved.

        Args:
            plugin_id: The plugin to install.
            domain_id: Target domain.
            user_id: User performing the installation.
            config: Optional plugin configuration.

        Returns:
            Tuple of (PluginInstallation, optional PermissionRequest).
            PermissionRequest is None if the plugin requires no permissions.

        Raises:
            PluginNotFoundError: if the plugin does not exist.
            DuplicateInstallationError: if the plugin is already installed.
        """
        listing = self._plugins.get(plugin_id)
        if listing is None:
            raise PluginNotFoundError(f"Plugin '{plugin_id}' not found")

        existing = self._installations.find_active(plugin_id, domain_id)
        if existing is not None:
            raise DuplicateInstallationError(
                f"Plugin '{listing.name}' is already installed in domain '{domain_id}'"
            )

        needs_permissions = len(listing.permissions) > 0
        initial_status = (
            PluginInstallationStatus.PENDING_PERMISSIONS
            if needs_permissions
            else PluginInstallationStatus.ACTIVE
        )

        installation = PluginInstallation(
            plugin_id=plugin_id,
            domain_id=domain_id,
            installed_by=user_id,
            status=initial_status,
            version=listing.version,
            config=config or {},
            permissions_granted=[] if needs_permissions else list(listing.permissions),
        )
        self._installations.add(installation)

        listing.downloads += 1
        self._plugins.update(listing)

        perm_request: PermissionRequest | None = None
        if needs_permissions:
            perm_request = PermissionRequest(
                installation_id=installation.id,
                plugin_id=plugin_id,
                domain_id=domain_id,
                permissions=list(listing.permissions),
            )
            self._permissions.add(perm_request)

            await self._tape.log_event(
                event_type=MarketplaceEventType.PERMISSIONS_REQUESTED.value,
                payload={
                    "installation_id": str(installation.id),
                    "plugin_id": str(plugin_id),
                    "domain_id": domain_id,
                    "permissions": [p.value for p in listing.permissions],
                },
                agent_id="marketplace-service",
            )

        await self._tape.log_event(
            event_type=MarketplaceEventType.INSTALLED.value,
            payload={
                "installation_id": str(installation.id),
                "plugin_id": str(plugin_id),
                "domain_id": domain_id,
                "user_id": user_id,
                "status": initial_status.value,
            },
            agent_id="marketplace-service",
        )

        return installation, perm_request

    # ------------------------------------------------------------------
    # Uninstall
    # ------------------------------------------------------------------

    async def uninstall(self, installation_id: UUID, domain_id: str) -> PluginInstallation:
        """Uninstall a plugin from a domain.

        Args:
            installation_id: The installation to remove.
            domain_id: Domain the plugin is installed in.

        Returns:
            The updated PluginInstallation (status=UNINSTALLED).

        Raises:
            InstallationNotFoundError: if the installation does not exist.
        """
        installation = self._installations.get(installation_id)
        if installation is None:
            raise InstallationNotFoundError(
                f"Installation '{installation_id}' not found"
            )

        if installation.domain_id != domain_id:
            raise InstallationNotFoundError(
                f"Installation '{installation_id}' does not belong to domain '{domain_id}'"
            )

        if installation.status == PluginInstallationStatus.UNINSTALLED:
            raise InstallationNotFoundError(
                f"Installation '{installation_id}' is already uninstalled"
            )

        installation = installation.model_copy(
            update={
                "status": PluginInstallationStatus.UNINSTALLED,
                "updated_at": datetime.now(UTC),
            }
        )
        self._installations.update(installation)

        listing = self._plugins.get(installation.plugin_id)
        if listing is not None and listing.downloads > 0:
            listing.downloads -= 1
            self._plugins.update(listing)

        await self._tape.log_event(
            event_type=MarketplaceEventType.UNINSTALLED.value,
            payload={
                "installation_id": str(installation_id),
                "plugin_id": str(installation.plugin_id),
                "domain_id": domain_id,
            },
            agent_id="marketplace-service",
        )

        return installation

    # ------------------------------------------------------------------
    # Rating
    # ------------------------------------------------------------------

    async def rate(
        self,
        plugin_id: UUID,
        user_id: str,
        score: int,
        review: str = "",
    ) -> PluginRating:
        """Rate a plugin.

        Args:
            plugin_id: The plugin to rate.
            user_id: User submitting the rating.
            score: Rating score (1-5).
            review: Optional review text.

        Returns:
            The newly created PluginRating.

        Raises:
            PluginNotFoundError: if the plugin does not exist.
            RatingValidationError: if score is out of range.
            AlreadyRatedError: if the user already rated this plugin.
            SelfRatingError: if the plugin author tries to rate their own plugin.
        """
        listing = self._plugins.get(plugin_id)
        if listing is None:
            raise PluginNotFoundError(f"Plugin '{plugin_id}' not found")

        if score < 1 or score > 5:
            raise RatingValidationError("Rating score must be between 1 and 5")

        if listing.author == user_id:
            raise SelfRatingError("Plugin authors cannot rate their own plugins")

        existing = self._ratings.find_by_user_and_plugin(user_id, plugin_id)
        if existing is not None:
            raise AlreadyRatedError(
                f"User '{user_id}' already rated plugin '{plugin_id}'"
            )

        rating = PluginRating(
            plugin_id=plugin_id,
            user_id=user_id,
            score=score,
            review=review,
        )
        self._ratings.add(rating)

        plugin_ratings = self._ratings.list_for_plugin(plugin_id)
        total_score = sum(r.score for r in plugin_ratings)
        listing.rating_count = len(plugin_ratings)
        listing.average_rating = round(total_score / listing.rating_count, 2)
        self._plugins.update(listing)

        await self._tape.log_event(
            event_type=MarketplaceEventType.RATED.value,
            payload={
                "rating_id": str(rating.id),
                "plugin_id": str(plugin_id),
                "user_id": user_id,
                "score": score,
                "new_average": listing.average_rating,
            },
            agent_id="marketplace-service",
        )

        return rating

    # ------------------------------------------------------------------
    # Permission flow
    # ------------------------------------------------------------------

    async def approve_permissions(
        self,
        request_id: UUID,
        approver_id: str,
        approved_permissions: list[PluginPermissionLevel] | None = None,
    ) -> tuple[PermissionRequest, PluginInstallation]:
        """Approve a pending permission request.

        Args:
            request_id: The permission request ID.
            approver_id: User approving the permissions.
            approved_permissions: Permissions to grant. If None, all requested
                permissions are approved. Must be a subset of requested permissions.

        Returns:
            Tuple of (updated PermissionRequest, updated PluginInstallation).

        Raises:
            PermissionRequestNotFoundError: if the request does not exist.
            InsufficientPermissionLevelError: if approved permissions exceed requested.
        """
        request = self._permissions.get(request_id)
        if request is None:
            raise PermissionRequestNotFoundError(
                f"Permission request '{request_id}' not found"
            )

        if request.status != PermissionRequestStatus.PENDING:
            raise PermissionRequestNotFoundError(
                f"Permission request '{request_id}' is not pending"
            )

        if approved_permissions is None:
            approved_permissions = list(request.permissions)
        else:
            requested_set = set(request.permissions)
            approved_set = set(approved_permissions)
            extra = approved_set - requested_set
            if extra:
                raise InsufficientPermissionLevelError(
                    f"Cannot approve permissions not requested: "
                    f"{[p.value for p in extra]}"
                )

        request = request.model_copy(
            update={
                "status": PermissionRequestStatus.APPROVED,
                "resolved_at": datetime.now(UTC),
                "resolved_by": approver_id,
            }
        )
        self._permissions.update(request)

        installation = self._installations.get(request.installation_id)
        if installation is not None:
            installation = installation.model_copy(
                update={
                    "status": PluginInstallationStatus.ACTIVE,
                    "permissions_granted": list(approved_permissions),
                    "updated_at": datetime.now(UTC),
                }
            )
            self._installations.update(installation)

        await self._tape.log_event(
            event_type=MarketplaceEventType.PERMISSIONS_APPROVED.value,
            payload={
                "request_id": str(request_id),
                "installation_id": str(request.installation_id),
                "plugin_id": str(request.plugin_id),
                "domain_id": request.domain_id,
                "approved_permissions": [p.value for p in approved_permissions],
                "approver_id": approver_id,
            },
            agent_id="marketplace-service",
        )

        return request, installation  # type: ignore[return-value]

    async def reject_permissions(
        self,
        request_id: UUID,
        rejector_id: str,
        reason: str = "",
    ) -> tuple[PermissionRequest, PluginInstallation]:
        """Reject a pending permission request.

        The associated installation is moved to DISABLED status.

        Args:
            request_id: The permission request ID.
            rejector_id: User rejecting the permissions.
            reason: Optional rejection reason.

        Returns:
            Tuple of (updated PermissionRequest, updated PluginInstallation).

        Raises:
            PermissionRequestNotFoundError: if the request does not exist.
        """
        request = self._permissions.get(request_id)
        if request is None:
            raise PermissionRequestNotFoundError(
                f"Permission request '{request_id}' not found"
            )

        if request.status != PermissionRequestStatus.PENDING:
            raise PermissionRequestNotFoundError(
                f"Permission request '{request_id}' is not pending"
            )

        request = request.model_copy(
            update={
                "status": PermissionRequestStatus.REJECTED,
                "resolved_at": datetime.now(UTC),
                "resolved_by": rejector_id,
            }
        )
        self._permissions.update(request)

        installation = self._installations.get(request.installation_id)
        if installation is not None:
            installation = installation.model_copy(
                update={
                    "status": PluginInstallationStatus.DISABLED,
                    "updated_at": datetime.now(UTC),
                }
            )
            self._installations.update(installation)

        await self._tape.log_event(
            event_type=MarketplaceEventType.PERMISSIONS_REJECTED.value,
            payload={
                "request_id": str(request_id),
                "installation_id": str(request.installation_id),
                "plugin_id": str(request.plugin_id),
                "domain_id": request.domain_id,
                "rejector_id": rejector_id,
                "reason": reason,
            },
            agent_id="marketplace-service",
        )

        return request, installation  # type: ignore[return-value]

    async def get_pending_permissions(self, domain_id: str) -> list[PermissionRequest]:
        """List all pending permission requests for a domain.

        Args:
            domain_id: The domain to check.

        Returns:
            List of pending PermissionRequests.
        """
        return self._permissions.list_for_domain(domain_id)

    # ------------------------------------------------------------------
    # Installation queries
    # ------------------------------------------------------------------

    async def get_installation(self, installation_id: UUID) -> PluginInstallation:
        """Get an installation record by ID.

        Raises:
            InstallationNotFoundError: if the installation does not exist.
        """
        installation = self._installations.get(installation_id)
        if installation is None:
            raise InstallationNotFoundError(
                f"Installation '{installation_id}' not found"
            )
        return installation

    async def list_installed(self, domain_id: str) -> list[PluginInstallation]:
        """List all installed (non-uninstalled) plugins for a domain.

        Args:
            domain_id: The domain to query.

        Returns:
            List of PluginInstallations.
        """
        return self._installations.list_for_domain(domain_id)

    # ------------------------------------------------------------------
    # Plugin updates
    # ------------------------------------------------------------------

    async def update_plugin(
        self,
        plugin_id: UUID,
        description: str | None = None,
        version: str | None = None,
        tags: list[str] | None = None,
        homepage_url: str | None = None,
        repository_url: str | None = None,
        icon_url: str | None = None,
        is_featured: bool | None = None,
    ) -> PluginListing:
        """Update an existing plugin listing.

        Args:
            plugin_id: The plugin to update.
            description: New description.
            version: New version.
            tags: New tags.
            homepage_url: New homepage URL.
            repository_url: New repository URL.
            icon_url: New icon URL.
            is_featured: New featured status.

        Returns:
            The updated PluginListing.

        Raises:
            PluginNotFoundError: if the plugin does not exist.
        """
        listing = self._plugins.get(plugin_id)
        if listing is None:
            raise PluginNotFoundError(f"Plugin '{plugin_id}' not found")

        update_data: dict[str, object] = {"updated_at": datetime.now(UTC)}
        if description is not None:
            update_data["description"] = description
        if version is not None:
            update_data["version"] = version
        if tags is not None:
            update_data["tags"] = tags
        if homepage_url is not None:
            update_data["homepage_url"] = homepage_url
        if repository_url is not None:
            update_data["repository_url"] = repository_url
        if icon_url is not None:
            update_data["icon_url"] = icon_url
        if is_featured is not None:
            update_data["is_featured"] = is_featured

        listing = listing.model_copy(update=update_data)
        self._plugins.update(listing)

        await self._tape.log_event(
            event_type=MarketplaceEventType.UPDATED.value,
            payload={
                "plugin_id": str(plugin_id),
                "updated_fields": list(update_data.keys()),
            },
            agent_id="marketplace-service",
        )

        return listing

    async def unpublish_plugin(self, plugin_id: UUID) -> PluginListing:
        """Remove a plugin from the marketplace.

        Args:
            plugin_id: The plugin to remove.

        Returns:
            The removed PluginListing.

        Raises:
            PluginNotFoundError: if the plugin does not exist.
        """
        listing = self._plugins.remove(plugin_id)
        if listing is None:
            raise PluginNotFoundError(f"Plugin '{plugin_id}' not found")

        await self._tape.log_event(
            event_type=MarketplaceEventType.UNPUBLISHED.value,
            payload={
                "plugin_id": str(plugin_id),
                "name": listing.name,
                "author": listing.author,
            },
            agent_id="marketplace-service",
        )

        return listing

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sort_listings(
        listings: list[PluginListing],
        sort: PluginSortOrder,
    ) -> list[PluginListing]:
        """Sort plugin listings by the specified order."""
        match sort:
            case PluginSortOrder.NEWEST:
                return sorted(listings, key=lambda p: p.published_at, reverse=True)
            case PluginSortOrder.POPULAR:
                return sorted(listings, key=lambda p: p.downloads, reverse=True)
            case PluginSortOrder.HIGHEST_RATED:
                return sorted(listings, key=lambda p: p.average_rating, reverse=True)
            case PluginSortOrder.MOST_INSTALLED:
                return sorted(listings, key=lambda p: p.downloads, reverse=True)
            case PluginSortOrder.NAME_ASC:
                return sorted(listings, key=lambda p: p.display_name.lower())

    @property
    def plugin_store(self) -> PublishedPluginStore:
        """Access the underlying plugin store (for testing)."""
        return self._plugins

    @property
    def installation_store(self) -> InstallationStore:
        """Access the underlying installation store (for testing)."""
        return self._installations

    @property
    def rating_store(self) -> RatingStore:
        """Access the underlying rating store (for testing)."""
        return self._ratings

    @property
    def permission_store(self) -> PermissionRequestStore:
        """Access the underlying permission store (for testing)."""
        return self._permissions
