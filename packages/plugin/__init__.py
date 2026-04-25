"""InkosAI Plugin System — Core, SDK, Runtime Bridge, and Models.

The Plugin System enables third-party extensions to integrate with InkosAI
in a safe, auditable, and permission-controlled manner.

Architecture::

    PluginSDK (core.py)
    ├── register_plugin() — Create plugin from manifest
    ├── load_plugin() — Resolve deps, validate version
    ├── activate_plugin() / deactivate_plugin() — Lifecycle control
    ├── execute_command() — Dispatch commands with permission checks
    ├── subscribe_to_events() / publish_event() — Plugin event bus
    └── search/list/get — Discovery queries

    Plugin Models (models.py)
    ├── PluginManifest — Declarative plugin metadata
    ├── Plugin — Runtime plugin instance
    ├── PluginPermission — Fine-grained permission enum
    ├── PluginCommand — Command exposed by a plugin
    └── PluginVersion — Semantic versioning

    AgentBridge (bridge.py)
    ├── AgentBridge — Secure command routing between plugins and agents
    ├── PluginEventBus — Pub/sub event system
    └── PluginSandbox — Isolated execution with rate limiting
"""

from packages.plugin.bridge import (
    AgentBridge,
    AuditLogEntry,
    BridgeCommand,
    BridgeCommandResult,
    BridgeError,
    CommandNotAllowedError,
    EventBusSubscription,
    PermissionDeniedError,
    PluginEvent,
    PluginEventBus,
    PluginNotRegisteredError,
    PluginSandbox,
    PluginSandboxConfig,
)
from packages.plugin.core import (
    CommandExecution,
    DependencyNotSatisfiedError,
    DuplicateCommandError,
    PluginAlreadyRegisteredError,
    PluginCommandExecutionError,
    PluginCommandNotFoundError,
    PluginError,
    PluginLoadError,
    PluginNotActiveError,
    PluginNotFoundError,
    PluginNotLoadedError,
    PluginSDK,
    PluginStats,
    PluginTransitionError,
    VersionNotCompatibleError,
)
from packages.plugin.models import (
    Plugin,
    PluginCommand,
    PluginDependency,
    PluginInstallInfo,
    PluginInstallSource,
    PluginManifest,
    PluginPermission,
    PluginStatus,
    PluginType,
    PluginVersion,
)

__all__ = [
    # Bridge
    "AgentBridge",
    "AuditLogEntry",
    "BridgeCommand",
    "BridgeCommandResult",
    "BridgeError",
    "CommandNotAllowedError",
    "EventBusSubscription",
    "PermissionDeniedError",
    "PluginEvent",
    "PluginEventBus",
    "PluginNotRegisteredError",
    "PluginSandbox",
    "PluginSandboxConfig",
    # Core
    "CommandExecution",
    "DependencyNotSatisfiedError",
    "DuplicateCommandError",
    "PluginAlreadyRegisteredError",
    "PluginCommandExecutionError",
    "PluginCommandNotFoundError",
    "PluginError",
    "PluginLoadError",
    "PluginNotFoundError",
    "PluginNotActiveError",
    "PluginNotLoadedError",
    "PluginSDK",
    "PluginStats",
    "PluginTransitionError",
    "VersionNotCompatibleError",
    # Models
    "Plugin",
    "PluginCommand",
    "PluginDependency",
    "PluginInstallInfo",
    "PluginInstallSource",
    "PluginManifest",
    "PluginPermission",
    "PluginStatus",
    "PluginType",
    "PluginVersion",
]
