"""Planning Domain Factory — One-click creation for planning domains.

This module provides a unified factory for creating all planning domains
(Gastown, GSD, BMAD) and the Planning Super Domain.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from packages.domain.domain_blueprint import DomainFolderTreeGenerator
from packages.domains.bmad.blueprint import BMADDomainBlueprint
from packages.domains.constants import PlanningDomainType
from packages.domains.gastown.blueprint import GastownDomainBlueprint
from packages.domains.gsd.blueprint import GSDDomainBlueprint
from packages.domains.super_domain.blueprint import PlanningSuperDomainBlueprint
from packages.tape.service import TapeService

if TYPE_CHECKING:
    from packages.folder_tree import FolderTree
    from packages.prime.domain_creation import DomainBlueprint


class PlanningDomainFactory:
    """Factory for creating planning domains.

    Usage::

        # Create individual domains
        gastown_blueprint = PlanningDomainFactory.create_blueprint(
            PlanningDomainType.GASTOWN
        )

        # Create the Planning Super Domain
        super_blueprint = PlanningDomainFactory.create_blueprint(
            PlanningDomainType.SUPER
        )

        # Generate folder trees
        generator = DomainFolderTreeGenerator(tape_service)
        gastown_tree = await generator.generate(gastown_blueprint)
    """

    _BLUEPRINT_MAP: dict[PlanningDomainType, type] = {
        PlanningDomainType.GASTOWN: GastownDomainBlueprint,
        PlanningDomainType.GSD: GSDDomainBlueprint,
        PlanningDomainType.BMAD: BMADDomainBlueprint,
        PlanningDomainType.SUPER: PlanningSuperDomainBlueprint,
    }

    @classmethod
    def create_blueprint(
        cls,
        domain_type: PlanningDomainType,
    ) -> DomainBlueprint:
        """Create a domain blueprint for the specified type.

        Args:
            domain_type: The type of planning domain to create

        Returns:
            A DomainBlueprint ready for folder tree generation

        Raises:
            ValueError: If the domain type is not recognized
        """
        blueprint_class = cls._BLUEPRINT_MAP.get(domain_type)
        if not blueprint_class:
            raise ValueError(f"Unknown planning domain type: {domain_type}")

        return blueprint_class.create()

    @classmethod
    async def create_domain(
        cls,
        domain_type: PlanningDomainType,
        tape_service: TapeService,
    ) -> FolderTree:
        """Create a complete domain with folder tree.

        Args:
            domain_type: The type of planning domain to create
            tape_service: Tape service for logging

        Returns:
            The generated FolderTree
        """
        blueprint = cls.create_blueprint(domain_type)
        generator = DomainFolderTreeGenerator(tape_service)
        return await generator.generate(blueprint)

    @classmethod
    async def create_all_domains(
        cls,
        tape_service: TapeService,
    ) -> dict[PlanningDomainType, FolderTree]:
        """Create all planning domains.

        Args:
            tape_service: Tape service for logging

        Returns:
            Dictionary mapping domain types to their folder trees
        """
        results = {}
        for domain_type in PlanningDomainType:
            if domain_type != PlanningDomainType.SUPER:  # Skip super in all_domains
                results[domain_type] = await cls.create_domain(
                    domain_type, tape_service
                )
        return results

    @classmethod
    async def create_planning_super_domain(
        cls,
        tape_service: TapeService,
    ) -> FolderTree:
        """Create the Planning Super Domain.

        This is a convenience method that also creates the underlying
        domains if they don't exist.

        Args:
            tape_service: Tape service for logging

        Returns:
            The generated FolderTree for the super domain
        """
        # Create the three base domains first
        await cls.create_domain(PlanningDomainType.GASTOWN, tape_service)
        await cls.create_domain(PlanningDomainType.GSD, tape_service)
        await cls.create_domain(PlanningDomainType.BMAD, tape_service)

        # Then create the super domain
        return await cls.create_domain(PlanningDomainType.SUPER, tape_service)

    @classmethod
    def get_domain_info(cls, domain_type: PlanningDomainType) -> dict:
        """Get information about a planning domain type.

        Args:
            domain_type: The type of planning domain

        Returns:
            Dictionary with domain metadata
        """
        blueprint = cls.create_blueprint(domain_type)
        return {
            "id": blueprint.domain_id,
            "name": blueprint.domain_name,
            "description": blueprint.description,
            "agent_count": len(blueprint.agents),
            "skill_count": len(blueprint.skills),
            "workflow_count": len(blueprint.workflows),
            "max_agents": blueprint.config.max_agents,
            "requires_approval": blueprint.config.requires_human_approval,
        }

    @classmethod
    def list_all_domain_info(cls) -> dict[PlanningDomainType, dict]:
        """Get information about all planning domains.

        Returns:
            Dictionary mapping domain types to their metadata
        """
        return {
            domain_type: cls.get_domain_info(domain_type)
            for domain_type in PlanningDomainType
        }
