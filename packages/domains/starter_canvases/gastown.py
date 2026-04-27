"""Gastown Domain Starter Canvas.

Provides a pre-configured visual canvas for the Gastown multi-agent
workspace orchestration domain.
"""

from __future__ import annotations

from packages.domain.starter_canvas import CanvasLayout, StarterCanvas
from packages.domains.constants import PlanningDomainType
from packages.domains.gastown.blueprint import GastownDomainBlueprint
from packages.domains.starter_canvases.base import PlanningStarterCanvasBase
from packages.tape.service import TapeService


class GastownStarterCanvas:
    """Starter canvas generator for the Gastown domain.

    Creates a visual layout with:
    - 5 specialized agents arranged in a hub-and-spoke pattern
    - Domain-specific indigo color scheme
    - Workspace Manager as the central hub
    - Agent Coordinator, Session Manager, Resource Allocator, Task Distributor as nodes
    - Quick Swarm and Governed Swarm buttons
    - Folder-tree dual mode indicator

    Usage::

        from packages.domains.starter_canvases.gastown import GastownStarterCanvas
        from packages.tape.service import TapeService

        tape_svc = TapeService(...)
        canvas = GastownStarterCanvas.generate(tape_svc)

        # Access canvas properties
        print(f"Generated {canvas.node_count} nodes")
        print(f"Canvas layout: {canvas.layout}")
    """

    # Gastown visual styling
    PRIMARY_COLOR = "#6366f1"  # Indigo
    SECONDARY_COLOR = "#818cf8"  # Light indigo
    ACCENT_COLOR = "#4f46e5"  # Dark indigo
    ICON = "LayoutGrid"

    @classmethod
    async def generate(
        cls,
        tape_service: TapeService,
        layout: CanvasLayout = CanvasLayout.HUB_AND_SPOKE,
    ) -> StarterCanvas:
        """Generate a starter canvas for the Gastown domain.

        Args:
            tape_service: Service for logging canvas creation
            layout: Layout strategy (defaults to HUB_AND_SPOKE for Gastown's hub topology)

        Returns:
            A StarterCanvas with Gastown-specific visual styling

        Example::

            canvas = GastownStarterCanvas.generate(tape_service)

            # Access nodes
            for node in canvas.nodes:
                print(f"{node.label}: ({node.x}, {node.y})")
        """
        blueprint = GastownDomainBlueprint.create()

        canvas = PlanningStarterCanvasBase.generate(
            blueprint=blueprint,
            domain_type=PlanningDomainType.GASTOWN,
            tape_service=tape_service,
            layout=layout,
        )

        # Apply Gastown-specific enhancements
        cls._enhance_hub_layout(canvas)
        cls._add_workspace_manager_privileges(canvas)

        return canvas

    @classmethod
    def _enhance_hub_layout(cls, canvas: StarterCanvas) -> None:
        """Enhance the hub-and-spoke layout for better visual balance.

        Ensures Workspace Manager is centered with proper spacing to
        connected agents.
        """
        # Find the Workspace Manager node
        workspace_manager = None
        for node in canvas.nodes:
            if "workspace_manager" in node.id:
                workspace_manager = node
                break

        if workspace_manager:
            # Ensure it's centered
            workspace_manager.x = 400
            workspace_manager.y = 300

            # Update metadata
            workspace_manager.metadata["is_central_hub"] = True
            workspace_manager.metadata["hub_type"] = "workspace_orchestration"

    @classmethod
    def _add_workspace_manager_privileges(cls, canvas: StarterCanvas) -> None:
        """Add special metadata indicating Workspace Manager privileges.

        The Workspace Manager has unique capabilities in Gastown:
        - Can initialize and teardown workspaces
        - Manages persistent state
        - Coordinates session recovery
        """
        for node in canvas.nodes:
            if "workspace_manager" in node.id:
                node.metadata["special_privileges"] = [
                    "workspace_initialization",
                    "workspace_teardown",
                    "persistent_state_management",
                    "session_recovery",
                ]
                node.metadata["permission_level"] = "admin"
                node.metadata["scope"] = "workspace"
