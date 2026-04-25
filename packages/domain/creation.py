"""One-Click Domain Creation Engine.

Orchestrates blueprint generation, folder-tree creation, and optional
starter-canvas generation into a single call.
"""

from __future__ import annotations

import json
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel

from packages.domain.domain_blueprint import (
    DomainBlueprint,
    DomainFolderTreeGenerator,
)
from packages.domain.starter_canvas import (
    StarterCanvas,
    StarterCanvasGenerator,
)
from packages.folder_tree import FolderTree
from packages.prime.domain_creation import (
    CreationMode,
    DomainCreationEngine,
)
from packages.prime.introspection import DomainDescriptor, PrimeIntrospector
from packages.prime.proposals import ProposalEngine
from packages.tape.service import TapeService


class DomainCreationOption(StrEnum):
    DOMAIN_ONLY = "domain_only"
    DOMAIN_WITH_STARTER_CANVAS = "domain_with_starter_canvas"


class OneClickDomainCreationResult(BaseModel):
    """Result of a one-click domain creation attempt."""

    blueprint: DomainBlueprint
    folder_tree: FolderTree | None = None
    starter_canvas: StarterCanvas | None = None
    canvas_id: str | None = None  # Explicit canvas ID for frontend convenience
    proposal_id: UUID | None = None
    registered: bool = False
    domain: DomainDescriptor | None = None
    message: str = ""


class OneClickDomainCreationEngine:

    def __init__(
        self,
        tape_service: TapeService,
        introspector: PrimeIntrospector | None = None,
        proposal_engine: ProposalEngine | None = None,
        base_engine: DomainCreationEngine | None = None,
    ) -> None:
        self._tape = tape_service
        self._proposal_engine = proposal_engine
        self._base_engine = base_engine or DomainCreationEngine(
            tape_service=tape_service,
            introspector=introspector,
            proposal_engine=proposal_engine,
        )
        self._folder_tree_generator = DomainFolderTreeGenerator(
            tape_service=tape_service,
        )
        self._canvas_generator = StarterCanvasGenerator(
            tape_service=tape_service,
        )

    async def create_domain_from_description(
        self,
        description: str,
        domain_name: str | None = None,
        creation_option: DomainCreationOption = DomainCreationOption.DOMAIN_ONLY,
        creation_mode: CreationMode = CreationMode.HUMAN_GUIDED,
        created_by: str = "prime",
    ) -> OneClickDomainCreationResult:
        """Create a domain from a natural language description.

        Generates a blueprint, produces the canonical folder tree, and
        optionally generates a starter canvas.  The blueprint is then
        submitted as a Proposal for approval.

        Raises
        ------
        ValueError
            If the description is empty.
        BlueprintValidationError
            If the generated blueprint fails validation.
        """
        if not description.strip():
            raise ValueError("Domain description cannot be empty")

        base_result = await self._base_engine.create_domain_from_description(
            description=description,
            domain_name=domain_name,
            creation_mode=creation_mode,
            created_by=created_by,
        )
        blueprint = base_result.blueprint

        folder_tree_id = blueprint.domain_id

        starter_canvas = None
        if creation_option == DomainCreationOption.DOMAIN_WITH_STARTER_CANVAS:
            starter_canvas = await self._canvas_generator.generate(
                blueprint, folder_tree_id=folder_tree_id,
            )

        folder_tree = await self._folder_tree_generator.generate(
            blueprint,
            starter_canvas=starter_canvas,
        )

        if starter_canvas is not None and starter_canvas.folder_tree_id is None:
            starter_canvas.folder_tree_id = folder_tree.domain_id
            await self._update_canvas_json_in_tree(folder_tree, starter_canvas)

        if starter_canvas is not None:
            await self._tape.log_event(
                event_type="canvas.linked_to_folder_tree",
                payload={
                    "canvas_id": str(starter_canvas.id),
                    "domain_id": starter_canvas.domain_id,
                    "folder_tree_id": folder_tree.domain_id,
                },
                agent_id="one-click-domain-creation-engine",
            )

        starter_canvas_id: str | None = None
        if starter_canvas is not None:
            starter_canvas_id = str(starter_canvas.id)

        await self._tape.log_event(
            event_type="domain.one_click_created",
            payload={
                "blueprint_id": str(blueprint.id),
                "domain_id": blueprint.domain_id,
                "domain_name": blueprint.domain_name,
                "creation_option": creation_option.value,
                "starter_canvas_generated": starter_canvas is not None,
                "starter_canvas_id": starter_canvas_id,
                "folder_tree_node_count": len(folder_tree.nodes),
                "canvas_linked_to_folder_tree": (
                    starter_canvas is not None
                    and starter_canvas.folder_tree_id is not None
                ),
                "proposal_id": (
                    str(base_result.proposal_id)
                    if base_result.proposal_id else None
                ),
                "created_by": created_by,
            },
            agent_id="one-click-domain-creation-engine",
        )

        return OneClickDomainCreationResult(
            blueprint=blueprint,
            folder_tree=folder_tree,
            starter_canvas=starter_canvas,
            canvas_id=starter_canvas_id,
            proposal_id=base_result.proposal_id,
            message=(
                "Domain blueprint generated with folder tree. "
                + (
                    "Starter canvas included. "
                    if starter_canvas else ""
                )
                + "Awaiting approval before registration."
            ),
        )

    async def generate_blueprint_only(
        self,
        description: str,
        domain_name: str | None = None,
        creation_mode: CreationMode = CreationMode.HUMAN_GUIDED,
        created_by: str = "prime",
    ) -> DomainBlueprint:
        return await self._base_engine.generate_domain_blueprint(
            description=description,
            domain_name=domain_name,
            creation_mode=creation_mode,
            created_by=created_by,
        )

    async def generate_folder_tree(
        self,
        blueprint: DomainBlueprint,
    ) -> FolderTree:
        return await self._folder_tree_generator.generate(blueprint)

    async def generate_starter_canvas(
        self,
        blueprint: DomainBlueprint,
        folder_tree_id: str | None = None,
    ) -> StarterCanvas:
        return await self._canvas_generator.generate(
            blueprint, folder_tree_id=folder_tree_id,
        )

    async def register_domain(
        self,
        blueprint_id: UUID,
        reviewer: str | None = None,
    ) -> DomainDescriptor:
        return await self._base_engine.register_domain(
            blueprint_id=blueprint_id,
            reviewer=reviewer,
        )

    @staticmethod
    async def _update_canvas_json_in_tree(
        folder_tree: FolderTree,
        starter_canvas: StarterCanvas,
    ) -> None:
        canvas_json_key = next(
            (k for k in folder_tree.nodes if k.endswith("canvas.json")),
            None,
        )
        if canvas_json_key is None:
            return
        canvas_json_node = folder_tree.nodes[canvas_json_key]
        data = json.loads(canvas_json_node.content)
        data["folder_tree_id"] = starter_canvas.folder_tree_id
        canvas_json_node.content = json.dumps(data, indent=2)
