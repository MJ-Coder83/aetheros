"""BMAD Plugin implementation.

Provides sprint planning, breakthrough facilitation, and track coordination
as an official InkosAI plugin.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from packages.plugin.models import (
    PluginCommand,
    PluginManifest,
    PluginType,
    PluginVersion,
)
from packages.plugin.bridge import PluginBridge
from packages.tape.service import TapeService


class BMADPlugin:
    """Official BMAD plugin for InkosAI.

    Integrates BMAD agile sprint planning with the InkosAI Plugin SDK.

    Usage::

        plugin = BMADPlugin(bridge=plugin_bridge, tape=tape_svc)
        await plugin.initialize()
        result = await plugin.execute_command(
            "start_sprint",
            {"sprint_name": "Sprint 1", "goals": ["Feature A"]}
        )
    """

    PLUGIN_ID = "bmad-plugin"
    PLUGIN_NAME = "BMAD Planning Domain Plugin"
    VERSION = "1.0.0"

    TRACKS = ["research", "design", "build", "review"]

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
                "Official InkosAI plugin for BMAD agile sprint planning "
                "and breakthrough facilitation"
            ),
            author="InkosAI",
            commands=[
                PluginCommand(
                    name="start_sprint",
                    description="Start a new BMAD sprint",
                ),
                PluginCommand(
                    name="schedule_breakthrough",
                    description="Schedule a breakthrough session",
                ),
                PluginCommand(
                    name="track_velocity",
                    description="Track team velocity metrics",
                ),
                PluginCommand(
                    name="coordinate_tracks",
                    description="Coordinate work across tracks",
                ),
                PluginCommand(
                    name="conduct_sprint_review",
                    description="Conduct sprint review",
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
                    "tracks": self.TRACKS,
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
            "start_sprint": self._cmd_start_sprint,
            "schedule_breakthrough": self._cmd_schedule_breakthrough,
            "track_velocity": self._cmd_track_velocity,
            "coordinate_tracks": self._cmd_coordinate_tracks,
            "conduct_sprint_review": self._cmd_conduct_sprint_review,
        }

        handler = handlers.get(command)
        if not handler:
            raise ValueError(f"Unknown command: {command}")

        return await handler(parameters)

    async def _cmd_start_sprint(
        self,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle start_sprint command."""
        name = params.get("sprint_name", "")
        goals = params.get("goals", [])
        duration = params.get("duration_days", 14)

        sprint_id = f"sprint_{name.lower().replace(' ', '_')}"

        if self._tape:
            await self._tape.log_event(
                event_type="bmad.sprint_started",
                agent_id=self.PLUGIN_ID,
                payload={
                    "sprint_id": sprint_id,
                    "sprint_name": name,
                    "goals_count": len(goals),
                    "duration_days": duration,
                },
            )

        return {
            "success": True,
            "sprint_id": sprint_id,
            "sprint_name": name,
            "goals": goals,
            "duration_days": duration,
            "tracks": self.TRACKS,
            "status": "started",
        }

    async def _cmd_schedule_breakthrough(
        self,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle schedule_breakthrough command."""
        challenge = params.get("challenge", "")
        participants = params.get("participants", [])

        session_id = f"breakthrough_{datetime.now(UTC).timestamp()}"

        if self._tape:
            await self._tape.log_event(
                event_type="bmad.breakthrough_scheduled",
                agent_id=self.PLUGIN_ID,
                payload={
                    "session_id": session_id,
                    "challenge": challenge,
                    "participants_count": len(participants),
                },
            )

        return {
            "success": True,
            "session_id": session_id,
            "challenge": challenge,
            "participants": participants,
            "scheduled_at": datetime.now(UTC).isoformat(),
            "facilitator": "bmad_breakthrough_facilitator",
        }

    async def _cmd_track_velocity(
        self,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle track_velocity command."""
        sprint_id = params.get("sprint_id", "")

        # Mock velocity data
        velocity = {
            "current_sprint_velocity": 42,
            "average_velocity": 38,
            "trend": "increasing",
            "points_completed": 35,
            "points_committed": 40,
        }

        if self._tape:
            await self._tape.log_event(
                event_type="bmad.velocity_updated",
                agent_id=self.PLUGIN_ID,
                payload={
                    "sprint_id": sprint_id,
                    "velocity": velocity,
                },
            )

        return {
            "success": True,
            "sprint_id": sprint_id,
            "velocity": velocity,
        }

    async def _cmd_coordinate_tracks(
        self,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle coordinate_tracks command."""
        tracks = params.get("tracks", [])
        dependencies = params.get("dependencies", {})

        if self._tape:
            await self._tape.log_event(
                event_type="bmad.track_coordinated",
                agent_id=self.PLUGIN_ID,
                payload={
                    "tracks_coordinated": tracks,
                    "dependencies_count": len(dependencies),
                },
            )

        return {
            "success": True,
            "tracks": tracks,
            "dependencies": dependencies,
            "coordinator": "bmad_track_coordinator",
            "flow": "research → design → build → review",
        }

    async def _cmd_conduct_sprint_review(
        self,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle conduct_sprint_review command."""
        sprint_id = params.get("sprint_id", "")
        deliverables = params.get("deliverables", [])

        # Mock review results
        review_results = {
            "deliverables_reviewed": len(deliverables),
            "accepted": len(deliverables) - 1,
            "rejected": 1,
            "feedback_count": 5,
        }

        if self._tape:
            await self._tape.log_event(
                event_type="bmad.sprint_reviewed",
                agent_id=self.PLUGIN_ID,
                payload={
                    "sprint_id": sprint_id,
                    "results": review_results,
                },
            )

        return {
            "success": True,
            "sprint_id": sprint_id,
            "review_results": review_results,
            "reviewer": "bmad_sprint_reviewer",
            "status": "completed",
        }

    @property
    def manifest(self) -> PluginManifest:
        """Get the plugin manifest."""
        return self._manifest

    @property
    def is_initialized(self) -> bool:
        """Check if plugin is initialized."""
        return self._initialized
