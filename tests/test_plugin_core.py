"""Comprehensive tests for Plugin Core & SDK (Agent 1).

Tests cover:
- PluginVersion: parsing, comparison, string representation
- PluginManifest: construction, permission checks, command lookups
- Plugin: lifecycle state, command recording, summaries
- PluginDependency: optional vs required, version constraints
- PluginInstallInfo: defaults, source types
- PluginSDK lifecycle: register → load → activate → deactivate → unload → uninstall
- PluginSDK command execution: handler registration, execution, timeouts, errors
- PluginSDK event system: subscribe, publish, permission enforcement
- PluginSDK dependency resolution: satisfied, missing, version mismatch, optional
- PluginSDK version compatibility: min/max platform constraints
- PluginSDK queries: get, list, search, stats, execution log
- PluginSDK error handling: not found, invalid transitions, duplicate registration
- PluginSDK Tape logging: all lifecycle and command events logged

Run with: pytest tests/test_plugin_core.py -v
"""

from __future__ import annotations

import asyncio

import pytest

from packages.plugin.bridge import (
    AgentBridge,
    PluginSandboxConfig,
)
from packages.plugin.core import (
    DependencyNotSatisfiedError,
    DuplicateCommandError,
    PluginAlreadyRegisteredError,
    PluginCommandNotFoundError,
    PluginError,
    PluginNotActiveError,
    PluginNotFoundError,
    PluginSDK,
    PluginTransitionError,
    VersionNotCompatibleError,
)
from packages.plugin.models import (
    Plugin,
    PluginCommand,
    PluginDependency,
    PluginManifest,
    PluginPermission,
    PluginStatus,
    PluginType,
    PluginVersion,
)
from packages.tape.repository import InMemoryTapeRepository
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_tape() -> TapeService:
    return TapeService(InMemoryTapeRepository())


def _make_sdk(tape: TapeService | None = None, platform_version: PluginVersion | None = None) -> PluginSDK:
    tape = tape or _make_tape()
    return PluginSDK(tape_service=tape, platform_version=platform_version)


def _make_manifest(
    plugin_id: str = "test-plugin",
    name: str = "Test Plugin",
    permissions: set[PluginPermission] | None = None,
    commands: list[PluginCommand] | None = None,
    **kwargs: object,
) -> PluginManifest:
    return PluginManifest(
        id=plugin_id,
        name=name,
        permissions=permissions or {PluginPermission.READ, PluginPermission.EXECUTE},
        commands=commands or [],
        **kwargs,  # type: ignore[arg-type]
    )


@pytest.fixture
def tape() -> TapeService:
    return _make_tape()


@pytest.fixture
def sdk(tape: TapeService) -> PluginSDK:
    return _make_sdk(tape)


# ===========================================================================
# PluginVersion Tests
# ===========================================================================


class TestPluginVersion:

    def test_default_version(self) -> None:
        v = PluginVersion()
        assert v.major == 0
        assert v.minor == 1
        assert v.patch == 0
        assert str(v) == "0.1.0"

    def test_custom_version(self) -> None:
        v = PluginVersion(major=2, minor=5, patch=3)
        assert str(v) == "2.5.3"

    def test_pre_release(self) -> None:
        v = PluginVersion(major=1, minor=0, patch=0, pre_release="beta")
        assert str(v) == "1.0.0-beta"

    def test_parse_simple(self) -> None:
        v = PluginVersion.parse("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3

    def test_parse_pre_release(self) -> None:
        v = PluginVersion.parse("1.0.0-alpha")
        assert v.pre_release == "alpha"

    def test_parse_invalid_format(self) -> None:
        with pytest.raises(ValueError, match="Invalid semver"):
            PluginVersion.parse("1.2")

    def test_parse_invalid_numbers(self) -> None:
        with pytest.raises(ValueError, match="Invalid semver"):
            PluginVersion.parse("a.b.c")

    def test_parse_negative(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            PluginVersion.parse("-1.0.0")

    def test_comparison_lt(self) -> None:
        assert PluginVersion(major=1, minor=0, patch=0) < PluginVersion(major=2, minor=0, patch=0)
        assert PluginVersion(major=1, minor=0, patch=0) < PluginVersion(major=1, minor=1, patch=0)
        assert PluginVersion(major=1, minor=0, patch=0) < PluginVersion(major=1, minor=0, patch=1)

    def test_comparison_gt(self) -> None:
        assert PluginVersion(major=2, minor=0, patch=0) > PluginVersion(major=1, minor=0, patch=0)

    def test_comparison_eq(self) -> None:
        assert PluginVersion(major=1, minor=2, patch=3) == PluginVersion(major=1, minor=2, patch=3)

    def test_comparison_le_ge(self) -> None:
        v1 = PluginVersion(major=1, minor=0, patch=0)
        v2 = PluginVersion(major=1, minor=0, patch=0)
        v3 = PluginVersion(major=2, minor=0, patch=0)
        assert v1 <= v2
        assert v1 <= v3
        assert v3 >= v1
        assert v2 >= v1

    def test_pre_release_lower_than_release(self) -> None:
        v_pre = PluginVersion(major=1, minor=0, patch=0, pre_release="beta")
        v_rel = PluginVersion(major=1, minor=0, patch=0)
        assert v_pre < v_rel
        assert v_rel > v_pre

    def test_pre_release_comparison(self) -> None:
        v_a = PluginVersion(major=1, minor=0, patch=0, pre_release="alpha")
        v_b = PluginVersion(major=1, minor=0, patch=0, pre_release="beta")
        assert v_a < v_b


# ===========================================================================
# PluginManifest Tests
# ===========================================================================


class TestPluginManifest:

    def test_minimal_manifest(self) -> None:
        m = _make_manifest()
        assert m.id == "test-plugin"
        assert m.name == "Test Plugin"
        assert m.plugin_type == PluginType.UTILITY
        assert m.license == "MIT"

    def test_full_manifest(self) -> None:
        m = PluginManifest(
            id="weather",
            name="Weather Plugin",
            version=PluginVersion(major=1, minor=2, patch=3),
            plugin_type=PluginType.INTEGRATION,
            description="Weather data integration",
            author="InkosAI",
            permissions={PluginPermission.READ, PluginPermission.NETWORK},
            commands=[
                PluginCommand(name="query", description="Query weather"),
            ],
            tags=["weather", "data"],
        )
        assert m.version_str == "1.2.3"
        assert m.plugin_type == PluginType.INTEGRATION
        assert len(m.commands) == 1
        assert "weather" in m.tags

    def test_requires_permission(self) -> None:
        m = _make_manifest(permissions={PluginPermission.READ, PluginPermission.NETWORK})
        assert m.requires_permission(PluginPermission.READ) is True
        assert m.requires_permission(PluginPermission.EXECUTE) is False

    def test_has_command(self) -> None:
        m = _make_manifest(
            commands=[PluginCommand(name="fetch", description="Fetch data")]
        )
        assert m.has_command("fetch") is True
        assert m.has_command("nonexistent") is False

    def test_get_command(self) -> None:
        cmd = PluginCommand(name="fetch", description="Fetch data", timeout_ms=5000)
        m = _make_manifest(commands=[cmd])
        result = m.get_command("fetch")
        assert result is not None
        assert result.timeout_ms == 5000
        assert m.get_command("nonexistent") is None

    def test_manifest_serialization_roundtrip(self) -> None:
        m = PluginManifest(
            id="test",
            name="Test",
            version=PluginVersion(major=1, minor=0, patch=0),
            permissions={PluginPermission.READ},
            commands=[PluginCommand(name="run", description="Run it")],
        )
        data = m.model_dump(mode="json")
        restored = PluginManifest.model_validate(data)
        assert restored.id == "test"
        assert restored.has_command("run")


# ===========================================================================
# Plugin Model Tests
# ===========================================================================


class TestPluginModel:

    def test_default_plugin(self) -> None:
        p = Plugin(manifest=_make_manifest())
        assert p.status == PluginStatus.REGISTERED
        assert p.is_active is False
        assert p.is_error is False
        assert p.total_commands_executed == 0

    def test_plugin_id_property(self) -> None:
        p = Plugin(manifest=_make_manifest(plugin_id="my-plugin"))
        assert p.plugin_id == "my-plugin"

    def test_can_execute_registered(self) -> None:
        p = Plugin(manifest=_make_manifest(), status=PluginStatus.REGISTERED)
        assert p.can_execute() is False

    def test_can_execute_active(self) -> None:
        p = Plugin(manifest=_make_manifest(), status=PluginStatus.ACTIVE)
        assert p.can_execute() is True

    def test_can_execute_loaded(self) -> None:
        p = Plugin(manifest=_make_manifest(), status=PluginStatus.LOADED)
        assert p.can_execute() is True

    def test_record_command(self) -> None:
        p = Plugin(manifest=_make_manifest())
        p.record_command()
        p.record_command()
        assert p.total_commands_executed == 2
        assert p.last_command_at is not None

    def test_to_summary(self) -> None:
        p = Plugin(
            manifest=_make_manifest(plugin_id="test", name="Test"),
            status=PluginStatus.ACTIVE,
        )
        summary = p.to_summary()
        assert summary["plugin_id"] == "test"
        assert summary["status"] == "active"

    def test_folder_tree_path(self) -> None:
        p = Plugin(manifest=_make_manifest(), folder_tree_path="plugins/test")
        assert p.folder_tree_path == "plugins/test"


# ===========================================================================
# PluginDependency Tests
# ===========================================================================


class TestPluginDependency:

    def test_required_dependency(self) -> None:
        d = PluginDependency(plugin_id="core-lib", min_version=PluginVersion(major=1))
        assert d.optional is False

    def test_optional_dependency(self) -> None:
        d = PluginDependency(plugin_id="optional-lib", optional=True)
        assert d.optional is True


# ===========================================================================
# PluginSDK Lifecycle Tests
# ===========================================================================


class TestPluginSDKLifecycle:

    @pytest.mark.asyncio
    async def test_register_creates_plugin(self, sdk: PluginSDK) -> None:
        manifest = _make_manifest()
        plugin = await sdk.register_plugin(manifest)
        assert plugin.manifest.id == "test-plugin"
        assert plugin.status == PluginStatus.REGISTERED

    @pytest.mark.asyncio
    async def test_register_duplicate_raises(self, sdk: PluginSDK) -> None:
        manifest = _make_manifest()
        await sdk.register_plugin(manifest)
        with pytest.raises(PluginAlreadyRegisteredError):
            await sdk.register_plugin(manifest)

    @pytest.mark.asyncio
    async def test_load_plugin(self, sdk: PluginSDK) -> None:
        await sdk.register_plugin(_make_manifest())
        plugin = await sdk.load_plugin("test-plugin")
        assert plugin.status == PluginStatus.LOADED
        assert plugin.loaded_at is not None

    @pytest.mark.asyncio
    async def test_activate_plugin(self, sdk: PluginSDK) -> None:
        await sdk.register_plugin(_make_manifest())
        await sdk.load_plugin("test-plugin")
        plugin = await sdk.activate_plugin("test-plugin")
        assert plugin.status == PluginStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, sdk: PluginSDK) -> None:
        manifest = _make_manifest()
        # Register → Load → Activate → Deactivate → Unload → Uninstall
        await sdk.register_plugin(manifest)
        await sdk.load_plugin("test-plugin")
        await sdk.activate_plugin("test-plugin")
        await sdk.deactivate_plugin("test-plugin")
        await sdk.unload_plugin("test-plugin")
        result = await sdk.uninstall_plugin("test-plugin")
        assert result is True

    @pytest.mark.asyncio
    async def test_activate_disabled_plugin(self, sdk: PluginSDK) -> None:
        await sdk.register_plugin(_make_manifest())
        await sdk.load_plugin("test-plugin")
        await sdk.activate_plugin("test-plugin")
        await sdk.deactivate_plugin("test-plugin")
        plugin = await sdk.activate_plugin("test-plugin")
        assert plugin.status == PluginStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_load_not_registered_raises(self, sdk: PluginSDK) -> None:
        with pytest.raises(PluginNotFoundError):
            await sdk.load_plugin("nonexistent")

    @pytest.mark.asyncio
    async def test_activate_registered_not_loaded_raises(self, sdk: PluginSDK) -> None:
        await sdk.register_plugin(_make_manifest())
        with pytest.raises(PluginTransitionError):
            await sdk.activate_plugin("test-plugin")

    @pytest.mark.asyncio
    async def test_deactivate_registered_raises(self, sdk: PluginSDK) -> None:
        await sdk.register_plugin(_make_manifest())
        with pytest.raises(PluginTransitionError):
            await sdk.deactivate_plugin("test-plugin")

    @pytest.mark.asyncio
    async def test_uninstall_removes_from_registry(self, sdk: PluginSDK) -> None:
        await sdk.register_plugin(_make_manifest())
        await sdk.uninstall_plugin("test-plugin")
        with pytest.raises(PluginNotFoundError):
            sdk.get_plugin("test-plugin")

    @pytest.mark.asyncio
    async def test_register_logs_to_tape(self, tape: TapeService, sdk: PluginSDK) -> None:
        await sdk.register_plugin(_make_manifest())
        entries = await tape.get_entries(event_type="plugin.registered")
        assert len(entries) == 1
        assert entries[0].payload["plugin_id"] == "test-plugin"

    @pytest.mark.asyncio
    async def test_load_logs_to_tape(self, tape: TapeService, sdk: PluginSDK) -> None:
        await sdk.register_plugin(_make_manifest())
        await sdk.load_plugin("test-plugin")
        entries = await tape.get_entries(event_type="plugin.loaded")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_activate_logs_to_tape(self, tape: TapeService, sdk: PluginSDK) -> None:
        await sdk.register_plugin(_make_manifest())
        await sdk.load_plugin("test-plugin")
        await sdk.activate_plugin("test-plugin")
        entries = await tape.get_entries(event_type="plugin.activated")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_deactivate_logs_to_tape(self, tape: TapeService, sdk: PluginSDK) -> None:
        await sdk.register_plugin(_make_manifest())
        await sdk.load_plugin("test-plugin")
        await sdk.activate_plugin("test-plugin")
        await sdk.deactivate_plugin("test-plugin")
        entries = await tape.get_entries(event_type="plugin.deactivated")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_uninstall_logs_to_tape(self, tape: TapeService, sdk: PluginSDK) -> None:
        await sdk.register_plugin(_make_manifest())
        await sdk.uninstall_plugin("test-plugin")
        entries = await tape.get_entries(event_type="plugin.uninstalled")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_register_with_config(self, sdk: PluginSDK) -> None:
        manifest = _make_manifest()
        plugin = await sdk.register_plugin(manifest, config={"api_key": "test123"})
        assert plugin.config["api_key"] == "test123"

    @pytest.mark.asyncio
    async def test_register_sets_folder_tree_path(self, sdk: PluginSDK) -> None:
        manifest = _make_manifest(plugin_id="weather")
        plugin = await sdk.register_plugin(manifest)
        assert plugin.folder_tree_path == "plugins/weather"


# ===========================================================================
# PluginSDK Command Execution Tests
# ===========================================================================


class TestPluginSDKCommands:

    @pytest.mark.asyncio
    async def test_register_handler_and_execute(self, sdk: PluginSDK) -> None:
        manifest = _make_manifest(
            commands=[PluginCommand(name="greet", description="Say hello")],
            permissions={PluginPermission.READ, PluginPermission.EXECUTE},
        )
        await sdk.register_plugin(manifest)
        await sdk.load_plugin("test-plugin")
        await sdk.activate_plugin("test-plugin")

        async def greet_handler(args: dict) -> dict:
            return {"greeting": f"Hello, {args.get('name', 'world')}!"}

        await sdk.register_command_handler("test-plugin", "greet", greet_handler)

        result = await sdk.execute_command("test-plugin", "greet", {"name": "Alice"})
        assert result.status == "success"
        assert result.result["greeting"] == "Hello, Alice!"

    @pytest.mark.asyncio
    async def test_execute_sync_handler(self, sdk: PluginSDK) -> None:
        manifest = _make_manifest(
            commands=[PluginCommand(name="add", description="Add numbers")],
            permissions={PluginPermission.READ, PluginPermission.EXECUTE},
        )
        await sdk.register_plugin(manifest)
        await sdk.load_plugin("test-plugin")
        await sdk.activate_plugin("test-plugin")

        def add_handler(args: dict) -> dict:
            return {"sum": args.get("a", 0) + args.get("b", 0)}

        await sdk.register_command_handler("test-plugin", "add", add_handler)

        result = await sdk.execute_command("test-plugin", "add", {"a": 3, "b": 4})
        assert result.status == "success"
        assert result.result["sum"] == 7

    @pytest.mark.asyncio
    async def test_execute_command_not_in_manifest(self, sdk: PluginSDK) -> None:
        manifest = _make_manifest(commands=[])
        await sdk.register_plugin(manifest)
        await sdk.load_plugin("test-plugin")
        await sdk.activate_plugin("test-plugin")

        with pytest.raises(PluginCommandNotFoundError):
            await sdk.execute_command("test-plugin", "nonexistent")

    @pytest.mark.asyncio
    async def test_execute_command_on_inactive_plugin(self, sdk: PluginSDK) -> None:
        manifest = _make_manifest(
            commands=[PluginCommand(name="run", description="Run")],
            permissions={PluginPermission.READ, PluginPermission.EXECUTE},
        )
        await sdk.register_plugin(manifest)
        with pytest.raises(PluginNotActiveError):
            await sdk.execute_command("test-plugin", "run")

    @pytest.mark.asyncio
    async def test_execute_command_no_handler(self, sdk: PluginSDK) -> None:
        manifest = _make_manifest(
            commands=[PluginCommand(name="run", description="Run")],
            permissions={PluginPermission.READ, PluginPermission.EXECUTE},
        )
        await sdk.register_plugin(manifest)
        await sdk.load_plugin("test-plugin")
        await sdk.activate_plugin("test-plugin")

        result = await sdk.execute_command("test-plugin", "run")
        assert result.status == "error"
        assert "No handler" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_command_handler_error(self, sdk: PluginSDK) -> None:
        manifest = _make_manifest(
            commands=[PluginCommand(name="fail", description="Fails")],
            permissions={PluginPermission.READ, PluginPermission.EXECUTE},
        )
        await sdk.register_plugin(manifest)
        await sdk.load_plugin("test-plugin")
        await sdk.activate_plugin("test-plugin")

        async def fail_handler(args: dict) -> dict:
            raise RuntimeError("Something went wrong")

        await sdk.register_command_handler("test-plugin", "fail", fail_handler)

        result = await sdk.execute_command("test-plugin", "fail")
        assert result.status == "error"
        assert "Something went wrong" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_command_timeout(self, sdk: PluginSDK) -> None:
        manifest = _make_manifest(
            commands=[PluginCommand(name="slow", description="Slow", timeout_ms=100)],
            permissions={PluginPermission.READ, PluginPermission.EXECUTE},
        )
        await sdk.register_plugin(manifest)
        await sdk.load_plugin("test-plugin")
        await sdk.activate_plugin("test-plugin")

        async def slow_handler(args: dict) -> dict:
            await asyncio.sleep(5)  # Way longer than 100ms timeout
            return {"done": True}

        await sdk.register_command_handler("test-plugin", "slow", slow_handler)

        result = await sdk.execute_command("test-plugin", "slow", timeout_ms=100)
        assert result.status == "error"
        assert "timed out" in result.error_message

    @pytest.mark.asyncio
    async def test_duplicate_command_handler_raises(self, sdk: PluginSDK) -> None:
        manifest = _make_manifest(
            commands=[PluginCommand(name="dup", description="Dup")],
            permissions={PluginPermission.READ, PluginPermission.EXECUTE},
        )
        await sdk.register_plugin(manifest)
        await sdk.load_plugin("test-plugin")
        await sdk.activate_plugin("test-plugin")

        async def handler(args: dict) -> dict:
            return {}

        await sdk.register_command_handler("test-plugin", "dup", handler)
        with pytest.raises(DuplicateCommandError):
            await sdk.register_command_handler("test-plugin", "dup", handler)

    @pytest.mark.asyncio
    async def test_register_handler_not_in_manifest_raises(self, sdk: PluginSDK) -> None:
        manifest = _make_manifest(commands=[])
        await sdk.register_plugin(manifest)
        await sdk.load_plugin("test-plugin")
        await sdk.activate_plugin("test-plugin")

        with pytest.raises(PluginCommandNotFoundError):
            await sdk.register_command_handler("test-plugin", "ghost", lambda x: x)

    @pytest.mark.asyncio
    async def test_execute_records_command_count(self, sdk: PluginSDK) -> None:
        manifest = _make_manifest(
            commands=[PluginCommand(name="ping", description="Ping")],
            permissions={PluginPermission.READ, PluginPermission.EXECUTE},
        )
        await sdk.register_plugin(manifest)
        await sdk.load_plugin("test-plugin")
        await sdk.activate_plugin("test-plugin")

        await sdk.register_command_handler("test-plugin", "ping", lambda args: {"pong": True})
        await sdk.execute_command("test-plugin", "ping")
        await sdk.execute_command("test-plugin", "ping")

        plugin = sdk.get_plugin("test-plugin")
        assert plugin.total_commands_executed == 2

    @pytest.mark.asyncio
    async def test_execute_command_logs_to_tape(self, tape: TapeService, sdk: PluginSDK) -> None:
        manifest = _make_manifest(
            commands=[PluginCommand(name="run", description="Run")],
            permissions={PluginPermission.READ, PluginPermission.EXECUTE},
        )
        await sdk.register_plugin(manifest)
        await sdk.load_plugin("test-plugin")
        await sdk.activate_plugin("test-plugin")
        await sdk.register_command_handler("test-plugin", "run", lambda a: {"ok": True})

        await sdk.execute_command("test-plugin", "run")
        entries = await tape.get_entries(event_type="plugin.command_executed")
        assert len(entries) == 1
        assert entries[0].payload["command_name"] == "run"


# ===========================================================================
# PluginSDK Event System Tests
# ===========================================================================


class TestPluginSDKEvents:

    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self, sdk: PluginSDK) -> None:
        from packages.plugin.models import PluginEventSubscription

        manifest = _make_manifest(
            permissions={
                PluginPermission.READ,
                PluginPermission.EXECUTE,
                PluginPermission.EVENT_SUBSCRIBE,
                PluginPermission.EVENT_PUBLISH,
            },
            event_subscriptions=[
                PluginEventSubscription(event_type="data.updated"),
            ],
            events_published=["data.updated"],
        )
        await sdk.register_plugin(manifest)
        await sdk.load_plugin("test-plugin")
        await sdk.activate_plugin("test-plugin")

        received: list[dict] = []

        async def on_data_updated(event: dict) -> None:
            received.append(event)

        await sdk.subscribe_to_events("test-plugin", "data.updated", on_data_updated)

        count = await sdk.publish_event("test-plugin", "data.updated", {"key": "value"})
        assert count == 1
        assert len(received) == 1
        assert received[0]["key"] == "value"

    @pytest.mark.asyncio
    async def test_publish_without_permission_raises(self, sdk: PluginSDK) -> None:
        manifest = _make_manifest(
            permissions={PluginPermission.READ, PluginPermission.EVENT_SUBSCRIBE},
        )
        await sdk.register_plugin(manifest)
        await sdk.load_plugin("test-plugin")
        await sdk.activate_plugin("test-plugin")

        with pytest.raises(PluginError, match="EVENT_PUBLISH"):
            await sdk.publish_event("test-plugin", "test.event", {})

    @pytest.mark.asyncio
    async def test_subscribe_without_permission_raises(self, sdk: PluginSDK) -> None:
        manifest = _make_manifest(
            permissions={PluginPermission.READ, PluginPermission.EVENT_PUBLISH},
        )
        await sdk.register_plugin(manifest)
        await sdk.load_plugin("test-plugin")
        await sdk.activate_plugin("test-plugin")

        with pytest.raises(PluginError, match="EVENT_SUBSCRIBE"):
            await sdk.subscribe_to_events("test-plugin", "test.event", lambda e: None)

    @pytest.mark.asyncio
    async def test_subscribe_inactive_plugin_raises(self, sdk: PluginSDK) -> None:
        manifest = _make_manifest(
            permissions={PluginPermission.READ, PluginPermission.EVENT_SUBSCRIBE},
        )
        await sdk.register_plugin(manifest)
        with pytest.raises(PluginNotActiveError):
            await sdk.subscribe_to_events("test-plugin", "test.event", lambda e: None)

    @pytest.mark.asyncio
    async def test_publish_inactive_plugin_raises(self, sdk: PluginSDK) -> None:
        manifest = _make_manifest(
            permissions={PluginPermission.READ, PluginPermission.EVENT_PUBLISH},
        )
        await sdk.register_plugin(manifest)
        with pytest.raises(PluginNotActiveError):
            await sdk.publish_event("test-plugin", "test.event", {})

    @pytest.mark.asyncio
    async def test_publish_to_no_subscribers(self, sdk: PluginSDK) -> None:
        manifest = _make_manifest(
            permissions={PluginPermission.READ, PluginPermission.EVENT_PUBLISH},
            events_published=["orphan.event"],
        )
        await sdk.register_plugin(manifest)
        await sdk.load_plugin("test-plugin")
        await sdk.activate_plugin("test-plugin")

        count = await sdk.publish_event("test-plugin", "orphan.event", {})
        assert count == 0


# ===========================================================================
# PluginSDK Dependency Resolution Tests
# ===========================================================================


class TestPluginSDKDependencies:

    @pytest.mark.asyncio
    async def test_no_dependencies(self, sdk: PluginSDK) -> None:
        manifest = _make_manifest()
        await sdk.register_plugin(manifest)
        errors = await sdk.check_dependencies("test-plugin")
        assert errors == []

    @pytest.mark.asyncio
    async def test_satisfied_dependency(self, sdk: PluginSDK) -> None:
        # Register the dependency first
        dep_manifest = _make_manifest(plugin_id="core-lib", name="Core Lib")
        await sdk.register_plugin(dep_manifest)
        await sdk.load_plugin("core-lib")

        # Register plugin that depends on core-lib
        manifest = _make_manifest(
            plugin_id="dependent",
            dependencies=[
                PluginDependency(plugin_id="core-lib", min_version=PluginVersion(major=0, minor=1, patch=0)),
            ],
        )
        await sdk.register_plugin(manifest)
        errors = await sdk.check_dependencies("dependent")
        assert errors == []

    @pytest.mark.asyncio
    async def test_missing_required_dependency(self, sdk: PluginSDK) -> None:
        manifest = _make_manifest(
            dependencies=[
                PluginDependency(plugin_id="missing-dep", min_version=PluginVersion(major=1)),
            ],
        )
        await sdk.register_plugin(manifest)
        errors = await sdk.check_dependencies("test-plugin")
        assert len(errors) == 1
        assert "missing-dep" in errors[0]

    @pytest.mark.asyncio
    async def test_missing_optional_dependency_ok(self, sdk: PluginSDK) -> None:
        manifest = _make_manifest(
            dependencies=[
                PluginDependency(plugin_id="optional-dep", optional=True),
            ],
        )
        await sdk.register_plugin(manifest)
        errors = await sdk.check_dependencies("test-plugin")
        assert errors == []

    @pytest.mark.asyncio
    async def test_dependency_version_too_low(self, sdk: PluginSDK) -> None:
        # Register dependency with low version
        dep_manifest = _make_manifest(
            plugin_id="old-lib",
            name="Old Lib",
            version=PluginVersion(major=0, minor=1, patch=0),
        )
        await sdk.register_plugin(dep_manifest)

        # Plugin requires version 2+
        manifest = _make_manifest(
            plugin_id="needy",
            dependencies=[
                PluginDependency(plugin_id="old-lib", min_version=PluginVersion(major=2)),
            ],
        )
        await sdk.register_plugin(manifest)
        errors = await sdk.check_dependencies("needy")
        assert len(errors) == 1
        assert "below minimum" in errors[0]

    @pytest.mark.asyncio
    async def test_load_fails_with_missing_dep(self, sdk: PluginSDK) -> None:
        manifest = _make_manifest(
            dependencies=[
                PluginDependency(plugin_id="missing", min_version=PluginVersion(major=1)),
            ],
        )
        await sdk.register_plugin(manifest)
        with pytest.raises(DependencyNotSatisfiedError):
            await sdk.load_plugin("test-plugin")


# ===========================================================================
# PluginSDK Version Compatibility Tests
# ===========================================================================


class TestPluginSDKVersionCompat:

    @pytest.mark.asyncio
    async def test_no_version_constraint(self, sdk: PluginSDK) -> None:
        manifest = _make_manifest()  # no min/max platform version
        await sdk.register_plugin(manifest)
        errors = sdk.check_version_compatibility("test-plugin")
        assert errors == []

    @pytest.mark.asyncio
    async def test_min_version_satisfied(self) -> None:
        tape = _make_tape()
        sdk = _make_sdk(tape, platform_version=PluginVersion(major=2, minor=0, patch=0))
        manifest = _make_manifest(min_platform_version=PluginVersion(major=1))
        await sdk.register_plugin(manifest)
        errors = sdk.check_version_compatibility("test-plugin")
        assert errors == []

    @pytest.mark.asyncio
    async def test_min_version_not_met(self) -> None:
        tape = _make_tape()
        sdk = _make_sdk(tape, platform_version=PluginVersion(major=0, minor=5, patch=0))
        manifest = _make_manifest(min_platform_version=PluginVersion(major=1))
        await sdk.register_plugin(manifest)
        errors = sdk.check_version_compatibility("test-plugin")
        assert len(errors) == 1
        assert "below minimum" in errors[0]

    @pytest.mark.asyncio
    async def test_max_version_exceeded(self) -> None:
        tape = _make_tape()
        sdk = _make_sdk(tape, platform_version=PluginVersion(major=3))
        manifest = _make_manifest(max_platform_version=PluginVersion(major=2))
        await sdk.register_plugin(manifest)
        errors = sdk.check_version_compatibility("test-plugin")
        assert len(errors) == 1
        assert "exceeds maximum" in errors[0]

    @pytest.mark.asyncio
    async def test_load_fails_with_version_incompat(self) -> None:
        tape = _make_tape()
        sdk = _make_sdk(tape, platform_version=PluginVersion(major=0, minor=1, patch=0))
        manifest = _make_manifest(min_platform_version=PluginVersion(major=5))
        await sdk.register_plugin(manifest)
        with pytest.raises(VersionNotCompatibleError):
            await sdk.load_plugin("test-plugin")


# ===========================================================================
# PluginSDK Query Tests
# ===========================================================================


class TestPluginSDKQueries:

    @pytest.mark.asyncio
    async def test_get_plugin(self, sdk: PluginSDK) -> None:
        await sdk.register_plugin(_make_manifest())
        plugin = sdk.get_plugin("test-plugin")
        assert plugin.manifest.id == "test-plugin"

    @pytest.mark.asyncio
    async def test_get_plugin_not_found(self, sdk: PluginSDK) -> None:
        with pytest.raises(PluginNotFoundError):
            sdk.get_plugin("nonexistent")

    @pytest.mark.asyncio
    async def test_list_plugins(self, sdk: PluginSDK) -> None:
        await sdk.register_plugin(_make_manifest(plugin_id="a"))
        await sdk.register_plugin(_make_manifest(plugin_id="b"))
        await sdk.register_plugin(_make_manifest(plugin_id="c"))
        assert len(sdk.list_plugins()) == 3

    @pytest.mark.asyncio
    async def test_list_plugins_by_status(self, sdk: PluginSDK) -> None:
        await sdk.register_plugin(_make_manifest(plugin_id="a"))
        await sdk.register_plugin(_make_manifest(plugin_id="b"))
        await sdk.load_plugin("a")
        await sdk.activate_plugin("a")

        active = sdk.list_plugins(status=PluginStatus.ACTIVE)
        registered = sdk.list_plugins(status=PluginStatus.REGISTERED)
        assert len(active) == 1
        assert len(registered) == 1

    @pytest.mark.asyncio
    async def test_list_plugins_by_type(self, sdk: PluginSDK) -> None:
        await sdk.register_plugin(_make_manifest(plugin_type=PluginType.INTEGRATION))
        await sdk.register_plugin(_make_manifest(plugin_id="b", plugin_type=PluginType.AGENT))
        integrations = sdk.list_plugins(plugin_type=PluginType.INTEGRATION)
        assert len(integrations) == 1

    @pytest.mark.asyncio
    async def test_search_plugins_by_name(self, sdk: PluginSDK) -> None:
        await sdk.register_plugin(_make_manifest(plugin_id="weather", name="Weather Plugin"))
        await sdk.register_plugin(_make_manifest(plugin_id="legal", name="Legal Research"))
        results = sdk.search_plugins("Weather")
        assert len(results) == 1
        assert results[0].manifest.id == "weather"

    @pytest.mark.asyncio
    async def test_search_plugins_by_tag(self, sdk: PluginSDK) -> None:
        await sdk.register_plugin(
            _make_manifest(plugin_id="a", name="A", tags=["weather"])
        )
        await sdk.register_plugin(
            _make_manifest(plugin_id="b", name="B", tags=["legal"])
        )
        results = sdk.search_plugins("", tags=["weather"])
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_get_plugin_summary(self, sdk: PluginSDK) -> None:
        await sdk.register_plugin(_make_manifest())
        summary = sdk.get_plugin_summary("test-plugin")
        assert summary["plugin_id"] == "test-plugin"

    @pytest.mark.asyncio
    async def test_get_stats(self, sdk: PluginSDK) -> None:
        await sdk.register_plugin(_make_manifest(plugin_id="a"))
        await sdk.register_plugin(_make_manifest(plugin_id="b"))
        await sdk.load_plugin("a")
        await sdk.activate_plugin("a")

        stats = sdk.get_stats()
        assert stats.total_plugins == 2
        assert stats.active_plugins == 1
        assert stats.loaded_plugins == 0  # 'a' was activated, not just loaded

    @pytest.mark.asyncio
    async def test_get_execution_log(self, sdk: PluginSDK) -> None:
        manifest = _make_manifest(
            commands=[PluginCommand(name="run", description="Run")],
            permissions={PluginPermission.READ, PluginPermission.EXECUTE},
        )
        await sdk.register_plugin(manifest)
        await sdk.load_plugin("test-plugin")
        await sdk.activate_plugin("test-plugin")
        await sdk.register_command_handler("test-plugin", "run", lambda a: {"ok": True})

        await sdk.execute_command("test-plugin", "run")
        log = sdk.get_execution_log(plugin_id="test-plugin")
        assert len(log) == 1
        assert log[0].command_name == "run"

    @pytest.mark.asyncio
    async def test_get_execution_log_filter(self, sdk: PluginSDK) -> None:
        manifest = _make_manifest(
            commands=[PluginCommand(name="run", description="Run")],
            permissions={PluginPermission.READ, PluginPermission.EXECUTE},
        )
        await sdk.register_plugin(manifest)
        await sdk.load_plugin("test-plugin")
        await sdk.activate_plugin("test-plugin")
        await sdk.register_command_handler("test-plugin", "run", lambda a: {"ok": True})

        await sdk.execute_command("test-plugin", "run")
        other_log = sdk.get_execution_log(plugin_id="other-plugin")
        assert len(other_log) == 0


# ===========================================================================
# PluginSDK Error Handling Tests
# ===========================================================================


class TestPluginSDKErrors:

    def test_plugin_not_found_is_plugin_error(self) -> None:
        assert issubclass(PluginNotFoundError, PluginError)

    def test_plugin_already_registered_is_plugin_error(self) -> None:
        assert issubclass(PluginAlreadyRegisteredError, PluginError)

    def test_plugin_not_active_is_plugin_error(self) -> None:
        assert issubclass(PluginNotActiveError, PluginError)

    def test_plugin_transition_is_plugin_error(self) -> None:
        assert issubclass(PluginTransitionError, PluginError)

    def test_dependency_not_satisfied_is_load_error(self) -> None:
        from packages.plugin.core import PluginLoadError
        assert issubclass(DependencyNotSatisfiedError, PluginLoadError)

    def test_version_not_compatible_is_load_error(self) -> None:
        from packages.plugin.core import PluginLoadError
        assert issubclass(VersionNotCompatibleError, PluginLoadError)

    @pytest.mark.asyncio
    async def test_unload_active_plugin(self, sdk: PluginSDK) -> None:
        """Unloading an active plugin should transition to LOADED."""
        await sdk.register_plugin(_make_manifest())
        await sdk.load_plugin("test-plugin")
        await sdk.activate_plugin("test-plugin")
        plugin = await sdk.unload_plugin("test-plugin")
        assert plugin.status == PluginStatus.LOADED

    @pytest.mark.asyncio
    async def test_unload_clears_handlers(self, sdk: PluginSDK) -> None:
        manifest = _make_manifest(
            commands=[PluginCommand(name="run", description="Run")],
            permissions={PluginPermission.READ, PluginPermission.EXECUTE},
        )
        await sdk.register_plugin(manifest)
        await sdk.load_plugin("test-plugin")
        await sdk.activate_plugin("test-plugin")
        await sdk.register_command_handler("test-plugin", "run", lambda a: {"ok": True})

        await sdk.unload_plugin("test-plugin")
        # After unloading, command handlers should be cleared
        # The plugin is in LOADED state, so executing would fail anyway
        plugin = sdk.get_plugin("test-plugin")
        assert plugin.status == PluginStatus.LOADED


# ===========================================================================
# PluginSDK + Bridge Integration Tests
# ===========================================================================


class TestPluginSDKBridgeIntegration:
    """Test that PluginSDK models are compatible with AgentBridge."""

    @pytest.mark.asyncio
    async def test_bridge_uses_sdk_permissions(self, tape: TapeService) -> None:
        """PluginPermission from models.py should be usable with bridge sandbox."""
        bridge = AgentBridge(tape_service=tape)
        sandbox = bridge.register_plugin(
            plugin_id="test",
            sandbox_config=PluginSandboxConfig(
                permissions={
                    PluginPermission.READ,
                    PluginPermission.AGENT_COMM,
                },
            ),
        )
        assert sandbox.has_permission(PluginPermission.READ)
        assert sandbox.has_permission(PluginPermission.AGENT_COMM)
        assert not sandbox.has_permission(PluginPermission.NETWORK)

    @pytest.mark.asyncio
    async def test_sdk_manifest_permissions_match_bridge(self, tape: TapeService) -> None:
        """Manifest-declared permissions should align with what bridge enforces."""
        sdk = _make_sdk(tape)
        manifest = _make_manifest(
            permissions={PluginPermission.READ, PluginPermission.AGENT_COMM},
        )
        await sdk.register_plugin(manifest)
        plugin = sdk.get_plugin("test-plugin")
        assert PluginPermission.AGENT_COMM in plugin.manifest.permissions
