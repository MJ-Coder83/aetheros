"""Unit tests for the Explainability Dashboard.

Run with: pytest tests/test_explainability.py -v
"""

import pytest

from packages.prime.explainability import (
    ActionType,
    AlternativeOutcome,
    DecisionStep,
    DecisionTrace,
    ExplainabilityEngine,
    Explanation,
    ExplanationGenerator,
    ExplanationMode,
    ExplanationNotFoundError,
    ExplanationStore,
    FactorCategory,
    FactorExtractor,
    KeyFactor,
    TraceBuilder,
)
from packages.tape.repository import InMemoryTapeRepository
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tape_svc() -> TapeService:
    return TapeService(InMemoryTapeRepository())


@pytest.fixture()
def engine(tape_svc: TapeService) -> ExplainabilityEngine:
    return ExplainabilityEngine(tape_service=tape_svc)


@pytest.fixture()
def store() -> ExplanationStore:
    return ExplanationStore()


@pytest.fixture()
def extractor() -> FactorExtractor:
    return FactorExtractor()


@pytest.fixture()
def trace_builder() -> TraceBuilder:
    return TraceBuilder()


@pytest.fixture()
def generator() -> ExplanationGenerator:
    return ExplanationGenerator()


# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------


def _tape_entry(
    event_type: str = "proposal.created",
    payload: dict[str, object] | None = None,
    entry_id: str = "entry-1",
) -> dict[str, object]:
    return {
        "id": entry_id,
        "event_type": event_type,
        "payload": payload or {},
        "timestamp": None,
        "agent_id": "prime",
    }


def _proposal_context() -> dict[str, object]:
    return {
        "risk_level": "medium",
        "confidence_score": 0.82,
        "modification_type": "behavior_change",
        "reviewer": "alice",
        "idle_agents": 2,
        "error_rate": 0.05,
        "skill_count": 8,
    }


def _simulation_context() -> dict[str, object]:
    return {
        "risk_level": "low",
        "confidence_score": 0.75,
        "scenario_type": "stress_test",
        "timeout_seconds": 60,
        "error_rate": 0.02,
    }


def _debate_context() -> dict[str, object]:
    return {
        "risk_level": "low",
        "confidence_score": 0.9,
        "max_rounds": 3,
        "initiator": "prime",
    }


# ===========================================================================
# ExplanationStore tests
# ===========================================================================


class TestExplanationStore:
    """Tests for the in-memory explanation store."""

    def test_add_and_get(self, store: ExplanationStore) -> None:
        exp = Explanation(
            action_id="act-1",
            action_type=ActionType.PROPOSAL_CREATED,
        )
        store.add(exp)
        assert store.get(exp.id) is exp

    def test_get_not_found(self, store: ExplanationStore) -> None:
        from uuid import uuid4

        assert store.get(uuid4()) is None

    def test_get_by_action(self, store: ExplanationStore) -> None:
        exp = Explanation(
            action_id="act-1",
            action_type=ActionType.PROPOSAL_CREATED,
        )
        store.add(exp)
        results = store.get_by_action("act-1")
        assert len(results) == 1
        assert results[0].id == exp.id

    def test_get_by_action_empty(self, store: ExplanationStore) -> None:
        results = store.get_by_action("nonexistent")
        assert results == []

    def test_list_all(self, store: ExplanationStore) -> None:
        store.add(Explanation(action_id="a", action_type=ActionType.PROPOSAL_CREATED))
        store.add(Explanation(action_id="b", action_type=ActionType.SIMULATION_RUN))
        assert len(store.list_all()) == 2

    def test_list_by_action_type(self, store: ExplanationStore) -> None:
        store.add(Explanation(action_id="a", action_type=ActionType.PROPOSAL_CREATED))
        store.add(Explanation(action_id="b", action_type=ActionType.SIMULATION_RUN))
        store.add(Explanation(action_id="c", action_type=ActionType.PROPOSAL_CREATED))
        proposals = store.list_all(action_type=ActionType.PROPOSAL_CREATED)
        assert len(proposals) == 2
        sims = store.list_all(action_type=ActionType.SIMULATION_RUN)
        assert len(sims) == 1

    def test_remove(self, store: ExplanationStore) -> None:
        exp = Explanation(action_id="to-remove", action_type=ActionType.SYSTEM_ACTION)
        store.add(exp)
        store.remove(exp.id)
        assert store.get(exp.id) is None

    def test_remove_nonexistent(self, store: ExplanationStore) -> None:
        from uuid import uuid4

        # Should not raise
        store.remove(uuid4())

    def test_list_sorted_by_created_at_desc(self, store: ExplanationStore) -> None:
        e1 = Explanation(action_id="old", action_type=ActionType.SYSTEM_ACTION)
        e2 = Explanation(action_id="new", action_type=ActionType.SYSTEM_ACTION)
        store.add(e1)
        store.add(e2)
        all_exps = store.list_all()
        assert all_exps[0].created_at >= all_exps[1].created_at


# ===========================================================================
# FactorExtractor tests
# ===========================================================================


class TestFactorExtractor:
    """Tests for key factor extraction from Tape and context."""

    def test_extract_risk_factor(self, extractor: FactorExtractor) -> None:
        ctx: dict[str, object] = {"risk_level": "high"}
        factors = extractor.extract_factors("act-1", ActionType.PROPOSAL_CREATED, [], ctx)
        risk_factors = [f for f in factors if f.category == FactorCategory.RISK_ASSESSMENT]
        assert len(risk_factors) == 1
        assert risk_factors[0].direction == "opposing"

    def test_extract_risk_factor_low(self, extractor: FactorExtractor) -> None:
        ctx: dict[str, object] = {"risk_level": "low"}
        factors = extractor.extract_factors("act-1", ActionType.PROPOSAL_CREATED, [], ctx)
        risk_factors = [f for f in factors if f.category == FactorCategory.RISK_ASSESSMENT]
        assert len(risk_factors) == 1
        assert risk_factors[0].direction == "supporting"

    def test_extract_confidence_factor(self, extractor: FactorExtractor) -> None:
        ctx: dict[str, object] = {"confidence_score": 0.85}
        factors = extractor.extract_factors("act-1", ActionType.PROPOSAL_CREATED, [], ctx)
        conf_factors = [f for f in factors if f.category == FactorCategory.CONFIDENCE]
        assert len(conf_factors) == 1
        assert conf_factors[0].direction == "supporting"

    def test_extract_low_confidence_factor(self, extractor: FactorExtractor) -> None:
        ctx: dict[str, object] = {"confidence_score": 0.3}
        factors = extractor.extract_factors("act-1", ActionType.PROPOSAL_CREATED, [], ctx)
        conf_factors = [f for f in factors if f.category == FactorCategory.CONFIDENCE]
        assert len(conf_factors) == 1
        assert conf_factors[0].direction == "opposing"

    def test_extract_system_state_idle_agents(
        self, extractor: FactorExtractor,
    ) -> None:
        ctx: dict[str, object] = {"idle_agents": 3}
        factors = extractor.extract_factors("act-1", ActionType.PROPOSAL_CREATED, [], ctx)
        state_factors = [f for f in factors if f.name == "Idle Agents"]
        assert len(state_factors) == 1

    def test_extract_system_state_error_rate(
        self, extractor: FactorExtractor,
    ) -> None:
        ctx: dict[str, object] = {"error_rate": 0.15}
        factors = extractor.extract_factors("act-1", ActionType.PROPOSAL_CREATED, [], ctx)
        state_factors = [f for f in factors if f.name == "Error Rate"]
        assert len(state_factors) == 1
        assert state_factors[0].direction == "opposing"

    def test_extract_evidence_base_from_tape(
        self, extractor: FactorExtractor,
    ) -> None:
        entries = [_tape_entry(entry_id=f"e{i}") for i in range(5)]
        factors = extractor.extract_factors("act-1", ActionType.PROPOSAL_CREATED, entries, {})
        data_factors = [f for f in factors if f.name == "Evidence Base"]
        assert len(data_factors) == 1
        assert "5" in data_factors[0].evidence[0]

    def test_extract_performance_metrics(
        self, extractor: FactorExtractor,
    ) -> None:
        entries = [_tape_entry(payload={"performance_metrics": {"latency": 42, "throughput": 100}})]
        factors = extractor.extract_factors("act-1", ActionType.PROPOSAL_CREATED, entries, {})
        metric_factors = [f for f in factors if f.name == "Performance Metrics"]
        assert len(metric_factors) == 1

    def test_extract_heuristic_proposal(
        self, extractor: FactorExtractor,
    ) -> None:
        ctx: dict[str, object] = {"modification_type": "architecture_change"}
        factors = extractor.extract_factors(
            "act-1", ActionType.PROPOSAL_CREATED, [], ctx,
        )
        heuristic_factors = [f for f in factors if "Heuristic" in f.name]
        assert len(heuristic_factors) >= 1

    def test_extract_heuristic_skill_evolution(
        self, extractor: FactorExtractor,
    ) -> None:
        ctx: dict[str, object] = {"evolution_type": "enhance"}
        factors = extractor.extract_factors(
            "act-1", ActionType.SKILL_EVOLUTION, [], ctx,
        )
        heuristic_factors = [f for f in factors if "Heuristic" in f.name]
        assert len(heuristic_factors) >= 1

    def test_extract_historical_precedent(
        self, extractor: FactorExtractor,
    ) -> None:
        entries = [
            _tape_entry(event_type="proposal_created", entry_id=f"h{i}")
            for i in range(3)
        ]
        factors = extractor.extract_factors(
            "act-1", ActionType.PROPOSAL_CREATED, entries, {},
        )
        historical = [f for f in factors if f.category == FactorCategory.HISTORICAL]
        assert len(historical) >= 1

    def test_extract_stakeholder_reviewer(
        self, extractor: FactorExtractor,
    ) -> None:
        ctx: dict[str, object] = {"reviewer": "alice"}
        factors = extractor.extract_factors(
            "act-1", ActionType.PROPOSAL_APPROVED, [], ctx,
        )
        stakeholder = [f for f in factors if f.category == FactorCategory.STAKEHOLDER]
        assert len(stakeholder) >= 1

    def test_extract_constraint_max_rounds(
        self, extractor: FactorExtractor,
    ) -> None:
        ctx: dict[str, object] = {"max_rounds": 5}
        factors = extractor.extract_factors(
            "act-1", ActionType.DEBATE_CONCLUDED, [], ctx,
        )
        constraint = [f for f in factors if f.category == FactorCategory.CONSTRAINT]
        assert len(constraint) >= 1

    def test_factors_sorted_by_importance(
        self, extractor: FactorExtractor,
    ) -> None:
        ctx = _proposal_context()
        entries = [_tape_entry(entry_id=f"e{i}") for i in range(8)]
        factors = extractor.extract_factors(
            "act-1", ActionType.PROPOSAL_CREATED, entries, ctx,
        )
        for i in range(len(factors) - 1):
            assert factors[i].importance >= factors[i + 1].importance

    def test_no_context_no_tape(self, extractor: FactorExtractor) -> None:
        factors = extractor.extract_factors(
            "act-1", ActionType.SYSTEM_ACTION, [], {},
        )
        # Should return some default factors, possibly empty
        assert isinstance(factors, list)

    def test_skill_count_factor(
        self, extractor: FactorExtractor,
    ) -> None:
        ctx: dict[str, object] = {"skill_count": 12}
        factors = extractor.extract_factors("act-1", ActionType.PROPOSAL_CREATED, [], ctx)
        skill_f = [f for f in factors if f.name == "Skill Coverage"]
        assert len(skill_f) == 1


# ===========================================================================
# TraceBuilder tests
# ===========================================================================


class TestTraceBuilder:
    """Tests for decision trace reconstruction."""

    @pytest.mark.asyncio
    async def test_build_trace_with_tape(
        self, trace_builder: TraceBuilder,
    ) -> None:
        entries = [_tape_entry(entry_id=f"e{i}") for i in range(3)]
        ctx = _proposal_context()
        trace = await trace_builder.build_trace(
            "act-1", ActionType.PROPOSAL_CREATED, entries, ctx,
        )
        assert trace.action_id == "act-1"
        assert len(trace.steps) >= 1  # At minimum, data gathering step
        assert trace.total_confidence > 0.0

    @pytest.mark.asyncio
    async def test_build_trace_steps_include_data_gathering(
        self, trace_builder: TraceBuilder,
    ) -> None:
        entries = [_tape_entry(entry_id="e1")]
        trace = await trace_builder.build_trace(
            "act-1", ActionType.PROPOSAL_CREATED, entries, {},
        )
        step_actions = [s.action for s in trace.steps]
        assert any("Gathered" in a for a in step_actions)

    @pytest.mark.asyncio
    async def test_build_trace_system_state_step(
        self, trace_builder: TraceBuilder,
    ) -> None:
        ctx: dict[str, object] = {"idle_agents": 2, "error_rate": 0.05}
        trace = await trace_builder.build_trace(
            "act-1", ActionType.PROPOSAL_CREATED, [], ctx,
        )
        step_actions = [s.action for s in trace.steps]
        assert any("system state" in a.lower() for a in step_actions)

    @pytest.mark.asyncio
    async def test_build_trace_risk_evaluation_step(
        self, trace_builder: TraceBuilder,
    ) -> None:
        ctx: dict[str, object] = {"risk_level": "medium"}
        trace = await trace_builder.build_trace(
            "act-1", ActionType.PROPOSAL_CREATED, [], ctx,
        )
        step_actions = [s.action for s in trace.steps]
        assert any("risk" in a.lower() for a in step_actions)

    @pytest.mark.asyncio
    async def test_build_trace_confidence_estimation(
        self, trace_builder: TraceBuilder,
    ) -> None:
        ctx: dict[str, object] = {"confidence_score": 0.88}
        trace = await trace_builder.build_trace(
            "act-1", ActionType.PROPOSAL_CREATED, [], ctx,
        )
        step_actions = [s.action for s in trace.steps]
        assert any("confidence" in a.lower() for a in step_actions)

    @pytest.mark.asyncio
    async def test_build_trace_human_review_step(
        self, trace_builder: TraceBuilder,
    ) -> None:
        ctx: dict[str, object] = {"reviewer": "bob"}
        trace = await trace_builder.build_trace(
            "act-1", ActionType.PROPOSAL_APPROVED, [], ctx,
        )
        step_actions = [s.action for s in trace.steps]
        assert any("review" in a.lower() for a in step_actions)

    @pytest.mark.asyncio
    async def test_build_trace_assumptions(
        self, trace_builder: TraceBuilder,
    ) -> None:
        ctx = _proposal_context()
        trace = await trace_builder.build_trace(
            "act-1", ActionType.PROPOSAL_CREATED, [], ctx,
        )
        assert len(trace.assumptions) > 0

    @pytest.mark.asyncio
    async def test_build_trace_limitations(
        self, trace_builder: TraceBuilder,
    ) -> None:
        ctx = _proposal_context()
        trace = await trace_builder.build_trace(
            "act-1", ActionType.PROPOSAL_CREATED, [], ctx,
        )
        assert len(trace.limitations) > 0

    @pytest.mark.asyncio
    async def test_build_trace_empty_context(
        self, trace_builder: TraceBuilder,
    ) -> None:
        trace = await trace_builder.build_trace(
            "act-1", ActionType.SYSTEM_ACTION, [], {},
        )
        assert trace.action_id == "act-1"
        # Should have some default assumptions
        assert "Tape history is complete and uncorrupted" in trace.assumptions

    @pytest.mark.asyncio
    async def test_build_trace_data_sources(
        self, trace_builder: TraceBuilder,
    ) -> None:
        entries = [_tape_entry(entry_id=f"e{i}") for i in range(3)]
        trace = await trace_builder.build_trace(
            "act-1", ActionType.PROPOSAL_CREATED, entries, {},
        )
        assert len(trace.data_sources_used) > 0

    @pytest.mark.asyncio
    async def test_build_trace_confidence_geometric_mean(
        self, trace_builder: TraceBuilder,
    ) -> None:
        ctx: dict[str, object] = {"risk_level": "low", "confidence_score": 0.9, "idle_agents": 1}
        trace = await trace_builder.build_trace(
            "act-1", ActionType.PROPOSAL_CREATED, [], ctx,
        )
        assert 0.0 < trace.total_confidence <= 1.0


# ===========================================================================
# ExplanationGenerator tests
# ===========================================================================


class TestExplanationGenerator:
    """Tests for explanation generation."""

    @pytest.mark.asyncio
    async def test_generate_basic(self, generator: ExplanationGenerator) -> None:
        exp = await generator.generate(
            action_id="act-1",
            action_type=ActionType.PROPOSAL_CREATED,
            tape_entries=[],
            context=_proposal_context(),
        )
        assert exp.action_id == "act-1"
        assert exp.action_type == ActionType.PROPOSAL_CREATED
        assert exp.technical_summary != ""
        assert exp.simplified_summary != ""
        assert len(exp.key_factors) > 0
        assert exp.decision_trace is not None

    @pytest.mark.asyncio
    async def test_generate_technical_summary_content(
        self, generator: ExplanationGenerator,
    ) -> None:
        exp = await generator.generate(
            action_id="act-1",
            action_type=ActionType.PROPOSAL_CREATED,
            tape_entries=[],
            context=_proposal_context(),
        )
        assert "act-1" in exp.technical_summary
        assert "proposal_created" in exp.technical_summary

    @pytest.mark.asyncio
    async def test_generate_simplified_summary_content(
        self, generator: ExplanationGenerator,
    ) -> None:
        exp = await generator.generate(
            action_id="act-1",
            action_type=ActionType.PROPOSAL_CREATED,
            tape_entries=[],
            context=_proposal_context(),
        )
        assert "change proposal was created" in exp.simplified_summary

    @pytest.mark.asyncio
    async def test_generate_with_tape_entries(
        self, generator: ExplanationGenerator,
    ) -> None:
        entries = [_tape_entry(payload={"risk_level": "low"}, entry_id=f"e{i}") for i in range(5)]
        exp = await generator.generate(
            action_id="act-1",
            action_type=ActionType.PROPOSAL_CREATED,
            tape_entries=entries,
            context=_proposal_context(),
        )
        assert len(exp.related_tape_entries) == 5

    @pytest.mark.asyncio
    async def test_generate_confidence_blended(
        self, generator: ExplanationGenerator,
    ) -> None:
        ctx: dict[str, object] = {**_proposal_context(), "confidence_score": 0.9}
        exp = await generator.generate(
            action_id="act-1",
            action_type=ActionType.PROPOSAL_CREATED,
            tape_entries=[],
            context=ctx,
        )
        # Confidence should be between 0 and 1
        assert 0.0 < exp.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_generate_risk_level(self, generator: ExplanationGenerator) -> None:
        exp = await generator.generate(
            action_id="act-1",
            action_type=ActionType.PROPOSAL_CREATED,
            tape_entries=[],
            context={"risk_level": "high"},
        )
        assert exp.risk_level == "high"

    @pytest.mark.asyncio
    async def test_generate_key_factors_limited_to_five(
        self, generator: ExplanationGenerator,
    ) -> None:
        ctx = _proposal_context()
        entries = [_tape_entry(payload={"performance_metrics": {"x": 1}}, entry_id=f"e{i}") for i in range(10)]
        exp = await generator.generate(
            action_id="act-1",
            action_type=ActionType.PROPOSAL_CREATED,
            tape_entries=entries,
            context=ctx,
        )
        assert len(exp.key_factors) <= 5

    @pytest.mark.asyncio
    async def test_generate_alternative_comparison(
        self, generator: ExplanationGenerator,
    ) -> None:
        ctx: dict[str, object] = {
            "confidence_score": 0.8,
            "chosen_label": "Option A",
            "alternatives": [
                {"action_id": "alt-1", "label": "Option B", "score": 0.7, "pros": ["cheaper"], "cons": ["slower"]},
                {"action_id": "alt-2", "label": "Option C", "score": 0.5, "pros": [], "cons": ["expensive"]},
            ],
        }
        exp = await generator.generate(
            action_id="act-1",
            action_type=ActionType.PROPOSAL_CREATED,
            tape_entries=[],
            context=ctx,
        )
        assert exp.alternative_comparison is not None
        assert len(exp.alternative_comparison.alternatives) == 2
        assert exp.alternative_comparison.chosen_label == "Option A"

    @pytest.mark.asyncio
    async def test_generate_simplified_confidence_levels(
        self, generator: ExplanationGenerator,
    ) -> None:
        # High confidence
        exp_high = await generator.generate(
            action_id="act-h", action_type=ActionType.PROPOSAL_CREATED,
            tape_entries=[], context={"confidence_score": 0.95},
        )
        assert "highly confident" in exp_high.simplified_summary.lower()

    @pytest.mark.asyncio
    async def test_generate_simplified_low_confidence(
        self, generator: ExplanationGenerator,
    ) -> None:
        exp_low = await generator.generate(
            action_id="act-l", action_type=ActionType.PROPOSAL_CREATED,
            tape_entries=[], context={"confidence_score": 0.2},
        )
        assert "low confidence" in exp_low.simplified_summary.lower() or "human review" in exp_low.simplified_summary.lower()

    @pytest.mark.asyncio
    async def test_generate_simulation_action_label(
        self, generator: ExplanationGenerator,
    ) -> None:
        exp = await generator.generate(
            action_id="act-sim",
            action_type=ActionType.SIMULATION_RUN,
            tape_entries=[],
            context=_simulation_context(),
        )
        assert "simulation" in exp.simplified_summary.lower()


# ===========================================================================
# ExplainabilityEngine — generate_explanation tests
# ===========================================================================


class TestGenerateExplanation:
    """Tests for the main generate_explanation method."""

    @pytest.mark.asyncio
    async def test_generate_explanation(self, engine: ExplainabilityEngine) -> None:
        exp = await engine.generate_explanation(
            action_id="prop-1",
            action_type=ActionType.PROPOSAL_CREATED,
            context=_proposal_context(),
        )
        assert exp.action_id == "prop-1"
        assert exp.technical_summary != ""
        assert exp.simplified_summary != ""
        assert len(exp.key_factors) > 0

    @pytest.mark.asyncio
    async def test_generate_explanation_stored(
        self, engine: ExplainabilityEngine,
    ) -> None:
        exp = await engine.generate_explanation(
            action_id="prop-1",
            action_type=ActionType.PROPOSAL_CREATED,
            context=_proposal_context(),
        )
        # Retrieve from store
        retrieved = engine._store.get(exp.id)
        assert retrieved is not None
        assert retrieved.action_id == "prop-1"

    @pytest.mark.asyncio
    async def test_generate_explanation_logs_to_tape(
        self, engine: ExplainabilityEngine,
    ) -> None:
        await engine.generate_explanation(
            action_id="prop-1",
            action_type=ActionType.PROPOSAL_CREATED,
            context=_proposal_context(),
        )
        entries = await engine._tape.get_entries(
            event_type="explainability.explanation_generated",
        )
        assert len(entries) == 1
        assert entries[0].payload["action_id"] == "prop-1"

    @pytest.mark.asyncio
    async def test_generate_explanation_with_tape_entries(
        self, engine: ExplainabilityEngine,
    ) -> None:
        # Pre-log some tape events that will be found by the engine
        await engine._tape.log_event(
            event_type="proposal.created",
            payload={"action_id": "prop-2", "risk_level": "low"},
            agent_id="prime",
        )
        exp = await engine.generate_explanation(
            action_id="prop-2",
            action_type=ActionType.PROPOSAL_CREATED,
        )
        assert exp.action_id == "prop-2"

    @pytest.mark.asyncio
    async def test_generate_explanation_skill_evolution(
        self, engine: ExplainabilityEngine,
    ) -> None:
        exp = await engine.generate_explanation(
            action_id="skill-evo-1",
            action_type=ActionType.SKILL_EVOLUTION,
            context={"risk_level": "low", "confidence_score": 0.7, "evolution_type": "enhance"},
        )
        assert exp.action_type == ActionType.SKILL_EVOLUTION
        assert "skill" in exp.simplified_summary.lower()


# ===========================================================================
# ExplainabilityEngine — get_decision_trace tests
# ===========================================================================


class TestGetDecisionTrace:
    """Tests for decision trace retrieval."""

    @pytest.mark.asyncio
    async def test_get_decision_trace(self, engine: ExplainabilityEngine) -> None:
        trace = await engine.get_decision_trace(
            action_id="prop-1",
            action_type=ActionType.PROPOSAL_CREATED,
            context=_proposal_context(),
        )
        assert trace.action_id == "prop-1"
        assert len(trace.steps) > 0

    @pytest.mark.asyncio
    async def test_get_decision_trace_logs_to_tape(
        self, engine: ExplainabilityEngine,
    ) -> None:
        await engine.get_decision_trace(
            action_id="prop-1",
            action_type=ActionType.PROPOSAL_CREATED,
            context=_proposal_context(),
        )
        entries = await engine._tape.get_entries(
            event_type="explainability.trace_requested",
        )
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_get_decision_trace_infers_action_type(
        self, engine: ExplainabilityEngine,
    ) -> None:
        trace = await engine.get_decision_trace(
            action_id="act-unknown",
            context={"risk_level": "low"},
        )
        # Should default to SYSTEM_ACTION
        assert trace.action_type == ActionType.SYSTEM_ACTION


# ===========================================================================
# ExplainabilityEngine — highlight_key_factors tests
# ===========================================================================


class TestHighlightKeyFactors:
    """Tests for key factor highlighting."""

    @pytest.mark.asyncio
    async def test_highlight_key_factors(
        self, engine: ExplainabilityEngine,
    ) -> None:
        factors = await engine.highlight_key_factors(
            action_id="prop-1",
            action_type=ActionType.PROPOSAL_CREATED,
            context=_proposal_context(),
        )
        assert len(factors) > 0
        assert len(factors) <= 5
        # Should be sorted by importance
        for i in range(len(factors) - 1):
            assert factors[i].importance >= factors[i + 1].importance

    @pytest.mark.asyncio
    async def test_highlight_key_factors_custom_top_n(
        self, engine: ExplainabilityEngine,
    ) -> None:
        factors = await engine.highlight_key_factors(
            action_id="prop-1",
            action_type=ActionType.PROPOSAL_CREATED,
            context=_proposal_context(),
            top_n=3,
        )
        assert len(factors) <= 3

    @pytest.mark.asyncio
    async def test_highlight_key_factors_logs_to_tape(
        self, engine: ExplainabilityEngine,
    ) -> None:
        await engine.highlight_key_factors(
            action_id="prop-1",
            action_type=ActionType.PROPOSAL_CREATED,
            context=_proposal_context(),
        )
        entries = await engine._tape.get_entries(
            event_type="explainability.factors_highlighted",
        )
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_highlight_key_factors_debate(
        self, engine: ExplainabilityEngine,
    ) -> None:
        factors = await engine.highlight_key_factors(
            action_id="debate-1",
            action_type=ActionType.DEBATE_CONCLUDED,
            context=_debate_context(),
        )
        assert len(factors) > 0


# ===========================================================================
# ExplainabilityEngine — compare_alternatives tests
# ===========================================================================


class TestCompareAlternatives:
    """Tests for alternative comparison."""

    @pytest.mark.asyncio
    async def test_compare_alternatives(
        self, engine: ExplainabilityEngine,
    ) -> None:
        comparison = await engine.compare_alternatives(
            action_id="prop-1",
            alternatives=[
                {"action_id": "alt-1", "label": "Option B", "score": 0.7,
                 "description": "Alternative B", "pros": ["cheaper"], "cons": ["slower"]},
                {"action_id": "alt-2", "label": "Option C", "score": 0.5,
                 "description": "Alternative C", "pros": [], "cons": ["risky"]},
            ],
            action_type=ActionType.PROPOSAL_CREATED,
            context={"confidence_score": 0.85, "chosen_label": "Option A"},
        )
        assert comparison.action_id == "prop-1"
        assert len(comparison.alternatives) == 2
        assert comparison.chosen_label == "Option A"
        assert comparison.chosen_score == 0.85

    @pytest.mark.asyncio
    async def test_compare_alternatives_logs_to_tape(
        self, engine: ExplainabilityEngine,
    ) -> None:
        await engine.compare_alternatives(
            action_id="prop-1",
            alternatives=[
                {"action_id": "alt-1", "label": "Alt", "score": 0.5,
                 "description": "An alternative", "pros": [], "cons": []},
            ],
            action_type=ActionType.PROPOSAL_CREATED,
        )
        entries = await engine._tape.get_entries(
            event_type="explainability.alternatives_compared",
        )
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_compare_alternatives_classifies_outcomes(
        self, engine: ExplainabilityEngine,
    ) -> None:
        comparison = await engine.compare_alternatives(
            action_id="prop-1",
            alternatives=[
                {"action_id": "alt-1", "label": "Better", "score": 0.95,
                 "description": "Superior", "pros": [], "cons": []},
                {"action_id": "alt-2", "label": "Worse", "score": 0.3,
                 "description": "Inferior", "pros": [], "cons": []},
                {"action_id": "alt-3", "label": "Same", "score": 0.80,
                 "description": "Equivalent", "pros": [], "cons": []},
            ],
            action_type=ActionType.PROPOSAL_CREATED,
            context={"confidence_score": 0.82, "chosen_label": "Chosen"},
        )
        outcomes = {a.label: a.outcome for a in comparison.alternatives}
        assert outcomes["Worse"] == AlternativeOutcome.INFERIOR

    @pytest.mark.asyncio
    async def test_compare_alternatives_empty(
        self, engine: ExplainabilityEngine,
    ) -> None:
        comparison = await engine.compare_alternatives(
            action_id="prop-1",
            alternatives=[],
            action_type=ActionType.PROPOSAL_CREATED,
        )
        # Should still return a comparison object
        assert comparison.action_id == "prop-1"

    @pytest.mark.asyncio
    async def test_compare_alternatives_trade_offs(
        self, engine: ExplainabilityEngine,
    ) -> None:
        comparison = await engine.compare_alternatives(
            action_id="prop-1",
            alternatives=[
                {"action_id": "alt-1", "label": "Better", "score": 0.95,
                 "description": "Superior option", "pros": ["faster"], "cons": ["costly"]},
            ],
            action_type=ActionType.PROPOSAL_CREATED,
            context={"confidence_score": 0.7, "chosen_label": "Chosen"},
        )
        # A superior alternative should generate a trade-off note
        assert len(comparison.trade_offs) > 0


# ===========================================================================
# ExplainabilityEngine — query methods tests
# ===========================================================================


class TestExplainabilityQueries:
    """Tests for explanation retrieval and listing."""

    @pytest.mark.asyncio
    async def test_get_explanation(self, engine: ExplainabilityEngine) -> None:
        exp = await engine.generate_explanation(
            action_id="prop-1",
            action_type=ActionType.PROPOSAL_CREATED,
            context=_proposal_context(),
        )
        retrieved = await engine.get_explanation(exp.id)
        assert retrieved.id == exp.id

    @pytest.mark.asyncio
    async def test_get_explanation_not_found(
        self, engine: ExplainabilityEngine,
    ) -> None:
        from uuid import uuid4

        with pytest.raises(ExplanationNotFoundError):
            await engine.get_explanation(uuid4())

    @pytest.mark.asyncio
    async def test_get_explanations_for_action(
        self, engine: ExplainabilityEngine,
    ) -> None:
        await engine.generate_explanation(
            action_id="prop-1",
            action_type=ActionType.PROPOSAL_CREATED,
            context=_proposal_context(),
        )
        results = await engine.get_explanations_for_action("prop-1")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_list_explanations(self, engine: ExplainabilityEngine) -> None:
        await engine.generate_explanation(
            action_id="a", action_type=ActionType.PROPOSAL_CREATED, context={"risk_level": "low"},
        )
        await engine.generate_explanation(
            action_id="b", action_type=ActionType.SIMULATION_RUN, context={"risk_level": "medium"},
        )
        all_exps = await engine.list_explanations()
        assert len(all_exps) == 2

    @pytest.mark.asyncio
    async def test_list_explanations_by_type(
        self, engine: ExplainabilityEngine,
    ) -> None:
        await engine.generate_explanation(
            action_id="a", action_type=ActionType.PROPOSAL_CREATED, context={"risk_level": "low"},
        )
        await engine.generate_explanation(
            action_id="b", action_type=ActionType.SIMULATION_RUN, context={"risk_level": "medium"},
        )
        proposals = await engine.list_explanations(action_type=ActionType.PROPOSAL_CREATED)
        assert len(proposals) == 1


# ===========================================================================
# Data model tests
# ===========================================================================


class TestDataModels:
    """Tests for data model validation and defaults."""

    def test_key_factor_defaults(self) -> None:
        f = KeyFactor(name="test", description="desc", category=FactorCategory.DATA_DRIVEN)
        assert f.importance == 0.0
        assert f.evidence == []
        assert f.direction == "supporting"

    def test_decision_step_defaults(self) -> None:
        s = DecisionStep(step_number=1, action="test", rationale="reason")
        assert s.confidence == 1.0
        assert s.data_sources == []
        assert s.timestamp is None

    def test_decision_trace_confidence_bounds(self) -> None:
        trace = DecisionTrace(
            action_id="a", action_type=ActionType.SYSTEM_ACTION, total_confidence=0.75,
        )
        assert 0.0 <= trace.total_confidence <= 1.0

    def test_explanation_defaults(self) -> None:
        exp = Explanation(action_id="a", action_type=ActionType.SYSTEM_ACTION)
        assert exp.technical_summary == ""
        assert exp.simplified_summary == ""
        assert exp.risk_level == "unknown"
        assert exp.key_factors == []
        assert exp.confidence == 0.0

    def test_alternative_outcome_enum(self) -> None:
        assert AlternativeOutcome.SUPERIOR.value == "superior"
        assert AlternativeOutcome.INFERIOR.value == "inferior"
        assert AlternativeOutcome.EQUIVALENT.value == "equivalent"
        assert AlternativeOutcome.INCOMPARABLE.value == "incomparable"

    def test_action_type_enum_values(self) -> None:
        assert ActionType.PROPOSAL_CREATED.value == "proposal_created"
        assert ActionType.SKILL_EVOLUTION.value == "skill_evolution"
        assert ActionType.SIMULATION_RUN.value == "simulation_run"
        assert ActionType.DEBATE_CONCLUDED.value == "debate_concluded"

    def test_factor_category_enum_values(self) -> None:
        assert FactorCategory.DATA_DRIVEN.value == "data_driven"
        assert FactorCategory.RISK_ASSESSMENT.value == "risk_assessment"
        assert FactorCategory.HEURISTIC.value == "heuristic"

    def test_explanation_mode_enum(self) -> None:
        assert ExplanationMode.TECHNICAL.value == "technical"
        assert ExplanationMode.SIMPLIFIED.value == "simplified"


# ===========================================================================
# Integration tests
# ===========================================================================


class TestExplainabilityIntegration:
    """Integration tests covering full workflows."""

    @pytest.mark.asyncio
    async def test_full_explanation_workflow(
        self, engine: ExplainabilityEngine,
    ) -> None:
        """Test: generate → get → list → query by action."""
        exp = await engine.generate_explanation(
            action_id="prop-integ",
            action_type=ActionType.PROPOSAL_CREATED,
            context=_proposal_context(),
        )

        # Get by ID
        retrieved = await engine.get_explanation(exp.id)
        assert retrieved.action_id == "prop-integ"

        # Get by action ID
        by_action = await engine.get_explanations_for_action("prop-integ")
        assert len(by_action) == 1

        # List all
        all_exps = await engine.list_explanations()
        assert len(all_exps) == 1

        # List by type
        proposals = await engine.list_explanations(action_type=ActionType.PROPOSAL_CREATED)
        assert len(proposals) == 1
        sims = await engine.list_explanations(action_type=ActionType.SIMULATION_RUN)
        assert len(sims) == 0

    @pytest.mark.asyncio
    async def test_trace_and_factors_consistent(
        self, engine: ExplainabilityEngine,
    ) -> None:
        """Decision trace and key factors should be consistent for same action."""
        ctx = _proposal_context()

        trace = await engine.get_decision_trace(
            action_id="prop-consist",
            action_type=ActionType.PROPOSAL_CREATED,
            context=ctx,
        )
        factors = await engine.highlight_key_factors(
            action_id="prop-consist",
            action_type=ActionType.PROPOSAL_CREATED,
            context=ctx,
        )

        # Both should reference the same action
        assert trace.action_id == "prop-consist"
        assert len(factors) > 0
        assert trace.total_confidence > 0.0

    @pytest.mark.asyncio
    async def test_all_tape_events_logged(
        self, engine: ExplainabilityEngine,
    ) -> None:
        """All explainability operations should log to Tape."""
        ctx = _proposal_context()

        await engine.generate_explanation(
            action_id="prop-1", action_type=ActionType.PROPOSAL_CREATED, context=ctx,
        )
        await engine.get_decision_trace(
            action_id="prop-1", action_type=ActionType.PROPOSAL_CREATED, context=ctx,
        )
        await engine.highlight_key_factors(
            action_id="prop-1", action_type=ActionType.PROPOSAL_CREATED, context=ctx,
        )
        await engine.compare_alternatives(
            action_id="prop-1",
            alternatives=[{"action_id": "a1", "label": "Alt", "score": 0.5,
                           "description": "An alt", "pros": [], "cons": []}],
            action_type=ActionType.PROPOSAL_CREATED,
            context=ctx,
        )

        gen = await engine._tape.get_entries(event_type="explainability.explanation_generated")
        trace = await engine._tape.get_entries(event_type="explainability.trace_requested")
        factors = await engine._tape.get_entries(event_type="explainability.factors_highlighted")
        compare = await engine._tape.get_entries(event_type="explainability.alternatives_compared")

        assert len(gen) == 1
        assert len(trace) == 1
        assert len(factors) == 1
        assert len(compare) == 1

    @pytest.mark.asyncio
    async def test_multiple_explanations_same_action(
        self, engine: ExplainabilityEngine,
    ) -> None:
        """Multiple explanations can be generated for the same action."""
        await engine.generate_explanation(
            action_id="prop-multi",
            action_type=ActionType.PROPOSAL_CREATED,
            context={"risk_level": "low"},
        )
        await engine.generate_explanation(
            action_id="prop-multi",
            action_type=ActionType.PROPOSAL_CREATED,
            context={"risk_level": "high"},
        )
        by_action = await engine.get_explanations_for_action("prop-multi")
        assert len(by_action) == 2
