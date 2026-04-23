"""Skill Evolution Engine — Automatic skill improvement, combination, and lifecycle.

This module enables Prime to continuously evolve the system's skill set based on
performance data, Tape history, and system introspection. Every evolution goes
through the Proposal approval workflow for safety, and all actions are logged
to the Tape for full auditability.

Evolution types:
- ENHANCE: Improve an existing skill's capabilities or performance
- MERGE: Combine two or more related skills into a single unified skill
- SPLIT: Break an overly broad skill into more focused sub-skills
- DEPRECATE: Retire a skill that is no longer useful or has been superseded
- CREATE: Add a brand-new skill based on observed system needs

Rollback:
- Every evolution stores a snapshot of the skill state before the change
- ``rollback()`` can revert the most recent applied evolution
- Rollback is itself logged to the Tape

Usage::

    from packages.prime.skill_evolution import SkillEvolutionEngine

    engine = SkillEvolutionEngine(
        tape_service=tape_svc,
        introspector=introspector,
        proposal_engine=proposal_engine,
        skill_registry=skill_registry,
    )

    # Analyse skills and generate evolution proposals
    proposals = await engine.generate_evolution_proposals()

    # After human approval, apply the evolution
    result = await engine.apply_evolution(proposal.id, reviewer="alice")

    # If something goes wrong, rollback
    await engine.rollback(proposal.id)
"""

import contextlib
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from packages.prime.introspection import (
    PrimeIntrospector,
    SkillDescriptor,
    SkillRegistry,
)
from packages.prime.proposals import (
    ModificationType,
    ProposalEngine,
    ProposalNotFoundError,
    ProposalStatus,
    RiskLevel,
)
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class EvolutionType(StrEnum):
    """Types of skill evolution Prime can propose and apply."""

    ENHANCE = "enhance"
    MERGE = "merge"
    SPLIT = "split"
    DEPRECATE = "deprecate"
    CREATE = "create"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class SkillEvolutionProposal(BaseModel):
    """A structured proposal for evolving one or more skills.

    This wraps a generic ``Proposal`` with skill-specific context: which
    skills are affected, what evolution type, and before/after snapshots.
    """

    id: UUID = Field(default_factory=uuid4)
    proposal_id: UUID
    evolution_type: EvolutionType
    target_skill_ids: list[str]
    new_skill_descriptor: SkillDescriptor | None = None
    before_snapshot: list[SkillDescriptor] = []
    reasoning: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvolutionResult(BaseModel):
    """Outcome of applying a skill evolution.

    Captures what changed, which skills were created/removed/modified,
    and whether the evolution succeeded.
    """

    id: UUID = Field(default_factory=uuid4)
    evolution_proposal_id: UUID
    success: bool
    skills_added: list[str] = []
    skills_removed: list[str] = []
    skills_modified: list[str] = []
    error_message: str | None = None
    applied_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SkillAnalysis(BaseModel):
    """Analysis report for a single skill, derived from Tape data.

    Provides the performance signals that Prime uses to decide whether
    and how a skill should evolve.
    """

    skill_id: str
    invocation_count: int = 0
    error_count: int = 0
    error_rate: float = 0.0
    last_invoked: datetime | None = None
    related_skill_ids: list[str] = []
    recommendation: str = "maintain"  # maintain, enhance, merge, split, deprecate
    recommendation_reason: str = ""


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SkillEvolutionError(Exception):
    """Base exception for skill evolution operations."""


class EvolutionProposalNotFoundError(SkillEvolutionError):
    """Raised when a requested evolution proposal does not exist."""


class EvolutionNotApprovedError(SkillEvolutionError):
    """Raised when trying to apply an evolution that hasn't been approved."""


class RollbackError(SkillEvolutionError):
    """Raised when a rollback cannot be performed."""


# ---------------------------------------------------------------------------
# SkillEvolutionStore — in-memory persistence
# ---------------------------------------------------------------------------


class SkillEvolutionStore:
    """In-memory store for skill evolution proposals and results.

    Will be replaced by a PostgreSQL-backed repository in a future phase.
    """

    def __init__(self) -> None:
        self._proposals: dict[UUID, SkillEvolutionProposal] = {}
        self._results: dict[UUID, EvolutionResult] = {}

    def add_proposal(self, proposal: SkillEvolutionProposal) -> None:
        self._proposals[proposal.id] = proposal

    def get_proposal(self, proposal_id: UUID) -> SkillEvolutionProposal | None:
        return self._proposals.get(proposal_id)

    def list_proposals(self) -> list[SkillEvolutionProposal]:
        return list(self._proposals.values())

    def add_result(self, result: EvolutionResult) -> None:
        self._results[result.id] = result

    def get_result(self, result_id: UUID) -> EvolutionResult | None:
        return self._results.get(result_id)

    def get_results_for_proposal(self, evolution_proposal_id: UUID) -> list[EvolutionResult]:
        return [
            r for r in self._results.values() if r.evolution_proposal_id == evolution_proposal_id
        ]


# ---------------------------------------------------------------------------
# SkillEvolutionEngine — the main public API
# ---------------------------------------------------------------------------


class SkillEvolutionEngine:
    """Engine for analysing, proposing, applying, and rolling back skill evolutions.

    SkillEvolutionEngine is Prime's mechanism for continuously improving the
    system's skill set. It analyses Tape data, generates structured proposals
    that go through the human approval workflow, applies approved changes to
    the SkillRegistry, and supports rollback if something goes wrong.

    Every action is logged to the Tape for full auditability.

    Usage::

        engine = SkillEvolutionEngine(
            tape_service=tape_svc,
            introspector=introspector,
            proposal_engine=proposal_engine,
            skill_registry=skill_registry,
        )

        # Analyse current skills
        analyses = await engine.analyze_skills()

        # Generate evolution proposals (goes through approval workflow)
        proposals = await engine.generate_evolution_proposals()

        # After human approves via proposal_engine...
        result = await engine.apply_evolution(evolution_proposal.id)

        # If needed, rollback
        await engine.rollback(evolution_proposal.id)
    """

    def __init__(
        self,
        tape_service: TapeService,
        introspector: PrimeIntrospector | None = None,
        proposal_engine: ProposalEngine | None = None,
        skill_registry: SkillRegistry | None = None,
        store: SkillEvolutionStore | None = None,
    ) -> None:
        self._tape = tape_service
        self._introspector = introspector
        self._proposals = proposal_engine or ProposalEngine(tape_service=tape_service)
        self._skills = skill_registry or SkillRegistry()
        self._store = store or SkillEvolutionStore()
        self._rollback_stack: dict[UUID, list[SkillDescriptor]] = {}

    # ------------------------------------------------------------------
    # Analyse skills
    # ------------------------------------------------------------------

    async def analyze_skills(self) -> list[SkillAnalysis]:
        """Analyse all registered skills using Tape data and performance metrics.

        Returns a list of ``SkillAnalysis`` objects — one per registered skill —
        with invocation counts, error rates, and evolution recommendations.
        """
        skills = self._skills.list_skills()
        analyses: list[SkillAnalysis] = []

        for skill in skills:
            # Gather Tape-based metrics
            invocations = await self._tape.get_entries(event_type="skill.invoke", limit=500)
            skill_invocations = [
                e
                for e in invocations
                if isinstance(e.payload, dict) and e.payload.get("skill_id") == skill.skill_id
            ]
            invocation_count = len(skill_invocations)
            error_count = sum(
                1
                for e in skill_invocations
                if isinstance(e.payload, dict)
                and str(e.payload.get("status", "")).lower() == "error"
            )
            error_rate = error_count / invocation_count if invocation_count > 0 else 0.0
            last_invoked = skill_invocations[0].timestamp if skill_invocations else None

            # Determine recommendation
            recommendation, reason = self._compute_recommendation(
                skill=skill,
                invocation_count=invocation_count,
                error_rate=error_rate,
                all_skills=skills,
            )

            analysis = SkillAnalysis(
                skill_id=skill.skill_id,
                invocation_count=invocation_count,
                error_count=error_count,
                error_rate=round(error_rate, 3),
                last_invoked=last_invoked,
                related_skill_ids=self._find_related_skills(skill, skills),
                recommendation=recommendation,
                recommendation_reason=reason,
            )
            analyses.append(analysis)

        await self._tape.log_event(
            event_type="prime.skill_analysis",
            payload={"skill_count": len(analyses)},
            agent_id="prime",
            metadata={a.skill_id: a.recommendation for a in analyses},
        )

        return analyses

    # ------------------------------------------------------------------
    # Generate evolution proposals
    # ------------------------------------------------------------------

    async def generate_evolution_proposals(self) -> list[SkillEvolutionProposal]:
        """Analyse skills and generate evolution proposals for improvements.

        Each generated proposal creates a corresponding entry in the
        ProposalEngine (with status PENDING_APPROVAL), so it goes through
        the standard human-in-the-loop governance workflow.
        """
        analyses = await self.analyze_skills()
        proposals: list[SkillEvolutionProposal] = []

        for analysis in analyses:
            if analysis.recommendation == "maintain":
                continue

            evolution_type = self._recommendation_to_evolution_type(analysis.recommendation)
            if evolution_type is None:
                continue

            target_skills = [
                s
                for s in self._skills.list_skills()
                if s.skill_id in ([analysis.skill_id, *analysis.related_skill_ids])
            ]

            ev_proposal = await self._create_evolution_proposal(
                evolution_type=evolution_type,
                analysis=analysis,
                target_skills=target_skills,
            )
            if ev_proposal is not None:
                proposals.append(ev_proposal)

        # Check if system has no skills at all → propose creation
        if len(analyses) == 0:
            ev_proposal = await self._create_new_skill_proposal(
                "code-gen",
                "Code Generation",
                "Generate high-quality code from natural language specifications",
            )
            if ev_proposal is not None:
                proposals.append(ev_proposal)

        return proposals

    # ------------------------------------------------------------------
    # Apply an approved evolution
    # ------------------------------------------------------------------

    async def apply_evolution(self, evolution_proposal_id: UUID) -> EvolutionResult:
        """Apply an approved skill evolution to the SkillRegistry.

        The corresponding Proposal must be in APPROVED status. This method
        mutates the SkillRegistry, logs the result to the Tape, and stores
        a before-snapshot for rollback.

        Raises:
            EvolutionProposalNotFoundError: if the evolution proposal doesn't exist
            EvolutionNotApprovedError: if the linked Proposal isn't approved
        """
        ev_proposal = self._get_evolution_proposal_or_raise(evolution_proposal_id)

        # Verify the linked proposal is approved
        try:
            proposal = await self._proposals.get_proposal(ev_proposal.proposal_id)
        except ProposalNotFoundError:
            proposal = None

        if proposal is None or proposal.status != ProposalStatus.APPROVED:
            raise EvolutionNotApprovedError(
                f"Evolution proposal {evolution_proposal_id} is not approved "
                f"(proposal status: {proposal.status.value if proposal else 'unknown'})"
            )

        # Store before-snapshot for rollback
        self._rollback_stack[evolution_proposal_id] = list(ev_proposal.before_snapshot)

        # Apply the evolution
        skills_added: list[str] = []
        skills_removed: list[str] = []
        skills_modified: list[str] = []
        error_message: str | None = None
        success = True

        try:
            match ev_proposal.evolution_type:
                case EvolutionType.ENHANCE:
                    skills_modified = await self._apply_enhance(ev_proposal)
                case EvolutionType.MERGE:
                    skills_added, skills_removed = await self._apply_merge(ev_proposal)
                case EvolutionType.SPLIT:
                    skills_added, skills_removed = await self._apply_split(ev_proposal)
                case EvolutionType.DEPRECATE:
                    skills_removed = await self._apply_deprecate(ev_proposal)
                case EvolutionType.CREATE:
                    skills_added = await self._apply_create(ev_proposal)
        except Exception as exc:
            success = False
            error_message = str(exc)

        result = EvolutionResult(
            evolution_proposal_id=evolution_proposal_id,
            success=success,
            skills_added=skills_added,
            skills_removed=skills_removed,
            skills_modified=skills_modified,
            error_message=error_message,
        )

        self._store.add_result(result)

        # Mark the linked proposal as implemented (best-effort)
        if success:
            with contextlib.suppress(Exception):
                await self._proposals.mark_implemented(ev_proposal.proposal_id)

        await self._tape.log_event(
            event_type="prime.skill_evolution_applied",
            payload={
                "evolution_proposal_id": str(evolution_proposal_id),
                "evolution_type": ev_proposal.evolution_type.value,
                "success": success,
                "skills_added": skills_added,
                "skills_removed": skills_removed,
                "skills_modified": skills_modified,
            },
            agent_id="prime",
        )

        return result

    # ------------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------------

    async def rollback(self, evolution_proposal_id: UUID) -> EvolutionResult:
        """Rollback a previously applied evolution.

        Restores the SkillRegistry to the state before the evolution was
        applied, using the stored before-snapshot. Rollback is itself
        logged to the Tape.

        Raises:
            RollbackError: if no before-snapshot exists for the proposal.
        """
        if evolution_proposal_id not in self._rollback_stack:
            raise RollbackError(f"No rollback snapshot found for evolution {evolution_proposal_id}")

        before_snapshot = self._rollback_stack.pop(evolution_proposal_id)
        ev_proposal = self._store.get_proposal(evolution_proposal_id)

        # Remove any skills that were added by the evolution
        current_skills = self._skills.list_skills()
        current_ids = {s.skill_id for s in current_skills}
        before_ids = {s.skill_id for s in before_snapshot}
        added_by_evolution = current_ids - before_ids
        removed_by_evolution = before_ids - current_ids

        for sid in added_by_evolution:
            self._skills.unregister(sid)

        # Restore skills that were removed by the evolution
        for skill in before_snapshot:
            if skill.skill_id not in current_ids:
                self._skills.register(skill)
            else:
                # Update to the before-snapshot version
                self._skills.register(skill)

        skills_restored = list(removed_by_evolution)
        skills_removed = list(added_by_evolution)

        result = EvolutionResult(
            evolution_proposal_id=evolution_proposal_id,
            success=True,
            skills_added=skills_restored,
            skills_removed=skills_removed,
        )
        self._store.add_result(result)

        await self._tape.log_event(
            event_type="prime.skill_evolution_rollback",
            payload={
                "evolution_proposal_id": str(evolution_proposal_id),
                "evolution_type": (ev_proposal.evolution_type.value if ev_proposal else "unknown"),
                "skills_restored": skills_restored,
                "skills_removed": skills_removed,
            },
            agent_id="prime",
        )

        return result

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    async def get_evolution_proposal(self, evolution_proposal_id: UUID) -> SkillEvolutionProposal:
        """Retrieve a single evolution proposal by ID.

        Raises:
            EvolutionProposalNotFoundError: if not found.
        """
        return self._get_evolution_proposal_or_raise(evolution_proposal_id)

    async def list_evolution_proposals(self) -> list[SkillEvolutionProposal]:
        """List all skill evolution proposals."""
        return self._store.list_proposals()

    async def list_results(
        self, evolution_proposal_id: UUID | None = None
    ) -> list[EvolutionResult]:
        """List evolution results, optionally filtered by proposal."""
        if evolution_proposal_id is not None:
            return self._store.get_results_for_proposal(evolution_proposal_id)
        return list(self._store._results.values())

    # ------------------------------------------------------------------
    # Internal: proposal creation
    # ------------------------------------------------------------------

    async def _create_evolution_proposal(
        self,
        evolution_type: EvolutionType,
        analysis: SkillAnalysis,
        target_skills: list[SkillDescriptor],
    ) -> SkillEvolutionProposal | None:
        """Create a SkillEvolutionProposal with a linked Proposal."""
        mod_type = self._evolution_to_modification_type(evolution_type)
        risk = self._evolution_to_risk(evolution_type)
        title = f"[{evolution_type.value}] Skill {analysis.skill_id}"
        description = analysis.recommendation_reason
        steps = self._evolution_steps(evolution_type, analysis)

        try:
            proposal = await self._proposals.propose(
                title=title,
                modification_type=mod_type,
                description=description,
                reasoning=analysis.recommendation_reason,
                expected_impact=self._evolution_impact(evolution_type, analysis),
                risk_level=risk,
                implementation_steps=steps,
                confidence_score=self._evolution_confidence(evolution_type),
            )
        except Exception:
            return None

        ev_proposal = SkillEvolutionProposal(
            proposal_id=proposal.id,
            evolution_type=evolution_type,
            target_skill_ids=[s.skill_id for s in target_skills],
            new_skill_descriptor=None,
            before_snapshot=list(target_skills),
            reasoning=analysis.recommendation_reason,
        )
        self._store.add_proposal(ev_proposal)
        return ev_proposal

    async def _create_new_skill_proposal(
        self,
        skill_id: str,
        name: str,
        description: str,
    ) -> SkillEvolutionProposal | None:
        """Create an evolution proposal for a brand-new skill."""
        try:
            proposal = await self._proposals.propose(
                title=f"[create] New skill: {name}",
                modification_type=ModificationType.SKILL_ADDITION,
                description=description,
                reasoning="System has no skills — foundational capabilities are needed.",
                expected_impact="Agents gain core capabilities",
                risk_level=RiskLevel.LOW,
                implementation_steps=[
                    f"Define skill specification for {name}",
                    f"Register skill '{skill_id}' in SkillRegistry",
                    "Verify skill is available to agents",
                ],
                confidence_score=0.90,
            )
        except Exception:
            return None

        ev_proposal = SkillEvolutionProposal(
            proposal_id=proposal.id,
            evolution_type=EvolutionType.CREATE,
            target_skill_ids=[],
            new_skill_descriptor=SkillDescriptor(
                skill_id=skill_id, name=name, description=description
            ),
            before_snapshot=[],
            reasoning="System has no skills registered.",
        )
        self._store.add_proposal(ev_proposal)
        return ev_proposal

    # ------------------------------------------------------------------
    # Internal: apply evolution types
    # ------------------------------------------------------------------

    async def _apply_enhance(self, ev_proposal: SkillEvolutionProposal) -> list[str]:
        """Enhance a skill by bumping its version and updating description."""
        modified: list[str] = []
        for skill_id in ev_proposal.target_skill_ids:
            skill = self._get_skill_or_skip(skill_id)
            if skill is None:
                continue
            parts = skill.version.split(".")
            minor = int(parts[-1]) + 1 if parts else 1
            new_version = ".".join([*parts[:-1], str(minor)]) if len(parts) > 1 else f"0.{minor}"
            enhanced = skill.model_copy(
                update={
                    "version": new_version,
                    "description": f"{skill.description} (enhanced)".strip(),
                }
            )
            self._skills.register(enhanced)
            modified.append(skill_id)
        return modified

    async def _apply_merge(
        self, ev_proposal: SkillEvolutionProposal
    ) -> tuple[list[str], list[str]]:
        """Merge target skills into a single combined skill."""
        if len(ev_proposal.target_skill_ids) < 2:
            return [], []

        skills_to_merge: list[SkillDescriptor] = [
            s
            for s in (self._get_skill_or_skip(sid) for sid in ev_proposal.target_skill_ids)
            if s is not None
        ]
        if not skills_to_merge:
            return [], []

        merged_id = "-".join(s.skill_id for s in skills_to_merge)
        merged_name = " + ".join(s.name for s in skills_to_merge)
        merged_desc = "Merged: " + "; ".join(
            s.description for s in skills_to_merge if s.description
        )

        merged = SkillDescriptor(
            skill_id=merged_id,
            name=merged_name,
            version="1.0.0",
            description=merged_desc,
        )
        self._skills.register(merged)

        removed: list[str] = []
        for s in skills_to_merge:
            self._skills.unregister(s.skill_id)
            removed.append(s.skill_id)

        return [merged_id], removed

    async def _apply_split(
        self, ev_proposal: SkillEvolutionProposal
    ) -> tuple[list[str], list[str]]:
        """Split a broad skill into two focused sub-skills."""
        if not ev_proposal.target_skill_ids:
            return [], []

        source_id = ev_proposal.target_skill_ids[0]
        source = self._get_skill_or_skip(source_id)
        if source is None:
            return [], []

        sub_a = SkillDescriptor(
            skill_id=f"{source_id}-a",
            name=f"{source.name} (Part A)",
            version="0.1.0",
            description=f"Split from {source.name}: focused subset A",
        )
        sub_b = SkillDescriptor(
            skill_id=f"{source_id}-b",
            name=f"{source.name} (Part B)",
            version="0.1.0",
            description=f"Split from {source.name}: focused subset B",
        )
        self._skills.register(sub_a)
        self._skills.register(sub_b)
        self._skills.unregister(source_id)

        return [sub_a.skill_id, sub_b.skill_id], [source_id]

    async def _apply_deprecate(self, ev_proposal: SkillEvolutionProposal) -> list[str]:
        """Deprecate skills by removing them from the registry."""
        removed: list[str] = []
        for skill_id in ev_proposal.target_skill_ids:
            self._skills.unregister(skill_id)
            removed.append(skill_id)
        return removed

    async def _apply_create(self, ev_proposal: SkillEvolutionProposal) -> list[str]:
        """Create a new skill from the evolution proposal's descriptor."""
        descriptor = ev_proposal.new_skill_descriptor
        if descriptor is None:
            return []
        self._skills.register(descriptor)
        return [descriptor.skill_id]

    # ------------------------------------------------------------------
    # Internal: analysis helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_recommendation(
        skill: SkillDescriptor,
        invocation_count: int,
        error_rate: float,
        all_skills: list[SkillDescriptor],
    ) -> tuple[str, str]:
        """Determine the best evolution recommendation for a skill.

        Returns (recommendation, reason). Heuristics:
        - error_rate > 0.3 → enhance (reliability issues)
        - invocation_count == 0 → deprecate (unused)
        - overlapping names with other skills → merge
        - overly broad description → split
        - otherwise → maintain
        """
        if error_rate > 0.3:
            return "enhance", f"High error rate ({error_rate:.0%}) indicates reliability issues"
        if invocation_count == 0:
            return "deprecate", "Skill has zero invocations — potentially unused"
        # Check for overlapping/mergeable skills
        name_words = set(skill.name.lower().split())
        for other in all_skills:
            if other.skill_id == skill.skill_id:
                continue
            other_words = set(other.name.lower().split())
            overlap = name_words & other_words
            if len(overlap) >= 1 and len(overlap) / max(len(name_words), 1) >= 0.5:
                return "merge", f"Overlaps with '{other.name}' — consider merging"
        # Check if skill is overly broad
        if len(skill.description) > 200 or " and " in skill.description.lower():
            return "split", "Skill scope is too broad — split into focused sub-skills"
        return "maintain", "Skill performance is within acceptable parameters"

    @staticmethod
    def _find_related_skills(
        skill: SkillDescriptor, all_skills: list[SkillDescriptor]
    ) -> list[str]:
        """Find skills with overlapping names (potential merge candidates)."""
        name_words = set(skill.name.lower().split())
        related: list[str] = []
        for other in all_skills:
            if other.skill_id == skill.skill_id:
                continue
            other_words = set(other.name.lower().split())
            if name_words & other_words:
                related.append(other.skill_id)
        return related

    @staticmethod
    def _recommendation_to_evolution_type(
        recommendation: str,
    ) -> EvolutionType | None:
        """Map a recommendation string to an EvolutionType."""
        mapping: dict[str, EvolutionType] = {
            "enhance": EvolutionType.ENHANCE,
            "merge": EvolutionType.MERGE,
            "split": EvolutionType.SPLIT,
            "deprecate": EvolutionType.DEPRECATE,
        }
        return mapping.get(recommendation)

    @staticmethod
    def _evolution_to_modification_type(
        evolution_type: EvolutionType,
    ) -> ModificationType:
        """Map EvolutionType to the corresponding ModificationType."""
        mapping: dict[EvolutionType, ModificationType] = {
            EvolutionType.ENHANCE: ModificationType.SKILL_MODIFICATION,
            EvolutionType.MERGE: ModificationType.SKILL_MODIFICATION,
            EvolutionType.SPLIT: ModificationType.SKILL_MODIFICATION,
            EvolutionType.DEPRECATE: ModificationType.SKILL_MODIFICATION,
            EvolutionType.CREATE: ModificationType.SKILL_ADDITION,
        }
        return mapping[evolution_type]

    @staticmethod
    def _evolution_to_risk(evolution_type: EvolutionType) -> RiskLevel:
        """Map EvolutionType to a default RiskLevel."""
        mapping: dict[EvolutionType, RiskLevel] = {
            EvolutionType.ENHANCE: RiskLevel.LOW,
            EvolutionType.CREATE: RiskLevel.LOW,
            EvolutionType.MERGE: RiskLevel.MEDIUM,
            EvolutionType.SPLIT: RiskLevel.MEDIUM,
            EvolutionType.DEPRECATE: RiskLevel.HIGH,
        }
        return mapping[evolution_type]

    @staticmethod
    def _evolution_steps(evolution_type: EvolutionType, analysis: SkillAnalysis) -> list[str]:
        """Generate implementation steps for an evolution proposal."""
        base_steps: dict[EvolutionType, list[str]] = {
            EvolutionType.ENHANCE: [
                f"Analyse error patterns for {analysis.skill_id}",
                "Implement reliability improvements",
                "Bump skill version",
                "Verify enhanced skill in staging",
            ],
            EvolutionType.MERGE: [
                "Validate overlapping functionality",
                "Create merged skill definition",
                "Register merged skill",
                "Remove superseded skills",
            ],
            EvolutionType.SPLIT: [
                "Identify distinct capability boundaries",
                "Define sub-skill specifications",
                "Register sub-skills",
                "Remove original broad skill",
            ],
            EvolutionType.DEPRECATE: [
                f"Verify {analysis.skill_id} has no active dependents",
                "Mark skill as deprecated",
                "Remove from registry",
                "Notify dependent agents",
            ],
            EvolutionType.CREATE: [
                "Define skill specification",
                "Implement skill logic",
                "Register in SkillRegistry",
                "Verify skill availability",
            ],
        }
        return base_steps.get(evolution_type, [])

    @staticmethod
    def _evolution_impact(evolution_type: EvolutionType, analysis: SkillAnalysis) -> str:
        """Describe the expected impact of an evolution."""
        impacts: dict[EvolutionType, str] = {
            EvolutionType.ENHANCE: f"Improved reliability for {analysis.skill_id}",
            EvolutionType.MERGE: "Consolidated skills reduce duplication and maintenance",
            EvolutionType.SPLIT: "Focused sub-skills improve precision and composability",
            EvolutionType.DEPRECATE: "Reduced complexity by removing unused capability",
            EvolutionType.CREATE: "New capability available to agents",
        }
        return impacts.get(evolution_type, "System skill set updated")

    @staticmethod
    def _evolution_confidence(evolution_type: EvolutionType) -> float:
        """Default confidence score per evolution type."""
        scores: dict[EvolutionType, float] = {
            EvolutionType.CREATE: 0.90,
            EvolutionType.ENHANCE: 0.85,
            EvolutionType.MERGE: 0.70,
            EvolutionType.SPLIT: 0.65,
            EvolutionType.DEPRECATE: 0.55,
        }
        return scores.get(evolution_type, 0.5)

    # ------------------------------------------------------------------
    # Internal: utility
    # ------------------------------------------------------------------

    def _get_evolution_proposal_or_raise(
        self, evolution_proposal_id: UUID
    ) -> SkillEvolutionProposal:
        """Look up an evolution proposal or raise."""
        proposal = self._store.get_proposal(evolution_proposal_id)
        if proposal is None:
            raise EvolutionProposalNotFoundError(
                f"Evolution proposal {evolution_proposal_id} not found"
            )
        return proposal

    def _get_skill_or_skip(self, skill_id: str) -> SkillDescriptor | None:
        """Look up a skill, returning None instead of raising if missing."""
        return self._skills.get_skill(skill_id)
