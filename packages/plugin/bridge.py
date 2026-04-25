"""Plugin Runtime & Agent Bridge for InkosAI.

This module implements the secure runtime layer between InkosAI plugins
and the host agent system. It provides:

1. AgentBridge -- routes commands from plugins to agents with permission
   checking, audit logging, and secure dispatch.
2. PluginEventBus -- decoupled pub/sub event system for inter-plugin
   and plugin-to-agent communication.
3. PluginSandbox -- isolated execution environment that enforces resource
   limits and permission boundaries on plugin commands.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class BridgeError(Exception):
    """Base exception for all plugin bridge operations."""


class PluginNotRegisteredError(BridgeError):
    """Raised when a command is dispatched for an unregistered plugin."""


class PermissionDeniedError(BridgeError):
    """Raised when a plugin lacks the required permission for an action."""


class CommandNotAllowedError(BridgeError):
    """Raised when a command is not in the plugin's allowed command set."""


class SandboxExecutionError(BridgeError):
    """Raised when sandboxed execution fails."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PluginPermission(StrEnum):
    """Permission levels that a plugin may be granted."""

    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    NETWORK = "network"
    FILESYSTEM = "filesystem"
    AGENT_COMM = "agent_comm"
    EVENT_SUBSCRIBE = "event_subscribe"
    EVENT_PUBLISH = "event_publish"


class CommandStatus(StrEnum):
    """Result status of a dispatched command."""

    SUCCESS = "success"
    DENIED = "denied"
    ERROR = "error"
    TIMEOUT = "timeout"
    NOT_FOUND = "not_found"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class BridgeCommand(BaseModel):
    """A command sent from a plugin through the bridge to an agent."""

    id: UUID = Field(default_factory=uuid4)
    plugin_id: str
    target_agent: str
    command_name: str
    arguments: dict[str, Any] = {}
    metadata: dict[str, object] = {}
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BridgeCommandResult(BaseModel):
    """Result of executing a bridge command."""

    command_id: UUID
    status: CommandStatus
    result: dict[str, Any] = {}
    error_message: str = ""
    execution_time_ms: float = 0.0


class AuditLogEntry(BaseModel):
    """Immutable record of a bridge operation for audit purposes."""

    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    plugin_id: str
    action: str
    target: str
    permitted: bool
    details: dict[str, object] = {}
    command_id: UUID | None = None


class PluginEvent(BaseModel):
    """An event on the plugin event bus."""

    id: UUID = Field(default_factory=uuid4)
    event_type: str
    source_plugin_id: str
    payload: dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EventBusSubscription(BaseModel):
    """A subscription to one or more event types on the bus."""

    id: UUID = Field(default_factory=uuid4)
    plugin_id: str
    event_types: list[str]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PluginSandboxConfig(BaseModel):
    """Configuration for a plugin sandbox environment."""

    max_execution_time_ms: int = 30_000
    max_memory_mb: int = 256
    max_commands_per_minute: int = 60
    allowed_commands: list[str] = []
    permissions: set[PluginPermission] = {PluginPermission.READ, PluginPermission.EVENT_SUBSCRIBE}


# ---------------------------------------------------------------------------
# PluginSandbox
# ---------------------------------------------------------------------------


class PluginSandbox:
    """Isolated execution environment for plugin commands.

    Enforces resource limits and permission boundaries. Each plugin gets
    its own sandbox instance with independent configuration.

    All enforcement is logged to the Tape for full auditability.
    """

    def __init__(
        self,
        plugin_id: str,
        config: PluginSandboxConfig,
        tape_service: TapeService,
    ) -> None:
        self._plugin_id = plugin_id
        self._config = config
        self._tape = tape_service
        self._command_timestamps: list[float] = []

    @property
    def plugin_id(self) -> str:
        return self._plugin_id

    @property
    def config(self) -> PluginSandboxConfig:
        return self._config

    def has_permission(self, permission: PluginPermission) -> bool:
        """Check if the sandbox grants a specific permission."""
        return permission in self._config.permissions

    def is_command_allowed(self, command_name: str) -> bool:
        """Check if a command is in the allowed set.

        An empty ``allowed_commands`` means all commands are permitted
        (subject to other constraints like rate limits).
        """
        if not self._config.allowed_commands:
            return True
        return command_name in self._config.allowed_commands

    def check_rate_limit(self) -> bool:
        """Return True if the plugin is within its per-minute rate limit."""
        now = time.monotonic()
        window_start = now - 60.0
        self._command_timestamps = [
            ts for ts in self._command_timestamps if ts > window_start
        ]
        return len(self._command_timestamps) < self._config.max_commands_per_minute

    def record_command(self) -> None:
        """Record a command dispatch for rate-limit tracking."""
        self._command_timestamps.append(time.monotonic())

    async def enforce_permission(
        self,
        permission: PluginPermission,
        action: str,
        target: str,
        command_id: UUID | None = None,
    ) -> None:
        """Enforce a permission requirement, raising if denied.

        Every check is logged to the Tape.
        """
        granted = self.has_permission(permission)
        await self._tape.log_event(
            event_type="plugin.permission_check",
            payload={
                "plugin_id": self._plugin_id,
                "permission": permission.value,
                "action": action,
                "target": target,
                "granted": granted,
            },
            agent_id=f"plugin-sandbox:{self._plugin_id}",
            metadata={"command_id": str(command_id)} if command_id else {},
        )
        if not granted:
            raise PermissionDeniedError(
                f"Plugin '{self._plugin_id}' lacks permission "
                f"'{permission.value}' for action '{action}' on '{target}'"
            )

    async def enforce_command_allowed(
        self,
        command_name: str,
        command_id: UUID | None = None,
    ) -> None:
        """Enforce that a command is in the allowed set, raising if not."""
        if not self.is_command_allowed(command_name):
            await self._tape.log_event(
                event_type="plugin.command_blocked",
                payload={
                    "plugin_id": self._plugin_id,
                    "command_name": command_name,
                    "reason": "not_in_allowed_set",
                },
                agent_id=f"plugin-sandbox:{self._plugin_id}",
                metadata={"command_id": str(command_id)} if command_id else {},
            )
            raise CommandNotAllowedError(
                f"Plugin '{self._plugin_id}' is not allowed to execute "
                f"command '{command_name}'"
            )

    async def enforce_rate_limit(self) -> None:
        """Enforce the per-minute rate limit, raising if exceeded."""
        if not self.check_rate_limit():
            await self._tape.log_event(
                event_type="plugin.rate_limited",
                payload={
                    "plugin_id": self._plugin_id,
                    "limit": self._config.max_commands_per_minute,
                    "window": "per_minute",
                },
                agent_id=f"plugin-sandbox:{self._plugin_id}",
            )
            raise BridgeError(
                f"Plugin '{self._plugin_id}' exceeded rate limit of "
                f"{self._config.max_commands_per_minute} commands/minute"
            )


# ---------------------------------------------------------------------------
# PluginEventBus
# ---------------------------------------------------------------------------

type EventHandler = object


class PluginEventBus:
    """Publish/subscribe event bus for plugin communication.

    Plugins can subscribe to event types and receive events published
    by other plugins or by the host system. All event traffic is logged
    to the Tape for auditability.

    Usage::

        bus = PluginEventBus(tape_service)
        sub = await bus.subscribe("plugin.weather", "weather.alert", handler)
        await bus.publish(PluginEvent(
            event_type="weather.alert",
            source_plugin_id="weather",
            payload={"alert": "storm"},
        ))
    """

    def __init__(self, tape_service: TapeService) -> None:
        self._tape = tape_service
        self._subscriptions: dict[str, list[tuple[EventBusSubscription, EventHandler]]] = (
            defaultdict(list)
        )
        self._all_subscriptions: dict[UUID, EventBusSubscription] = {}

    async def subscribe(
        self,
        plugin_id: str,
        event_type: str,
        handler: EventHandler,
    ) -> EventBusSubscription:
        """Subscribe a plugin to an event type with a handler callback.

        Args:
            plugin_id: The plugin subscribing.
            event_type: Event type pattern (exact match).
            handler: Callable invoked when a matching event is published.

        Returns:
            The subscription record.
        """
        sub = EventBusSubscription(
            plugin_id=plugin_id,
            event_types=[event_type],
        )
        self._subscriptions[event_type].append((sub, handler))
        self._all_subscriptions[sub.id] = sub

        await self._tape.log_event(
            event_type="plugin.event_subscribed",
            payload={
                "plugin_id": plugin_id,
                "event_type": event_type,
                "subscription_id": str(sub.id),
            },
            agent_id="plugin-event-bus",
        )
        return sub

    async def unsubscribe(self, subscription_id: UUID) -> bool:
        """Remove a subscription by ID.

        Returns:
            True if the subscription was found and removed.
        """
        sub = self._all_subscriptions.pop(subscription_id, None)
        if sub is None:
            return False

        for event_type in sub.event_types:
            self._subscriptions[event_type] = [
                (s, h) for s, h in self._subscriptions[event_type]
                if s.id != subscription_id
            ]

        await self._tape.log_event(
            event_type="plugin.event_unsubscribed",
            payload={
                "plugin_id": sub.plugin_id,
                "subscription_id": str(subscription_id),
            },
            agent_id="plugin-event-bus",
        )
        return True

    async def publish(self, event: PluginEvent) -> int:
        """Publish an event to all matching subscribers.

        Args:
            event: The event to publish.

        Returns:
            Number of handlers that were notified.
        """
        handlers = self._subscriptions.get(event.event_type, [])
        for _sub, handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            elif callable(handler):
                handler(event)

        await self._tape.log_event(
            event_type="plugin.event_published",
            payload={
                "event_id": str(event.id),
                "event_type": event.event_type,
                "source_plugin_id": event.source_plugin_id,
                "subscriber_count": len(handlers),
            },
            agent_id="plugin-event-bus",
        )
        return len(handlers)

    def get_subscriptions(self, plugin_id: str) -> list[EventBusSubscription]:
        """Return all subscriptions for a given plugin."""
        return [
            sub for sub in self._all_subscriptions.values()
            if sub.plugin_id == plugin_id
        ]

    def get_subscription_count(self, event_type: str | None = None) -> int:
        """Return the number of active subscriptions, optionally filtered by event type."""
        if event_type is not None:
            return len(self._subscriptions.get(event_type, []))
        return len(self._all_subscriptions)


# ---------------------------------------------------------------------------
# AgentBridge
# ---------------------------------------------------------------------------

type CommandHandler = object


class AgentBridge:
    """Secure command routing layer between plugins and agents.

    The AgentBridge is the central piece of the plugin runtime. It:

    - Registers plugins with their permission and command configurations
    - Routes commands from plugins to target agents with full permission
      and rate-limit checks
    - Maintains an audit log of every command dispatched
    - Logs all operations to the Tape for immutability and auditability

    Usage::

        bridge = AgentBridge(tape_service)
        bridge.register_plugin(
            plugin_id="weather-plugin",
            sandbox_config=PluginSandboxConfig(
                permissions={PluginPermission.READ, PluginPermission.AGENT_COMM},
                allowed_commands=["query_weather"],
            ),
        )
        result = await bridge.dispatch_command(BridgeCommand(
            plugin_id="weather-plugin",
            target_agent="weather-agent",
            command_name="query_weather",
            arguments={"city": "London"},
        ))
    """

    def __init__(self, tape_service: TapeService) -> None:
        self._tape = tape_service
        self._sandboxes: dict[str, PluginSandbox] = {}
        self._agent_handlers: dict[str, dict[str, CommandHandler]] = defaultdict(dict)
        self._audit_log: list[AuditLogEntry] = []
        self._event_bus = PluginEventBus(tape_service)

    @property
    def event_bus(self) -> PluginEventBus:
        """Access the plugin event bus."""
        return self._event_bus

    def register_plugin(
        self,
        plugin_id: str,
        sandbox_config: PluginSandboxConfig | None = None,
    ) -> PluginSandbox:
        """Register a plugin with the bridge.

        Creates a sandbox for the plugin with the given (or default)
        configuration. The sandbox governs all future command dispatches
        from this plugin.

        Args:
            plugin_id: Unique identifier for the plugin.
            sandbox_config: Optional sandbox configuration. If not
                provided, a default config with read + event_subscribe
                permissions is used.

        Returns:
            The created PluginSandbox.

        Raises:
            BridgeError: if the plugin is already registered.
        """
        if plugin_id in self._sandboxes:
            raise BridgeError(f"Plugin '{plugin_id}' is already registered")

        config = sandbox_config or PluginSandboxConfig()
        sandbox = PluginSandbox(
            plugin_id=plugin_id,
            config=config,
            tape_service=self._tape,
        )
        self._sandboxes[plugin_id] = sandbox
        return sandbox

    async def unregister_plugin(self, plugin_id: str) -> bool:
        """Unregister a plugin from the bridge.

        Removes the plugin's sandbox and all its event subscriptions.

        Returns:
            True if the plugin was found and removed.
        """
        sandbox = self._sandboxes.pop(plugin_id, None)
        if sandbox is None:
            return False

        for sub in self._event_bus.get_subscriptions(plugin_id):
            await self._event_bus.unsubscribe(sub.id)

        await self._tape.log_event(
            event_type="plugin.unregistered",
            payload={"plugin_id": plugin_id},
            agent_id="agent-bridge",
        )
        return True

    def get_sandbox(self, plugin_id: str) -> PluginSandbox | None:
        """Retrieve the sandbox for a registered plugin."""
        return self._sandboxes.get(plugin_id)

    def is_registered(self, plugin_id: str) -> bool:
        """Check if a plugin is currently registered."""
        return plugin_id in self._sandboxes

    def register_agent_handler(
        self,
        agent_id: str,
        command_name: str,
        handler: CommandHandler,
    ) -> None:
        """Register a command handler for an agent.

        Args:
            agent_id: The agent that will handle the command.
            command_name: The command name this handler responds to.
            handler: Callable that processes the command. May be async.
        """
        self._agent_handlers[agent_id][command_name] = handler

    def unregister_agent_handler(
        self,
        agent_id: str,
        command_name: str,
    ) -> bool:
        """Remove a command handler for an agent.

        Returns:
            True if the handler was found and removed.
        """
        return self._agent_handlers.get(agent_id, {}).pop(command_name, None) is not None

    async def dispatch_command(
        self,
        command: BridgeCommand,
        timeout_ms: int | None = None,
    ) -> BridgeCommandResult:
        """Dispatch a command from a plugin to a target agent.

        Full enforcement pipeline:
        1. Verify the plugin is registered
        2. Check AGENT_COMM permission
        3. Check the command is in the allowed set
        4. Enforce the per-minute rate limit
        5. Route the command to the target agent's handler
        6. Record the result in the audit log
        7. Log everything to the Tape

        Args:
            command: The command to dispatch.
            timeout_ms: Optional per-command timeout override. If not
                provided, the sandbox's default is used.

        Returns:
            BridgeCommandResult with status, return data, and timing.
        """
        start = time.monotonic()
        sandbox = self._sandboxes.get(command.plugin_id)

        if sandbox is None:
            result = BridgeCommandResult(
                command_id=command.id,
                status=CommandStatus.NOT_FOUND,
                error_message=f"Plugin '{command.plugin_id}' is not registered",
            )
            await self._log_audit(
                command=command, permitted=False,
                reason="plugin_not_registered",
            )
            return result

        try:
            await sandbox.enforce_permission(
                PluginPermission.AGENT_COMM,
                action=command.command_name,
                target=command.target_agent,
                command_id=command.id,
            )
            await sandbox.enforce_command_allowed(
                command.command_name,
                command_id=command.id,
            )
            await sandbox.enforce_rate_limit()
        except PermissionDeniedError as exc:
            result = BridgeCommandResult(
                command_id=command.id,
                status=CommandStatus.DENIED,
                error_message=str(exc),
                execution_time_ms=self._elapsed_ms(start),
            )
            await self._log_audit(
                command=command, permitted=False,
                reason="permission_denied",
                details={"permission": PluginPermission.AGENT_COMM.value},
            )
            return result
        except CommandNotAllowedError as exc:
            result = BridgeCommandResult(
                command_id=command.id,
                status=CommandStatus.DENIED,
                error_message=str(exc),
                execution_time_ms=self._elapsed_ms(start),
            )
            await self._log_audit(
                command=command, permitted=False,
                reason="command_not_allowed",
                details={"command_name": command.command_name},
            )
            return result
        except BridgeError as exc:
            result = BridgeCommandResult(
                command_id=command.id,
                status=CommandStatus.DENIED,
                error_message=str(exc),
                execution_time_ms=self._elapsed_ms(start),
            )
            await self._log_audit(
                command=command, permitted=False,
                reason="rate_limited",
            )
            return result

        sandbox.record_command()

        agent_handlers = self._agent_handlers.get(command.target_agent, {})
        handler = agent_handlers.get(command.command_name)

        if handler is None:
            result = BridgeCommandResult(
                command_id=command.id,
                status=CommandStatus.NOT_FOUND,
                error_message=(
                    f"No handler for command '{command.command_name}' "
                    f"on agent '{command.target_agent}'"
                ),
                execution_time_ms=self._elapsed_ms(start),
            )
            await self._log_audit(
                command=command, permitted=True,
                reason="handler_not_found",
                status_override=CommandStatus.NOT_FOUND,
            )
            return result

        effective_timeout = timeout_ms or sandbox.config.max_execution_time_ms

        try:
            if asyncio.iscoroutinefunction(handler):
                raw_result = await asyncio.wait_for(
                    handler(command),
                    timeout=effective_timeout / 1000.0,
                )
            elif callable(handler):
                raw_result = handler(command)
            else:
                raw_result = None

            result_data = (
                raw_result if isinstance(raw_result, dict) else {"value": raw_result}
            )
            result = BridgeCommandResult(
                command_id=command.id,
                status=CommandStatus.SUCCESS,
                result=result_data,
                execution_time_ms=self._elapsed_ms(start),
            )
        except TimeoutError:
            result = BridgeCommandResult(
                command_id=command.id,
                status=CommandStatus.TIMEOUT,
                error_message=(
                    f"Command timed out after {effective_timeout}ms"
                ),
                execution_time_ms=self._elapsed_ms(start),
            )
        except Exception as exc:
            result = BridgeCommandResult(
                command_id=command.id,
                status=CommandStatus.ERROR,
                error_message=str(exc),
                execution_time_ms=self._elapsed_ms(start),
            )

        await self._log_audit(
            command=command,
            permitted=True,
            reason="dispatched",
            status_override=result.status,
        )

        await self._tape.log_event(
            event_type="plugin.command_dispatched",
            payload={
                "command_id": str(command.id),
                "plugin_id": command.plugin_id,
                "target_agent": command.target_agent,
                "command_name": command.command_name,
                "status": result.status.value,
                "execution_time_ms": result.execution_time_ms,
            },
            agent_id="agent-bridge",
        )

        return result

    def get_audit_log(
        self,
        plugin_id: str | None = None,
        limit: int = 100,
    ) -> list[AuditLogEntry]:
        """Retrieve audit log entries, optionally filtered by plugin.

        Args:
            plugin_id: If provided, only return entries for this plugin.
            limit: Maximum entries to return (newest first).

        Returns:
            List of audit log entries.
        """
        entries = self._audit_log
        if plugin_id is not None:
            entries = [e for e in entries if e.plugin_id == plugin_id]
        return list(reversed(entries[-limit:]))

    def get_registered_plugins(self) -> list[str]:
        """Return a list of all registered plugin IDs."""
        return list(self._sandboxes.keys())

    def get_agent_commands(self, agent_id: str) -> list[str]:
        """Return the list of commands registered for an agent."""
        return list(self._agent_handlers.get(agent_id, {}).keys())

    @staticmethod
    def _elapsed_ms(start: float) -> float:
        return (time.monotonic() - start) * 1000.0

    async def _log_audit(
        self,
        command: BridgeCommand,
        permitted: bool,
        reason: str,
        details: dict[str, object] | None = None,
        status_override: CommandStatus | None = None,
    ) -> None:
        entry = AuditLogEntry(
            plugin_id=command.plugin_id,
            action=command.command_name,
            target=command.target_agent,
            permitted=permitted,
            details={
                "reason": reason,
                "command_id": str(command.id),
                **(details or {}),
                **({"status": status_override.value} if status_override else {}),
            },
            command_id=command.id,
        )
        self._audit_log.append(entry)

        event_type = (
            "plugin.command_permitted" if permitted
            else "plugin.command_denied"
        )
        await self._tape.log_event(
            event_type=event_type,
            payload={
                "command_id": str(command.id),
                "plugin_id": command.plugin_id,
                "action": command.command_name,
                "target": command.target_agent,
                "permitted": permitted,
                "reason": reason,
                **(details or {}),
            },
            agent_id="agent-bridge",
        )
