"""One-Click Domain Creation Engine.

Orchestrates blueprint generation, folder-tree creation, and optional
starter-canvas generation into a single call.
"""

from __future__ import annotations

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
    blueprint: DomainBlueprint
    folder_tree: FolderTree | None = None
    starter_canvas: StarterCanvas | None = None
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

        folder_tree = await self._folder_tree_generator.generate(blueprint)

        starter_canvas = None
        if creation_option == DomainCreationOption.DOMAIN_WITH_STARTER_CANVAS:
            starter_canvas = await self._canvas_generator.generate(blueprint)

        await self._tape.log_event(
            event_type="domain.one_click_created",
            payload={
                "blueprint_id": str(blueprint.id),
                "domain_id": blueprint.domain_id,
                "domain_name": blueprint.domain_name,
                "creation_option": creation_option.value,
                "starter_canvas_generated": starter_canvas is not None,
                "folder_tree_node_count": len(folder_tree.nodes),
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
    ) -> StarterCanvas:
        return await self._canvas_generator.generate(blueprint)

    async def register_domain(
        self,
        blueprint_id: UUID,
        reviewer: str | None = None,
    ) -> DomainDescriptor:
        return await self._base_engine.register_domain(
            blueprint_id=blueprint_id,
            reviewer=reviewer,
        )
