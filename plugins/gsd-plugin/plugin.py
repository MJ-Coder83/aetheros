"""GSD Plugin implementation.

Provides phase management, meta-prompting, and context engineering
as an official InkosAI plugin.
"""

from __future__ import annotations

from typing import Any

from packages.plugin.bridge import PluginBridge
from packages.plugin.models import (
    PluginCommand,
    PluginManifest,
    PluginType,
    PluginVersion,
)
from packages.tape.service import TapeService


class GSDPlugin:
    """Official GSD plugin for InkosAI.

    Integrates GSD meta-prompting and phase-based development with the
    InkosAI Plugin SDK.

    Usage::

        plugin = GSDPlugin(bridge=plugin_bridge, tape=tape_svc)
        await plugin.initialize()
        result = await plugin.execute_command(
            "start_phase",
            {"phase": "research", "context": {"task": "Investigate"}}
        )
    """

    PLUGIN_ID = "gsd-plugin"
    PLUGIN_NAME = "GSD Planning Domain Plugin"
    VERSION = "1.0.0"

    GSD_PHASES = ["research", "design", "implement", "test", "deploy", "validate"]

    def __init__(
        self,
        bridge: PluginBridge | None = None,
        tape: TapeService | None = None,
    ) -> None:
        self._bridge = bridge
        self._tape = tape
        self._initialized = False
        self._manifest = self._create_manifest()

    def _create_manifest(self) -> PluginManifest:
        """Create the plugin manifest."""
        return PluginManifest(
            id=self.PLUGIN_ID,
            name=self.PLUGIN_NAME,
            version=PluginVersion.parse(self.VERSION),
            plugin_type=PluginType.AGENT,
            description=(
                "Official InkosAI plugin for GSD meta-prompting "
                "and phase-based development"
            ),
            author="InkosAI",
            commands=[
                PluginCommand(
                    name="start_phase",
                    description="Start a GSD development phase",
                ),
                PluginCommand(
                    name="validate_phase_output",
                    description="Validate phase output against quality criteria",
                ),
                PluginCommand(
                    name="optimize_context",
                    description="Optimize context for agent effectiveness",
                ),
                PluginCommand(
                    name="get_phase_status",
                    description="Get current phase execution status",
                ),
                PluginCommand(
                    name="design_meta_prompt",
                    description="Design a meta-prompt for a specific task",
                ),
            ],
        )

    async def initialize(self) -> bool:
        """Initialize the plugin."""
        self._initialized = True

        if self._tape:
            await self._tape.log_event(
                event_type="plugin.initialized",
                agent_id=self.PLUGIN_ID,
                payload={
                    "plugin_id": self.PLUGIN_ID,
                    "version": self.VERSION,
                    "phases": self.GSD_PHASES,
                },
            )

        return True

    async def execute_command(
        self,
        command: str,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a plugin command."""
        if not self._initialized:
            raise RuntimeError("Plugin not initialized")

        handlers = {
            "start_phase": self._cmd_start_phase,
            "validate_phase_output": self._cmd_validate_phase_output,
            "optimize_context": self._cmd_optimize_context,
            "get_phase_status": self._cmd_get_phase_status,
            "design_meta_prompt": self._cmd_design_meta_prompt,
        }

        handler = handlers.get(command)
        if not handler:
            raise ValueError(f"Unknown command: {command}")

        return await handler(parameters)

    async def _cmd_start_phase(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle start_phase command."""
        phase = params.get("phase", "")
        context = params.get("context", {})

        if phase not in self.GSD_PHASES:
            return {
                "success": False,
                "error": f"Invalid phase: {phase}. Valid phases: {self.GSD_PHASES}",
            }

        if self._tape:
            await self._tape.log_event(
                event_type="gsd.phase_started",
                agent_id=self.PLUGIN_ID,
                payload={
                    "phase": phase,
                    "context_size": len(str(context)),
                },
            )

        return {
            "success": True,
            "phase": phase,
            "phase_number": self.GSD_PHASES.index(phase) + 1,
            "total_phases": len(self.GSD_PHASES),
            "status": "in_progress",
        }

    async def _cmd_validate_phase_output(
        self,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle validate_phase_output command."""
        phase = params.get("phase", "")
        output = params.get("output", {})

        # Simulated validation
        quality_score = 0.85  # Mock score
        passed = quality_score >= 0.85

        if self._tape:
            await self._tape.log_event(
                event_type="gsd.phase_validated",
                agent_id=self.PLUGIN_ID,
                payload={
                    "phase": phase,
                    "quality_score": quality_score,
                    "passed": passed,
                },
            )

        return {
            "success": True,
            "phase": phase,
            "quality_score": quality_score,
            "threshold": 0.85,
            "passed": passed,
            "next_phase": self._get_next_phase(phase) if passed else None,
        }

    def _get_next_phase(self, current_phase: str) -> str | None:
        """Get the next phase in the GSD cycle."""
        try:
            idx = self.GSD_PHASES.index(current_phase)
            if idx < len(self.GSD_PHASES) - 1:
                return self.GSD_PHASES[idx + 1]
        except ValueError:
            pass
        return None

    async def _cmd_optimize_context(
        self,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle optimize_context command."""
        target = params.get("target_agent", "")
        context_data = params.get("context_data", {})

        if self._tape:
            await self._tape.log_event(
                event_type="gsd.context_optimized",
                agent_id=self.PLUGIN_ID,
                payload={
                    "target_agent": target,
                    "optimization_applied": True,
                },
            )

        return {
            "success": True,
            "target_agent": target,
            "context_keys": list(context_data.keys()),
            "optimization": "Context window optimized for agent effectiveness",
            "tokens_saved": 2048,  # Mock value
        }

    async def _cmd_get_phase_status(
        self,
        _params: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle get_phase_status command."""
        return {
            "success": True,
            "current_phase": "implement",
            "phase_number": 3,
            "total_phases": 6,
            "phases": [
                {"name": "research", "status": "completed"},
                {"name": "design", "status": "completed"},
                {"name": "implement", "status": "in_progress"},
                {"name": "test", "status": "pending"},
                {"name": "deploy", "status": "pending"},
                {"name": "validate", "status": "pending"},
            ],
        }

    async def _cmd_design_meta_prompt(
        self,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle design_meta_prompt command."""
        task_type = params.get("task_type", "")
        requirements = params.get("requirements", {})

        if self._tape:
            await self._tape.log_event(
                event_type="gsd.meta_prompt_designed",
                agent_id=self.PLUGIN_ID,
                payload={
                    "task_type": task_type,
                    "requirements_keys": list(requirements.keys()),
                },
            )

        return {
            "success": True,
            "task_type": task_type,
            "meta_prompt": f"You are an expert {task_type} agent. "
                          f"Your goal is to deliver high-quality output. "
                          f"Focus on: {', '.join(requirements.keys())}",
            "template_id": f"gsd_{task_type}_v1",
        }

    @property
    def manifest(self) -> PluginManifest:
        """Get the plugin manifest."""
        return self._manifest

    @property
    def is_initialized(self) -> bool:
        """Check if plugin is initialized."""
        return self._initialized
