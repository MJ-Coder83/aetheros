"""Domain Canvas Service — high-level operations for canvas creation from domains.

This module provides convenience methods for creating canvases from domain
blueprints with automatic folder-tree synchronization.
"""

from __future__ import annotations

from packages.canvas.core import Canvas, CanvasLayout
from packages.canvas.core import CanvasService as CoreCanvasService
from packages.domain.domain_blueprint import DomainBlueprint, DomainFolderTreeGenerator
from packages.folder_tree import FolderTreeService
from packages.tape.service import TapeService


class CanvasDomainService(CoreCanvasService):
    """Extended canvas service with domain-aware creation methods.

    This service wraps the core CanvasService and adds convenience methods
    for creating canvases from domain blueprints with automatic folder-tree
    synchronization.

    All operations are logged to the Tape for full auditability.
    """

    def __init__(
        self,
        tape_service: TapeService,
        folder_tree_service: FolderTreeService | None = None,
        store: type(CoreCanvasService._store) | None = None,  # type: ignore
        layout_engine: type(CoreCanvasService._layout_engine) | None = None,  # type: ignore
    ) -> None:
        """Initialize the canvas domain service.

        Parameters
        ----------
        tape_service : TapeService
            Shared tape service for audit logging.
        folder_tree_service : FolderTreeService | None
            Optional folder tree service for synchronization.
        store : CanvasStore | None
            Optional backing store. Defaults to new CanvasStore.
        layout_engine : LayoutEngine | None
            Optional layout engine. Defaults to new LayoutEngine.
        """
        super().__init__(
            tape_service=tape_service,
            folder_tree_service=folder_tree_service,
            store=store,
            layout_engine=layout_engine,
        )

    async def create_canvas_from_domain(
        self,
        blueprint: DomainBlueprint,
        layout: CanvasLayout = CanvasLayout.SMART,
        sync_to_tree: bool = True,
    ) -> Canvas:
        """Create a canvas from a domain blueprint with folder-tree sync.

        This method creates a fully-populated canvas from a domain blueprint,
        applies the requested layout, and optionally synchronizes the canvas
        nodes to the folder tree (creating corresponding directories).

        Parameters
        ----------
        blueprint : DomainBlueprint
            The domain blueprint to visualize as a canvas.
        layout : CanvasLayout, optional
            Layout strategy to apply. Defaults to SMART.
        sync_to_tree : bool, optional
            If True (default) and a FolderTreeService is configured,
            creates corresponding directories in the folder tree.

        Returns
        -------
        Canvas
            The newly created canvas with positioned nodes and edges.
        """
        # Create the canvas using the core method (sync_to_tree=False here, we handle below)
        canvas = await self.canvas_from_domain_blueprint(blueprint, layout=layout, sync_to_tree=False)

        # Sync to folder tree if requested and service is available
        if sync_to_tree and self._folder_tree is not None:
            await self.sync_to_folder_tree(canvas.domain_id)

        return canvas

    async def create_canvas_from_domain_with_tree(
        self,
        blueprint: DomainBlueprint,
        layout: CanvasLayout = CanvasLayout.SMART,
    ) -> tuple[Canvas, bool]:
        """Create a canvas and ensure folder tree exists and is synced.

        This is a convenience method that creates a canvas from a blueprint
        and ensures the folder tree is created (if it doesn't exist) and
        synchronized with the canvas nodes.

        Parameters
        ----------
        blueprint : DomainBlueprint
            The domain blueprint to visualize.
        layout : CanvasLayout, optional
            Layout strategy to apply. Defaults to SMART.

        Returns
        -------
        tuple[Canvas, bool]
            The created canvas and a boolean indicating whether the
            folder tree was newly created (True) or already existed (False).
        """
        # Create the canvas
        canvas = await self.create_canvas_from_domain(blueprint, layout=layout, sync_to_tree=True)

        # Check if folder tree already existed
        tree_existed = True
        if self._folder_tree is not None:
            try:
                await self._folder_tree.get_tree(blueprint.domain_id)
            except Exception:
                tree_existed = False
                # Create the folder tree from blueprint
                generator = DomainFolderTreeGenerator(self._tape)
                folder_tree = await generator.generate(blueprint)
                self._folder_tree._store.add(folder_tree)

        return canvas, tree_existed
