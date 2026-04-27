"""BMAD Domain Starter Canvas.

Provides a pre-configured visual canvas for the BMAD (Breakthrough Method
for Agile AI-Driven Development) domain.
"""

from __future__ import annotations

from packages.domain.starter_canvas import CanvasLayout, StarterCanvas
from packages.domains.constants import PlanningDomainType
from packages.domains.bmad.blueprint import BMADDomainBlueprint
from packages.domains.starter_canvases.base import PlanningStarterCanvasBase
from packages.tape.service import TapeService


class BMADStarterCanvas:
    """Starter canvas generator for the BMAD domain.

    Creates a visual layout with:
    - 6 specialized agents arranged in track clusters
    - Domain-specific amber color scheme
    - Sprint Planner and Track Coordinator as central nodes
    - Breakthrough Facilitator and Agile Coach as support nodes
    - Research, Design, Build, Review tracks
    - Sprint review indicators
    - Quick Swarm and Governed Swarm buttons
    - Folder-tree dual mode indicator
    """

    # BMAD visual styling
    PRIMARY_COLOR = "#f59e0b"  # Amber
    SECONDARY_COLOR = "#fbbf24"  # Light amber
    ACCENT_COLOR = "#d97706"  # Dark amber
    ICON = "Rocket"

    # Track colors
    TRACK_COLORS = {
        "research": "#3b82f6",  # Blue
        "design": "#8b5cf6",  # Violet
        "build": "#10b981",  # Emerald
        "review": "#f59e0b",  # Amber
    }

    @classmethod
    async def generate(
        cls,
        tape_service: TapeService,
        layout: CanvasLayout = CanvasLayout.CLUSTERED,
    ) -> StarterCanvas:
        """Generate a starter canvas for the BMAD domain."""
        blueprint = BMADDomainBlueprint.create()

        canvas = await PlanningStarterCanvasBase.generate(
            blueprint=blueprint,
            domain_type=PlanningDomainType.BMAD,
            tape_service=tape_service,
            layout=layout,
        )

        # Apply BMAD-specific enhancements
        cls._add_track_clusters(canvas)
        cls._highlight_sprint_planner(canvas)
        cls._add_breakthrough_session_node(canvas)
        cls._add_velocity_tracker(canvas)

        return canvas

    @classmethod
    def _add_track_clusters(cls, canvas: StarterCanvas) -> None:
        """Add visual track cluster indicators for the 4 BMAD tracks."""
        from packages.domain.starter_canvas import CanvasNode, CanvasNodeType

        tracks = [
            ("Research Track", "research", "🔍"),
            ("Design Track", "design", "🎨"),
            ("Build Track", "build", "🔨"),
            ("Review Track", "review", "✓"),
        ]

        y_position = 500

        for i, (name, track_id, icon) in enumerate(tracks):
            track_cluster = CanvasNode(
                id=f"bmad_track_{track_id}",
                node_type=CanvasNodeType.TEMPLATE,
                label=f"{icon} {name}",
                x=150 + (i * 220),
                y=y_position,
                width=180,
                height=50,
                metadata={
                    "cluster_type": "track",
                    "track_id": track_id,
                    "primary_color": cls.TRACK_COLORS[track_id],
                    "icon": icon,
                    "tooltip": f"BMAD {name} - work flows through here",
                },
            )
            canvas.nodes.append(track_cluster)

    @classmethod
    def _highlight_sprint_planner(cls, canvas: StarterCanvas) -> None:
        """Highlight the Sprint Planner as the agile coordinator."""
        for node in canvas.nodes:
            if "sprint_planner" in node.id:
                node.metadata["is_sprint_coordinator"] = True
                node.metadata["sprint_scope"] = "2_week_sprints"
                node.metadata["special_capability"] = "sprint_planning"
                node.metadata["border_width"] = 3
                node.metadata["glow_effect"] = True
                node.metadata["badge"] = "🎯 Sprint Lead"

    @classmethod
    def _add_breakthrough_session_node(cls, canvas: StarterCanvas) -> None:
        """Add a visual indicator for breakthrough sessions."""
        from packages.domain.starter_canvas import CanvasNode, CanvasNodeType

        # Find position for breakthrough node
        max_x = max((n.x for n in canvas.nodes), default=0)

        breakthrough = CanvasNode(
            id="bmad_breakthrough_session",
            node_type=CanvasNodeType.TEMPLATE,
            label="💡 Breakthrough Session",
            x=max_x + 200,
            y=300,
            width=180,
            height=60,
            metadata={
                "session_type": "breakthrough",
                "primary_color": "#ec4899",  # Pink for breakthrough
                "icon": "Lightbulb",
                "tooltip": "Schedule a breakthrough session for creative problem solving",
                "action": "create_breakthrough_session",
            },
        )
        canvas.nodes.append(breakthrough)

    @classmethod
    def _add_velocity_tracker(cls, canvas: StarterCanvas) -> None:
        """Add a velocity tracking indicator for agile metrics."""
        from packages.domain.starter_canvas import CanvasNode, CanvasNodeType

        velocity = CanvasNode(
            id="bmad_velocity_tracker",
            node_type=CanvasNodeType.TEMPLATE,
            label="📊 Velocity: --",
            x=50,
            y=200,
            width=140,
            height=40,
            metadata={
                "tracker_type": "velocity",
                "primary_color": "#22c55e",
                "icon": "TrendingUp",
                "tooltip": "Team velocity tracking for sprint planning",
                "widget": True,
            },
        )
        canvas.nodes.append(velocity)
