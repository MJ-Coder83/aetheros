"""Plugin data models for InkosAI.

This module defines the core data structures for the plugin system:

1. PluginManifest — Declarative plugin metadata (id, version, permissions, commands, events)
2. Plugin — Runtime plugin instance with lifecycle state and configuration
3. PluginPermission — Fine-grained permission enumeration (shared with bridge)
4. PluginCommand — A command exposed by a plugin
5. PluginEventSubscription — An event subscription declared in the manifest
6. PluginVersion — Semantic versioning for plugins
7. PluginInstallInfo — Installation metadata (source, timestamp, user)
8. PluginDependency — Dependency on another plugin or system component
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PluginPermission(StrEnum):
    """Fine-grained permissions that a plugin may request.

    These are declared in the manifest and enforced by the sandbox at runtime.
    """

    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    NETWORK = "network"
    FILESYSTEM = "filesystem"
    AGENT_COMM = "agent_comm"
    EVENT_SUBSCRIBE = "event_subscribe"
    EVENT_PUBLISH = "event_publish"
    TAPE_READ = "tape_read"
    TAPE_WRITE = "tape_write"
    PROFILE_READ = "profile_read"
    DOMAIN_READ = "domain_read"
    DOMAIN_WRITE = "domain_write"


class PluginStatus(StrEnum):
    """Lifecycle states for a plugin instance."""

    REGISTERED = "registered"
    LOADED = "loaded"
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"
    UNINSTALLING = "uninstalling"


class PluginType(StrEnum):
    """Types of plugins."""

    AGENT = "agent"
    SKILL = "skill"
    CANVAS = "canvas"
    INTEGRATION = "integration"
    THEME = "theme"
    UTILITY = "utility"


class PluginInstallSource(StrEnum):
    """Where a plugin was installed from."""

    MARKETPLACE = "marketplace"
    LOCAL = "local"
    URL = "url"
    GIT = "git"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class PluginVersion(BaseModel):
    """Semantic version for a plugin.

    Follows semver: MAJOR.MINOR.PATCH with optional pre-release tag.
    """

    major: int = 0
    minor: int = 1
    patch: int = 0
    pre_release: str = ""

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.pre_release:
            base += f"-{self.pre_release}"
        return base

    def __lt__(self, other: PluginVersion) -> bool:
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        if self.patch != other.patch:
            return self.patch < other.patch
        # Pre-release versions are lower than release versions
        if self.pre_release and not other.pre_release:
            return True
        if not self.pre_release and other.pre_release:
            return False
        return self.pre_release < other.pre_release

    def __le__(self, other: PluginVersion) -> bool:
        return self == other or self < other

    def __gt__(self, other: PluginVersion) -> bool:
        return not self <= other

    def __ge__(self, other: PluginVersion) -> bool:
        return not self < other

    @classmethod
    def parse(cls, version_str: str) -> PluginVersion:
        """Parse a semver string like '1.2.3' or '1.2.3-beta'.

        Raises:
            ValueError: if the string is not valid semver.
        """
        pre = ""
        # Only split on '-' for pre-release if it doesn't start with '-'
        # (to handle cases like '-1.0.0' gracefully)
        if "-" in version_str and not version_str.startswith("-"):
            version_str, pre = version_str.split("-", 1)
        parts = version_str.split(".")
        if len(parts) != 3:
            raise ValueError(f"Invalid semver: expected MAJOR.MINOR.PATCH, got '{version_str}'")
        try:
            major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        except ValueError as exc:
            raise ValueError(f"Invalid semver numbers in '{version_str}'") from exc
        if major < 0 or minor < 0 or patch < 0:
            raise ValueError(f"Semver components must be non-negative: '{version_str}'")
        return cls(major=major, minor=minor, patch=patch, pre_release=pre)


class PluginCommand(BaseModel):
    """A command exposed by a plugin.

    Commands are the primary interface that a plugin provides to the host
    system and other plugins. Each command has a name, description, and
    an optional parameter schema.
    """

    name: str
    description: str = ""
    parameters: dict[str, Any] = {}
    requires: set[PluginPermission] = {PluginPermission.EXECUTE}
    timeout_ms: int = 30_000


class PluginEventSubscription(BaseModel):
    """An event subscription declared in the plugin manifest."""

    event_type: str
    description: str = ""


class PluginDependency(BaseModel):
    """A dependency on another plugin or system component."""

    plugin_id: str
    min_version: PluginVersion = PluginVersion(major=0, minor=1, patch=0)
    optional: bool = False


class PluginManifest(BaseModel):
    """Declarative plugin metadata.

    The manifest is the single source of truth for what a plugin is,
    what it requires, and what it provides. It is used for:
    - Registration with the PluginSDK
    - Permission review during installation
    - Dependency resolution before loading
    - Discovery and search in the Marketplace

    Example::

        manifest = PluginManifest(
            id="weather-plugin",
            name="Weather Integration",
            version=PluginVersion(major=1, minor=0, patch=0),
            plugin_type=PluginType.INTEGRATION,
            description="Provides weather data to agents and canvases",
            author="InkosAI Community",
            permissions={PluginPermission.READ, PluginPermission.NETWORK},
            commands=[
                PluginCommand(name="query_weather", description="Get weather for a city"),
            ],
            event_subscriptions=[
                PluginEventSubscription(event_type="location.updated"),
            ],
        )
    """

    id: str
    name: str
    version: PluginVersion = PluginVersion(major=0, minor=1, patch=0)
    plugin_type: PluginType = PluginType.UTILITY
    description: str = ""
    author: str = ""
    homepage_url: str = ""
    repository_url: str = ""
    license: str = "MIT"
    permissions: set[PluginPermission] = {PluginPermission.READ}
    commands: list[PluginCommand] = []
    event_subscriptions: list[PluginEventSubscription] = []
    events_published: list[str] = []
    dependencies: list[PluginDependency] = []
    tags: list[str] = []
    config_schema: dict[str, Any] = {}
    min_platform_version: PluginVersion | None = None
    max_platform_version: PluginVersion | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def version_str(self) -> str:
        return str(self.version)

    def requires_permission(self, perm: PluginPermission) -> bool:
        """Check if the manifest requests a specific permission."""
        return perm in self.permissions

    def has_command(self, command_name: str) -> bool:
        """Check if the manifest declares a specific command."""
        return any(c.name == command_name for c in self.commands)

    def get_command(self, command_name: str) -> PluginCommand | None:
        """Get a command by name, or None if not found."""
        for cmd in self.commands:
            if cmd.name == command_name:
                return cmd
        return None


class PluginInstallInfo(BaseModel):
    """Installation metadata for a plugin instance."""

    source: PluginInstallSource = PluginInstallSource.LOCAL
    installed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    installed_by: str = ""
    source_url: str = ""
    auto_update: bool = False


class Plugin(BaseModel):
    """Runtime plugin instance.

    A Plugin is the full runtime representation — it wraps a manifest with
    lifecycle state, installation info, configuration, and statistics.
    Plugins are managed by the PluginSDK.
    """

    id: UUID = Field(default_factory=uuid4)
    manifest: PluginManifest
    status: PluginStatus = PluginStatus.REGISTERED
    install_info: PluginInstallInfo = Field(default_factory=PluginInstallInfo)
    config: dict[str, Any] = {}
    error_message: str = ""
    loaded_at: datetime | None = None
    last_command_at: datetime | None = None
    total_commands_executed: int = 0
    folder_tree_path: str = ""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def plugin_id(self) -> str:
        """Convenient access to the manifest id."""
        return self.manifest.id

    @property
    def name(self) -> str:
        return self.manifest.name

    @property
    def version(self) -> PluginVersion:
        return self.manifest.version

    @property
    def is_active(self) -> bool:
        return self.status == PluginStatus.ACTIVE

    @property
    def is_error(self) -> bool:
        return self.status == PluginStatus.ERROR

    def can_execute(self) -> bool:
        """Check if the plugin is in a state that allows command execution."""
        return self.status in {PluginStatus.ACTIVE, PluginStatus.LOADED}

    def record_command(self) -> None:
        """Record that a command was executed on this plugin."""
        self.total_commands_executed += 1
        self.last_command_at = datetime.now(UTC)

    def to_summary(self) -> dict[str, Any]:
        """Produce a lightweight summary for listing and search."""
        return {
            "id": str(self.id),
            "plugin_id": self.manifest.id,
            "name": self.manifest.name,
            "version": str(self.manifest.version),
            "type": self.manifest.plugin_type.value,
            "status": self.status.value,
            "description": self.manifest.description,
            "author": self.manifest.author,
            "tags": self.manifest.tags,
            "total_commands_executed": self.total_commands_executed,
        }
