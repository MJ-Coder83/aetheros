"""Unit tests for the Plugin Marketplace service.

Run with: pytest tests/test_marketplace.py -v
"""

from uuid import UUID

import pytest

from packages.marketplace.service import (
    AlreadyRatedError,
    DuplicateInstallationError,
    DuplicateListingError,
    InstallationNotFoundError,
    InsufficientPermissionLevelError,
    MarketplaceService,
    PermissionRequestNotFoundError,
    PermissionRequestStatus,
    PluginCategory,
    PluginInstallationStatus,
    PluginListing,
    PluginNotFoundError,
    PluginPermissionLevel,
    PluginSortOrder,
    RatingValidationError,
    SelfRatingError,
)
from packages.tape.repository import InMemoryTapeRepository
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tape_svc() -> TapeService:
    repo = InMemoryTapeRepository()
    return TapeService(repo)


@pytest.fixture()
def svc(tape_svc: TapeService) -> MarketplaceService:
    return MarketplaceService(tape_service=tape_svc)


async def _publish_sample(
    svc: MarketplaceService,
    name: str = "analytics-pro",
    display_name: str = "Analytics Pro",
    author: str = "inkosai",
    category: PluginCategory = PluginCategory.ANALYTICS,
    permissions: list[PluginPermissionLevel] | None = None,
    tags: list[str] | None = None,
) -> PluginListing:
    return await svc.publish_plugin(
        name=name,
        display_name=display_name,
        description=f"{display_name} — a powerful plugin",
        version="1.0.0",
        author=author,
        category=category,
        tags=tags or ["data", "analytics"],
        permissions=permissions or [],
    )


# ---------------------------------------------------------------------------
# publish_plugin
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_plugin_returns_listing(svc: MarketplaceService) -> None:
    listing = await _publish_sample(svc)
    assert isinstance(listing.id, UUID)
    assert listing.name == "analytics-pro"
    assert listing.display_name == "Analytics Pro"
    assert listing.version == "1.0.0"
    assert listing.author == "inkosai"
    assert listing.category == PluginCategory.ANALYTICS
    assert listing.tags == ["data", "analytics"]
    assert listing.downloads == 0
    assert listing.average_rating == 0.0


@pytest.mark.asyncio
async def test_publish_plugin_duplicate_raises(svc: MarketplaceService) -> None:
    await _publish_sample(svc)
    with pytest.raises(DuplicateListingError):
        await _publish_sample(svc)


@pytest.mark.asyncio
async def test_publish_plugin_empty_name_raises(svc: MarketplaceService) -> None:
    with pytest.raises(ValueError, match="name"):
        await svc.publish_plugin(
            name="",
            display_name="Test",
            description="desc",
            version="1.0.0",
            author="author",
            category=PluginCategory.UTILITY,
        )


@pytest.mark.asyncio
async def test_publish_plugin_empty_version_raises(svc: MarketplaceService) -> None:
    with pytest.raises(ValueError, match="Version"):
        await svc.publish_plugin(
            name="test",
            display_name="Test",
            description="desc",
            version="",
            author="author",
            category=PluginCategory.UTILITY,
        )


@pytest.mark.asyncio
async def test_publish_plugin_empty_author_raises(svc: MarketplaceService) -> None:
    with pytest.raises(ValueError, match="Author"):
        await svc.publish_plugin(
            name="test",
            display_name="Test",
            description="desc",
            version="1.0.0",
            author="",
            category=PluginCategory.UTILITY,
        )


@pytest.mark.asyncio
async def test_publish_plugin_same_name_different_author(svc: MarketplaceService) -> None:
    listing1 = await _publish_sample(svc, name="my-plugin", author="alice")
    listing2 = await _publish_sample(svc, name="my-plugin", author="bob")
    assert listing1.id != listing2.id


# ---------------------------------------------------------------------------
# discover
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_discover_returns_all(svc: MarketplaceService) -> None:
    await _publish_sample(svc, name="p1", display_name="P1")
    await _publish_sample(svc, name="p2", display_name="P2", category=PluginCategory.SKILL)
    results = await svc.discover()
    assert len(results) == 2


@pytest.mark.asyncio
async def test_discover_filter_by_category(svc: MarketplaceService) -> None:
    await _publish_sample(svc, name="p1", display_name="P1", category=PluginCategory.ANALYTICS)
    await _publish_sample(svc, name="p2", display_name="P2", category=PluginCategory.SKILL)
    results = await svc.discover(category=PluginCategory.ANALYTICS)
    assert len(results) == 1
    assert results[0].category == PluginCategory.ANALYTICS


@pytest.mark.asyncio
async def test_discover_filter_by_tags(svc: MarketplaceService) -> None:
    await _publish_sample(svc, name="p1", display_name="P1", tags=["data", "viz"])
    await _publish_sample(svc, name="p2", display_name="P2", tags=["automation"])
    results = await svc.discover(tags=["viz"])
    assert len(results) == 1
    assert results[0].name == "p1"


@pytest.mark.asyncio
async def test_discover_featured_only(svc: MarketplaceService) -> None:
    await svc.publish_plugin(
        name="feat",
        display_name="Featured",
        description="Featured plugin",
        version="1.0.0",
        author="inkosai",
        category=PluginCategory.UTILITY,
        is_featured=True,
    )
    await _publish_sample(svc, name="normal", display_name="Normal")
    results = await svc.discover(featured_only=True)
    assert len(results) == 1
    assert results[0].is_featured is True


@pytest.mark.asyncio
async def test_discover_pagination(svc: MarketplaceService) -> None:
    for i in range(5):
        await _publish_sample(svc, name=f"p{i}", display_name=f"P{i}")
    page1 = await svc.discover(limit=2, offset=0)
    page2 = await svc.discover(limit=2, offset=2)
    assert len(page1) == 2
    assert len(page2) == 2
    assert page1[0].id != page2[0].id


@pytest.mark.asyncio
async def test_discover_sort_by_name(svc: MarketplaceService) -> None:
    await _publish_sample(svc, name="z-plugin", display_name="Z Plugin")
    await _publish_sample(svc, name="a-plugin", display_name="A Plugin")
    results = await svc.discover(sort=PluginSortOrder.NAME_ASC)
    assert results[0].display_name == "A Plugin"


@pytest.mark.asyncio
async def test_discover_sort_by_popular(svc: MarketplaceService) -> None:
    popular = await _publish_sample(svc, name="popular", display_name="Popular")
    await _publish_sample(svc, name="unpopular", display_name="Unpopular")

    popular.downloads = 100
    svc.plugin_store.update(popular)

    results = await svc.discover(sort=PluginSortOrder.POPULAR)
    assert results[0].name == "popular"


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_by_name(svc: MarketplaceService) -> None:
    await _publish_sample(svc, name="analytics-pro", display_name="Analytics Pro", tags=["data"])
    await _publish_sample(svc, name="workflow-engine", display_name="Workflow Engine", tags=["automation"])
    results = await svc.search("analytics-pro")
    assert len(results) == 1
    assert results[0].name == "analytics-pro"


@pytest.mark.asyncio
async def test_search_by_description(svc: MarketplaceService) -> None:
    await svc.publish_plugin(
        name="data-viz",
        display_name="Data Visualization",
        description="Powerful data visualization tool for charts",
        version="1.0.0",
        author="inkosai",
        category=PluginCategory.ANALYTICS,
    )
    await _publish_sample(svc, name="other", display_name="Other")
    results = await svc.search("charts")
    assert len(results) == 1
    assert results[0].name == "data-viz"


@pytest.mark.asyncio
async def test_search_by_author(svc: MarketplaceService) -> None:
    await _publish_sample(svc, name="p1", display_name="P1", author="alice")
    await _publish_sample(svc, name="p2", display_name="P2", author="bob")
    results = await svc.search("alice")
    assert len(results) == 1
    assert results[0].author == "alice"


@pytest.mark.asyncio
async def test_search_by_tag(svc: MarketplaceService) -> None:
    await _publish_sample(svc, name="p1", display_name="P1", tags=["visualization"])
    await _publish_sample(svc, name="p2", display_name="P2", tags=["automation"])
    results = await svc.search("visualization")
    assert len(results) == 1
    assert results[0].name == "p1"


@pytest.mark.asyncio
async def test_search_no_results(svc: MarketplaceService) -> None:
    await _publish_sample(svc)
    results = await svc.search("nonexistent-xyz")
    assert len(results) == 0


@pytest.mark.asyncio
async def test_search_with_category_filter(svc: MarketplaceService) -> None:
    await _publish_sample(svc, name="p1", display_name="P1", category=PluginCategory.ANALYTICS)
    await _publish_sample(svc, name="p2", display_name="P2", category=PluginCategory.SKILL)
    results = await svc.search("p", category=PluginCategory.ANALYTICS)
    assert len(results) == 1
    assert results[0].category == PluginCategory.ANALYTICS


@pytest.mark.asyncio
async def test_search_case_insensitive(svc: MarketplaceService) -> None:
    await _publish_sample(svc, name="MyPlugin", display_name="My Plugin")
    results = await svc.search("myplugin")
    assert len(results) == 1


@pytest.mark.asyncio
async def test_search_pagination(svc: MarketplaceService) -> None:
    for i in range(5):
        await _publish_sample(svc, name=f"search-p{i}", display_name=f"Search P{i}")
    page1 = await svc.search("search", limit=2, offset=0)
    page2 = await svc.search("search", limit=2, offset=2)
    assert len(page1) == 2
    assert len(page2) == 2


# ---------------------------------------------------------------------------
# get_plugin
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_plugin_found(svc: MarketplaceService) -> None:
    listing = await _publish_sample(svc)
    fetched = await svc.get_plugin(listing.id)
    assert fetched.id == listing.id
    assert fetched.name == listing.name


@pytest.mark.asyncio
async def test_get_plugin_not_found(svc: MarketplaceService) -> None:
    with pytest.raises(PluginNotFoundError):
        await svc.get_plugin(UUID("00000000-0000-0000-0000-000000000000"))


# ---------------------------------------------------------------------------
# install
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_install_no_permissions(svc: MarketplaceService) -> None:
    listing = await _publish_sample(svc)
    installation, perm_request = await svc.install(
        plugin_id=listing.id,
        domain_id="domain-1",
        user_id="user-1",
    )
    assert installation.plugin_id == listing.id
    assert installation.domain_id == "domain-1"
    assert installation.status == PluginInstallationStatus.ACTIVE
    assert installation.installed_by == "user-1"
    assert perm_request is None


@pytest.mark.asyncio
async def test_install_with_permissions_creates_request(svc: MarketplaceService) -> None:
    listing = await _publish_sample(
        svc,
        name="secure-plugin",
        display_name="Secure Plugin",
        permissions=[PluginPermissionLevel.READ, PluginPermissionLevel.NETWORK],
    )
    installation, perm_request = await svc.install(
        plugin_id=listing.id,
        domain_id="domain-1",
        user_id="user-1",
    )
    assert installation.status == PluginInstallationStatus.PENDING_PERMISSIONS
    assert perm_request is not None
    assert perm_request.plugin_id == listing.id
    assert perm_request.permissions == [PluginPermissionLevel.READ, PluginPermissionLevel.NETWORK]
    assert perm_request.status == PermissionRequestStatus.PENDING


@pytest.mark.asyncio
async def test_install_duplicate_raises(svc: MarketplaceService) -> None:
    listing = await _publish_sample(svc)
    await svc.install(plugin_id=listing.id, domain_id="domain-1", user_id="user-1")
    with pytest.raises(DuplicateInstallationError):
        await svc.install(plugin_id=listing.id, domain_id="domain-1", user_id="user-2")


@pytest.mark.asyncio
async def test_install_nonexistent_plugin_raises(svc: MarketplaceService) -> None:
    with pytest.raises(PluginNotFoundError):
        await svc.install(
            plugin_id=UUID("00000000-0000-0000-0000-000000000000"),
            domain_id="domain-1",
            user_id="user-1",
        )


@pytest.mark.asyncio
async def test_install_increments_downloads(svc: MarketplaceService) -> None:
    listing = await _publish_sample(svc)
    assert listing.downloads == 0
    await svc.install(plugin_id=listing.id, domain_id="domain-1", user_id="user-1")
    updated = await svc.get_plugin(listing.id)
    assert updated.downloads == 1


@pytest.mark.asyncio
async def test_install_same_plugin_different_domains(svc: MarketplaceService) -> None:
    listing = await _publish_sample(svc)
    inst1, _ = await svc.install(plugin_id=listing.id, domain_id="domain-1", user_id="user-1")
    inst2, _ = await svc.install(plugin_id=listing.id, domain_id="domain-2", user_id="user-1")
    assert inst1.id != inst2.id
    assert inst1.domain_id != inst2.domain_id


# ---------------------------------------------------------------------------
# uninstall
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_uninstall(svc: MarketplaceService) -> None:
    listing = await _publish_sample(svc)
    installation, _ = await svc.install(plugin_id=listing.id, domain_id="domain-1", user_id="user-1")
    result = await svc.uninstall(installation.id, "domain-1")
    assert result.status == PluginInstallationStatus.UNINSTALLED


@pytest.mark.asyncio
async def test_uninstall_decrements_downloads(svc: MarketplaceService) -> None:
    listing = await _publish_sample(svc)
    installation, _ = await svc.install(plugin_id=listing.id, domain_id="domain-1", user_id="user-1")
    await svc.uninstall(installation.id, "domain-1")
    updated = await svc.get_plugin(listing.id)
    assert updated.downloads == 0


@pytest.mark.asyncio
async def test_uninstall_wrong_domain_raises(svc: MarketplaceService) -> None:
    listing = await _publish_sample(svc)
    installation, _ = await svc.install(plugin_id=listing.id, domain_id="domain-1", user_id="user-1")
    with pytest.raises(InstallationNotFoundError):
        await svc.uninstall(installation.id, "domain-2")


@pytest.mark.asyncio
async def test_uninstall_already_uninstalled_raises(svc: MarketplaceService) -> None:
    listing = await _publish_sample(svc)
    installation, _ = await svc.install(plugin_id=listing.id, domain_id="domain-1", user_id="user-1")
    await svc.uninstall(installation.id, "domain-1")
    with pytest.raises(InstallationNotFoundError):
        await svc.uninstall(installation.id, "domain-1")


@pytest.mark.asyncio
async def test_uninstall_not_found_raises(svc: MarketplaceService) -> None:
    with pytest.raises(InstallationNotFoundError):
        await svc.uninstall(UUID("00000000-0000-0000-0000-000000000000"), "domain-1")


# ---------------------------------------------------------------------------
# rate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rate_plugin(svc: MarketplaceService) -> None:
    listing = await _publish_sample(svc, author="alice")
    rating = await svc.rate(plugin_id=listing.id, user_id="bob", score=4, review="Great plugin")
    assert rating.score == 4
    assert rating.review == "Great plugin"
    assert rating.user_id == "bob"


@pytest.mark.asyncio
async def test_rate_updates_average(svc: MarketplaceService) -> None:
    listing = await _publish_sample(svc, author="alice")
    await svc.rate(plugin_id=listing.id, user_id="bob", score=5)
    await svc.rate(plugin_id=listing.id, user_id="carol", score=3)
    updated = await svc.get_plugin(listing.id)
    assert updated.rating_count == 2
    assert updated.average_rating == 4.0


@pytest.mark.asyncio
async def test_rate_out_of_range_raises(svc: MarketplaceService) -> None:
    listing = await _publish_sample(svc, author="alice")
    with pytest.raises(RatingValidationError):
        await svc.rate(plugin_id=listing.id, user_id="bob", score=0)
    with pytest.raises(RatingValidationError):
        await svc.rate(plugin_id=listing.id, user_id="bob", score=6)


@pytest.mark.asyncio
async def test_rate_duplicate_raises(svc: MarketplaceService) -> None:
    listing = await _publish_sample(svc, author="alice")
    await svc.rate(plugin_id=listing.id, user_id="bob", score=4)
    with pytest.raises(AlreadyRatedError):
        await svc.rate(plugin_id=listing.id, user_id="bob", score=3)


@pytest.mark.asyncio
async def test_rate_self_rating_raises(svc: MarketplaceService) -> None:
    listing = await _publish_sample(svc, author="alice")
    with pytest.raises(SelfRatingError):
        await svc.rate(plugin_id=listing.id, user_id="alice", score=5)


@pytest.mark.asyncio
async def test_rate_nonexistent_plugin_raises(svc: MarketplaceService) -> None:
    with pytest.raises(PluginNotFoundError):
        await svc.rate(
            plugin_id=UUID("00000000-0000-0000-0000-000000000000"),
            user_id="bob",
            score=4,
        )


# ---------------------------------------------------------------------------
# Permission flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approve_permissions_full(svc: MarketplaceService) -> None:
    listing = await _publish_sample(
        svc,
        name="perm-plugin",
        display_name="Perm Plugin",
        permissions=[PluginPermissionLevel.READ, PluginPermissionLevel.EXECUTE],
    )
    installation, perm_request = await svc.install(
        plugin_id=listing.id, domain_id="domain-1", user_id="user-1",
    )
    assert perm_request is not None
    assert installation.status == PluginInstallationStatus.PENDING_PERMISSIONS

    updated_request, updated_installation = await svc.approve_permissions(
        request_id=perm_request.id,
        approver_id="admin-1",
    )
    assert updated_request.status == PermissionRequestStatus.APPROVED
    assert updated_request.resolved_by == "admin-1"
    assert updated_installation.status == PluginInstallationStatus.ACTIVE
    assert PluginPermissionLevel.READ in updated_installation.permissions_granted
    assert PluginPermissionLevel.EXECUTE in updated_installation.permissions_granted


@pytest.mark.asyncio
async def test_approve_permissions_partial(svc: MarketplaceService) -> None:
    listing = await _publish_sample(
        svc,
        name="partial-perm",
        display_name="Partial Perm Plugin",
        permissions=[PluginPermissionLevel.READ, PluginPermissionLevel.EXECUTE, PluginPermissionLevel.NETWORK],
    )
    _, perm_request = await svc.install(
        plugin_id=listing.id, domain_id="domain-1", user_id="user-1",
    )
    assert perm_request is not None

    updated_request, updated_installation = await svc.approve_permissions(
        request_id=perm_request.id,
        approver_id="admin-1",
        approved_permissions=[PluginPermissionLevel.READ],
    )
    assert updated_request.status == PermissionRequestStatus.APPROVED
    assert updated_installation.status == PluginInstallationStatus.ACTIVE
    assert updated_installation.permissions_granted == [PluginPermissionLevel.READ]


@pytest.mark.asyncio
async def test_approve_permissions_extra_raises(svc: MarketplaceService) -> None:
    listing = await _publish_sample(
        svc,
        name="extra-perm",
        display_name="Extra Perm Plugin",
        permissions=[PluginPermissionLevel.READ],
    )
    _, perm_request = await svc.install(
        plugin_id=listing.id, domain_id="domain-1", user_id="user-1",
    )
    assert perm_request is not None

    with pytest.raises(InsufficientPermissionLevelError):
        await svc.approve_permissions(
            request_id=perm_request.id,
            approver_id="admin-1",
            approved_permissions=[PluginPermissionLevel.READ, PluginPermissionLevel.ADMIN],
        )


@pytest.mark.asyncio
async def test_reject_permissions(svc: MarketplaceService) -> None:
    listing = await _publish_sample(
        svc,
        name="reject-perm",
        display_name="Reject Perm Plugin",
        permissions=[PluginPermissionLevel.ADMIN],
    )
    _, perm_request = await svc.install(
        plugin_id=listing.id, domain_id="domain-1", user_id="user-1",
    )
    assert perm_request is not None

    updated_request, updated_installation = await svc.reject_permissions(
        request_id=perm_request.id,
        rejector_id="admin-1",
        reason="Admin permission not allowed",
    )
    assert updated_request.status == PermissionRequestStatus.REJECTED
    assert updated_request.resolved_by == "admin-1"
    assert updated_installation.status == PluginInstallationStatus.DISABLED


@pytest.mark.asyncio
async def test_approve_non_pending_raises(svc: MarketplaceService) -> None:
    listing = await _publish_sample(
        svc,
        name="double-approve",
        display_name="Double Approve",
        permissions=[PluginPermissionLevel.READ],
    )
    _, perm_request = await svc.install(
        plugin_id=listing.id, domain_id="domain-1", user_id="user-1",
    )
    assert perm_request is not None
    await svc.approve_permissions(request_id=perm_request.id, approver_id="admin-1")

    with pytest.raises(PermissionRequestNotFoundError):
        await svc.approve_permissions(request_id=perm_request.id, approver_id="admin-1")


@pytest.mark.asyncio
async def test_get_pending_permissions(svc: MarketplaceService) -> None:
    listing = await _publish_sample(
        svc,
        name="pending-perm",
        display_name="Pending Perm",
        permissions=[PluginPermissionLevel.READ],
    )
    await svc.install(plugin_id=listing.id, domain_id="domain-1", user_id="user-1")

    pending = await svc.get_pending_permissions("domain-1")
    assert len(pending) == 1
    assert pending[0].status == PermissionRequestStatus.PENDING


@pytest.mark.asyncio
async def test_get_pending_permissions_empty(svc: MarketplaceService) -> None:
    pending = await svc.get_pending_permissions("domain-1")
    assert len(pending) == 0


# ---------------------------------------------------------------------------
# Installation queries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_installation(svc: MarketplaceService) -> None:
    listing = await _publish_sample(svc)
    installation, _ = await svc.install(plugin_id=listing.id, domain_id="domain-1", user_id="user-1")
    fetched = await svc.get_installation(installation.id)
    assert fetched.id == installation.id


@pytest.mark.asyncio
async def test_get_installation_not_found(svc: MarketplaceService) -> None:
    with pytest.raises(InstallationNotFoundError):
        await svc.get_installation(UUID("00000000-0000-0000-0000-000000000000"))


@pytest.mark.asyncio
async def test_list_installed(svc: MarketplaceService) -> None:
    listing1 = await _publish_sample(svc, name="p1", display_name="P1")
    listing2 = await _publish_sample(svc, name="p2", display_name="P2")
    await svc.install(plugin_id=listing1.id, domain_id="domain-1", user_id="user-1")
    await svc.install(plugin_id=listing2.id, domain_id="domain-1", user_id="user-1")

    installed = await svc.list_installed("domain-1")
    assert len(installed) == 2


@pytest.mark.asyncio
async def test_list_installed_excludes_uninstalled(svc: MarketplaceService) -> None:
    listing = await _publish_sample(svc)
    installation, _ = await svc.install(plugin_id=listing.id, domain_id="domain-1", user_id="user-1")
    await svc.uninstall(installation.id, "domain-1")

    installed = await svc.list_installed("domain-1")
    assert len(installed) == 0


@pytest.mark.asyncio
async def test_list_installed_filters_by_domain(svc: MarketplaceService) -> None:
    listing = await _publish_sample(svc)
    await svc.install(plugin_id=listing.id, domain_id="domain-1", user_id="user-1")
    await svc.install(plugin_id=listing.id, domain_id="domain-2", user_id="user-1")

    installed_1 = await svc.list_installed("domain-1")
    installed_2 = await svc.list_installed("domain-2")
    assert len(installed_1) == 1
    assert len(installed_2) == 1


# ---------------------------------------------------------------------------
# Plugin updates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_plugin(svc: MarketplaceService) -> None:
    listing = await _publish_sample(svc)
    updated = await svc.update_plugin(
        plugin_id=listing.id,
        description="Updated description",
        version="2.0.0",
    )
    assert updated.description == "Updated description"
    assert updated.version == "2.0.0"


@pytest.mark.asyncio
async def test_update_plugin_not_found(svc: MarketplaceService) -> None:
    with pytest.raises(PluginNotFoundError):
        await svc.update_plugin(
            plugin_id=UUID("00000000-0000-0000-0000-000000000000"),
            description="Nope",
        )


@pytest.mark.asyncio
async def test_unpublish_plugin(svc: MarketplaceService) -> None:
    listing = await _publish_sample(svc)
    removed = await svc.unpublish_plugin(listing.id)
    assert removed.name == "analytics-pro"
    with pytest.raises(PluginNotFoundError):
        await svc.get_plugin(listing.id)


@pytest.mark.asyncio
async def test_unpublish_plugin_not_found(svc: MarketplaceService) -> None:
    with pytest.raises(PluginNotFoundError):
        await svc.unpublish_plugin(UUID("00000000-0000-0000-0000-000000000000"))


# ---------------------------------------------------------------------------
# Tape logging
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tape_logs_publish(tape_svc: TapeService, svc: MarketplaceService) -> None:
    await _publish_sample(svc)
    entries = await tape_svc.get_entries(event_type="marketplace.plugin_published")
    assert len(entries) == 1
    assert entries[0].payload["name"] == "analytics-pro"


@pytest.mark.asyncio
async def test_tape_logs_install(tape_svc: TapeService, svc: MarketplaceService) -> None:
    listing = await _publish_sample(svc)
    await svc.install(plugin_id=listing.id, domain_id="domain-1", user_id="user-1")
    entries = await tape_svc.get_entries(event_type="marketplace.plugin_installed")
    assert len(entries) == 1


@pytest.mark.asyncio
async def test_tape_logs_uninstall(tape_svc: TapeService, svc: MarketplaceService) -> None:
    listing = await _publish_sample(svc)
    installation, _ = await svc.install(plugin_id=listing.id, domain_id="domain-1", user_id="user-1")
    await svc.uninstall(installation.id, "domain-1")
    entries = await tape_svc.get_entries(event_type="marketplace.plugin_uninstalled")
    assert len(entries) == 1


@pytest.mark.asyncio
async def test_tape_logs_rating(tape_svc: TapeService, svc: MarketplaceService) -> None:
    listing = await _publish_sample(svc, author="alice")
    await svc.rate(plugin_id=listing.id, user_id="bob", score=5)
    entries = await tape_svc.get_entries(event_type="marketplace.plugin_rated")
    assert len(entries) == 1
    assert entries[0].payload["score"] == 5


@pytest.mark.asyncio
async def test_tape_logs_permission_approval(tape_svc: TapeService, svc: MarketplaceService) -> None:
    listing = await _publish_sample(
        svc,
        name="tape-perm",
        display_name="Tape Perm",
        permissions=[PluginPermissionLevel.READ],
    )
    _, perm_request = await svc.install(
        plugin_id=listing.id, domain_id="domain-1", user_id="user-1",
    )
    assert perm_request is not None
    await svc.approve_permissions(request_id=perm_request.id, approver_id="admin-1")

    entries = await tape_svc.get_entries(event_type="marketplace.permissions_approved")
    assert len(entries) == 1


@pytest.mark.asyncio
async def test_tape_logs_search(tape_svc: TapeService, svc: MarketplaceService) -> None:
    await _publish_sample(svc)
    await svc.search("analytics")
    entries = await tape_svc.get_entries(event_type="marketplace.searched")
    assert len(entries) == 1
    assert entries[0].payload["query"] == "analytics"


@pytest.mark.asyncio
async def test_tape_logs_discover(tape_svc: TapeService, svc: MarketplaceService) -> None:
    await _publish_sample(svc)
    await svc.discover()
    entries = await tape_svc.get_entries(event_type="marketplace.discovered")
    assert len(entries) == 1


# ---------------------------------------------------------------------------
# Full integration flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_marketplace_lifecycle(svc: MarketplaceService) -> None:
    listing = await svc.publish_plugin(
        name="lifecycle-plugin",
        display_name="Lifecycle Plugin",
        description="Test full lifecycle",
        version="1.0.0",
        author="dev-team",
        category=PluginCategory.WORKFLOW,
        tags=["lifecycle", "test"],
        permissions=[PluginPermissionLevel.READ, PluginPermissionLevel.WRITE],
    )

    results = await svc.search("lifecycle")
    assert len(results) == 1

    installation, perm_request = await svc.install(
        plugin_id=listing.id, domain_id="test-domain", user_id="tester",
    )
    assert installation.status == PluginInstallationStatus.PENDING_PERMISSIONS
    assert perm_request is not None

    pending = await svc.get_pending_permissions("test-domain")
    assert len(pending) == 1

    updated_req, updated_inst = await svc.approve_permissions(
        request_id=perm_request.id,
        approver_id="admin",
        approved_permissions=[PluginPermissionLevel.READ],
    )
    assert updated_req.status == PermissionRequestStatus.APPROVED
    assert updated_inst.status == PluginInstallationStatus.ACTIVE

    installed = await svc.list_installed("test-domain")
    assert len(installed) == 1

    rating = await svc.rate(
        plugin_id=listing.id, user_id="rater", score=5, review="Excellent",
    )
    assert rating.score == 5

    updated_listing = await svc.get_plugin(listing.id)
    assert updated_listing.average_rating == 5.0
    assert updated_listing.rating_count == 1
    assert updated_listing.downloads == 1

    uninstalled = await svc.uninstall(installation.id, "test-domain")
    assert uninstalled.status == PluginInstallationStatus.UNINSTALLED

    remaining = await svc.list_installed("test-domain")
    assert len(remaining) == 0
