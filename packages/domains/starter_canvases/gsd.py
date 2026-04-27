"""GSD Domain Starter Canvas.

Provides a pre-configured visual canvas for the GSD (Get Shit Done)
meta-prompting and phase-based development domain.
"""

from __future__ import annotations

from packages.domain.starter_canvas import CanvasLayout, StarterCanvas
from packages.domains.constants import PlanningDomainType
from packages.domains.gsd.blueprint import GSDDomainBlueprint
from packages.domains.starter_canvases.base import PlanningStarterCanvasBase
from packages.tape.service import TapeService


class GSDStarterCanvas:
    """Starter canvas generator for the GSD domain.

    Creates a visual layout with:
    - 6 specialized agents arranged in phase-pipeline formation
    - Domain-specific emerald color scheme
    - Phase Manager as the central orchestrator
    - Context Engineer, Meta-Prompt Designer, Execution Tracker,
      Quality Validator, and Implementation Builder as phase participants
    - Phase gate indicators
    - Quick Swarm and Governed Swarm buttons
    - Folder-tree dual mode indicator

    Usage::

        from packages.domains.starter_canvases.gsd import GSDStarterCanvas
        from packages.tape.service import TapeService

        tape_svc = TapeService(...)
        canvas = await GSDStarterCanvas.generate(tape_svc)
    """

    # GSD visual styling
    PRIMARY_COLOR = "#10b981"  # Emerald
    SECONDARY_COLOR = "#34d399"  # Light emerald
    ACCENT_COLOR = "#059669"  # Dark emerald
    ICON = "Zap"

    # GSD phase colors
    PHASE_COLORS = {
        "research": "#3b82f6",  # Blue
        "design": "#8b5cf6",  # Violet
        "implement": "#10b981",  # Emerald
        "test": "#f59e0b",  # Amber
        "deploy": "#22c55e",  # Green
        "validate": "#06b6d4",  # Cyan
    }

    @classmethod
    async def generate(
        cls,
        tape_service: TapeService,
        layout: CanvasLayout = CanvasLayout.LAYERED,
    ) -> StarterCanvas:
        """Generate a starter canvas for the GSD domain.

        Args:
            tape_service: Service for logging canvas creation
            layout: Layout strategy (defaults to LAYERED for GSD's phase pipeline)

        Returns:
            A StarterCanvas with GSD-specific visual styling
        """
        blueprint = GSDDomainBlueprint.create()

        canvas = await PlanningStarterCanvasBase.generate(
            blueprint=blueprint,
            domain_type=PlanningDomainType.GSD,
            tape_service=tape_service,
            layout=layout,
        )

        # Apply GSD-specific enhancements
        cls._add_phase_gates(canvas)
        cls._highlight_phase_manager(canvas)
        cls._add_quality_threshold_indicator(canvas)

        return canvas

    @classmethod
    def _add_phase_gates(cls, canvas: StarterCanvas) -> None:
        """Add visual phase gate indicators to the canvas.

        GSD uses quality gates between phases to ensure standards.
        """
        from packages.domain.starter_canvas import CanvasNode, CanvasNodeType

        phases = ["Research", "Design", "Implement", "Test", "Deploy", "Validate"]
        y_position = 550  # Below the phase pipeline

        for i, phase in enumerate(phases):
            if i < len(phases) - 1:  # Add gate after each phase except last
                gate = CanvasNode(
                    id=f"gsd_gate_{phase.lower()}",
                    node_type=CanvasNodeType.TEMPLATE,
                    label=f"✓ {phase} Gate",
                    x=200 + (i * 300),
                    y=y_position,
                    width=100,
                    height=40,
                    metadata={
                        "gate_type": "quality_gate",
                        "phase": phase,
                        "primary_color": cls.PHASE_COLORS.get(phase.lower(), "#6b7280"),
                        "icon": "ShieldCheck",
                        "tooltip": f"Quality gate for {phase} phase",
                    },
                )
                canvas.nodes.append(gate)

    @classmethod
    def _highlight_phase_manager(cls, canvas: StarterCanvas) -> None:
        """Highlight the Phase Manager as the central orchestrator.

        The Phase Manager is the key coordinator for GSD's phase-based approach.
        """
        for node in canvas.nodes:
            if "phase_manager" in node.id:
                node.metadata["is_phase_orchestrator"] = True
                node.metadata["orchestration_scope"] = "6_phase_pipeline"
                node.metadata["special_capability"] = "gate_management"
                node.metadata["border_width"] = 3
                node.metadata["glow_effect"] = True

    @classmethod
    def _add_quality_threshold_indicator(cls, canvas: StarterCanvas) -> None:
        """Add a quality threshold indicator to the canvas.

        Shows the configured quality threshold for phase transitions.
        """
        from packages.domain.starter_canvas import CanvasNode, CanvasNodeType

        threshold_node = CanvasNode(
            id="gsd_quality_threshold",
            node_type=CanvasNodeType.TEMPLATE,
            label="Quality Threshold: 85%",
            x=50,
            y=150,
            width=150,
            height=40,
            metadata={
                "indicator_type": "quality_threshold",
                "threshold_value": 0.85,
                "primary_color": "#f59e0b",
                "icon": "Target",
                "tooltip": "Minimum quality score required for phase transitions",
            },
        )
        canvas.nodes.append(threshold_node)
