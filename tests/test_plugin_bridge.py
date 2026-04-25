"""Unit tests for the Plugin Runtime & Agent Bridge.

Tests cover:
- PluginSandbox: permission checks, command allowlists, rate limiting
- PluginEventBus: subscribe, unsubscribe, publish, multi-subscriber
- AgentBridge: plugin registration, command dispatch, audit logging
- Permission enforcement: denied permissions, blocked commands, rate limits
- Command routing: handler invocation, timeout, handler-not-found
- Tape logging: all operations logged to the immutable Tape
- Error handling: unregistered plugins, missing handlers, execution errors

Run with: pytest tests/test_plugin_bridge.py -v
"""

import asyncio
from datetime import datetime
from uuid import UUID

import pytest

from packages.plugin.bridge import (
    AgentBridge,
    AuditLogEntry,
    BridgeCommand,
    BridgeCommandResult,
    BridgeError,
    CommandNotAllowedError,
    CommandStatus,
    EventBusSubscription,
    PermissionDeniedError,
    PluginEvent,
    PluginEventBus,
    PluginPermission,
    PluginSandbox,
    PluginSandboxConfig,
)
from packages.tape.repository import InMemoryTapeRepository
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tape_svc() -> TapeService:
    return TapeService(InMemoryTapeRepository())


@pytest.fixture()
def sandbox(tape_svc: TapeService) -> PluginSandbox:
    config = PluginSandboxConfig(
        max_execution_time_ms=5000,
        max_commands_per_minute=10,
        allowed_commands=[],
        permissions={PluginPermission.READ, PluginPermission.AGENT_COMM},
    )
    return PluginSandbox(
        plugin_id="test-plugin",
        config=config,
        tape_service=tape_svc,
    )


@pytest.fixture()
def event_bus(tape_svc: TapeService) -> PluginEventBus:
    return PluginEventBus(tape_svc)


@pytest.fixture()
def bridge(tape_svc: TapeService) -> AgentBridge:
    return AgentBridge(tape_svc)


def _default_sandbox_config() -> PluginSandboxConfig:
    return PluginSandboxConfig(
        max_execution_time_ms=5000,
        max_commands_per_minute=60,
        allowed_commands=[],
        permissions={
            PluginPermission.READ,
            PluginPermission.AGENT_COMM,
            PluginPermission.EXECUTE,
            PluginPermission.EVENT_SUBSCRIBE,
            PluginPermission.EVENT_PUBLISH,
        },
    )


# ===========================================================================
# PluginSandbox tests
# ===========================================================================


class TestPluginSandbox:
    """Tests for PluginSandbox permission and rate-limit enforcement."""

    def test_has_permission_granted(self, sandbox: PluginSandbox) -> None:
        assert sandbox.has_permission(PluginPermission.READ) is True

    def test_has_permission_denied(self, sandbox: PluginSandbox) -> None:
        assert sandbox.has_permission(PluginPermission.NETWORK) is False

    def test_is_command_allowed_in_set(self, tape_svc: TapeService) -> None:
        config = PluginSandboxConfig(allowed_commands=["query", "analyze"])
        sb = PluginSandbox("allowlist-plugin", config, tape_svc)
        assert sb.is_command_allowed("query") is True

    def test_is_command_allowed_not_in_set(self, tape_svc: TapeService) -> None:
        config = PluginSandboxConfig(allowed_commands=["query", "analyze"])
        sb = PluginSandbox("allowlist-plugin", config, tape_svc)
        assert sb.is_command_allowed("delete") is False

    def test_is_command_allowed_empty_means_all(self, tape_svc: TapeService) -> None:
        config = PluginSandboxConfig(allowed_commands=[])
        sandbox_all = PluginSandbox("open-plugin", config, tape_svc)
        assert sandbox_all.is_command_allowed("anything") is True

    def test_check_rate_limit_within(self, sandbox: PluginSandbox) -> None:
        for _ in range(10):
            assert sandbox.check_rate_limit() is True
            sandbox.record_command()

    def test_check_rate_limit_exceeded(self, sandbox: PluginSandbox) -> None:
        for _ in range(10):
            sandbox.record_command()
        assert sandbox.check_rate_limit() is False

    @pytest.mark.asyncio
    async def test_enforce_permission_granted(
        self, sandbox: PluginSandbox,
    ) -> None:
        await sandbox.enforce_permission(
            PluginPermission.READ, "read_data", "domain-1",
        )

    @pytest.mark.asyncio
    async def test_enforce_permission_denied(
        self, sandbox: PluginSandbox,
    ) -> None:
        with pytest.raises(PermissionDeniedError, match="lacks permission"):
            await sandbox.enforce_permission(
                PluginPermission.NETWORK, "http_request", "external-api",
            )

    @pytest.mark.asyncio
    async def test_enforce_command_allowed(self, tape_svc: TapeService) -> None:
        config = PluginSandboxConfig(allowed_commands=["query"])
        sb = PluginSandbox("cmd-plugin", config, tape_svc)
        await sb.enforce_command_allowed("query")

    @pytest.mark.asyncio
    async def test_enforce_command_blocked(self, tape_svc: TapeService) -> None:
        config = PluginSandboxConfig(allowed_commands=["query"])
        sb = PluginSandbox("cmd-plugin", config, tape_svc)
        with pytest.raises(CommandNotAllowedError, match="not allowed"):
            await sb.enforce_command_allowed("delete")

    @pytest.mark.asyncio
    async def test_enforce_rate_limit(self, sandbox: PluginSandbox) -> None:
        for _ in range(10):
            sandbox.record_command()
        with pytest.raises(BridgeError, match="exceeded rate limit"):
            await sandbox.enforce_rate_limit()

    def test_plugin_id_property(self, sandbox: PluginSandbox) -> None:
        assert sandbox.plugin_id == "test-plugin"

    def test_config_property(self, sandbox: PluginSandbox) -> None:
        assert sandbox.config.max_commands_per_minute == 10


# ===========================================================================
# PluginEventBus tests
# ===========================================================================


class TestPluginEventBus:
    """Tests for PluginEventBus pub/sub functionality."""

    @pytest.mark.asyncio
    async def test_subscribe_returns_subscription(
        self, event_bus: PluginEventBus,
    ) -> None:
        sub = await event_bus.subscribe(
            "plugin-a", "test.event", handler=lambda e: None,
        )
        assert isinstance(sub, EventBusSubscription)
        assert sub.plugin_id == "plugin-a"
        assert "test.event" in sub.event_types

    @pytest.mark.asyncio
    async def test_publish_notifies_subscriber(
        self, event_bus: PluginEventBus,
    ) -> None:
        received: list[PluginEvent] = []

        async def handler(event: PluginEvent) -> None:
            received.append(event)

        await event_bus.subscribe("plugin-a", "alert", handler=handler)
        event = PluginEvent(
            event_type="alert",
            source_plugin_id="plugin-b",
            payload={"msg": "hello"},
        )
        count = await event_bus.publish(event)
        assert count == 1
        assert len(received) == 1
        assert received[0].payload["msg"] == "hello"

    @pytest.mark.asyncio
    async def test_publish_sync_handler(
        self, event_bus: PluginEventBus,
    ) -> None:
        received: list[PluginEvent] = []

        def handler(event: PluginEvent) -> None:
            received.append(event)

        await event_bus.subscribe("plugin-a", "sync.event", handler=handler)
        event = PluginEvent(
            event_type="sync.event",
            source_plugin_id="plugin-b",
            payload={"x": 1},
        )
        count = await event_bus.publish(event)
        assert count == 1
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_publish_no_subscribers(
        self, event_bus: PluginEventBus,
    ) -> None:
        event = PluginEvent(
            event_type="orphan.event",
            source_plugin_id="plugin-x",
        )
        count = await event_bus.publish(event)
        assert count == 0

    @pytest.mark.asyncio
    async def test_multiple_subscribers_same_event(
        self, event_bus: PluginEventBus,
    ) -> None:
        received_a: list[PluginEvent] = []
        received_b: list[PluginEvent] = []

        await event_bus.subscribe("plugin-a", "multi", handler=lambda e: received_a.append(e))
        await event_bus.subscribe("plugin-b", "multi", handler=lambda e: received_b.append(e))

        event = PluginEvent(event_type="multi", source_plugin_id="plugin-c")
        count = await event_bus.publish(event)
        assert count == 2
        assert len(received_a) == 1
        assert len(received_b) == 1

    @pytest.mark.asyncio
    async def test_unsubscribe(
        self, event_bus: PluginEventBus,
    ) -> None:
        sub = await event_bus.subscribe(
            "plugin-a", "temp", handler=lambda e: None,
        )
        removed = await event_bus.unsubscribe(sub.id)
        assert removed is True
        assert event_bus.get_subscription_count("temp") == 0

    @pytest.mark.asyncio
    async def test_unsubscribe_not_found(
        self, event_bus: PluginEventBus,
    ) -> None:
        from uuid import uuid4
        removed = await event_bus.unsubscribe(uuid4())
        assert removed is False

    @pytest.mark.asyncio
    async def test_get_subscriptions(
        self, event_bus: PluginEventBus,
    ) -> None:
        await event_bus.subscribe("plugin-a", "evt1", handler=lambda e: None)
        await event_bus.subscribe("plugin-a", "evt2", handler=lambda e: None)
        await event_bus.subscribe("plugin-b", "evt1", handler=lambda e: None)
        subs_a = event_bus.get_subscriptions("plugin-a")
        assert len(subs_a) == 2
        subs_b = event_bus.get_subscriptions("plugin-b")
        assert len(subs_b) == 1

    @pytest.mark.asyncio
    async def test_subscribe_logs_to_tape(
        self, event_bus: PluginEventBus, tape_svc: TapeService,
    ) -> None:
        await event_bus.subscribe("plugin-a", "taped.event", handler=lambda e: None)
        entries = await tape_svc.get_entries(event_type="plugin.event_subscribed")
        assert len(entries) == 1
        assert entries[0].payload["plugin_id"] == "plugin-a"

    @pytest.mark.asyncio
    async def test_publish_logs_to_tape(
        self, event_bus: PluginEventBus, tape_svc: TapeService,
    ) -> None:
        event = PluginEvent(
            event_type="logged.event",
            source_plugin_id="plugin-z",
        )
        await event_bus.publish(event)
        entries = await tape_svc.get_entries(event_type="plugin.event_published")
        assert len(entries) == 1
        assert entries[0].payload["event_type"] == "logged.event"

    @pytest.mark.asyncio
    async def test_unsubscribe_logs_to_tape(
        self, event_bus: PluginEventBus, tape_svc: TapeService,
    ) -> None:
        sub = await event_bus.subscribe("plugin-a", "unsub.event", handler=lambda e: None)
        await event_bus.unsubscribe(sub.id)
        entries = await tape_svc.get_entries(event_type="plugin.event_unsubscribed")
        assert len(entries) == 1

    def test_get_subscription_count(
        self, event_bus: PluginEventBus,
    ) -> None:
        assert event_bus.get_subscription_count() == 0


# ===========================================================================
# AgentBridge — Registration tests
# ===========================================================================


class TestAgentBridgeRegistration:
    """Tests for plugin registration and unregistration."""

    def test_register_plugin(self, bridge: AgentBridge) -> None:
        sandbox = bridge.register_plugin("test-plugin")
        assert isinstance(sandbox, PluginSandbox)
        assert sandbox.plugin_id == "test-plugin"
        assert bridge.is_registered("test-plugin") is True

    def test_register_plugin_duplicate(self, bridge: AgentBridge) -> None:
        bridge.register_plugin("dup-plugin")
        with pytest.raises(BridgeError, match="already registered"):
            bridge.register_plugin("dup-plugin")

    def test_register_plugin_custom_config(self, bridge: AgentBridge) -> None:
        config = PluginSandboxConfig(
            max_commands_per_minute=100,
            permissions={PluginPermission.READ},
        )
        sandbox = bridge.register_plugin("custom-plugin", sandbox_config=config)
        assert sandbox.config.max_commands_per_minute == 100

    @pytest.mark.asyncio
    async def test_unregister_plugin(self, bridge: AgentBridge) -> None:
        bridge.register_plugin("temp-plugin")
        removed = await bridge.unregister_plugin("temp-plugin")
        assert removed is True
        assert bridge.is_registered("temp-plugin") is False

    @pytest.mark.asyncio
    async def test_unregister_plugin_not_found(self, bridge: AgentBridge) -> None:
        removed = await bridge.unregister_plugin("nonexistent")
        assert removed is False

    @pytest.mark.asyncio
    async def test_unregister_removes_event_subscriptions(
        self, bridge: AgentBridge,
    ) -> None:
        bridge.register_plugin(
            "sub-plugin",
            sandbox_config=PluginSandboxConfig(
                permissions={PluginPermission.READ, PluginPermission.EVENT_SUBSCRIBE},
            ),
        )
        await bridge.event_bus.subscribe(
            "sub-plugin", "some.event", handler=lambda e: None,
        )
        assert bridge.event_bus.get_subscription_count() == 1
        await bridge.unregister_plugin("sub-plugin")
        assert bridge.event_bus.get_subscription_count() == 0

    @pytest.mark.asyncio
    async def test_unregister_logs_to_tape(
        self, bridge: AgentBridge, tape_svc: TapeService,
    ) -> None:
        bridge.register_plugin("tape-plugin")
        await bridge.unregister_plugin("tape-plugin")
        entries = await tape_svc.get_entries(event_type="plugin.unregistered")
        assert len(entries) == 1
        assert entries[0].payload["plugin_id"] == "tape-plugin"

    def test_get_sandbox(self, bridge: AgentBridge) -> None:
        bridge.register_plugin("sandbox-plugin")
        sandbox = bridge.get_sandbox("sandbox-plugin")
        assert sandbox is not None
        assert sandbox.plugin_id == "sandbox-plugin"

    def test_get_sandbox_not_found(self, bridge: AgentBridge) -> None:
        assert bridge.get_sandbox("nonexistent") is None

    def test_get_registered_plugins(self, bridge: AgentBridge) -> None:
        bridge.register_plugin("a-plugin")
        bridge.register_plugin("b-plugin")
        plugins = bridge.get_registered_plugins()
        assert "a-plugin" in plugins
        assert "b-plugin" in plugins


# ===========================================================================
# AgentBridge — Command dispatch tests
# ===========================================================================


class TestAgentBridgeDispatch:
    """Tests for secure command dispatch through the bridge."""

    @pytest.fixture()
    def setup_bridge(self, bridge: AgentBridge) -> AgentBridge:
        bridge.register_plugin(
            "sender-plugin",
            sandbox_config=_default_sandbox_config(),
        )

        async def query_handler(cmd: BridgeCommand) -> dict[str, object]:
            return {"result": f"queried_{cmd.arguments.get('key', 'default')}"}

        def analyze_handler(cmd: BridgeCommand) -> dict[str, object]:
            return {"analysis": "complete"}

        bridge.register_agent_handler("target-agent", "query", query_handler)
        bridge.register_agent_handler("target-agent", "analyze", analyze_handler)
        return bridge

    @pytest.mark.asyncio
    async def test_dispatch_success(
        self, setup_bridge: AgentBridge,
    ) -> None:
        cmd = BridgeCommand(
            plugin_id="sender-plugin",
            target_agent="target-agent",
            command_name="query",
            arguments={"key": "weather"},
        )
        result = await setup_bridge.dispatch_command(cmd)
        assert result.status == CommandStatus.SUCCESS
        assert result.result["result"] == "queried_weather"
        assert result.execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_dispatch_sync_handler(
        self, setup_bridge: AgentBridge,
    ) -> None:
        cmd = BridgeCommand(
            plugin_id="sender-plugin",
            target_agent="target-agent",
            command_name="analyze",
        )
        result = await setup_bridge.dispatch_command(cmd)
        assert result.status == CommandStatus.SUCCESS
        assert result.result["analysis"] == "complete"

    @pytest.mark.asyncio
    async def test_dispatch_unregistered_plugin(
        self, setup_bridge: AgentBridge,
    ) -> None:
        cmd = BridgeCommand(
            plugin_id="ghost-plugin",
            target_agent="target-agent",
            command_name="query",
        )
        result = await setup_bridge.dispatch_command(cmd)
        assert result.status == CommandStatus.NOT_FOUND
        assert "not registered" in result.error_message

    @pytest.mark.asyncio
    async def test_dispatch_permission_denied(
        self, bridge: AgentBridge,
    ) -> None:
        config = PluginSandboxConfig(
            permissions={PluginPermission.READ},
            allowed_commands=["query"],
        )
        bridge.register_plugin("no-comm-plugin", sandbox_config=config)
        bridge.register_agent_handler(
            "target-agent", "query",
            handler=lambda cmd: {"ok": True},
        )
        cmd = BridgeCommand(
            plugin_id="no-comm-plugin",
            target_agent="target-agent",
            command_name="query",
        )
        result = await bridge.dispatch_command(cmd)
        assert result.status == CommandStatus.DENIED
        assert "lacks permission" in result.error_message

    @pytest.mark.asyncio
    async def test_dispatch_command_not_allowed(
        self, bridge: AgentBridge,
    ) -> None:
        config = PluginSandboxConfig(
            permissions={PluginPermission.READ, PluginPermission.AGENT_COMM},
            allowed_commands=["query"],
        )
        bridge.register_plugin("restricted-plugin", sandbox_config=config)
        bridge.register_agent_handler(
            "target-agent", "dangerous",
            handler=lambda cmd: {"ok": True},
        )
        cmd = BridgeCommand(
            plugin_id="restricted-plugin",
            target_agent="target-agent",
            command_name="dangerous",
        )
        result = await bridge.dispatch_command(cmd)
        assert result.status == CommandStatus.DENIED
        assert "not allowed" in result.error_message

    @pytest.mark.asyncio
    async def test_dispatch_handler_not_found(
        self, setup_bridge: AgentBridge,
    ) -> None:
        cmd = BridgeCommand(
            plugin_id="sender-plugin",
            target_agent="target-agent",
            command_name="nonexistent",
        )
        result = await setup_bridge.dispatch_command(cmd)
        assert result.status == CommandStatus.NOT_FOUND
        assert "No handler" in result.error_message

    @pytest.mark.asyncio
    async def test_dispatch_agent_not_found(
        self, setup_bridge: AgentBridge,
    ) -> None:
        cmd = BridgeCommand(
            plugin_id="sender-plugin",
            target_agent="missing-agent",
            command_name="query",
        )
        result = await setup_bridge.dispatch_command(cmd)
        assert result.status == CommandStatus.NOT_FOUND

    @pytest.mark.asyncio
    async def test_dispatch_timeout(
        self, bridge: AgentBridge,
    ) -> None:
        config = PluginSandboxConfig(
            max_execution_time_ms=100,
            permissions={PluginPermission.READ, PluginPermission.AGENT_COMM},
            allowed_commands=["slow"],
        )
        bridge.register_plugin("slow-plugin", sandbox_config=config)

        async def slow_handler(cmd: BridgeCommand) -> dict[str, object]:
            await asyncio.sleep(10)
            return {"done": True}

        bridge.register_agent_handler("slow-agent", "slow", slow_handler)

        cmd = BridgeCommand(
            plugin_id="slow-plugin",
            target_agent="slow-agent",
            command_name="slow",
        )
        result = await bridge.dispatch_command(cmd)
        assert result.status == CommandStatus.TIMEOUT

    @pytest.mark.asyncio
    async def test_dispatch_handler_error(
        self, bridge: AgentBridge,
    ) -> None:
        config = PluginSandboxConfig(
            permissions={PluginPermission.READ, PluginPermission.AGENT_COMM},
            allowed_commands=["fail"],
        )
        bridge.register_plugin("error-plugin", sandbox_config=config)

        async def failing_handler(cmd: BridgeCommand) -> dict[str, object]:
            raise ValueError("handler exploded")

        bridge.register_agent_handler("error-agent", "fail", failing_handler)

        cmd = BridgeCommand(
            plugin_id="error-plugin",
            target_agent="error-agent",
            command_name="fail",
        )
        result = await bridge.dispatch_command(cmd)
        assert result.status == CommandStatus.ERROR
        assert "handler exploded" in result.error_message

    @pytest.mark.asyncio
    async def test_dispatch_rate_limited(
        self, bridge: AgentBridge,
    ) -> None:
        config = PluginSandboxConfig(
            max_commands_per_minute=2,
            permissions={PluginPermission.READ, PluginPermission.AGENT_COMM},
            allowed_commands=["ping"],
        )
        bridge.register_plugin("ratey-plugin", sandbox_config=config)

        async def ping_handler(cmd: BridgeCommand) -> dict[str, object]:
            return {"pong": True}

        bridge.register_agent_handler("ping-agent", "ping", ping_handler)

        for _ in range(2):
            cmd = BridgeCommand(
                plugin_id="ratey-plugin",
                target_agent="ping-agent",
                command_name="ping",
            )
            result = await bridge.dispatch_command(cmd)
            assert result.status == CommandStatus.SUCCESS

        cmd = BridgeCommand(
            plugin_id="ratey-plugin",
            target_agent="ping-agent",
            command_name="ping",
        )
        result = await bridge.dispatch_command(cmd)
        assert result.status == CommandStatus.DENIED


# ===========================================================================
# AgentBridge — Agent handler registration
# ===========================================================================


class TestAgentHandlerRegistration:
    """Tests for agent command handler registration."""

    def test_register_agent_handler(self, bridge: AgentBridge) -> None:
        bridge.register_agent_handler("agent-1", "cmd-a", handler=lambda c: None)
        assert "cmd-a" in bridge.get_agent_commands("agent-1")

    def test_unregister_agent_handler(self, bridge: AgentBridge) -> None:
        bridge.register_agent_handler("agent-1", "cmd-b", handler=lambda c: None)
        removed = bridge.unregister_agent_handler("agent-1", "cmd-b")
        assert removed is True
        assert "cmd-b" not in bridge.get_agent_commands("agent-1")

    def test_unregister_agent_handler_not_found(self, bridge: AgentBridge) -> None:
        removed = bridge.unregister_agent_handler("agent-1", "nonexistent")
        assert removed is False

    def test_get_agent_commands(self, bridge: AgentBridge) -> None:
        bridge.register_agent_handler("agent-2", "cmd-x", handler=lambda c: None)
        bridge.register_agent_handler("agent-2", "cmd-y", handler=lambda c: None)
        commands = bridge.get_agent_commands("agent-2")
        assert "cmd-x" in commands
        assert "cmd-y" in commands

    def test_get_agent_commands_empty(self, bridge: AgentBridge) -> None:
        assert bridge.get_agent_commands("unknown-agent") == []


# ===========================================================================
# AgentBridge — Audit log tests
# ===========================================================================


class TestAgentBridgeAuditLog:
    """Tests for the audit logging system."""

    @pytest.fixture()
    def audited_bridge(self, bridge: AgentBridge) -> AgentBridge:
        bridge.register_plugin(
            "audited-plugin",
            sandbox_config=_default_sandbox_config(),
        )
        bridge.register_agent_handler(
            "audit-agent", "ping",
            handler=lambda cmd: {"ok": True},
        )
        return bridge

    @pytest.mark.asyncio
    async def test_dispatch_creates_audit_entry(
        self, audited_bridge: AgentBridge,
    ) -> None:
        cmd = BridgeCommand(
            plugin_id="audited-plugin",
            target_agent="audit-agent",
            command_name="ping",
        )
        await audited_bridge.dispatch_command(cmd)
        log = audited_bridge.get_audit_log()
        assert len(log) >= 1
        entry = log[0]
        assert entry.permitted is True
        assert entry.action == "ping"

    @pytest.mark.asyncio
    async def test_denied_dispatch_creates_audit_entry(
        self, bridge: AgentBridge,
    ) -> None:
        config = PluginSandboxConfig(
            permissions={PluginPermission.READ},
            allowed_commands=["ping"],
        )
        bridge.register_plugin("denied-plugin", sandbox_config=config)
        cmd = BridgeCommand(
            plugin_id="denied-plugin",
            target_agent="any-agent",
            command_name="ping",
        )
        await bridge.dispatch_command(cmd)
        log = bridge.get_audit_log(plugin_id="denied-plugin")
        assert len(log) >= 1
        assert log[0].permitted is False

    @pytest.mark.asyncio
    async def test_audit_log_filter_by_plugin(
        self, audited_bridge: AgentBridge,
    ) -> None:
        cmd = BridgeCommand(
            plugin_id="audited-plugin",
            target_agent="audit-agent",
            command_name="ping",
        )
        await audited_bridge.dispatch_command(cmd)
        filtered = audited_bridge.get_audit_log(plugin_id="audited-plugin")
        assert all(e.plugin_id == "audited-plugin" for e in filtered)

    @pytest.mark.asyncio
    async def test_audit_log_respects_limit(
        self, audited_bridge: AgentBridge,
    ) -> None:
        for i in range(20):
            cmd = BridgeCommand(
                plugin_id="audited-plugin",
                target_agent="audit-agent",
                command_name="ping",
                arguments={"i": i},
            )
            await audited_bridge.dispatch_command(cmd)
        log = audited_bridge.get_audit_log(limit=5)
        assert len(log) == 5

    @pytest.mark.asyncio
    async def test_audit_entry_has_command_id(
        self, audited_bridge: AgentBridge,
    ) -> None:
        cmd = BridgeCommand(
            plugin_id="audited-plugin",
            target_agent="audit-agent",
            command_name="ping",
        )
        await audited_bridge.dispatch_command(cmd)
        log = audited_bridge.get_audit_log()
        assert log[0].command_id == cmd.id


# ===========================================================================
# AgentBridge — Tape logging tests
# ===========================================================================


class TestAgentBridgeTapeLogging:
    """Tests that all bridge operations are logged to the Tape."""

    @pytest.fixture()
    def taped_bridge(self, bridge: AgentBridge) -> AgentBridge:
        bridge.register_plugin(
            "taped-plugin",
            sandbox_config=_default_sandbox_config(),
        )
        bridge.register_agent_handler(
            "taped-agent", "query",
            handler=lambda cmd: {"data": "ok"},
        )
        return bridge

    @pytest.mark.asyncio
    async def test_dispatch_logs_to_tape(
        self, taped_bridge: AgentBridge, tape_svc: TapeService,
    ) -> None:
        cmd = BridgeCommand(
            plugin_id="taped-plugin",
            target_agent="taped-agent",
            command_name="query",
        )
        await taped_bridge.dispatch_command(cmd)
        entries = await tape_svc.get_entries(event_type="plugin.command_dispatched")
        assert len(entries) == 1
        assert entries[0].payload["plugin_id"] == "taped-plugin"
        assert entries[0].payload["status"] == "success"

    @pytest.mark.asyncio
    async def test_denied_dispatch_logs_to_tape(
        self, bridge: AgentBridge, tape_svc: TapeService,
    ) -> None:
        config = PluginSandboxConfig(
            max_execution_time_ms=5000,
            max_commands_per_minute=60,
            allowed_commands=["query"],
            permissions={
                PluginPermission.READ,
                PluginPermission.AGENT_COMM,
                PluginPermission.EXECUTE,
            },
        )
        bridge.register_plugin("denied-tape-plugin", sandbox_config=config)
        cmd = BridgeCommand(
            plugin_id="denied-tape-plugin",
            target_agent="taped-agent",
            command_name="nonexistent",
        )
        await bridge.dispatch_command(cmd)
        entries = await tape_svc.get_entries(event_type="plugin.command_denied")
        assert len(entries) >= 1

    @pytest.mark.asyncio
    async def test_permission_check_logs_to_tape(
        self, bridge: AgentBridge, tape_svc: TapeService,
    ) -> None:
        config = PluginSandboxConfig(
            permissions={PluginPermission.READ, PluginPermission.AGENT_COMM},
            allowed_commands=["query"],
        )
        bridge.register_plugin("perm-check-plugin", sandbox_config=config)
        cmd = BridgeCommand(
            plugin_id="perm-check-plugin",
            target_agent="some-agent",
            command_name="query",
        )
        await bridge.dispatch_command(cmd)
        entries = await tape_svc.get_entries(event_type="plugin.permission_check")
        assert len(entries) >= 1

    @pytest.mark.asyncio
    async def test_command_blocked_logs_to_tape(
        self, bridge: AgentBridge, tape_svc: TapeService,
    ) -> None:
        config = PluginSandboxConfig(
            permissions={PluginPermission.READ, PluginPermission.AGENT_COMM},
            allowed_commands=["query"],
        )
        bridge.register_plugin("blocked-plugin", sandbox_config=config)
        cmd = BridgeCommand(
            plugin_id="blocked-plugin",
            target_agent="some-agent",
            command_name="forbidden_cmd",
        )
        await bridge.dispatch_command(cmd)
        entries = await tape_svc.get_entries(event_type="plugin.command_blocked")
        assert len(entries) >= 1

    @pytest.mark.asyncio
    async def test_rate_limited_logs_to_tape(
        self, bridge: AgentBridge, tape_svc: TapeService,
    ) -> None:
        config = PluginSandboxConfig(
            max_commands_per_minute=1,
            permissions={PluginPermission.READ, PluginPermission.AGENT_COMM},
            allowed_commands=["ping"],
        )
        bridge.register_plugin("rl-plugin", sandbox_config=config)
        bridge.register_agent_handler(
            "rl-agent", "ping",
            handler=lambda cmd: {"ok": True},
        )
        cmd1 = BridgeCommand(
            plugin_id="rl-plugin", target_agent="rl-agent",
            command_name="ping",
        )
        await bridge.dispatch_command(cmd1)
        cmd2 = BridgeCommand(
            plugin_id="rl-plugin", target_agent="rl-agent",
            command_name="ping",
        )
        await bridge.dispatch_command(cmd2)
        entries = await tape_svc.get_entries(event_type="plugin.rate_limited")
        assert len(entries) >= 1


# ===========================================================================
# Data model tests
# ===========================================================================


class TestDataModels:
    """Tests for bridge data model validation and defaults."""

    def test_bridge_command_defaults(self) -> None:
        cmd = BridgeCommand(
            plugin_id="p1",
            target_agent="a1",
            command_name="test",
        )
        assert isinstance(cmd.id, UUID)
        assert cmd.arguments == {}
        assert cmd.metadata == {}
        assert isinstance(cmd.timestamp, datetime)

    def test_bridge_command_result_defaults(self) -> None:
        result = BridgeCommandResult(
            command_id=UUID("00000000-0000-0000-0000-000000000001"),
            status=CommandStatus.SUCCESS,
        )
        assert result.result == {}
        assert result.error_message == ""
        assert result.execution_time_ms == 0.0

    def test_plugin_event_defaults(self) -> None:
        event = PluginEvent(
            event_type="test",
            source_plugin_id="p1",
        )
        assert isinstance(event.id, UUID)
        assert event.payload == {}

    def test_audit_log_entry_defaults(self) -> None:
        entry = AuditLogEntry(
            plugin_id="p1",
            action="test",
            target="t1",
            permitted=True,
        )
        assert isinstance(entry.id, UUID)
        assert entry.details == {}

    def test_sandbox_config_defaults(self) -> None:
        config = PluginSandboxConfig()
        assert config.max_execution_time_ms == 30_000
        assert config.max_memory_mb == 256
        assert config.max_commands_per_minute == 60
        assert config.allowed_commands == []
        assert PluginPermission.READ in config.permissions

    def test_subscription_defaults(self) -> None:
        sub = EventBusSubscription(
            plugin_id="p1",
            event_types=["e1"],
        )
        assert isinstance(sub.id, UUID)
        assert isinstance(sub.created_at, datetime)


# ===========================================================================
# Integration tests
# ===========================================================================


class TestBridgeIntegration:
    """End-to-end integration tests for the full bridge pipeline."""

    @pytest.mark.asyncio
    async def test_full_plugin_lifecycle(
        self, bridge: AgentBridge, tape_svc: TapeService,
    ) -> None:
        bridge.register_plugin(
            "lifecycle-plugin",
            sandbox_config=_default_sandbox_config(),
        )

        events_received: list[PluginEvent] = []
        await bridge.event_bus.subscribe(
            "lifecycle-plugin", "lifecycle.result",
            handler=lambda e: events_received.append(e),
        )

        async def process_handler(cmd: BridgeCommand) -> dict[str, object]:
            return {"processed": True, "input": cmd.arguments.get("data")}

        bridge.register_agent_handler("worker-agent", "process", process_handler)

        cmd = BridgeCommand(
            plugin_id="lifecycle-plugin",
            target_agent="worker-agent",
            command_name="process",
            arguments={"data": "test-input"},
        )
        result = await bridge.dispatch_command(cmd)
        assert result.status == CommandStatus.SUCCESS
        assert result.result["processed"] is True
        assert result.result["input"] == "test-input"

        log = bridge.get_audit_log(plugin_id="lifecycle-plugin")
        assert len(log) >= 1
        assert log[0].permitted is True

        await bridge.unregister_plugin("lifecycle-plugin")
        assert bridge.is_registered("lifecycle-plugin") is False

        tape_entries = await tape_svc.get_entries(event_type="plugin.command_dispatched")
        assert len(tape_entries) >= 1

    @pytest.mark.asyncio
    async def test_multi_plugin_command_routing(
        self, bridge: AgentBridge,
    ) -> None:
        bridge.register_plugin(
            "plugin-alpha",
            sandbox_config=_default_sandbox_config(),
        )
        bridge.register_plugin(
            "plugin-beta",
            sandbox_config=_default_sandbox_config(),
        )

        results_log: list[str] = []

        async def alpha_handler(cmd: BridgeCommand) -> dict[str, object]:
            results_log.append(f"alpha:{cmd.plugin_id}")
            return {"handler": "alpha"}

        async def beta_handler(cmd: BridgeCommand) -> dict[str, object]:
            results_log.append(f"beta:{cmd.plugin_id}")
            return {"handler": "beta"}

        bridge.register_agent_handler("shared-agent", "work", alpha_handler)
        bridge.register_agent_handler("shared-agent", "compute", beta_handler)

        cmd_a = BridgeCommand(
            plugin_id="plugin-alpha",
            target_agent="shared-agent",
            command_name="work",
        )
        cmd_b = BridgeCommand(
            plugin_id="plugin-beta",
            target_agent="shared-agent",
            command_name="compute",
        )
        result_a = await bridge.dispatch_command(cmd_a)
        result_b = await bridge.dispatch_command(cmd_b)

        assert result_a.status == CommandStatus.SUCCESS
        assert result_a.result["handler"] == "alpha"
        assert result_b.status == CommandStatus.SUCCESS
        assert result_b.result["handler"] == "beta"

    @pytest.mark.asyncio
    async def test_event_bus_bridge_integration(
        self, bridge: AgentBridge,
    ) -> None:
        bridge.register_plugin(
            "event-producer",
            sandbox_config=_default_sandbox_config(),
        )
        bridge.register_plugin(
            "event-consumer",
            sandbox_config=_default_sandbox_config(),
        )

        received_events: list[PluginEvent] = []
        await bridge.event_bus.subscribe(
            "event-consumer", "data.ready",
            handler=lambda e: received_events.append(e),
        )

        event = PluginEvent(
            event_type="data.ready",
            source_plugin_id="event-producer",
            payload={"dataset": "sales_2024"},
        )
        await bridge.event_bus.publish(event)
        assert len(received_events) == 1
        assert received_events[0].payload["dataset"] == "sales_2024"

    @pytest.mark.asyncio
    async def test_handler_returning_non_dict_wrapped(
        self, bridge: AgentBridge,
    ) -> None:
        config = PluginSandboxConfig(
            permissions={PluginPermission.READ, PluginPermission.AGENT_COMM},
            allowed_commands=["raw"],
        )
        bridge.register_plugin("raw-plugin", sandbox_config=config)

        async def raw_handler(cmd: BridgeCommand) -> str:
            return "raw_string_result"

        bridge.register_agent_handler("raw-agent", "raw", raw_handler)

        cmd = BridgeCommand(
            plugin_id="raw-plugin",
            target_agent="raw-agent",
            command_name="raw",
        )
        result = await bridge.dispatch_command(cmd)
        assert result.status == CommandStatus.SUCCESS
        assert result.result["value"] == "raw_string_result"

    @pytest.mark.asyncio
    async def test_dispatch_with_timeout_override(
        self, bridge: AgentBridge,
    ) -> None:
        config = PluginSandboxConfig(
            max_execution_time_ms=60_000,
            permissions={PluginPermission.READ, PluginPermission.AGENT_COMM},
            allowed_commands=["slow"],
        )
        bridge.register_plugin("timeout-override-plugin", sandbox_config=config)

        async def slow_handler(cmd: BridgeCommand) -> dict[str, object]:
            await asyncio.sleep(5)
            return {"late": True}

        bridge.register_agent_handler("slow-agent-2", "slow", slow_handler)

        cmd = BridgeCommand(
            plugin_id="timeout-override-plugin",
            target_agent="slow-agent-2",
            command_name="slow",
        )
        result = await bridge.dispatch_command(cmd, timeout_ms=100)
        assert result.status == CommandStatus.TIMEOUT
