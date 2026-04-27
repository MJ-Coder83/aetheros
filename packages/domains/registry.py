"""Planning Domain Registry — Registration and discovery for planning domains.

This module provides registration and discovery capabilities for the
Gastown, GSD, BMAD, and Planning Super domains within the InkosAI
DomainRegistry.
"""

from __future__ import annotations

from packages.domains.constants import PlanningDomainType
from packages.domains.factory import PlanningDomainFactory
from packages.prime.introspection import DomainDescriptor, DomainRegistry
from packages.tape.service import TapeService


class PlanningDomainRegistry:
    """Registry for InkosAI Planning Domains.

    Provides registration, discovery, and management of the three
    official planning domains and the Planning Super Domain.

    Usage::

        registry = PlanningDomainRegistry(tape_service)
        await registry.register_all()

        # Later
        domains = await registry.list_planning_domains()
    """

    def __init__(self, tape_service: TapeService) -> None:
        """Initialize the planning domain registry.

        Args:
            tape_service: Service for logging to Tape
        """
        self._tape = tape_service

    async def register_domain(
        self,
        domain_type: PlanningDomainType,
        domain_registry: DomainRegistry,
    ) -> str:
        """Register a single planning domain.

        Args:
            domain_type: The type of planning domain to register
            domain_registry: The InkosAI DomainRegistry to register with

        Returns:
            The registered domain ID
        """
        blueprint = PlanningDomainFactory.create_blueprint(domain_type)

        descriptor = DomainDescriptor(
            domain_id=blueprint.domain_id,
            name=blueprint.domain_name,
            description=blueprint.description,
            agent_count=len(blueprint.agents),
        )

        # Register with the domain registry
        domain_registry.register(descriptor)

        # Log to Tape
        await self._tape.log_event(
            event_type="planning_domain.registered",
            agent_id="planning_domain_registry",
            payload={
                "domain_type": domain_type.value,
                "domain_id": descriptor.domain_id,
                "domain_name": blueprint.domain_name,
            },
        )

        return descriptor.domain_id

    async def register_all(
        self,
        domain_registry: DomainRegistry,
    ) -> dict[PlanningDomainType, str]:
        """Register all planning domains.

        Args:
            domain_registry: The InkosAI DomainRegistry to register with

        Returns:
            Dictionary mapping domain types to their registered IDs
        """
        results = {}
        for domain_type in PlanningDomainType:
            domain_id = await self.register_domain(domain_type, domain_registry)
            results[domain_type] = domain_id

        # Log completion
        await self._tape.log_event(
            event_type="planning_domains.all_registered",
            agent_id="planning_domain_registry",
            payload={
                "registered_count": len(results),
                "domain_types": [dt.value for dt in results],
            },
        )

        return results

    async def get_domain(
        self,
        domain_type: PlanningDomainType,
        domain_registry: DomainRegistry,
    ) -> DomainDescriptor | None:
        """Get a registered planning domain.

        Args:
            domain_type: The type of planning domain
            domain_registry: The InkosAI DomainRegistry

        Returns:
            DomainDescriptor or None if not found
        """
        blueprint = PlanningDomainFactory.create_blueprint(domain_type)
        return domain_registry.get_domain(blueprint.domain_id)

    async def list_domains(
        self,
        domain_registry: DomainRegistry,
    ) -> list[DomainDescriptor]:
        """List all registered planning domains.

        Args:
            domain_registry: The InkosAI DomainRegistry

        Returns:
            List of DomainDescriptor objects
        """
        domains = []
        for domain_type in PlanningDomainType:
            domain_info = await self.get_domain(domain_type, domain_registry)
            if domain_info:
                domains.append(domain_info)
        return domains

    async def is_registered(
        self,
        domain_type: PlanningDomainType,
        domain_registry: DomainRegistry,
    ) -> bool:
        """Check if a planning domain is registered.

        Args:
            domain_type: The type of planning domain
            domain_registry: The InkosAI DomainRegistry

        Returns:
            True if registered, False otherwise
        """
        blueprint = PlanningDomainFactory.create_blueprint(domain_type)
        return domain_registry.get_domain(blueprint.domain_id) is not None

    async def unregister_domain(
        self,
        domain_type: PlanningDomainType,
        domain_registry: DomainRegistry,
    ) -> bool:
        """Unregister a planning domain.

        Args:
            domain_type: The type of planning domain
            domain_registry: The InkosAI DomainRegistry

        Returns:
            True if unregistered, False if not found
        """
        blueprint = PlanningDomainFactory.create_blueprint(domain_type)
        domain_registry.unregister(blueprint.domain_id)

        await self._tape.log_event(
            event_type="planning_domain.unregistered",
            agent_id="planning_domain_registry",
            payload={
                "domain_type": domain_type.value,
                "domain_id": blueprint.domain_id,
            },
        )

        return True
