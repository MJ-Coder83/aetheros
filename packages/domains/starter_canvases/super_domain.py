"""Planning Super Domain Starter Canvas.

Provides a unified visual canvas combining agents from all three
methodologies with cross-methodology orchestration.
"""

from __future__ import annotations

from packages.domain.starter_canvas import CanvasLayout, StarterCanvas
from packages.domains.constants import PlanningDomainType
from packages.domains.super_domain.blueprint import PlanningSuperDomainBlueprint
from packages.domains.starter_canvases.base import PlanningStarterCanvasBase
from packages.tape.service import TapeService


class PlanningSuperStarterCanvas:
    """Starter canvas generator for the Planning Super Domain.

    Creates a unified visual layout with:
    - 7 specialized cross-methodology agents
    - Violet color scheme (distinct from base domains)
    - Triple-column layout showing methodology mix
    - Conflict resolution workflows visible
    - Hybrid swarm orchestration panel
    - Methodology recommendation engine
    """

    # Super domain visual styling
    PRIMARY_COLOR = "#8b5cf6"  # Violet
    SECONDARY_COLOR = "#a78bfa"  # Light violet
    ACCENT_COLOR = "#7c3aed"  # Dark violet
    ICON = "Layers"

    @classmethod
    async def generate(
        cls,
        tape_service: TapeService,
        layout: CanvasLayout = CanvasLayout.LAYERED,
    ) -> StarterCanvas:
        """Generate a starter canvas for the Planning Super Domain."""
        blueprint = PlanningSuperDomainBlueprint.create()

        canvas = await PlanningStarterCanvasBase.generate(
            blueprint=blueprint,
            domain_type=PlanningDomainType.SUPER,
            tape_service=tape_service,
            layout=layout,
        )

        # Apply Super Domain-specific enhancements
        cls._add_methodology_legend(canvas)
        cls._add_conflict_resolution_panel(canvas)
        cls._add_hybrid_pattern_selector(canvas)
        cls._highlight_planning_orchestrator(canvas)

        return canvas

    @classmethod
    def _add_methodology_legend(cls, canvas: StarterCanvas) -> None:
        """Add a visual legend showing the three methodologies."""
        from packages.domain.starter_canvas import CanvasNode, CanvasNodeType

        legend_items = [
            ("Gastown", "#6366f1", "Workspace"),
            ("GSD", "#10b981", "Phases"),
            ("BMAD", "#f59e0b", "Sprints"),
        ]

        for i, (name, color, desc) in enumerate(legend_items):
            legend = CanvasNode(
                id=f"legend_{name.lower()}",
                node_type=CanvasNodeType.TEMPLATE,
                label=f"● {name}",
                x=50,
                y=250 + (i * 60),
                width=120,
                height=40,
                metadata={
                    "legend_item": True,
                    "methodology": name.lower(),
                    "primary_color": color,
                    "secondary_label": desc,
                    "icon": "Circle",
                },
            )
            canvas.nodes.append(legend)

    @classmethod
    def _add_conflict_resolution_panel(cls, canvas: StarterCanvas) -> None:
        """Add a panel for conflict resolution options."""
        from packages.domain.starter_canvas import CanvasNode, CanvasNodeType

        # Find rightmost position
        max_x = max((n.x for n in canvas.nodes), default=0)

        panel = CanvasNode(
            id="conflict_resolution_panel",
            node_type=CanvasNodeType.TEMPLATE,
            label="⚖️ Conflict Resolution",
            x=max_x + 250,
            y=200,
            width=200,
            height=120,
            metadata={
                "panel_type": "conflict_resolution",
                "primary_color": "#f43f5e",  # Rose
                "icon": "Scale",
                "tooltip": "Resolve conflicts between methodologies",
                "actions": [
                    "debate_arena",
                    "simulation",
                    "prime_override",
                    "voting",
                ],
            },
        )
        canvas.nodes.append(panel)

    @classmethod
    def _add_hybrid_pattern_selector(cls, canvas: StarterCanvas) -> None:
        """Add a selector for hybrid workflow patterns."""
        from packages.domain.starter_canvas import CanvasNode, CanvasNodeType

        # Find rightmost position
        max_x = max((n.x for n in canvas.nodes), default=0)

        patterns = [
            ("GSD → BMAD", "Research then Sprint"),
            ("Gastown → BMAD", "Execute then Review"),
            ("Full Hybrid", "All Methods"),
        ]

        selector = CanvasNode(
            id="hybrid_pattern_selector",
            node_type=CanvasNodeType.TEMPLATE,
            label="🔀 Hybrid Patterns",
            x=max_x + 250,
            y=400,
            width=200,
            height=150,
            metadata={
                "selector_type": "hybrid_pattern",
                "primary_color": "#8b5cf6",
                "icon": "GitMerge",
                "tooltip": "Select hybrid workflow patterns",
                "patterns": patterns,
            },
        )
        canvas.nodes.append(selector)

    @classmethod
    def _highlight_planning_orchestrator(cls, canvas: StarterCanvas) -> None:
        """Highlight the Planning Orchestrator as the central coordinator."""
        for node in canvas.nodes:
            if "planning_orchestrator" in node.id:
                node.metadata["is_super_coordinator"] = True
                node.metadata["coordinates"] = [
                    "gastown",
                    "gsd",
                    "bmad",
                ]
                node.metadata["border_width"] = 4
                node.metadata["glow_effect"] = True
                node.metadata["badge"] = "👑 Super Orchestrator"
                node.metadata["special_capability"] = "cross_methodology_coordination"
