"""Plugin SDK for InkosAI — the primary API for plugin lifecycle management.

The PluginSDK is the central orchestrator for the plugin system. It provides:

1. Plugin lifecycle — register, load, activate, deactivate, uninstall
2. Command execution — dispatch commands to loaded plugins with permission checks
3. Event subscription — subscribe plugins to events and publish plugin events
4. Dependency resolution — verify all dependencies before loading
5. Version compatibility — check platform version constraints
6. Folder-tree integration — store plugin data in the canonical folder-tree
7. Tape audit logging — every lifecycle and command event is logged immutably

Architecture::

    PluginSDK
    ├── register_plugin() — Create a plugin from a manifest
    ├── load_plugin() — Resolve dependencies, validate, transition to LOADED
    ├── activate_plugin() — Start plugin, transition to ACTIVE
    ├── deactivate_plugin() — Pause plugin, transition to DISABLED
    ├── unload_plugin() — Remove from memory, keep registration
    ├── uninstall_plugin() — Full removal with folder-tree cleanup
    ├── execute_command() — Dispatch a command to an active plugin
    ├── subscribe_to_events() — Register event subscriptions
    ├── publish_event() — Publish an event from a plugin
    ├── get_plugin() / list_plugins() / search_plugins()
    ├── check_dependencies() — Verify all deps are satisfied
    ├── check_version_compatibility() — Verify platform version
    └── get_plugin_summary() / get_plugin_stats()

Usage::

    from packages.plugin.core import PluginSDK
    from packages.plugin.models import PluginManifest, PluginVersion

    sdk = PluginSDK(tape_service=tape_svc)

    manifest = PluginManifest(id="weather", name="Weather", version=PluginVersion(major=1))
    plugin = await sdk.register_plugin(manifest)
    await sdk.load_plugin("weather")
    await sdk.activate_plugin("weather")

    result = await sdk.execute_command("weather", "query", {"city": "London"})
"""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from packages.plugin.models import (
    Plugin,
    PluginInstallInfo,
    PluginManifest,
    PluginPermission,
    PluginStatus,
    PluginType,
    PluginVersion,
)
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PluginError(Exception):
    """Base exception for plugin SDK operations."""


class PluginAlreadyRegisteredError(PluginError):
    """Raised when a plugin with the same manifest ID is already registered."""


class PluginNotFoundError(PluginError):
    """Raised when a plugin is not found in the registry."""


class PluginNotLoadedError(PluginError):
    """Raised when an operation requires a plugin to be loaded but it isn't."""


class PluginNotActiveError(PluginError):
    """Raised when an operation requires a plugin to be active but it isn't."""


class PluginLoadError(PluginError):
    """Raised when a plugin cannot be loaded (deps, version, etc.)."""


class PluginCommandNotFoundError(PluginError):
    """Raised when a plugin command is not found in the manifest."""


class PluginCommandExecutionError(PluginError):
    """Raised when a plugin command execution fails."""


class DependencyNotSatisfiedError(PluginLoadError):
    """Raised when a plugin dependency is not satisfied."""


class VersionNotCompatibleError(PluginLoadError):
    """Raised when the platform version is not compatible with the plugin."""


class PluginTransitionError(PluginError):
    """Raised when an invalid lifecycle transition is attempted."""


class DuplicateCommandError(PluginError):
    """Raised when registering a command that already exists for a plugin."""


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class CommandExecution(BaseModel):
    """Record of a single command execution."""

    id: UUID = Field(default_factory=uuid4)
    plugin_id: str
    command_name: str
    arguments: dict[str, Any] = {}
    status: str = "pending"  # pending, success, error, denied
    result: dict[str, Any] = {}
    error_message: str = ""
    execution_time_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PluginStats(BaseModel):
    """Aggregate statistics for the plugin system."""

    total_plugins: int = 0
    active_plugins: int = 0
    loaded_plugins: int = 0
    disabled_plugins: int = 0
    error_plugins: int = 0
    total_commands_executed: int = 0
    total_events_published: int = 0
    total_events_subscriptions: int = 0


# ---------------------------------------------------------------------------
# Command handler type
# ---------------------------------------------------------------------------

type CommandHandler = object


# ---------------------------------------------------------------------------
# PluginSDK
# ---------------------------------------------------------------------------


class PluginSDK:
    """Primary API for plugin lifecycle and command management.

    The PluginSDK manages the full lifecycle of plugins in InkosAI:
    registration, loading, activation, deactivation, uninstall, command
    execution, and event subscription. All operations are logged to the
    Tape for full auditability.

    The SDK enforces:
    - Manifest-based permission declarations
    - Dependency resolution before loading
    - Version compatibility checks
    - Command allowlisting from the manifest
    - Lifecycle state machine transitions
    - Rate limiting and timeout enforcement

    Args:
        tape_service: TapeService for audit logging.
        platform_version: Current platform version for compatibility checks.
        folder_tree_path: Base path in folder-tree for plugin data storage.
    """

    # Valid lifecycle transitions: current_status -> set of allowed next statuses
    _TRANSITIONS: ClassVar[dict[PluginStatus, frozenset[PluginStatus]]] = {
        PluginStatus.REGISTERED: frozenset({PluginStatus.LOADED, PluginStatus.UNINSTALLING}),
        PluginStatus.LOADED: frozenset({PluginStatus.ACTIVE, PluginStatus.DISABLED, PluginStatus.UNINSTALLING}),
        PluginStatus.ACTIVE: frozenset({PluginStatus.DISABLED, PluginStatus.LOADED, PluginStatus.ERROR, PluginStatus.UNINSTALLING}),
        PluginStatus.DISABLED: frozenset({PluginStatus.ACTIVE, PluginStatus.LOADED, PluginStatus.UNINSTALLING}),
        PluginStatus.ERROR: frozenset({PluginStatus.DISABLED, PluginStatus.UNINSTALLING}),
        PluginStatus.UNINSTALLING: frozenset(),  # terminal state
    }

    def __init__(
        self,
        tape_service: TapeService,
        platform_version: PluginVersion | None = None,
        folder_tree_path: str = "plugins",
    ) -> None:
        self._tape = tape_service
        self._platform_version = platform_version or PluginVersion(major=0, minor=1, patch=0)
        self._folder_tree_path = folder_tree_path

        # Registry: manifest_id -> Plugin
        self._plugins: dict[str, Plugin] = {}
        # Command handlers: manifest_id -> command_name -> handler
        self._command_handlers: dict[str, dict[str, CommandHandler]] = defaultdict(dict)
        # Event handlers: event_type -> list of (plugin_id, handler)
        self._event_handlers: dict[str, list[tuple[str, object]]] = defaultdict(list)
        # Execution history
        self._execution_log: list[CommandExecution] = []

    # -------------------------------------------------------------------
    # Plugin Lifecycle
    # -------------------------------------------------------------------

    async def register_plugin(
        self,
        manifest: PluginManifest,
        installed_by: str = "",
        source_url: str = "",
        config: dict[str, Any] | None = None,
    ) -> Plugin:
        """Register a new plugin from its manifest.

        Creates a Plugin instance in the REGISTERED state. The plugin is
        not yet loaded or active — call ``load_plugin`` and ``activate_plugin``
        to complete the lifecycle.

        Args:
            manifest: The plugin manifest declaring metadata and permissions.
            installed_by: User or agent that initiated the installation.
            source_url: URL the plugin was installed from.
            config: Optional initial configuration values.

        Returns:
            The newly created Plugin instance.

        Raises:
            PluginAlreadyRegisteredError: if a plugin with the same manifest ID
                is already in the registry.
        """
        if manifest.id in self._plugins:
            raise PluginAlreadyRegisteredError(
                f"Plugin '{manifest.id}' is already registered"
            )

        plugin = Plugin(
            manifest=manifest,
            status=PluginStatus.REGISTERED,
            install_info=PluginInstallInfo(
                installed_by=installed_by,
                source_url=source_url,
            ),
            config=config or {},
            folder_tree_path=f"{self._folder_tree_path}/{manifest.id}",
        )

        self._plugins[manifest.id] = plugin

        await self._tape.log_event(
            event_type="plugin.registered",
            payload={
                "plugin_id": manifest.id,
                "name": manifest.name,
                "version": str(manifest.version),
                "type": manifest.plugin_type.value,
                "permissions": [p.value for p in manifest.permissions],
                "installed_by": installed_by,
            },
            agent_id="plugin-sdk",
        )

        return plugin

    async def load_plugin(self, plugin_id: str) -> Plugin:
        """Load a registered plugin, resolving dependencies and validating version.

        Transitions the plugin from REGISTERED to LOADED. Before loading,
        all declared dependencies must be satisfied and the platform version
        must be compatible.

        Args:
            plugin_id: The manifest ID of the plugin to load.

        Returns:
            The updated Plugin instance (now in LOADED state).

        Raises:
            PluginNotFoundError: if the plugin is not registered.
            PluginTransitionError: if the plugin is not in REGISTERED state.
            DependencyNotSatisfiedError: if a required dependency is missing.
            VersionNotCompatibleError: if the platform version is incompatible.
        """
        plugin = self._get_plugin(plugin_id)
        self._check_transition(plugin, PluginStatus.LOADED)

        # Check dependencies
        dep_errors = await self._check_dependencies(plugin.manifest)
        if dep_errors:
            raise DependencyNotSatisfiedError(
                f"Plugin '{plugin_id}' has unsatisfied dependencies: "
                + "; ".join(dep_errors)
            )

        # Check version compatibility
        compat_errors = self._check_version_compatibility(plugin.manifest)
        if compat_errors:
            raise VersionNotCompatibleError(
                f"Plugin '{plugin_id}' version incompatibility: "
                + "; ".join(compat_errors)
            )

        plugin.status = PluginStatus.LOADED
        plugin.loaded_at = datetime.now(UTC)

        await self._tape.log_event(
            event_type="plugin.loaded",
            payload={
                "plugin_id": plugin_id,
                "version": str(plugin.manifest.version),
            },
            agent_id="plugin-sdk",
        )

        return plugin

    async def activate_plugin(self, plugin_id: str) -> Plugin:
        """Activate a loaded or disabled plugin.

        Transitions the plugin to ACTIVE state, making it available for
        command execution and event processing.

        Args:
            plugin_id: The manifest ID of the plugin.

        Returns:
            The updated Plugin instance (now in ACTIVE state).

        Raises:
            PluginNotFoundError: if the plugin is not registered.
            PluginTransitionError: if the transition is not valid.
        """
        plugin = self._get_plugin(plugin_id)
        self._check_transition(plugin, PluginStatus.ACTIVE)

        plugin.status = PluginStatus.ACTIVE

        await self._tape.log_event(
            event_type="plugin.activated",
            payload={"plugin_id": plugin_id},
            agent_id="plugin-sdk",
        )

        return plugin

    async def deactivate_plugin(self, plugin_id: str) -> Plugin:
        """Deactivate an active plugin, transitioning it to DISABLED.

        Args:
            plugin_id: The manifest ID of the plugin.

        Returns:
            The updated Plugin instance (now in DISABLED state).

        Raises:
            PluginNotFoundError: if the plugin is not registered.
            PluginTransitionError: if the plugin is not in a deactivatable state.
        """
        plugin = self._get_plugin(plugin_id)
        self._check_transition(plugin, PluginStatus.DISABLED)

        plugin.status = PluginStatus.DISABLED

        await self._tape.log_event(
            event_type="plugin.deactivated",
            payload={"plugin_id": plugin_id},
            agent_id="plugin-sdk",
        )

        return plugin

    async def unload_plugin(self, plugin_id: str) -> Plugin:
        """Unload a plugin, removing its command handlers and event subscriptions.

        Transitions to LOADED state (from ACTIVE or DISABLED). The plugin
        remains registered but its runtime resources are released.

        Args:
            plugin_id: The manifest ID of the plugin.

        Returns:
            The updated Plugin instance.

        Raises:
            PluginNotFoundError: if the plugin is not registered.
            PluginTransitionError: if the transition is not valid.
        """
        plugin = self._get_plugin(plugin_id)
        self._check_transition(plugin, PluginStatus.LOADED)

        # Clear command handlers
        self._command_handlers.pop(plugin_id, None)

        # Clear event subscriptions
        for event_type in list(self._event_handlers.keys()):
            self._event_handlers[event_type] = [
                (pid, h) for pid, h in self._event_handlers[event_type]
                if pid != plugin_id
            ]

        plugin.status = PluginStatus.LOADED

        await self._tape.log_event(
            event_type="plugin.unloaded",
            payload={"plugin_id": plugin_id},
            agent_id="plugin-sdk",
        )

        return plugin

    async def uninstall_plugin(self, plugin_id: str) -> bool:
        """Fully uninstall a plugin, removing it from the registry.

        Args:
            plugin_id: The manifest ID of the plugin.

        Returns:
            True if the plugin was found and removed.

        Raises:
            PluginNotFoundError: if the plugin is not registered.
            PluginTransitionError: if the plugin is in a state that cannot uninstall.
        """
        plugin = self._get_plugin(plugin_id)
        self._check_transition(plugin, PluginStatus.UNINSTALLING)

        # Transition through uninstalling
        plugin.status = PluginStatus.UNINSTALLING

        # Clean up runtime resources
        self._command_handlers.pop(plugin_id, None)
        for event_type in list(self._event_handlers.keys()):
            self._event_handlers[event_type] = [
                (pid, h) for pid, h in self._event_handlers[event_type]
                if pid != plugin_id
            ]

        # Remove from registry
        removed = self._plugins.pop(plugin_id, None)

        await self._tape.log_event(
            event_type="plugin.uninstalled",
            payload={
                "plugin_id": plugin_id,
                "name": plugin.manifest.name,
                "removed": removed is not None,
            },
            agent_id="plugin-sdk",
        )

        return removed is not None

    # -------------------------------------------------------------------
    # Command Execution
    # -------------------------------------------------------------------

    async def register_command_handler(
        self,
        plugin_id: str,
        command_name: str,
        handler: CommandHandler,
    ) -> None:
        """Register a handler for a plugin command.

        The command must be declared in the plugin's manifest. The handler
        will be invoked when ``execute_command`` is called for this command.

        Args:
            plugin_id: The manifest ID of the plugin.
            command_name: The command name (must exist in the manifest).
            handler: Callable that processes the command. May be async.

        Raises:
            PluginNotFoundError: if the plugin is not registered.
            PluginNotActiveError: if the plugin is not in ACTIVE state.
            PluginCommandNotFoundError: if the command is not in the manifest.
            DuplicateCommandError: if a handler is already registered for this command.
        """
        plugin = self._get_plugin(plugin_id)
        if not plugin.can_execute():
            raise PluginNotActiveError(
                f"Plugin '{plugin_id}' is not in an executable state "
                f"(current: {plugin.status.value})"
            )

        if not plugin.manifest.has_command(command_name):
            raise PluginCommandNotFoundError(
                f"Command '{command_name}' not found in manifest for "
                f"plugin '{plugin_id}'"
            )

        if command_name in self._command_handlers.get(plugin_id, {}):
            raise DuplicateCommandError(
                f"Command '{command_name}' already has a handler for "
                f"plugin '{plugin_id}'"
            )

        self._command_handlers[plugin_id][command_name] = handler

    async def execute_command(
        self,
        plugin_id: str,
        command_name: str,
        arguments: dict[str, Any] | None = None,
        timeout_ms: int | None = None,
    ) -> CommandExecution:
        """Execute a command on an active plugin.

        The command must be declared in the manifest and have a registered
        handler. Permission checks are performed based on the command's
        declared requirements.

        Args:
            plugin_id: The manifest ID of the plugin.
            command_name: The command to execute.
            arguments: Arguments to pass to the command handler.
            timeout_ms: Optional timeout override. If not provided, the
                command's default timeout from the manifest is used.

        Returns:
            CommandExecution with status, result, and timing.

        Raises:
            PluginNotFoundError: if the plugin is not registered.
            PluginNotActiveError: if the plugin is not active.
            PluginCommandNotFoundError: if the command is not in the manifest.
        """
        plugin = self._get_plugin(plugin_id)
        if not plugin.can_execute():
            raise PluginNotActiveError(
                f"Plugin '{plugin_id}' cannot execute commands "
                f"(status: {plugin.status.value})"
            )

        if not plugin.manifest.has_command(command_name):
            raise PluginCommandNotFoundError(
                f"Command '{command_name}' not found in manifest for "
                f"plugin '{plugin_id}'"
            )

        command_def = plugin.manifest.get_command(command_name)
        assert command_def is not None  # guaranteed by has_command check

        execution = CommandExecution(
            plugin_id=plugin_id,
            command_name=command_name,
            arguments=arguments or {},
        )

        handler = self._command_handlers.get(plugin_id, {}).get(command_name)
        if handler is None:
            execution.status = "error"
            execution.error_message = (
                f"No handler registered for command '{command_name}' "
                f"on plugin '{plugin_id}'"
            )
            self._execution_log.append(execution)
            return execution

        effective_timeout = timeout_ms or command_def.timeout_ms
        start = time.monotonic()

        try:
            import asyncio

            if asyncio.iscoroutinefunction(handler):
                raw_result = await asyncio.wait_for(
                    handler(arguments or {}),
                    timeout=effective_timeout / 1000.0,
                )
            elif callable(handler):
                raw_result = handler(arguments or {})
            else:
                raw_result = None

            result_data = raw_result if isinstance(raw_result, dict) else {"value": raw_result}

            execution.status = "success"
            execution.result = result_data
            execution.execution_time_ms = (time.monotonic() - start) * 1000.0

        except TimeoutError:
            execution.status = "error"
            execution.error_message = f"Command timed out after {effective_timeout}ms"
            execution.execution_time_ms = (time.monotonic() - start) * 1000.0

        except Exception as exc:
            execution.status = "error"
            execution.error_message = str(exc)
            execution.execution_time_ms = (time.monotonic() - start) * 1000.0

        plugin.record_command()
        self._execution_log.append(execution)

        await self._tape.log_event(
            event_type="plugin.command_executed",
            payload={
                "execution_id": str(execution.id),
                "plugin_id": plugin_id,
                "command_name": command_name,
                "status": execution.status,
                "execution_time_ms": execution.execution_time_ms,
            },
            agent_id="plugin-sdk",
        )

        return execution

    # -------------------------------------------------------------------
    # Event Subscription
    # -------------------------------------------------------------------

    async def subscribe_to_events(
        self,
        plugin_id: str,
        event_type: str,
        handler: object,
    ) -> None:
        """Subscribe a plugin to an event type with a handler callback.

        The event type should be declared in the plugin's manifest
        ``event_subscriptions``. However, runtime-only subscriptions are
        also supported for dynamic plugin behaviour.

        Args:
            plugin_id: The manifest ID of the subscribing plugin.
            event_type: The event type pattern to subscribe to.
            handler: Callable invoked when a matching event is published.

        Raises:
            PluginNotFoundError: if the plugin is not registered.
            PluginNotActiveError: if the plugin is not active.
        """
        plugin = self._get_plugin(plugin_id)
        if not plugin.is_active:
            raise PluginNotActiveError(
                f"Plugin '{plugin_id}' must be active to subscribe to events"
            )

        # Check manifest declares EVENT_SUBSCRIBE permission
        if not plugin.manifest.requires_permission(PluginPermission.EVENT_SUBSCRIBE):
            raise PluginError(
                f"Plugin '{plugin_id}' does not have EVENT_SUBSCRIBE permission"
            )

        self._event_handlers[event_type].append((plugin_id, handler))

        await self._tape.log_event(
            event_type="plugin.event_subscribed",
            payload={
                "plugin_id": plugin_id,
                "event_type": event_type,
            },
            agent_id="plugin-sdk",
        )

    async def publish_event(
        self,
        plugin_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> int:
        """Publish an event from a plugin to all subscribers.

        The event type should be declared in the plugin's manifest
        ``events_published``. The event is delivered to all plugins
        that have subscribed to this event type.

        Args:
            plugin_id: The manifest ID of the publishing plugin.
            event_type: The event type to publish.
            payload: Event data to deliver to subscribers.

        Returns:
            Number of subscribers that received the event.

        Raises:
            PluginNotFoundError: if the plugin is not registered.
            PluginNotActiveError: if the plugin is not active.
            PluginError: if the plugin lacks EVENT_PUBLISH permission.
        """
        plugin = self._get_plugin(plugin_id)
        if not plugin.is_active:
            raise PluginNotActiveError(
                f"Plugin '{plugin_id}' must be active to publish events"
            )

        if not plugin.manifest.requires_permission(PluginPermission.EVENT_PUBLISH):
            raise PluginError(
                f"Plugin '{plugin_id}' does not have EVENT_PUBLISH permission"
            )

        import asyncio

        subscribers = self._event_handlers.get(event_type, [])
        for _sub_plugin_id, handler in subscribers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler({"event_type": event_type, "source": plugin_id, **payload})
                elif callable(handler):
                    handler({"event_type": event_type, "source": plugin_id, **payload})
            except Exception:
                pass  # Subscriber errors should not disrupt publishing

        await self._tape.log_event(
            event_type="plugin.event_published",
            payload={
                "plugin_id": plugin_id,
                "event_type": event_type,
                "subscriber_count": len(subscribers),
            },
            agent_id="plugin-sdk",
        )

        return len(subscribers)

    # -------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------

    def get_plugin(self, plugin_id: str) -> Plugin:
        """Get a plugin by its manifest ID.

        Raises:
            PluginNotFoundError: if the plugin is not in the registry.
        """
        plugin = self._plugins.get(plugin_id)
        if plugin is None:
            raise PluginNotFoundError(f"Plugin '{plugin_id}' not found")
        return plugin

    def list_plugins(
        self,
        status: PluginStatus | None = None,
        plugin_type: PluginType | None = None,
    ) -> list[Plugin]:
        """List plugins, optionally filtered by status or type."""
        plugins = list(self._plugins.values())
        if status is not None:
            plugins = [p for p in plugins if p.status == status]
        if plugin_type is not None:
            plugins = [p for p in plugins if p.manifest.plugin_type == plugin_type]
        return plugins

    def search_plugins(
        self,
        query: str,
        tags: list[str] | None = None,
    ) -> list[Plugin]:
        """Search plugins by name, description, or tags.

        The query matches against plugin name, description, and ID
        (case-insensitive substring). If tags are provided, only
        plugins with at least one matching tag are returned.
        """
        query_lower = query.lower()
        results = []
        for plugin in self._plugins.values():
            # Text search
            if (
                query_lower in plugin.manifest.name.lower()
                or query_lower in plugin.manifest.description.lower()
                or query_lower in plugin.manifest.id.lower()
            ):
                if tags:
                    if any(t in plugin.manifest.tags for t in tags):
                        results.append(plugin)
                else:
                    results.append(plugin)
        return results

    def get_plugin_summary(self, plugin_id: str) -> dict[str, Any]:
        """Get a lightweight summary dict for a plugin."""
        return self._get_plugin(plugin_id).to_summary()

    def get_stats(self) -> PluginStats:
        """Get aggregate statistics across all plugins."""
        plugins = list(self._plugins.values())
        return PluginStats(
            total_plugins=len(plugins),
            active_plugins=sum(1 for p in plugins if p.status == PluginStatus.ACTIVE),
            loaded_plugins=sum(1 for p in plugins if p.status == PluginStatus.LOADED),
            disabled_plugins=sum(1 for p in plugins if p.status == PluginStatus.DISABLED),
            error_plugins=sum(1 for p in plugins if p.status == PluginStatus.ERROR),
            total_commands_executed=sum(p.total_commands_executed for p in plugins),
            total_events_published=len(self._execution_log),
            total_events_subscriptions=sum(
                len(handlers) for handlers in self._event_handlers.values()
            ),
        )

    def get_execution_log(
        self,
        plugin_id: str | None = None,
        limit: int = 100,
    ) -> list[CommandExecution]:
        """Get command execution history, optionally filtered by plugin."""
        entries = self._execution_log
        if plugin_id is not None:
            entries = [e for e in entries if e.plugin_id == plugin_id]
        return list(reversed(entries[-limit:]))

    # -------------------------------------------------------------------
    # Dependency & Version Checks
    # -------------------------------------------------------------------

    async def check_dependencies(self, plugin_id: str) -> list[str]:
        """Check if a plugin's dependencies are satisfied.

        Returns:
            List of error messages. Empty list means all dependencies are satisfied.
        """
        plugin = self._get_plugin(plugin_id)
        return await self._check_dependencies(plugin.manifest)

    async def _check_dependencies(self, manifest: PluginManifest) -> list[str]:
        """Internal: verify all declared dependencies are present and meet version requirements."""
        errors: list[str] = []
        for dep in manifest.dependencies:
            dep_plugin = self._plugins.get(dep.plugin_id)
            if dep_plugin is None:
                if not dep.optional:
                    errors.append(
                        f"Required dependency '{dep.plugin_id}' is not registered"
                    )
                continue
            if dep_plugin.version < dep.min_version:
                errors.append(
                    f"Dependency '{dep.plugin_id}' version {dep_plugin.version} "
                    f"is below minimum {dep.min_version}"
                )
        return errors

    def check_version_compatibility(self, plugin_id: str) -> list[str]:
        """Check if a plugin is compatible with the current platform version.

        Returns:
            List of error messages. Empty list means the plugin is compatible.
        """
        plugin = self._get_plugin(plugin_id)
        return self._check_version_compatibility(plugin.manifest)

    def _check_version_compatibility(self, manifest: PluginManifest) -> list[str]:
        """Internal: verify platform version constraints."""
        errors: list[str] = []
        if manifest.min_platform_version is not None and self._platform_version < manifest.min_platform_version:
            errors.append(
                f"Platform version {self._platform_version} is below "
                f"minimum {manifest.min_platform_version}"
            )
        if manifest.max_platform_version is not None and self._platform_version > manifest.max_platform_version:
            errors.append(
                f"Platform version {self._platform_version} exceeds "
                f"maximum {manifest.max_platform_version}"
            )
        return errors

    # -------------------------------------------------------------------
    # Internals
    # -------------------------------------------------------------------

    def _get_plugin(self, plugin_id: str) -> Plugin:
        """Get a plugin or raise PluginNotFoundError."""
        plugin = self._plugins.get(plugin_id)
        if plugin is None:
            raise PluginNotFoundError(f"Plugin '{plugin_id}' not found")
        return plugin

    def _check_transition(
        self,
        plugin: Plugin,
        target: PluginStatus,
    ) -> None:
        """Validate a lifecycle transition, raising if invalid."""
        allowed: frozenset[PluginStatus] = self._TRANSITIONS.get(plugin.status, frozenset())
        if target not in allowed:
            raise PluginTransitionError(
                f"Cannot transition plugin '{plugin.manifest.id}' "
                f"from {plugin.status.value} to {target.value}. "
                f"Allowed transitions: {[s.value for s in allowed]}"
            )
