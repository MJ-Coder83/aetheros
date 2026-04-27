"""Base class for Planning Domain Starter Canvases.

Extends the standard StarterCanvasGenerator with planning-specific
visual styling and methodology tagging.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from packages.domain.starter_canvas import (
    CanvasLayout,
    CanvasNode,
    CanvasNodeType,
    StarterCanvas,
    StarterCanvasGenerator,
)
from packages.domains.constants import (
    PlanningDomainType,
    DOMAIN_VISUAL_STYLES,
)
from packages.tape.service import TapeService

if TYPE_CHECKING:
    from packages.prime.domain_creation import DomainBlueprint


class PlanningStarterCanvasBase:
    """Base class for generating planning domain starter canvases.

    Provides methodology-specific visual styling:
    - Domain-specific colors from DOMAIN_VISUAL_STYLES
    - Methodology tags on nodes
    - Dual-mode (Visual + Folder) support indicators
    - Swarm mode buttons (Quick Swarm + Governed Swarm)

    Usage::

        canvas = await PlanningStarterCanvasBase.generate(
            blueprint=gastown_blueprint,
            domain_type=PlanningDomainType.GASTOWN,
            tape_service=tape_svc,
        )
    """

    @classmethod
    async def generate(
        cls,
        blueprint: DomainBlueprint,
        domain_type: PlanningDomainType,
        tape_service: TapeService,
        layout: CanvasLayout = CanvasLayout.CLUSTERED,
    ) -> StarterCanvas:
        """Generate a starter canvas with planning-specific styling.

        Args:
            blueprint: The domain blueprint to visualize
            domain_type: The type of planning domain (for styling)
            tape_service: Service for logging canvas creation
            layout: Layout strategy (defaults to CLUSTERED for planning domains)

        Returns:
            A StarterCanvas with methodology-specific visual styling
        """
        # Use the standard generator for base layout
        generator = StarterCanvasGenerator(tape_service=tape_service)
        canvas = await generator.generate(blueprint, layout=layout)

        # Apply planning-specific styling
        cls._apply_methodology_styling(canvas, domain_type)
        cls._add_swarm_buttons(canvas, domain_type)
        cls._add_dual_mode_indicators(canvas)

        return canvas

    @classmethod
    def _apply_methodology_styling(
        cls,
        canvas: StarterCanvas,
        domain_type: PlanningDomainType,
    ) -> None:
        """Apply domain-specific colors and icons to canvas nodes."""
        style = DOMAIN_VISUAL_STYLES.get(domain_type, {})
        primary_color = style.get("primary_color", "#6366f1")
        secondary_color = style.get("secondary_color", "#818cf8")
        icon = style.get("icon", "LayoutGrid")

        for node in canvas.nodes:
            # Add methodology color to node metadata
            if node.node_type == CanvasNodeType.DOMAIN:
                node.metadata["primary_color"] = primary_color
                node.metadata["secondary_color"] = secondary_color
                node.metadata["methodology_icon"] = icon
                node.metadata["methodology_tag"] = domain_type.value
            elif node.node_type == CanvasNodeType.AGENT:
                node.metadata["border_color"] = primary_color
                node.metadata["methodology_tag"] = domain_type.value
            elif node.node_type == CanvasNodeType.SKILL:
                node.metadata["accent_color"] = secondary_color
                node.metadata["methodology_tag"] = domain_type.value
            elif node.node_type == CanvasNodeType.WORKFLOW:
                node.metadata["highlight_color"] = primary_color
                node.metadata["methodology_tag"] = domain_type.value

    @classmethod
    def _add_swarm_buttons(
        cls,
        canvas: StarterCanvas,
        domain_type: PlanningDomainType,
    ) -> None:
        """Add Quick Swarm and Governed Swarm buttons to the canvas."""
        # Find the rightmost position for swarm buttons
        max_x = max((n.x for n in canvas.nodes), default=0)
        max_y = max((n.y for n in canvas.nodes), default=0)

        # Quick Swarm button
        quick_swarm = CanvasNode(
            id=f"{domain_type.value}_quick_swarm",
            node_type=CanvasNodeType.TEMPLATE,
            label="Quick Swarm",
            x=max_x + 300,
            y=max_y - 100,
            width=140,
            height=50,
            metadata={
                "button_type": "quick_swarm",
                "primary_color": "#22c55e",  # Green for quick
                "icon": "Zap",
                "tooltip": "Start a quick swarm with this domain's agents",
                "methodology_tag": domain_type.value,
            },
        )

        # Governed Swarm button
        governed_swarm = CanvasNode(
            id=f"{domain_type.value}_governed_swarm",
            node_type=CanvasNodeType.TEMPLATE,
            label="Governed Swarm",
            x=max_x + 300,
            y=max_y + 20,
            width=140,
            height=50,
            metadata={
                "button_type": "governed_swarm",
                "primary_color": "#3b82f6",  # Blue for governed
                "icon": "Shield",
                "tooltip": "Start a governed swarm with full audit trail",
                "methodology_tag": domain_type.value,
            },
        )

        canvas.nodes.append(quick_swarm)
        canvas.nodes.append(governed_swarm)

    @classmethod
    def _add_dual_mode_indicators(cls, canvas: StarterCanvas) -> None:
        """Add folder-tree indicators for dual-mode support."""
        folder_tree_indicator = CanvasNode(
            id="folder_tree_indicator",
            node_type=CanvasNodeType.TEMPLATE,
            label="📁 Folder Mode",
            x=50,
            y=50,
            width=120,
            height=40,
            metadata={
                "indicator_type": "dual_mode",
                "tooltip": "Click to toggle between Visual and Folder modes",
                "primary_color": "#64748b",
                "icon": "FolderTree",
            },
        )

        canvas.nodes.insert(0, folder_tree_indicator)
