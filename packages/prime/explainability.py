"""Explainability Dashboard — Full transparency into Prime's decision-making.

This module enables users to understand *why* Prime and the InkosAI system
made specific decisions, proposals, skill evolutions, simulation outcomes,
and debate results.  Every explanation is itself logged to the Tape, creating
a recursive audit trail.

Core capabilities:

- **generate_explanation()** — Produce a human-readable explanation for any
  system action, with both a *technical* (detailed) and *simplified*
  (user-friendly) mode.
- **get_decision_trace()** — Reconstruct the full chain of reasoning, data
  sources, and confidence factors that led to a decision.
- **highlight_key_factors()** -- Identify the top 3-5 factors that most
  influenced a decision, with importance scores.
- **compare_alternatives()** — Explain why one option was chosen over
  alternatives, with relative scoring.

Integration points:

- Tape entries (event history for any action)
- PrimeIntrospector (system state at decision time)
- ProposalEngine / proposals (self-modification decisions)
- SkillEvolutionEngine (skill change decisions)
- SimulationEngine (what-if outcomes)
- DebateArena (debate outcomes)

Architecture::

    ExplainabilityEngine
    ├── generate_explanation()    — Full explanation for an action
    ├── get_decision_trace()      — Step-by-step reasoning chain
    ├── highlight_key_factors()   — Top influencing factors
    ├── compare_alternatives()    — Why this option over others
    ├── get_explanation()         — Retrieve a stored explanation
    └── list_explanations()       — List all explanations (optionally filtered)

Usage::

    engine = ExplainabilityEngine(tape_service=tape_svc)

    explanation = await engine.generate_explanation(
        action_id="proposal-abc123",
        action_type=ActionType.PROPOSAL_CREATED,
    )
    # explanation.technical_summary  — detailed reasoning
    # explanation.simplified_summary — plain-English version
    # explanation.key_factors        — ranked list of influences

    trace = await engine.get_decision_trace(action_id="proposal-abc123")
    factors = await engine.highlight_key_factors(action_id="proposal-abc123")
    comparison = await engine.compare_alternatives(
        action_id="proposal-abc123",
        alternatives=["proposal-def456", "proposal-ghi789"],
    )
"""

import contextlib
import math
from datetime import UTC, datetime
from enum import StrEnum
from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from packages.prime.intelligence_profile import IntelligenceProfileEngine
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ActionType(StrEnum):
    """Categories of system actions that can be explained."""

    PROPOSAL_CREATED = "proposal_created"
    PROPOSAL_APPROVED = "proposal_approved"
    PROPOSAL_REJECTED = "proposal_rejected"
    PROPOSAL_IMPLEMENTED = "proposal_implemented"
    SKILL_EVOLUTION = "skill_evolution"
    SKILL_CREATED = "skill_created"
    SKILL_DEPRECATED = "skill_deprecated"
    SKILL_MERGED = "skill_merged"
    SKILL_SPLIT = "skill_split"
    SKILL_ENHANCED = "skill_enhanced"
    SIMULATION_RUN = "simulation_run"
    SIMULATION_COMPARISON = "simulation_comparison"
    DEBATE_STARTED = "debate_started"
    DEBATE_ROUND = "debate_round"
    DEBATE_CONCLUDED = "debate_concluded"
    TAPE_ENTRY = "tape_entry"
    INTROSPECTION = "introspection"
    SYSTEM_ACTION = "system_action"


class ExplanationMode(StrEnum):
    """Verbosity level for explanations."""

    TECHNICAL = "technical"  # Detailed, for engineers
    SIMPLIFIED = "simplified"  # Plain English, for all users


class FactorCategory(StrEnum):
    """Categories of decision-influencing factors."""

    DATA_DRIVEN = "data_driven"  # Based on metrics, evidence
    HEURISTIC = "heuristic"  # Based on rules of thumb
    RISK_ASSESSMENT = "risk_assessment"  # Safety/risk evaluation
    STAKEHOLDER = "stakeholder"  # Human input, preferences
    HISTORICAL = "historical"  # Past outcomes, precedents
    SYSTEM_STATE = "system_state"  # Current system conditions
    CONSTRAINT = "constraint"  # Technical or policy limits
    CONFIDENCE = "confidence"  # Uncertainty quantification


class AlternativeOutcome(StrEnum):
    """How an alternative compares to the chosen option."""

    SUPERIOR = "superior"
    EQUIVALENT = "equivalent"
    INFERIOR = "inferior"
    INCOMPARABLE = "incomparable"  # Different trade-offs


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class KeyFactor(BaseModel):
    """A single factor that influenced a decision, with importance score."""

    name: str
    description: str
    category: FactorCategory
    importance: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: list[str] = []
    direction: str = "supporting"  # "supporting" | "opposing" | "neutral"


class DecisionStep(BaseModel):
    """One step in a chain of reasoning behind a decision."""

    step_number: int
    action: str  # What was done or considered
    rationale: str  # Why this step was taken
    data_sources: list[str] = []  # Tape entries, metrics, etc.
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    timestamp: datetime | None = None


class DecisionTrace(BaseModel):
    """Full chain of reasoning behind a decision."""

    action_id: str
    action_type: ActionType
    steps: list[DecisionStep] = []
    total_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    data_sources_used: list[str] = []
    assumptions: list[str] = []
    limitations: list[str] = []


class Alternative(BaseModel):
    """An alternative option that was considered but not chosen."""

    action_id: str
    label: str
    description: str
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    outcome: AlternativeOutcome = AlternativeOutcome.INCOMPARABLE
    pros: list[str] = []
    cons: list[str] = []
    key_differences: list[str] = []


class AlternativeComparison(BaseModel):
    """Comparison between the chosen option and alternatives."""

    action_id: str
    chosen_label: str
    chosen_score: float
    alternatives: list[Alternative] = []
    summary: str = ""
    trade_offs: list[str] = []


class Explanation(BaseModel):
    """A complete explanation for a system action.

    Contains both technical and simplified summaries, the key factors
    that influenced the decision, a confidence score, and optional
    links to related Tape entries.
    """

    id: UUID = Field(default_factory=uuid4)
    action_id: str
    action_type: ActionType
    technical_summary: str = ""
    simplified_summary: str = ""
    key_factors: list[KeyFactor] = []
    decision_trace: DecisionTrace | None = None
    alternative_comparison: AlternativeComparison | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    risk_level: str = "unknown"
    related_tape_entries: list[str] = []  # Tape entry IDs
    metadata: dict[str, object] = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ExplainabilityError(Exception):
    """Base exception for explainability operations."""


class ActionNotFoundError(ExplainabilityError):
    """Raised when the specified action cannot be found or traced."""


class ExplanationNotFoundError(ExplainabilityError):
    """Raised when a requested explanation does not exist."""


# ---------------------------------------------------------------------------
# Explanation Store (in-memory; will be Postgres-backed later)
# ---------------------------------------------------------------------------


class ExplanationStore:
    """In-memory store for generated explanations."""

    def __init__(self) -> None:
        self._explanations: dict[UUID, Explanation] = {}
        self._by_action: dict[str, list[Explanation]] = {}

    def add(self, explanation: Explanation) -> None:
        self._explanations[explanation.id] = explanation
        self._by_action.setdefault(explanation.action_id, []).append(explanation)

    def get(self, explanation_id: UUID) -> Explanation | None:
        return self._explanations.get(explanation_id)

    def get_by_action(self, action_id: str) -> list[Explanation]:
        return list(self._by_action.get(action_id, []))

    def list_all(
        self,
        action_type: ActionType | None = None,
    ) -> list[Explanation]:
        results = list(self._explanations.values())
        if action_type is not None:
            results = [e for e in results if e.action_type == action_type]
        return sorted(results, key=lambda e: e.created_at, reverse=True)

    def remove(self, explanation_id: UUID) -> None:
        with contextlib.suppress(KeyError):
            exp = self._explanations.pop(explanation_id)
            action_list = self._by_action.get(exp.action_id, [])
            self._by_action[exp.action_id] = [
                e for e in action_list if e.id != explanation_id
            ]


# ---------------------------------------------------------------------------
# FactorExtractor — derives key factors from Tape and system data
# ---------------------------------------------------------------------------


class FactorExtractor:
    """Extracts key decision-influencing factors from Tape events and context.

    The FactorExtractor analyses the payload and metadata of Tape entries
    related to an action, and derives a ranked list of KeyFactor objects.
    It uses heuristic rules based on common action types.
    """

    # Weight heuristics: how much each factor category contributes
    # to the overall importance score for different action types.
    _CATEGORY_WEIGHTS: ClassVar[dict[ActionType, dict[FactorCategory, float]]] = {
        ActionType.PROPOSAL_CREATED: {
            FactorCategory.RISK_ASSESSMENT: 0.30,
            FactorCategory.DATA_DRIVEN: 0.25,
            FactorCategory.HEURISTIC: 0.20,
            FactorCategory.SYSTEM_STATE: 0.15,
            FactorCategory.STAKEHOLDER: 0.10,
        },
        ActionType.SKILL_EVOLUTION: {
            FactorCategory.DATA_DRIVEN: 0.30,
            FactorCategory.HISTORICAL: 0.25,
            FactorCategory.HEURISTIC: 0.20,
            FactorCategory.SYSTEM_STATE: 0.15,
            FactorCategory.RISK_ASSESSMENT: 0.10,
        },
        ActionType.SIMULATION_RUN: {
            FactorCategory.DATA_DRIVEN: 0.35,
            FactorCategory.SYSTEM_STATE: 0.25,
            FactorCategory.CONFIDENCE: 0.20,
            FactorCategory.CONSTRAINT: 0.10,
            FactorCategory.RISK_ASSESSMENT: 0.10,
        },
        ActionType.DEBATE_CONCLUDED: {
            FactorCategory.DATA_DRIVEN: 0.25,
            FactorCategory.STAKEHOLDER: 0.25,
            FactorCategory.HEURISTIC: 0.20,
            FactorCategory.CONFIDENCE: 0.15,
            FactorCategory.RISK_ASSESSMENT: 0.15,
        },
    }

    # Default weights for action types not explicitly listed
    _DEFAULT_WEIGHTS: ClassVar[dict[FactorCategory, float]] = {
        FactorCategory.DATA_DRIVEN: 0.25,
        FactorCategory.HEURISTIC: 0.20,
        FactorCategory.RISK_ASSESSMENT: 0.20,
        FactorCategory.SYSTEM_STATE: 0.15,
        FactorCategory.CONFIDENCE: 0.10,
        FactorCategory.STAKEHOLDER: 0.05,
        FactorCategory.HISTORICAL: 0.03,
        FactorCategory.CONSTRAINT: 0.02,
    }

    def extract_factors(
        self,
        action_id: str,
        action_type: ActionType,
        tape_entries: list[dict[str, object]],
        context: dict[str, object] | None = None,
    ) -> list[KeyFactor]:
        """Extract key factors from Tape events and optional context.

        Args:
            action_id: The action being explained.
            action_type: Category of the action.
            tape_entries: Related Tape entry payloads (as dicts).
            context: Optional additional context (proposal data, etc.).

        Returns:
            A list of KeyFactor objects, sorted by importance (descending).
        """
        factors: list[KeyFactor] = []
        ctx = context or {}

        # --- Factor: Risk level (from context or Tape) ---
        risk_level = self._extract_risk_level(tape_entries, ctx)
        risk_importance = self._compute_importance(
            FactorCategory.RISK_ASSESSMENT, action_type,
        )
        if risk_level != "unknown":
            risk_direction = "opposing" if risk_level == "high" else "supporting"
            factors.append(KeyFactor(
                name="Risk Assessment",
                description=f"The action carries {risk_level} risk based on system evaluation.",
                category=FactorCategory.RISK_ASSESSMENT,
                importance=risk_importance,
                evidence=[f"Risk level: {risk_level}"],
                direction=risk_direction,
            ))

        # --- Factor: Confidence score (from context or Tape) ---
        confidence = self._extract_confidence(tape_entries, ctx)
        conf_importance = self._compute_importance(
            FactorCategory.CONFIDENCE, action_type,
        )
        if confidence is not None:
            direction = "supporting" if confidence >= 0.6 else "opposing"
            factors.append(KeyFactor(
                name="Confidence Level",
                description=f"System confidence for this action is {confidence:.0%}.",
                category=FactorCategory.CONFIDENCE,
                importance=conf_importance * confidence,
                evidence=[f"Confidence score: {confidence:.2f}"],
                direction=direction,
            ))

        # --- Factor: System state indicators ---
        state_factors = self._extract_system_state_factors(ctx, action_type)
        factors.extend(state_factors)

        # --- Factor: Data-driven evidence from Tape ---
        data_factors = self._extract_data_factors(tape_entries, action_type)
        factors.extend(data_factors)

        # --- Factor: Heuristic rules ---
        heuristic_factors = self._extract_heuristic_factors(action_type, ctx)
        factors.extend(heuristic_factors)

        # --- Factor: Historical precedents ---
        historical_factors = self._extract_historical_factors(tape_entries, action_type)
        factors.extend(historical_factors)

        # --- Factor: Constraints ---
        constraint_factors = self._extract_constraint_factors(ctx, action_type)
        factors.extend(constraint_factors)

        # --- Factor: Stakeholder input ---
        stakeholder_factors = self._extract_stakeholder_factors(tape_entries, ctx, action_type)
        factors.extend(stakeholder_factors)

        # Sort by importance (descending) and return top factors
        factors.sort(key=lambda f: f.importance, reverse=True)
        return factors

    def _compute_importance(
        self, category: FactorCategory, action_type: ActionType,
    ) -> float:
        weights = self._CATEGORY_WEIGHTS.get(
            action_type, self._DEFAULT_WEIGHTS,
        )
        return weights.get(category, 0.05)

    def _extract_risk_level(
        self,
        tape_entries: list[dict[str, object]],
        context: dict[str, object],
    ) -> str:
        # Check context first (e.g. from proposal data)
        if "risk_level" in context:
            return str(context["risk_level"])
        # Then check Tape entries
        for entry in tape_entries:
            payload = entry.get("payload", {})
            if isinstance(payload, dict) and "risk_level" in payload:
                return str(payload["risk_level"])
        return "unknown"

    def _extract_confidence(
        self,
        tape_entries: list[dict[str, object]],
        context: dict[str, object],
    ) -> float | None:
        if "confidence_score" in context:
            val = context["confidence_score"]
            if isinstance(val, (int, float)):
                return float(val)
        for entry in tape_entries:
            payload = entry.get("payload", {})
            if isinstance(payload, dict) and "confidence_score" in payload:
                val = payload["confidence_score"]
                if isinstance(val, (int, float)):
                    return float(val)
        return None

    def _extract_system_state_factors(
        self,
        context: dict[str, object],
        action_type: ActionType,
    ) -> list[KeyFactor]:
        factors: list[KeyFactor] = []
        importance = self._compute_importance(FactorCategory.SYSTEM_STATE, action_type)

        # Check for idle agents
        if "idle_agents" in context:
            idle = context["idle_agents"]
            if isinstance(idle, (int, float)) and int(idle) > 0:
                factors.append(KeyFactor(
                    name="Idle Agents",
                    description=f"{int(idle)} agent(s) are currently idle and available.",
                    category=FactorCategory.SYSTEM_STATE,
                    importance=importance * 0.8,
                    evidence=[f"Idle agent count: {int(idle)}"],
                    direction="supporting",
                ))

        # Check for error rate
        if "error_rate" in context:
            error_rate = context["error_rate"]
            if isinstance(error_rate, (int, float)):
                direction = "opposing" if float(error_rate) > 0.1 else "supporting"
                factors.append(KeyFactor(
                    name="Error Rate",
                    description=f"Current system error rate is {float(error_rate):.1%}.",
                    category=FactorCategory.SYSTEM_STATE,
                    importance=importance * min(1.0, float(error_rate) * 5),
                    evidence=[f"Error rate: {float(error_rate):.2f}"],
                    direction=direction,
                ))

        # Check for active skills/domains count
        if "skill_count" in context:
            skill_count = context["skill_count"]
            if isinstance(skill_count, (int, float)):
                factors.append(KeyFactor(
                    name="Skill Coverage",
                    description=f"System currently has {int(skill_count)} registered skill(s).",
                    category=FactorCategory.SYSTEM_STATE,
                    importance=importance * 0.5,
                    evidence=[f"Skill count: {int(skill_count)}"],
                    direction="neutral",
                ))

        return factors

    def _extract_data_factors(
        self,
        tape_entries: list[dict[str, object]],
        action_type: ActionType,
    ) -> list[KeyFactor]:
        factors: list[KeyFactor] = []
        importance = self._compute_importance(FactorCategory.DATA_DRIVEN, action_type)

        # Count Tape events as evidence density
        if tape_entries:
            factors.append(KeyFactor(
                name="Evidence Base",
                description=f"Decision is supported by {len(tape_entries)} related Tape event(s).",
                category=FactorCategory.DATA_DRIVEN,
                importance=importance * min(1.0, len(tape_entries) / 10),
                evidence=[f"Tape events: {len(tape_entries)}"],
                direction="supporting",
            ))

        # Check for performance metrics in Tape entries
        metrics_found: list[str] = []
        for entry in tape_entries:
            payload = entry.get("payload", {})
            if isinstance(payload, dict) and "performance_metrics" in payload:
                pm = payload["performance_metrics"]
                if isinstance(pm, dict):
                    metrics_found.extend(pm.keys())

        if metrics_found:
            unique_metrics = list(set(metrics_found))
            factors.append(KeyFactor(
                name="Performance Metrics",
                description=f"Decision referenced {len(unique_metrics)} metric(s): {', '.join(unique_metrics[:5])}.",
                category=FactorCategory.DATA_DRIVEN,
                importance=importance * min(1.0, len(unique_metrics) / 5),
                evidence=[f"Metrics: {', '.join(unique_metrics[:5])}"],
                direction="supporting",
            ))

        return factors

    def _extract_heuristic_factors(
        self,
        action_type: ActionType,
        context: dict[str, object],
    ) -> list[KeyFactor]:
        factors: list[KeyFactor] = []
        importance = self._compute_importance(FactorCategory.HEURISTIC, action_type)

        # Proposal-specific heuristics
        if action_type in (
            ActionType.PROPOSAL_CREATED,
            ActionType.PROPOSAL_APPROVED,
            ActionType.PROPOSAL_REJECTED,
        ):
            mod_type = context.get("modification_type", "")
            if mod_type:
                factors.append(KeyFactor(
                    name="Modification Type Heuristic",
                    description=f"The action targets a {mod_type} change, which influences governance requirements.",
                    category=FactorCategory.HEURISTIC,
                    importance=importance * 0.7,
                    evidence=[f"Modification type: {mod_type}"],
                    direction="neutral",
                ))

        # Skill evolution heuristics
        if action_type in (
            ActionType.SKILL_EVOLUTION,
            ActionType.SKILL_CREATED,
            ActionType.SKILL_DEPRECATED,
            ActionType.SKILL_MERGED,
            ActionType.SKILL_SPLIT,
            ActionType.SKILL_ENHANCED,
        ):
            evo_type = context.get("evolution_type", "")
            if evo_type:
                factors.append(KeyFactor(
                    name="Evolution Type Heuristic",
                    description=f"Skill evolution type is {evo_type}, which determines the safety review level.",
                    category=FactorCategory.HEURISTIC,
                    importance=importance * 0.7,
                    evidence=[f"Evolution type: {evo_type}"],
                    direction="neutral",
                ))

        # Simulation heuristics
        if action_type in (ActionType.SIMULATION_RUN, ActionType.SIMULATION_COMPARISON):
            scenario_type = context.get("scenario_type", "")
            if scenario_type:
                factors.append(KeyFactor(
                    name="Scenario Type Heuristic",
                    description=f"Simulation scenario type is {scenario_type}, which affects interpretation of results.",
                    category=FactorCategory.HEURISTIC,
                    importance=importance * 0.6,
                    evidence=[f"Scenario type: {scenario_type}"],
                    direction="neutral",
                ))

        return factors

    def _extract_historical_factors(
        self,
        tape_entries: list[dict[str, object]],
        action_type: ActionType,
    ) -> list[KeyFactor]:
        factors: list[KeyFactor] = []
        importance = self._compute_importance(FactorCategory.HISTORICAL, action_type)

        # Check for similar past events in Tape
        similar_count = 0
        for entry in tape_entries:
            etype = entry.get("event_type", "")
            if isinstance(etype, str) and action_type.value in etype:
                similar_count += 1

        if similar_count > 1:
            factors.append(KeyFactor(
                name="Historical Precedent",
                description=f"{similar_count} similar past action(s) found in the Tape.",
                category=FactorCategory.HISTORICAL,
                importance=importance * min(1.0, similar_count / 5),
                evidence=[f"Similar past events: {similar_count}"],
                direction="supporting",
            ))

        return factors

    def _extract_constraint_factors(
        self,
        context: dict[str, object],
        action_type: ActionType,
    ) -> list[KeyFactor]:
        factors: list[KeyFactor] = []
        importance = self._compute_importance(FactorCategory.CONSTRAINT, action_type)

        # Check for max_rounds constraint (debates/simulations)
        if "max_rounds" in context:
            max_r = context["max_rounds"]
            if isinstance(max_r, (int, float)):
                factors.append(KeyFactor(
                    name="Round Limit Constraint",
                    description=f"Debate/simulation is constrained to {int(max_r)} round(s).",
                    category=FactorCategory.CONSTRAINT,
                    importance=importance * 0.6,
                    evidence=[f"Max rounds: {int(max_r)}"],
                    direction="neutral",
                ))

        # Check for timeout constraint
        if "timeout_seconds" in context:
            timeout = context["timeout_seconds"]
            if isinstance(timeout, (int, float)):
                factors.append(KeyFactor(
                    name="Timeout Constraint",
                    description=f"Simulation has a {int(timeout)}s timeout limit.",
                    category=FactorCategory.CONSTRAINT,
                    importance=importance * 0.5,
                    evidence=[f"Timeout: {int(timeout)}s"],
                    direction="neutral",
                ))

        return factors

    def _extract_stakeholder_factors(
        self,
        tape_entries: list[dict[str, object]],
        context: dict[str, object],
        action_type: ActionType = ActionType.SYSTEM_ACTION,
    ) -> list[KeyFactor]:
        factors: list[KeyFactor] = []
        importance = self._compute_importance(FactorCategory.STAKEHOLDER, action_type)

        # Check for reviewer/human input
        if "reviewer" in context:
            reviewer = context["reviewer"]
            factors.append(KeyFactor(
                name="Human Review",
                description=f"Action was reviewed by {reviewer}.",
                category=FactorCategory.STAKEHOLDER,
                importance=importance * 0.9,
                evidence=[f"Reviewer: {reviewer}"],
                direction="supporting",
            ))

        # Check for initiator
        if "initiator" in context:
            initiator = context["initiator"]
            factors.append(KeyFactor(
                name="Initiator Input",
                description=f"Action was initiated by {initiator}.",
                category=FactorCategory.STAKEHOLDER,
                importance=importance * 0.6,
                evidence=[f"Initiator: {initiator}"],
                direction="neutral",
            ))

        return factors


# ---------------------------------------------------------------------------
# TraceBuilder — reconstructs the reasoning chain for a decision
# ---------------------------------------------------------------------------


class TraceBuilder:
    """Builds a DecisionTrace by reconstructing the reasoning chain.

    The TraceBuilder analyses Tape events chronologically to identify
    the sequence of steps that led to a decision, including what data
    was consulted, what heuristics were applied, and what alternatives
    were considered.
    """

    async def build_trace(
        self,
        action_id: str,
        action_type: ActionType,
        tape_entries: list[dict[str, object]],
        context: dict[str, object] | None = None,
    ) -> DecisionTrace:
        """Reconstruct the full decision trace for an action.

        Args:
            action_id: The action to trace.
            action_type: Category of the action.
            tape_entries: Related Tape entries (chronological).
            context: Optional additional context.

        Returns:
            A DecisionTrace with the full reasoning chain.
        """
        ctx = context or {}
        steps: list[DecisionStep] = []
        data_sources: list[str] = []
        assumptions: list[str] = []
        limitations: list[str] = []
        confidence_values: list[float] = []

        # Step 1: Data gathering — identify what data was consulted
        if tape_entries:
            data_ids = [
                str(e.get("id", "unknown"))
                for e in tape_entries
                if "id" in e
            ]
            steps.append(DecisionStep(
                step_number=1,
                action="Gathered relevant data from Tape",
                rationale=f"Found {len(tape_entries)} related Tape event(s) providing context for the decision.",
                data_sources=data_ids[:10],
                confidence=1.0,
            ))
            data_sources.extend(data_ids[:10])

        # Step 2: System state assessment
        state_desc = self._describe_system_state(ctx)
        state_conf = self._state_confidence(ctx)
        if state_desc:
            steps.append(DecisionStep(
                step_number=len(steps) + 1,
                action="Assessed current system state",
                rationale=state_desc,
                data_sources=[],
                confidence=state_conf,
            ))
            confidence_values.append(state_conf)

        # Step 3: Risk evaluation
        risk_desc, risk_conf = self._evaluate_risk(ctx)
        if risk_desc:
            steps.append(DecisionStep(
                step_number=len(steps) + 1,
                action="Evaluated risk level",
                rationale=risk_desc,
                data_sources=[],
                confidence=risk_conf,
            ))
            confidence_values.append(risk_conf)

        # Step 4: Heuristic application
        heuristic_desc = self._describe_heuristics(action_type, ctx)
        if heuristic_desc:
            steps.append(DecisionStep(
                step_number=len(steps) + 1,
                action="Applied decision heuristics",
                rationale=heuristic_desc,
                data_sources=[],
                confidence=0.7,
            ))
            confidence_values.append(0.7)

        # Step 5: Confidence estimation
        conf = ctx.get("confidence_score")
        if isinstance(conf, (int, float)):
            steps.append(DecisionStep(
                step_number=len(steps) + 1,
                action="Estimated confidence in the decision",
                rationale=f"Confidence score of {float(conf):.0%} was assigned based on available evidence and heuristic evaluation.",
                data_sources=[],
                confidence=float(conf),
            ))
            confidence_values.append(float(conf))

        # Step 6: Stakeholder review (if applicable)
        reviewer = ctx.get("reviewer")
        if reviewer and isinstance(reviewer, str):
            steps.append(DecisionStep(
                step_number=len(steps) + 1,
                action="Human review and approval",
                rationale=f"Decision was reviewed and approved by {reviewer}.",
                data_sources=[],
                confidence=0.95,
            ))
            confidence_values.append(0.95)

        # Compute total confidence as geometric mean
        total_conf = 0.0
        if confidence_values:
            product = 1.0
            for cv in confidence_values:
                product *= max(cv, 0.01)  # Avoid zero
            total_conf = product ** (1.0 / len(confidence_values))
        elif steps:
            total_conf = 0.5  # Default moderate confidence

        # Extract assumptions and limitations
        assumptions = self._extract_assumptions(action_type, ctx)
        limitations = self._extract_limitations(action_type, ctx)

        # Set timestamps from Tape entries if available
        for i, step in enumerate(steps):
            if i < len(tape_entries):
                ts = tape_entries[i].get("timestamp")
                step.timestamp = ts if isinstance(ts, datetime) else None

        return DecisionTrace(
            action_id=action_id,
            action_type=action_type,
            steps=steps,
            total_confidence=round(total_conf, 3),
            data_sources_used=data_sources,
            assumptions=assumptions,
            limitations=limitations,
        )

    def _describe_system_state(self, context: dict[str, object]) -> str:
        parts: list[str] = []
        if "idle_agents" in context:
            parts.append(f"{context['idle_agents']} idle agent(s)")
        if "error_rate" in context:
            parts.append(f"{context['error_rate']} error rate")
        if "skill_count" in context:
            parts.append(f"{context['skill_count']} skill(s)")
        return "; ".join(parts) if parts else ""

    def _state_confidence(self, context: dict[str, object]) -> float:
        """Confidence in the system state assessment."""
        data_points = sum(
            1 for k in ("idle_agents", "error_rate", "skill_count") if k in context
        )
        if data_points >= 3:
            return 0.9
        if data_points >= 2:
            return 0.75
        if data_points >= 1:
            return 0.6
        return 0.4

    def _evaluate_risk(
        self, context: dict[str, object],
    ) -> tuple[str, float]:
        risk = context.get("risk_level")
        if not isinstance(risk, str):
            return "", 0.0
        conf_map = {"low": 0.9, "medium": 0.7, "high": 0.4}
        return f"Risk level assessed as {risk}", conf_map.get(risk, 0.5)

    def _describe_heuristics(
        self, action_type: ActionType, context: dict[str, object],
    ) -> str:
        if action_type in (
            ActionType.PROPOSAL_CREATED,
            ActionType.PROPOSAL_APPROVED,
        ):
            mod = context.get("modification_type", "unknown")
            return f"Applied governance heuristics for {mod} modification type"
        if action_type in (ActionType.SKILL_EVOLUTION, ActionType.SKILL_ENHANCED):
            evo = context.get("evolution_type", "unknown")
            return f"Applied skill evolution heuristics for {evo} evolution type"
        if action_type in (ActionType.SIMULATION_RUN,):
            return "Applied simulation safety and isolation heuristics"
        if action_type in (ActionType.DEBATE_CONCLUDED,):
            return "Applied debate quality and consensus heuristics"
        return "Applied general system decision heuristics"

    def _extract_assumptions(
        self, action_type: ActionType, context: dict[str, object],
    ) -> list[str]:
        assumptions: list[str] = []
        if action_type in (
            ActionType.PROPOSAL_CREATED,
            ActionType.PROPOSAL_APPROVED,
        ):
            assumptions.append("Current system state is representative of near-term future")
            assumptions.append("Risk assessment covers the most significant risk factors")
        if action_type in (ActionType.SIMULATION_RUN,):
            assumptions.append("Simulation environment accurately models production behavior")
            assumptions.append("Timeout is sufficient to capture meaningful results")
        if action_type in (ActionType.DEBATE_CONCLUDED,):
            assumptions.append("Debate participants represent diverse viewpoints")
            assumptions.append("Consensus tracking heuristics are calibrated")
        if action_type in (
            ActionType.SKILL_EVOLUTION,
            ActionType.SKILL_ENHANCED,
        ):
            assumptions.append("Skill performance metrics are accurate and recent")
        assumptions.append("Tape history is complete and uncorrupted")
        return assumptions

    def _extract_limitations(
        self, action_type: ActionType, context: dict[str, object],
    ) -> list[str]:
        limitations: list[str] = []
        conf = context.get("confidence_score")
        if isinstance(conf, (int, float)) and float(conf) < 0.5:
            limitations.append("Low confidence score — decision should be treated with caution")
        risk = context.get("risk_level")
        if risk == "high":
            limitations.append("High risk — implementation should include rollback plan")
        if action_type in (ActionType.SIMULATION_RUN,):
            limitations.append("Simulation results are based on a sandboxed environment")
            limitations.append("Results may not fully predict production behavior")
        if action_type in (ActionType.DEBATE_CONCLUDED,):
            limitations.append("Debate outcome depends on participant selection and argument quality")
        limitations.append("Explanations are based on available data; unknown factors may exist")
        return limitations


# ---------------------------------------------------------------------------
# ExplanationGenerator — creates human-readable explanations
# ---------------------------------------------------------------------------


class ExplanationGenerator:
    """Generates technical and simplified explanations for system actions.

    The ExplanationGenerator uses FactorExtractor and TraceBuilder to
    produce structured explanations that are both machine-readable and
    human-friendly.
    """

    def __init__(
        self,
        factor_extractor: FactorExtractor | None = None,
        trace_builder: TraceBuilder | None = None,
    ) -> None:
        self._extractor = factor_extractor or FactorExtractor()
        self._trace_builder = trace_builder or TraceBuilder()

    async def generate(
        self,
        action_id: str,
        action_type: ActionType,
        tape_entries: list[dict[str, object]],
        context: dict[str, object] | None = None,
    ) -> Explanation:
        """Generate a complete explanation for a system action.

        Args:
            action_id: The action to explain.
            action_type: Category of the action.
            tape_entries: Related Tape entries (as dicts).
            context: Optional additional context from other modules.

        Returns:
            A fully populated Explanation object.
        """
        ctx = context or {}

        # Extract key factors
        factors = self._extractor.extract_factors(
            action_id, action_type, tape_entries, ctx,
        )

        # Build decision trace
        trace = await self._trace_builder.build_trace(
            action_id, action_type, tape_entries, ctx,
        )

        # Compute overall confidence
        confidence = trace.total_confidence
        conf_override = ctx.get("confidence_score")
        if isinstance(conf_override, (int, float)):
            # Blend: 60% trace confidence + 40% explicit confidence
            confidence = 0.6 * confidence + 0.4 * float(conf_override)

        # Determine risk level
        risk = self._determine_risk(factors, ctx)

        # Generate summaries
        technical = await self._generate_technical_summary(
            action_id, action_type, factors, trace, ctx,
        )
        simplified = await self._generate_simplified_summary(
            action_id, action_type, factors, trace, ctx,
        )

        # Collect related Tape entry IDs
        related_ids = [
            str(e.get("id", ""))
            for e in tape_entries
            if e.get("id")
        ]

        # Build alternative comparison if alternatives are provided
        alt_comparison = self._build_alternative_comparison(
            action_id, action_type, factors, ctx,
        )

        return Explanation(
            action_id=action_id,
            action_type=action_type,
            technical_summary=technical,
            simplified_summary=simplified,
            key_factors=factors[:5],  # Top 5 factors
            decision_trace=trace,
            alternative_comparison=alt_comparison,
            confidence=round(confidence, 3),
            risk_level=risk,
            related_tape_entries=related_ids,
            metadata=ctx,
        )

    def _determine_risk(
        self, factors: list[KeyFactor], context: dict[str, object],
    ) -> str:
        if "risk_level" in context:
            return str(context["risk_level"])
        # Derive from factors
        risk_factors = [
            f for f in factors if f.category == FactorCategory.RISK_ASSESSMENT
        ]
        if risk_factors:
            evidence = " ".join(risk_factors[0].evidence)
            if "high" in evidence:
                return "high"
            if "medium" in evidence:
                return "medium"
            if "low" in evidence:
                return "low"
        # Heuristic: high opposing factors = higher risk
        opposing = [f for f in factors if f.direction == "opposing"]
        if len(opposing) >= 3:
            return "high"
        if len(opposing) >= 1:
            return "medium"
        return "low"

    async def _generate_technical_summary(
        self,
        action_id: str,
        action_type: ActionType,
        factors: list[KeyFactor],
        trace: DecisionTrace,
        context: dict[str, object],
    ) -> str:
        """Generate a technical summary, optionally enhanced by LLM."""
        from packages.llm import get_llm_provider, is_llm_enabled

        parts: list[str] = []

        # Opening: action description
        parts.append(f"Action `{action_id}` (type: {action_type.value}) was executed by the system.")

        # Key factors summary
        if factors:
            top = factors[:3]
            factor_desc = "; ".join(
                f"{f.name} ({f.direction}, importance={f.importance:.2f})"
                for f in top
            )
            parts.append(f"Key influences: {factor_desc}.")

        # Trace summary
        if trace.steps:
            parts.append(
                f"Decision trace: {len(trace.steps)} step(s), "
                f"total confidence={trace.total_confidence:.3f}."
            )

        # Risk
        risk = context.get("risk_level", "unknown")
        parts.append(f"Risk assessment: {risk}.")

        # Assumptions
        if trace.assumptions:
            parts.append(f"Assumptions: {'; '.join(trace.assumptions[:3])}.")

        # Limitations
        if trace.limitations:
            parts.append(f"Limitations: {'; '.join(trace.limitations[:2])}.")

        base_summary = " ".join(parts)

        if is_llm_enabled():
            llm = get_llm_provider()
            prompt = (
                f"Rewrite the following technical summary into a concise, "
                f"professional paragraph (max 3 sentences):\n\n{base_summary}"
            )
            try:
                enhanced = await llm.generate(prompt, max_tokens=256)
                if enhanced.strip():
                    return enhanced.strip()
            except Exception:
                pass  # Fall back to base summary

        return base_summary

    async def _generate_simplified_summary(
        self,
        action_id: str,
        action_type: ActionType,
        factors: list[KeyFactor],
        trace: DecisionTrace,
        context: dict[str, object],
    ) -> str:
        """Generate a plain-English summary, optionally enhanced by LLM."""
        from packages.llm import get_llm_provider, is_llm_enabled

        # Human-friendly action description
        action_labels: dict[str, str] = {
            ActionType.PROPOSAL_CREATED: "a new change proposal was created",
            ActionType.PROPOSAL_APPROVED: "a change proposal was approved",
            ActionType.PROPOSAL_REJECTED: "a change proposal was rejected",
            ActionType.PROPOSAL_IMPLEMENTED: "a change proposal was implemented",
            ActionType.SKILL_EVOLUTION: "a skill was evolved",
            ActionType.SKILL_CREATED: "a new skill was created",
            ActionType.SKILL_DEPRECATED: "a skill was deprecated",
            ActionType.SKILL_MERGED: "skills were merged",
            ActionType.SKILL_SPLIT: "a skill was split",
            ActionType.SKILL_ENHANCED: "a skill was enhanced",
            ActionType.SIMULATION_RUN: "a what-if simulation was run",
            ActionType.SIMULATION_COMPARISON: "simulation results were compared",
            ActionType.DEBATE_STARTED: "a structured debate was started",
            ActionType.DEBATE_ROUND: "a debate round was completed",
            ActionType.DEBATE_CONCLUDED: "a debate was concluded",
            ActionType.TAPE_ENTRY: "an event was logged",
            ActionType.INTROSPECTION: "the system examined itself",
            ActionType.SYSTEM_ACTION: "a system action was performed",
        }

        label = action_labels.get(action_type, "an action was taken")

        parts: list[str] = [f"The system decided that {label}."]

        # Top factors in plain English
        supporting = [f for f in factors if f.direction == "supporting"][:2]
        opposing = [f for f in factors if f.direction == "opposing"][:2]

        if supporting:
            support_desc = " and ".join(f.name.lower() for f in supporting)
            parts.append(f"This was supported by {support_desc}.")

        if opposing:
            oppose_desc = " and ".join(f.name.lower() for f in opposing)
            parts.append(f"Concerns included {oppose_desc}.")

        # Confidence
        conf = trace.total_confidence
        if conf >= 0.8:
            parts.append("The system is highly confident in this decision.")
        elif conf >= 0.6:
            parts.append("The system is moderately confident in this decision.")
        elif conf >= 0.4:
            parts.append("The system has limited confidence in this decision — caution is advised.")
        else:
            parts.append("The system has low confidence in this decision — human review is recommended.")

        # Risk
        risk = context.get("risk_level", "unknown")
        if risk == "high":
            parts.append("⚠ This action carries high risk.")
        elif risk == "medium":
            parts.append("This action carries moderate risk.")

        base_summary = " ".join(parts)

        if is_llm_enabled():
            llm = get_llm_provider()
            prompt = (
                f"Rewrite the following summary into plain English that a "
                f"non-technical person can understand (max 3 sentences):\n\n"
                f"{base_summary}"
            )
            try:
                enhanced = await llm.generate(prompt, max_tokens=256)
                if enhanced.strip():
                    return enhanced.strip()
            except Exception:
                pass  # Fall back to base summary

        return base_summary

    def _build_alternative_comparison(
        self,
        action_id: str,
        action_type: ActionType,
        factors: list[KeyFactor],
        context: dict[str, object],
    ) -> AlternativeComparison | None:
        alternatives_data = context.get("alternatives")
        if not isinstance(alternatives_data, list) or not alternatives_data:
            return None

        chosen_score = 0.0
        conf = context.get("confidence_score")
        if isinstance(conf, (int, float)):
            chosen_score = float(conf)

        chosen_label = context.get("chosen_label", action_id)
        if not isinstance(chosen_label, str):
            chosen_label = str(chosen_label)

        alts: list[Alternative] = []
        for alt in alternatives_data:
            if not isinstance(alt, dict):
                continue
            alt_score = float(alt.get("score", 0.0))
            outcome = self._classify_alternative(chosen_score, alt_score)
            alts.append(Alternative(
                action_id=str(alt.get("action_id", "")),
                label=str(alt.get("label", "Alternative")),
                description=str(alt.get("description", "")),
                score=alt_score,
                outcome=outcome,
                pros=alt.get("pros", []) if isinstance(alt.get("pros"), list) else [],
                cons=alt.get("cons", []) if isinstance(alt.get("cons"), list) else [],
                key_differences=(
                    alt.get("key_differences", [])
                    if isinstance(alt.get("key_differences"), list)
                    else []
                ),
            ))

        if not alts:
            return None

        trade_offs = self._identify_trade_offs(chosen_score, alts)

        summary = self._generate_comparison_summary(
            chosen_label, chosen_score, alts,
        )

        return AlternativeComparison(
            action_id=action_id,
            chosen_label=chosen_label,
            chosen_score=chosen_score,
            alternatives=alts,
            summary=summary,
            trade_offs=trade_offs,
        )

    def _classify_alternative(
        self, chosen_score: float, alt_score: float,
    ) -> AlternativeOutcome:
        if math.isclose(chosen_score, alt_score, abs_tol=0.05):
            return AlternativeOutcome.EQUIVALENT
        if alt_score > chosen_score + 0.1:
            return AlternativeOutcome.SUPERIOR
        if alt_score < chosen_score - 0.1:
            return AlternativeOutcome.INFERIOR
        return AlternativeOutcome.INCOMPARABLE

    def _identify_trade_offs(
        self, chosen_score: float, alternatives: list[Alternative],
    ) -> list[str]:
        trade_offs: list[str] = []
        for alt in alternatives:
            if alt.outcome == AlternativeOutcome.SUPERIOR:
                trade_offs.append(
                    f"{alt.label} scored higher ({alt.score:.2f} vs {chosen_score:.2f}) "
                    f"but was not chosen — consider reviewing"
                )
            elif alt.outcome == AlternativeOutcome.EQUIVALENT:
                trade_offs.append(
                    f"{alt.label} performed equivalently ({alt.score:.2f}) "
                    f"and may be viable in different contexts"
                )
        return trade_offs

    def _generate_comparison_summary(
        self,
        chosen_label: str,
        chosen_score: float,
        alternatives: list[Alternative],
    ) -> str:
        if not alternatives:
            return ""
        superior = [a for a in alternatives if a.outcome == AlternativeOutcome.SUPERIOR]
        inferior = [a for a in alternatives if a.outcome == AlternativeOutcome.INFERIOR]
        equivalent = [a for a in alternatives if a.outcome == AlternativeOutcome.EQUIVALENT]

        parts = [f"\"{chosen_label}\" was chosen with a score of {chosen_score:.2f}."]
        if superior:
            names = ", ".join(a.label for a in superior)
            parts.append(
                f"Note: {names} scored higher but had other trade-offs."
            )
        if equivalent:
            names = ", ".join(a.label for a in equivalent)
            parts.append(f"{names} performed similarly and are viable alternatives.")
        if inferior:
            names = ", ".join(a.label for a in inferior)
            parts.append(f"{names} scored lower and were less favourable.")

        return " ".join(parts)


# ---------------------------------------------------------------------------
# ExplainabilityEngine — the main public API
# ---------------------------------------------------------------------------


class ExplainabilityEngine:
    """Full-transparency explainability engine for InkosAI.

    Generates explanations, decision traces, key factor highlights, and
    alternative comparisons for any system action. All operations are
    logged to the Tape for full auditability.

    Usage::

        engine = ExplainabilityEngine(tape_service=tape_svc)

        # Generate a full explanation
        explanation = await engine.generate_explanation(
            action_id="proposal-abc123",
            action_type=ActionType.PROPOSAL_CREATED,
            context={"risk_level": "low", "confidence_score": 0.85},
        )

        # Get the decision trace
        trace = await engine.get_decision_trace(action_id="proposal-abc123")

        # Highlight key factors
        factors = await engine.highlight_key_factors(action_id="proposal-abc123")

        # Compare alternatives
        comparison = await engine.compare_alternatives(
            action_id="proposal-abc123",
            alternatives=[
                {"action_id": "alt-1", "label": "Option B", "score": 0.7},
                {"action_id": "alt-2", "label": "Option C", "score": 0.5},
            ],
        )
    """

    def __init__(
        self,
        tape_service: TapeService,
        store: ExplanationStore | None = None,
        generator: ExplanationGenerator | None = None,
        profile_engine: IntelligenceProfileEngine | None = None,
    ) -> None:
        self._tape = tape_service
        self._store = store or ExplanationStore()
        self._generator = generator or ExplanationGenerator()
        self._profile_engine = profile_engine

    # ------------------------------------------------------------------
    # generate_explanation
    # ------------------------------------------------------------------

    async def generate_explanation(
        self,
        action_id: str,
        action_type: ActionType,
        context: dict[str, object] | None = None,
        tape_entries: list[dict[str, object]] | None = None,
    ) -> Explanation:
        """Create a human-readable explanation for a system action.

        Fetches related Tape entries, extracts key factors, builds a
        decision trace, and produces both technical and simplified
        summaries.  The explanation is stored and logged to the Tape.

        Args:
            action_id: Identifier of the action to explain.
            action_type: Category of the action.
            context: Optional context dict (risk_level, confidence_score, etc.).
            tape_entries: Optional pre-fetched Tape entries; if not provided,
                          they will be queried from the TapeService.

        Returns:
            A fully populated Explanation object.
        """
        ctx = context or {}

        # Fetch Tape entries if not provided
        if tape_entries is None:
            tape_entries = await self._fetch_tape_entries(action_id, action_type)

        explanation = await self._generator.generate(
            action_id=action_id,
            action_type=action_type,
            tape_entries=tape_entries,
            context=ctx,
        )

        # Store the explanation
        self._store.add(explanation)

        # Log to Tape
        await self._tape.log_event(
            event_type="explainability.explanation_generated",
            payload={
                "explanation_id": str(explanation.id),
                "action_id": action_id,
                "action_type": action_type.value,
                "confidence": explanation.confidence,
                "risk_level": explanation.risk_level,
                "factor_count": len(explanation.key_factors),
            },
            agent_id="explainability-engine",
        )

        return explanation

    # ------------------------------------------------------------------
    # get_decision_trace
    # ------------------------------------------------------------------

    async def get_decision_trace(
        self,
        action_id: str,
        action_type: ActionType | None = None,
        context: dict[str, object] | None = None,
    ) -> DecisionTrace:
        """Reconstruct the full chain of reasoning behind a decision.

        Args:
            action_id: The action to trace.
            action_type: Category of the action (inferred if not provided).
            context: Optional additional context.

        Returns:
            A DecisionTrace with the step-by-step reasoning chain.
        """
        ctx = context or {}
        a_type = action_type or ActionType.SYSTEM_ACTION

        tape_entries = await self._fetch_tape_entries(action_id, a_type)

        trace = await self._generator._trace_builder.build_trace(
            action_id=action_id,
            action_type=a_type,
            tape_entries=tape_entries,
            context=ctx,
        )

        # Log to Tape
        await self._tape.log_event(
            event_type="explainability.trace_requested",
            payload={
                "action_id": action_id,
                "action_type": a_type.value,
                "step_count": len(trace.steps),
                "total_confidence": trace.total_confidence,
            },
            agent_id="explainability-engine",
        )

        return trace

    # ------------------------------------------------------------------
    # highlight_key_factors
    # ------------------------------------------------------------------

    async def highlight_key_factors(
        self,
        action_id: str,
        action_type: ActionType | None = None,
        context: dict[str, object] | None = None,
        top_n: int = 5,
    ) -> list[KeyFactor]:
        """Identify the top N factors that most influenced a decision.

        Args:
            action_id: The action to analyse.
            action_type: Category of the action (inferred if not provided).
            context: Optional additional context.
            top_n: Maximum number of factors to return (default: 5).

        Returns:
            A list of KeyFactor objects, sorted by importance (descending).
        """
        ctx = context or {}
        a_type = action_type or ActionType.SYSTEM_ACTION

        tape_entries = await self._fetch_tape_entries(action_id, a_type)

        factors = self._generator._extractor.extract_factors(
            action_id=action_id,
            action_type=a_type,
            tape_entries=tape_entries,
            context=ctx,
        )

        # Log to Tape
        await self._tape.log_event(
            event_type="explainability.factors_highlighted",
            payload={
                "action_id": action_id,
                "factor_count": len(factors[:top_n]),
                "top_factor": factors[0].name if factors else "",
            },
            agent_id="explainability-engine",
        )

        return factors[:top_n]

    # ------------------------------------------------------------------
    # compare_alternatives
    # ------------------------------------------------------------------

    async def compare_alternatives(
        self,
        action_id: str,
        alternatives: list[dict[str, object]],
        action_type: ActionType | None = None,
        context: dict[str, object] | None = None,
    ) -> AlternativeComparison:
        """Explain why one option was chosen over alternatives.

        Args:
            action_id: The chosen action.
            alternatives: List of alternative options (as dicts with
                action_id, label, description, score, pros, cons).
            action_type: Category of the action (inferred if not provided).
            context: Optional additional context.

        Returns:
            An AlternativeComparison with relative scoring.
        """
        ctx = context or {}
        a_type = action_type or ActionType.SYSTEM_ACTION

        # Inject alternatives into context for the generator
        ctx_with_alts = {**ctx, "alternatives": alternatives}

        tape_entries = await self._fetch_tape_entries(action_id, a_type)

        explanation = await self._generator.generate(
            action_id=action_id,
            action_type=a_type,
            tape_entries=tape_entries,
            context=ctx_with_alts,
        )

        if explanation.alternative_comparison is None:
            # Build a basic comparison even without alternatives data
            explanation.alternative_comparison = AlternativeComparison(
                action_id=action_id,
                chosen_label=action_id,
                chosen_score=explanation.confidence,
                alternatives=[],
                summary="No alternatives were provided for comparison.",
                trade_offs=[],
            )

        # Log to Tape
        await self._tape.log_event(
            event_type="explainability.alternatives_compared",
            payload={
                "action_id": action_id,
                "alternative_count": len(alternatives),
                "chosen_score": explanation.alternative_comparison.chosen_score,
            },
            agent_id="explainability-engine",
        )

        return explanation.alternative_comparison

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    async def get_explanation(self, explanation_id: UUID) -> Explanation:
        """Retrieve a stored explanation by its ID.

        Args:
            explanation_id: The UUID of the explanation.

        Returns:
            The Explanation object.

        Raises:
            ExplanationNotFoundError: if the explanation does not exist.
        """
        exp = self._store.get(explanation_id)
        if exp is None:
            raise ExplanationNotFoundError(
                f"Explanation {explanation_id} not found"
            )
        return exp

    async def get_explanations_for_action(
        self, action_id: str,
    ) -> list[Explanation]:
        """Retrieve all explanations for a specific action.

        Args:
            action_id: The action to look up.

        Returns:
            List of Explanation objects for the action.
        """
        return self._store.get_by_action(action_id)

    async def list_explanations(
        self,
        action_type: ActionType | None = None,
    ) -> list[Explanation]:
        """List all stored explanations, optionally filtered by action type.

        Args:
            action_type: Optional filter by action category.

        Returns:
            List of Explanation objects, newest first.
        """
        return self._store.list_all(action_type=action_type)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _fetch_tape_entries(
        self,
        action_id: str,
        action_type: ActionType,
    ) -> list[dict[str, object]]:
        """Fetch related Tape entries for an action.

        Attempts to find Tape entries whose payload references the action_id
        or whose event_type matches the action_type.  Returns an empty list
        on any error (best-effort).
        """
        entries: list[dict[str, object]] = []
        with contextlib.suppress(Exception):
            # Try to find entries related to this action
            all_entries = await self._tape.get_entries(limit=100)
            for entry in all_entries:
                payload = entry.payload if isinstance(entry.payload, dict) else {}
                # Match if the action_id appears in the payload or event_type matches
                if (
                    str(payload.get("action_id")) == action_id
                    or str(payload.get("proposal_id")) == action_id
                    or str(payload.get("debate_id")) == action_id
                    or str(payload.get("simulation_id")) == action_id
                    or action_type.value in (entry.event_type or "")
                ):
                    entries.append({
                        "id": str(entry.id),
                        "event_type": entry.event_type,
                        "payload": payload,
                        "timestamp": entry.timestamp,
                        "agent_id": entry.agent_id,
                    })
        return entries
