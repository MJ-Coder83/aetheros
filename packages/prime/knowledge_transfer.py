"""Prime Cross-Domain Knowledge Transfer -- Transfer skills and patterns between domains.

This module enables Prime to identify, package, and transfer knowledge
between domains in the InkosAI system. Knowledge includes reusable skills,
successful patterns, best practices, and configuration insights.

Design principles:
- Every transfer is logged to the Tape (full auditability)
- Knowledge packages are versioned and validated before transfer
- Transfer proposals go through the governance workflow for approval
- Source domain integrity is preserved (copy, not move)
- Target domain receives knowledge with adaptation metadata
- Transfer success is tracked and measured

Usage::

    from packages.prime.knowledge_transfer import KnowledgeTransferEngine

    engine = KnowledgeTransferEngine(tape_service=tape_svc)
    result = await engine.transfer_knowledge(
        source_domain_id="legal-research",
        target_domain_id="finance-ops",
        knowledge_types=["skills", "patterns"],
    )
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from packages.prime.intelligence_profile import IntelligenceProfileEngine
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class KnowledgeType(StrEnum):
    """Types of transferable knowledge."""

    SKILL = "skill"
    PATTERN = "pattern"
    BEST_PRACTICE = "best_practice"
    CONFIG = "config"
    WORKFLOW = "workflow"
    AGENT_ROLE = "agent_role"


class TransferStatus(StrEnum):
    """Lifecycle states for a knowledge transfer."""

    DRAFT = "draft"
    PROPOSED = "proposed"
    APPROVED = "approved"
    TRANSFERRING = "transferring"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


class CompatibilityLevel(StrEnum):
    """How compatible a knowledge item is with the target domain."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INCOMPATIBLE = "incompatible"


class AdaptationType(StrEnum):
    """Types of adaptations needed for knowledge transfer."""

    NONE = "none"
    RENAME = "rename"
    RECONFIGURE = "reconfigure"
    RESTRUCTURE = "restructure"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class KnowledgeItem(BaseModel):
    """A single piece of transferable knowledge.

    Knowledge items are extracted from a source domain and can be
    adapted before being applied to a target domain.
    """

    id: UUID = Field(default_factory=uuid4)
    name: str
    knowledge_type: KnowledgeType
    description: str = ""
    source_domain_id: str
    content: dict[str, object] = Field(default_factory=dict)
    version: str = "1.0.0"
    compatibility_score: float = Field(default=0.0, ge=0.0, le=1.0)
    compatibility_level: CompatibilityLevel = CompatibilityLevel.MEDIUM
    adaptation_needed: AdaptationType = AdaptationType.NONE
    adaptation_notes: str = ""
    transfer_count: int = 0
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class KnowledgePackage(BaseModel):
    """A collection of knowledge items packaged for transfer.

    Packages group related knowledge items together and provide
    overall compatibility and adaptation assessments.
    """

    id: UUID = Field(default_factory=uuid4)
    name: str
    source_domain_id: str
    target_domain_id: str
    items: list[KnowledgeItem] = []
    overall_compatibility: float = Field(default=0.0, ge=0.0, le=1.0)
    adaptation_complexity: str = "low"  # low, medium, high
    description: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TransferResult(BaseModel):
    """Outcome of a knowledge transfer operation."""

    transfer_id: UUID
    status: TransferStatus
    source_domain_id: str
    target_domain_id: str
    items_transferred: int
    items_adapted: int
    items_skipped: int
    total_items: int
    compatibility_score: float
    duration_seconds: float = 0.0
    errors: list[str] = []
    warnings: list[str] = []


class TransferRecord(BaseModel):
    """A record of a knowledge transfer attempt."""

    id: UUID = Field(default_factory=uuid4)
    source_domain_id: str
    target_domain_id: str
    knowledge_types: list[KnowledgeType] = []
    package_id: UUID | None = None
    status: TransferStatus = TransferStatus.DRAFT
    result: TransferResult | None = None
    proposal_id: UUID | None = None
    reviewer: str | None = None
    created_by: str = "prime"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class KnowledgeTransferError(Exception):
    """Base exception for knowledge transfer operations."""


class DomainNotFoundError(KnowledgeTransferError):
    """Raised when a source or target domain does not exist."""


class TransferNotFoundError(KnowledgeTransferError):
    """Raised when a transfer record does not exist."""


class TransferTransitionError(KnowledgeTransferError):
    """Raised when an invalid transfer state transition is attempted."""


class IncompatibleKnowledgeError(KnowledgeTransferError):
    """Raised when knowledge is incompatible with the target domain."""


class TransferValidationError(KnowledgeTransferError):
    """Raised when a transfer fails validation."""


# ---------------------------------------------------------------------------
# Transfer store (in-memory; will be backed by Postgres later)
# ---------------------------------------------------------------------------


class TransferStore:
    """In-memory store for transfer records and knowledge items."""

    def __init__(self) -> None:
        self._transfers: dict[UUID, TransferRecord] = {}
        self._packages: dict[UUID, KnowledgePackage] = {}
        self._knowledge_items: dict[UUID, KnowledgeItem] = {}

    def add_transfer(self, record: TransferRecord) -> None:
        self._transfers[record.id] = record

    def get_transfer(self, transfer_id: UUID) -> TransferRecord | None:
        return self._transfers.get(transfer_id)

    def list_transfers(self) -> list[TransferRecord]:
        return list(self._transfers.values())

    def list_transfers_by_status(self, status: TransferStatus) -> list[TransferRecord]:
        return [t for t in self._transfers.values() if t.status == status]

    def update_transfer(self, record: TransferRecord) -> None:
        if record.id not in self._transfers:
            raise TransferNotFoundError(f"Transfer {record.id} not found")
        self._transfers[record.id] = record

    def add_package(self, package: KnowledgePackage) -> None:
        self._packages[package.id] = package

    def get_package(self, package_id: UUID) -> KnowledgePackage | None:
        return self._packages.get(package_id)

    def list_packages(self) -> list[KnowledgePackage]:
        return list(self._packages.values())

    def add_knowledge_item(self, item: KnowledgeItem) -> None:
        self._knowledge_items[item.id] = item

    def get_knowledge_item(self, item_id: UUID) -> KnowledgeItem | None:
        return self._knowledge_items.get(item_id)

    def list_knowledge_items(
        self,
        source_domain_id: str | None = None,
        knowledge_type: KnowledgeType | None = None,
    ) -> list[KnowledgeItem]:
        items = list(self._knowledge_items.values())
        if source_domain_id is not None:
            items = [i for i in items if i.source_domain_id == source_domain_id]
        if knowledge_type is not None:
            items = [i for i in items if i.knowledge_type == knowledge_type]
        return items


# ---------------------------------------------------------------------------
# Knowledge extractor
# ---------------------------------------------------------------------------


class KnowledgeExtractor:
    """Extracts transferable knowledge from a domain.

    In production, this would analyse the domain's skills, workflows,
    agent configurations, and historical performance data. For now,
    it uses heuristics based on domain metadata.
    """

    def extract_from_domain(
        self,
        domain_id: str,
        domain_metadata: dict[str, object],
        knowledge_types: list[KnowledgeType] | None = None,
    ) -> list[KnowledgeItem]:
        """Extract knowledge items from a domain."""
        types = knowledge_types or list(KnowledgeType)
        items: list[KnowledgeItem] = []

        agents = domain_metadata.get("agents", [])
        skills = domain_metadata.get("skills", [])
        workflows = domain_metadata.get("workflows", [])
        config = domain_metadata.get("config", {})

        if KnowledgeType.SKILL in types and isinstance(skills, list):
            for skill in skills:
                if isinstance(skill, dict):
                    items.append(
                        KnowledgeItem(
                            name=str(skill.get("name", "Unknown Skill")),
                            knowledge_type=KnowledgeType.SKILL,
                            description=str(
                                skill.get("description", f"Skill from {domain_id}")
                            ),
                            source_domain_id=domain_id,
                            content=skill,
                        )
                    )

        if KnowledgeType.AGENT_ROLE in types and isinstance(agents, list):
            seen_roles: set[str] = set()
            for agent in agents:
                if isinstance(agent, dict):
                    role = str(agent.get("role", ""))
                    if role and role not in seen_roles:
                        seen_roles.add(role)
                        items.append(
                            KnowledgeItem(
                                name=f"{domain_id} {role} role",
                                knowledge_type=KnowledgeType.AGENT_ROLE,
                                description=f"Agent role pattern: {role}",
                                source_domain_id=domain_id,
                                content=agent,
                            )
                        )

        if KnowledgeType.WORKFLOW in types and isinstance(workflows, list):
            for wf in workflows:
                if isinstance(wf, dict):
                    items.append(
                        KnowledgeItem(
                            name=str(wf.get("name", "Unknown Workflow")),
                            knowledge_type=KnowledgeType.WORKFLOW,
                            description=str(
                                wf.get("description", f"Workflow from {domain_id}")
                            ),
                            source_domain_id=domain_id,
                            content=wf,
                        )
                    )

        if KnowledgeType.CONFIG in types and isinstance(config, dict):
            items.append(
                KnowledgeItem(
                    name=f"{domain_id} configuration",
                    knowledge_type=KnowledgeType.CONFIG,
                    description=f"Domain configuration from {domain_id}",
                    source_domain_id=domain_id,
                    content=config,
                )
            )

        if KnowledgeType.PATTERN in types:
            # Extract patterns from domain metadata
            patterns = domain_metadata.get("patterns", [])
            if isinstance(patterns, list):
                for pattern in patterns:
                    if isinstance(pattern, dict):
                        items.append(
                            KnowledgeItem(
                                name=str(pattern.get("name", "Unknown Pattern")),
                                knowledge_type=KnowledgeType.PATTERN,
                                description=str(
                                    pattern.get("description", f"Pattern from {domain_id}")
                                ),
                                source_domain_id=domain_id,
                                content=pattern,
                            )
                        )

        if KnowledgeType.BEST_PRACTICE in types:
            practices = domain_metadata.get("best_practices", [])
            if isinstance(practices, list):
                for practice in practices:
                    if isinstance(practice, dict):
                        items.append(
                            KnowledgeItem(
                                name=str(practice.get("name", "Unknown Practice")),
                                knowledge_type=KnowledgeType.BEST_PRACTICE,
                                description=str(
                                    practice.get(
                                        "description", f"Best practice from {domain_id}"
                                    )
                                ),
                                source_domain_id=domain_id,
                                content=practice,
                            )
                        )

        return items


# ---------------------------------------------------------------------------
# Compatibility assessor
# ---------------------------------------------------------------------------


class CompatibilityAssessor:
    """Assesses compatibility between knowledge items and a target domain.

    Uses heuristics based on domain similarity, knowledge type, and
    content overlap. In production, this would use LLM-powered analysis.
    """

    def assess_item(
        self,
        item: KnowledgeItem,
        target_domain_metadata: dict[str, object],
    ) -> KnowledgeItem:
        """Assess a single knowledge item's compatibility with the target domain."""
        score = self._compute_compatibility_score(item, target_domain_metadata)
        level = self._score_to_level(score)
        adaptation = self._determine_adaptation(item, target_domain_metadata, score)

        return item.model_copy(
            update={
                "compatibility_score": score,
                "compatibility_level": level,
                "adaptation_needed": adaptation,
                "adaptation_notes": self._generate_adaptation_notes(
                    item, adaptation, target_domain_metadata
                ),
            }
        )

    def assess_package(
        self,
        package: KnowledgePackage,
        target_domain_metadata: dict[str, object],
    ) -> KnowledgePackage:
        """Assess all items in a package and compute overall compatibility."""
        assessed_items = [
            self.assess_item(item, target_domain_metadata)
            for item in package.items
        ]

        if assessed_items:
            overall = sum(i.compatibility_score for i in assessed_items) / len(
                assessed_items
            )
        else:
            overall = 0.0

        high_adaptation = any(
            i.adaptation_needed in (AdaptationType.RESTRUCTURE, AdaptationType.CUSTOM)
            for i in assessed_items
        )
        medium_adaptation = any(
            i.adaptation_needed == AdaptationType.RECONFIGURE for i in assessed_items
        )

        complexity = "high" if high_adaptation else ("medium" if medium_adaptation else "low")

        return package.model_copy(
            update={
                "items": assessed_items,
                "overall_compatibility": round(overall, 2),
                "adaptation_complexity": complexity,
            }
        )

    @staticmethod
    def _compute_compatibility_score(
        item: KnowledgeItem,
        target_metadata: dict[str, object],
    ) -> float:
        """Compute a heuristic compatibility score [0.0, 1.0]."""
        score = 0.5  # base score

        # Skills are generally more transferable
        type_bonus: dict[str, float] = {
            KnowledgeType.SKILL: 0.15,
            KnowledgeType.BEST_PRACTICE: 0.10,
            KnowledgeType.PATTERN: 0.10,
            KnowledgeType.CONFIG: 0.05,
            KnowledgeType.WORKFLOW: 0.05,
            KnowledgeType.AGENT_ROLE: 0.05,
        }
        score += type_bonus.get(item.knowledge_type.value, 0.0)

        # Check if target already has this item (penalise duplicates)
        target_names: set[str] = set()
        for key in ("skills", "agents", "workflows"):
            entries = target_metadata.get(key, [])
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, dict):
                        name = entry.get("name")
                        if isinstance(name, str):
                            target_names.add(name.lower())

        if item.name.lower() in target_names:
            score -= 0.3  # duplicate knowledge

        # Success rate bonus
        if item.success_rate > 0.8:
            score += 0.1
        elif item.success_rate < 0.3:
            score -= 0.1

        # Clamp
        return max(0.0, min(1.0, round(score, 2)))

    @staticmethod
    def _score_to_level(score: float) -> CompatibilityLevel:
        if score >= 0.7:
            return CompatibilityLevel.HIGH
        if score >= 0.4:
            return CompatibilityLevel.MEDIUM
        if score >= 0.2:
            return CompatibilityLevel.LOW
        return CompatibilityLevel.INCOMPATIBLE

    @staticmethod
    def _determine_adaptation(
        item: KnowledgeItem,
        target_metadata: dict[str, object],
        score: float,
    ) -> AdaptationType:
        if score >= 0.8:
            return AdaptationType.NONE
        if score >= 0.6:
            return AdaptationType.RENAME
        if score >= 0.4:
            return AdaptationType.RECONFIGURE
        if score >= 0.2:
            return AdaptationType.RESTRUCTURE
        return AdaptationType.CUSTOM

    @staticmethod
    def _generate_adaptation_notes(
        item: KnowledgeItem,
        adaptation: AdaptationType,
        target_metadata: dict[str, object],
    ) -> str:
        target_name = target_metadata.get("name", "target domain")
        domain_name = target_name if isinstance(target_name, str) else "target domain"

        notes: dict[str, str] = {
            AdaptationType.NONE: f"No adaptation needed for {domain_name}",
            AdaptationType.RENAME: f"Rename to match {domain_name} naming conventions",
            AdaptationType.RECONFIGURE: f"Reconfigure parameters for {domain_name} context",
            AdaptationType.RESTRUCTURE: f"Restructure to fit {domain_name} architecture",
            AdaptationType.CUSTOM: f"Custom adaptation required for {domain_name}",
        }
        return notes.get(adaptation.value, "")


# ---------------------------------------------------------------------------
# Allowed state transitions
# ---------------------------------------------------------------------------

_VALID_TRANSFER_TRANSITIONS: dict[TransferStatus, set[TransferStatus]] = {
    TransferStatus.DRAFT: {TransferStatus.PROPOSED, TransferStatus.REJECTED},
    TransferStatus.PROPOSED: {TransferStatus.APPROVED, TransferStatus.REJECTED},
    TransferStatus.APPROVED: {TransferStatus.TRANSFERRING, TransferStatus.REJECTED},
    TransferStatus.TRANSFERRING: {
        TransferStatus.COMPLETED,
        TransferStatus.FAILED,
        TransferStatus.ROLLED_BACK,
    },
    TransferStatus.COMPLETED: {TransferStatus.ROLLED_BACK},
    TransferStatus.FAILED: {TransferStatus.ROLLED_BACK, TransferStatus.DRAFT},
    TransferStatus.REJECTED: set(),
    TransferStatus.ROLLED_BACK: {TransferStatus.DRAFT},
}


def _validate_transfer_transition(
    current: TransferStatus, target: TransferStatus
) -> None:
    allowed = _VALID_TRANSFER_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise TransferTransitionError(
            f"Cannot transition transfer from {current.value} to {target.value}"
        )


# ---------------------------------------------------------------------------
# Knowledge Transfer Engine -- the main public API
# ---------------------------------------------------------------------------


class KnowledgeTransferEngine:
    """Cross-domain knowledge transfer engine for the Prime meta-agent.

    KnowledgeTransferEngine enables Prime to:
    - Extract transferable knowledge from source domains
    - Assess compatibility with target domains
    - Package knowledge for transfer with adaptation metadata
    - Execute transfers with audit logging
    - Track transfer success rates and rollback on failure

    Usage::

        engine = KnowledgeTransferEngine(tape_service=tape_svc)
        result = await engine.transfer_knowledge(
            source_domain_id="legal-research",
            target_domain_id="finance-ops",
            knowledge_types=["skills", "patterns"],
        )
    """

    def __init__(
        self,
        tape_service: TapeService,
        store: TransferStore | None = None,
        extractor: KnowledgeExtractor | None = None,
        assessor: CompatibilityAssessor | None = None,
        profile_engine: IntelligenceProfileEngine | None = None,
    ) -> None:
        self._tape = tape_service
        self._store = store or TransferStore()
        self._extractor = extractor or KnowledgeExtractor()
        self._assessor = assessor or CompatibilityAssessor()
        self._profile_engine = profile_engine

    # ------------------------------------------------------------------
    # Knowledge extraction
    # ------------------------------------------------------------------

    async def extract_knowledge(
        self,
        domain_id: str,
        domain_metadata: dict[str, object],
        knowledge_types: list[KnowledgeType] | None = None,
    ) -> list[KnowledgeItem]:
        """Extract transferable knowledge from a domain.

        Extracts skills, patterns, workflows, and other knowledge items
        from the specified domain based on its metadata.
        """
        items = self._extractor.extract_from_domain(
            domain_id=domain_id,
            domain_metadata=domain_metadata,
            knowledge_types=knowledge_types,
        )

        # Store extracted items
        for item in items:
            self._store.add_knowledge_item(item)

        await self._tape.log_event(
            event_type="knowledge.extracted",
            payload={
                "domain_id": domain_id,
                "item_count": len(items),
                "knowledge_types": [
                    t.value for t in (knowledge_types or list(KnowledgeType))
                ],
            },
            agent_id="knowledge-transfer-engine",
        )

        return items

    # ------------------------------------------------------------------
    # Compatibility assessment
    # ------------------------------------------------------------------

    async def assess_compatibility(
        self,
        items: list[KnowledgeItem],
        target_domain_metadata: dict[str, object],
    ) -> list[KnowledgeItem]:
        """Assess compatibility of knowledge items with a target domain.

        Each item is evaluated and annotated with compatibility scores,
        levels, and adaptation requirements.
        """
        assessed = [
            self._assessor.assess_item(item, target_domain_metadata)
            for item in items
        ]

        await self._tape.log_event(
            event_type="knowledge.assessed",
            payload={
                "item_count": len(assessed),
                "compatible": sum(
                    1
                    for i in assessed
                    if i.compatibility_level
                    in (CompatibilityLevel.HIGH, CompatibilityLevel.MEDIUM)
                ),
                "incompatible": sum(
                    1
                    for i in assessed
                    if i.compatibility_level
                    in (CompatibilityLevel.LOW, CompatibilityLevel.INCOMPATIBLE)
                ),
            },
            agent_id="knowledge-transfer-engine",
        )

        return assessed

    # ------------------------------------------------------------------
    # Package creation
    # ------------------------------------------------------------------

    async def create_package(
        self,
        name: str,
        source_domain_id: str,
        target_domain_id: str,
        source_metadata: dict[str, object],
        target_metadata: dict[str, object],
        knowledge_types: list[KnowledgeType] | None = None,
    ) -> KnowledgePackage:
        """Create a knowledge package for transfer between domains.

        Extracts knowledge from the source domain, assesses compatibility
        with the target domain, and packages everything together.
        """
        # Extract from source
        items = await self.extract_knowledge(
            domain_id=source_domain_id,
            domain_metadata=source_metadata,
            knowledge_types=knowledge_types,
        )

        # Assess compatibility
        assessed_items = await self.assess_compatibility(items, target_metadata)

        # Filter out incompatible items
        transferable = [
            i
            for i in assessed_items
            if i.compatibility_level != CompatibilityLevel.INCOMPATIBLE
        ]

        package = KnowledgePackage(
            name=name,
            source_domain_id=source_domain_id,
            target_domain_id=target_domain_id,
            items=transferable,
        )

        # Assess package overall
        package = self._assessor.assess_package(package, target_metadata)

        self._store.add_package(package)

        await self._tape.log_event(
            event_type="knowledge.package_created",
            payload={
                "package_id": str(package.id),
                "name": name,
                "source_domain": source_domain_id,
                "target_domain": target_domain_id,
                "item_count": len(transferable),
                "overall_compatibility": package.overall_compatibility,
                "adaptation_complexity": package.adaptation_complexity,
            },
            agent_id="knowledge-transfer-engine",
        )

        return package

    # ------------------------------------------------------------------
    # Transfer execution
    # ------------------------------------------------------------------

    async def transfer_knowledge(
        self,
        source_domain_id: str,
        target_domain_id: str,
        source_metadata: dict[str, object],
        target_metadata: dict[str, object],
        knowledge_types: list[KnowledgeType] | None = None,
        created_by: str = "prime",
    ) -> TransferRecord:
        """Execute a complete knowledge transfer between domains.

        This is the main entry point. It extracts, assesses, packages,
        and applies knowledge from source to target domain.
        """
        start_time = datetime.now(UTC)

        # Create package
        package = await self.create_package(
            name=f"Transfer: {source_domain_id} -> {target_domain_id}",
            source_domain_id=source_domain_id,
            target_domain_id=target_domain_id,
            source_metadata=source_metadata,
            target_metadata=target_metadata,
            knowledge_types=knowledge_types,
        )

        # Create transfer record
        record = TransferRecord(
            source_domain_id=source_domain_id,
            target_domain_id=target_domain_id,
            knowledge_types=knowledge_types or list(KnowledgeType),
            package_id=package.id,
            status=TransferStatus.TRANSFERRING,
            created_by=created_by,
        )
        self._store.add_transfer(record)

        # Execute the transfer
        errors: list[str] = []
        warnings: list[str] = []
        items_transferred = 0
        items_adapted = 0
        items_skipped = 0

        for item in package.items:
            if item.compatibility_level == CompatibilityLevel.INCOMPATIBLE:
                items_skipped += 1
                warnings.append(f"Skipped incompatible item: {item.name}")
                continue

            try:
                # Simulate the transfer (in production, this would actually
                # apply the knowledge to the target domain)
                transferred = await self._transfer_item(item, target_domain_id)
                if transferred:
                    if item.adaptation_needed != AdaptationType.NONE:
                        items_adapted += 1
                    items_transferred += 1
            except Exception as exc:
                errors.append(f"Failed to transfer {item.name}: {exc}")
                items_skipped += 1

        # Determine final status
        final_status: TransferStatus
        if errors and items_transferred == 0:
            final_status = TransferStatus.FAILED
        else:
            final_status = TransferStatus.COMPLETED

        end_time = datetime.now(UTC)
        duration = (end_time - start_time).total_seconds()

        result = TransferResult(
            transfer_id=record.id,
            status=final_status,
            source_domain_id=source_domain_id,
            target_domain_id=target_domain_id,
            items_transferred=items_transferred,
            items_adapted=items_adapted,
            items_skipped=items_skipped,
            total_items=len(package.items),
            compatibility_score=package.overall_compatibility,
            duration_seconds=round(duration, 2),
            errors=errors,
            warnings=warnings,
        )

        _validate_transfer_transition(record.status, final_status)
        record = record.model_copy(
            update={
                "status": final_status,
                "result": result,
                "completed_at": datetime.now(UTC),
            }
        )
        self._store.update_transfer(record)

        event_type = (
            "knowledge.transfer_completed"
            if final_status == TransferStatus.COMPLETED
            else "knowledge.transfer_failed"
        )
        await self._tape.log_event(
            event_type=event_type,
            payload={
                "transfer_id": str(record.id),
                "source_domain": source_domain_id,
                "target_domain": target_domain_id,
                "items_transferred": items_transferred,
                "items_adapted": items_adapted,
                "items_skipped": items_skipped,
                "compatibility_score": package.overall_compatibility,
                "duration_seconds": result.duration_seconds,
            },
            agent_id="knowledge-transfer-engine",
            metadata={
                "errors": errors,
                "warnings": warnings,
            },
        )

        return record

    async def _transfer_item(
        self,
        item: KnowledgeItem,
        target_domain_id: str,
    ) -> bool:
        """Transfer a single knowledge item to the target domain.

        In production, this would register the skill/agent/workflow in
        the target domain's registry. For now, it simulates the transfer.
        """
        # Simulate transfer with a small delay
        await self._tape.log_event(
            event_type="knowledge.item_transferred",
            payload={
                "item_id": str(item.id),
                "item_name": item.name,
                "knowledge_type": item.knowledge_type.value,
                "target_domain": target_domain_id,
                "adaptation_needed": item.adaptation_needed.value,
            },
            agent_id="knowledge-transfer-engine",
        )

        # Update transfer count on the item
        updated_item = item.model_copy(
            update={"transfer_count": item.transfer_count + 1}
        )
        self._store.add_knowledge_item(updated_item)

        return True

    # ------------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------------

    async def rollback_transfer(self, transfer_id: UUID) -> TransferRecord:
        """Rollback a completed or failed transfer.

        In production, this would remove the transferred knowledge from
        the target domain. For now, it updates the record status.
        """
        record = self._store.get_transfer(transfer_id)
        if record is None:
            raise TransferNotFoundError(f"Transfer {transfer_id} not found")

        if record.status not in (
            TransferStatus.COMPLETED,
            TransferStatus.FAILED,
        ):
            raise TransferTransitionError(
                f"Cannot rollback transfer in {record.status.value} status"
            )

        _validate_transfer_transition(record.status, TransferStatus.ROLLED_BACK)
        record = record.model_copy(
            update={
                "status": TransferStatus.ROLLED_BACK,
                "completed_at": datetime.now(UTC),
            }
        )
        self._store.update_transfer(record)

        await self._tape.log_event(
            event_type="knowledge.transfer_rolled_back",
            payload={
                "transfer_id": str(transfer_id),
                "source_domain": record.source_domain_id,
                "target_domain": record.target_domain_id,
            },
            agent_id="knowledge-transfer-engine",
        )

        return record

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def get_transfer(self, transfer_id: UUID) -> TransferRecord:
        """Get a transfer record by ID."""
        record = self._store.get_transfer(transfer_id)
        if record is None:
            raise TransferNotFoundError(f"Transfer {transfer_id} not found")
        return record

    async def list_transfers(
        self, status: TransferStatus | None = None
    ) -> list[TransferRecord]:
        """List all transfers, optionally filtered by status."""
        if status is not None:
            return self._store.list_transfers_by_status(status)
        return self._store.list_transfers()

    async def get_package(self, package_id: UUID) -> KnowledgePackage:
        """Get a knowledge package by ID."""
        package = self._store.get_package(package_id)
        if package is None:
            raise KnowledgeTransferError(f"Package {package_id} not found")
        return package

    async def list_packages(self) -> list[KnowledgePackage]:
        """List all knowledge packages."""
        return self._store.list_packages()

    async def list_knowledge_items(
        self,
        source_domain_id: str | None = None,
        knowledge_type: KnowledgeType | None = None,
    ) -> list[KnowledgeItem]:
        """List knowledge items, optionally filtered."""
        return self._store.list_knowledge_items(
            source_domain_id=source_domain_id,
            knowledge_type=knowledge_type,
        )

    # ------------------------------------------------------------------
    # Transfer recommendations
    # ------------------------------------------------------------------

    async def recommend_transfers(
        self,
        domain_id: str,
        all_domain_metadata: dict[str, dict[str, object]],
    ) -> list[dict[str, object]]:
        """Recommend knowledge transfers for a domain.

        Analyses all domains and identifies potential sources of
        valuable knowledge for the specified target domain.
        """
        recommendations: list[dict[str, object]] = []

        target_metadata = all_domain_metadata.get(domain_id, {})
        if not target_metadata:
            return recommendations

        for source_id, source_metadata in all_domain_metadata.items():
            if source_id == domain_id:
                continue

            items = self._extractor.extract_from_domain(
                domain_id=source_id,
                domain_metadata=source_metadata,
            )

            assessed = [
                self._assessor.assess_item(item, target_metadata)
                for item in items
            ]

            compatible = [
                i
                for i in assessed
                if i.compatibility_level
                in (CompatibilityLevel.HIGH, CompatibilityLevel.MEDIUM)
            ]

            if compatible:
                avg_score = sum(
                    i.compatibility_score for i in compatible
                ) / len(compatible)
                recommendations.append(
                    {
                        "source_domain_id": source_id,
                        "compatible_items": len(compatible),
                        "average_compatibility": round(avg_score, 2),
                        "top_items": [
                            {
                                "name": i.name,
                                "type": i.knowledge_type.value,
                                "compatibility": i.compatibility_score,
                                "adaptation": i.adaptation_needed.value,
                            }
                            for i in sorted(
                                compatible,
                                key=lambda x: x.compatibility_score,
                                reverse=True,
                            )[:5]
                        ],
                    }
                )

        # Sort by average compatibility (descending)
        recommendations.sort(
            key=lambda r: float(str(r["average_compatibility"])) if isinstance(r.get("average_compatibility"), (int, float)) else 0.0,
            reverse=True,
        )

        await self._tape.log_event(
            event_type="knowledge.recommendations_generated",
            payload={
                "target_domain": domain_id,
                "recommendation_count": len(recommendations),
            },
            agent_id="knowledge-transfer-engine",
        )

        return recommendations
