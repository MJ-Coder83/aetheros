"""Unit tests for the Multi-Agent Debate Arena.

Run with: pytest tests/test_debate.py -v
"""

import pytest

from packages.prime.debate import (
    ArgumentQualityScorer,
    ArgumentStyle,
    BiasDetector,
    BiasType,
    ConsensusTracker,
    Debate,
    DebateAlreadyConcludedError,
    DebateArena,
    DebateArgument,
    DebateConsensus,
    DebateFormat,
    DebateNotFoundError,
    DebateParticipant,
    DebatePhase,
    DebateResult,
    DebateRoundLimitError,
    DebateRoundResult,
    DebateStatus,
    DebateStore,
    NoParticipantsError,
    ParticipantRole,
)
from packages.tape.repository import InMemoryTapeRepository
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_participant(
    agent_id: str = "agent-1",
    name: str = "TestAgent",
    role: ParticipantRole = ParticipantRole.PROPONENT,
    argument_style: ArgumentStyle = ArgumentStyle.ANALYTICAL,
    persona: str = "A test participant",
    expertise: list[str] | None = None,
    initial_position: str = "",
) -> DebateParticipant:
    return DebateParticipant(
        agent_id=agent_id,
        name=name,
        role=role,
        persona=persona,
        argument_style=argument_style,
    )


def _make_proponent(
    agent_id: str = "pro-1",
    name: str = "Proponent",
    style: ArgumentStyle = ArgumentStyle.EVIDENCE_BASED,
) -> DebateParticipant:
    return _make_participant(
        agent_id=agent_id,
        name=name,
        role=ParticipantRole.PROPONENT,
        argument_style=style,
        persona="An advocate for the proposition",
        expertise=["architecture"],
    )


def _make_opponent(
    agent_id: str = "opp-1",
    name: str = "Opponent",
    style: ArgumentStyle = ArgumentStyle.RISK_FOCUSED,
) -> DebateParticipant:
    return _make_participant(
        agent_id=agent_id,
        name=name,
        role=ParticipantRole.OPPONENT,
        argument_style=style,
        persona="A critic of the proposition",
        expertise=["operations"],
        initial_position="The proposition introduces unnecessary risk",
    )


def _make_argument(
    participant_agent_id: str = "agent-1",
    content: str = "I believe this is the right approach because of the evidence.",
    round_number: int = 1,
    phase: DebatePhase = DebatePhase.OPENING,
    evidence: list[str] | None = None,
) -> DebateArgument:
    return DebateArgument(
        participant_agent_id=participant_agent_id,
        round_number=round_number,
        phase=phase,
        content=content,
        evidence=evidence or ["Data point from analysis"],
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tape_svc() -> TapeService:
    return TapeService(InMemoryTapeRepository())


@pytest.fixture()
def arena(tape_svc: TapeService) -> DebateArena:
    return DebateArena(tape_service=tape_svc)


@pytest.fixture()
def store() -> DebateStore:
    return DebateStore()


@pytest.fixture()
def scorer() -> ArgumentQualityScorer:
    return ArgumentQualityScorer()


@pytest.fixture()
def bias_detector() -> BiasDetector:
    return BiasDetector()


@pytest.fixture()
def consensus_tracker() -> ConsensusTracker:
    return ConsensusTracker()


# ===========================================================================
# ArgumentQualityScorer tests
# ===========================================================================


class TestArgumentQualityScorer:
    """Tests for argument quality scoring heuristics."""

    def test_short_argument_low_score(self, scorer: ArgumentQualityScorer) -> None:
        score = scorer.score("Too short", [], [])
        assert score < 0.5

    def test_long_argument_higher_score(self, scorer: ArgumentQualityScorer) -> None:
        long_arg = (
            "I believe this is the right approach because the evidence clearly "
            "shows that migrating to event-sourced architecture will improve "
            "our system's scalability and maintainability. However, we must "
            "also consider the operational risks involved in such a migration."
        )
        score = scorer.score(long_arg, [], [])
        assert score > 0.5

    def test_evidence_boosts_score(self, scorer: ArgumentQualityScorer) -> None:
        no_evidence = scorer.score("A reasonable argument with some content here.", [], [])
        with_evidence = scorer.score(
            "A reasonable argument with some content here.",
            ["Study X", "Benchmark Y"],
            [],
        )
        assert with_evidence > no_evidence

    def test_bias_reduces_score(self, scorer: ArgumentQualityScorer) -> None:
        clean = scorer.score(
            "A reasonable argument with some good content and supporting evidence.",
            ["Evidence A"],
            [],
        )
        biased = scorer.score(
            "A reasonable argument with some good content and supporting evidence.",
            ["Evidence A"],
            [BiasType.CONFIRMATION_BIAS],
        )
        assert biased < clean

    def test_score_clamped_to_range(self, scorer: ArgumentQualityScorer) -> None:
        score = scorer.score("x", [], [BiasType.CONFIRMATION_BIAS, BiasType.STRAW_MAN])
        assert 0.0 <= score <= 1.0

    def test_causal_connectors_boost(self, scorer: ArgumentQualityScorer) -> None:
        with_connector = scorer.score(
            "This is the right approach because the data supports it.", [], []
        )
        without = scorer.score(
            "This is the right approach. The data supports it.", [], []
        )
        assert with_connector >= without

    def test_balance_signal_boost(self, scorer: ArgumentQualityScorer) -> None:
        balanced = scorer.score(
            "Although there are risks, the benefits outweigh them.", [], []
        )
        unbalanced = scorer.score(
            "There are no risks at all. It's perfect.", [], []
        )
        assert balanced >= unbalanced

    def test_structure_signal_boost(self, scorer: ArgumentQualityScorer) -> None:
        structured = scorer.score(
            "First, the architecture is sound. However, the costs are high.", [], []
        )
        unstructured = scorer.score(
            "The architecture is sound. The costs are high.", [], []
        )
        assert structured >= unstructured


# ===========================================================================
# BiasDetector tests
# ===========================================================================


class TestBiasDetector:
    """Tests for cognitive bias detection heuristics."""

    def test_no_bias_detected(self, bias_detector: BiasDetector) -> None:
        biases = bias_detector.detect("This approach has trade-offs worth considering.")
        assert BiasType.NONE_DETECTED in biases
        assert all(b == BiasType.NONE_DETECTED for b in biases)

    def test_confirmation_bias(self, bias_detector: BiasDetector) -> None:
        biases = bias_detector.detect("Obviously everyone knows this is the right choice.")
        assert BiasType.CONFIRMATION_BIAS in biases

    def test_anchoring_bias(self, bias_detector: BiasDetector) -> None:
        biases = bias_detector.detect("As we already established, the current system is broken.")
        assert BiasType.ANCHORING_BIAS in biases

    def test_appeal_to_authority(self, bias_detector: BiasDetector) -> None:
        biases = bias_detector.detect("Experts say we should migrate to microservices.")
        assert BiasType.APPEAL_TO_AUTHORITY in biases

    def test_bandwagon_effect(self, bias_detector: BiasDetector) -> None:
        biases = bias_detector.detect("Most people in the industry use this approach.")
        assert BiasType.BANDWAGON_EFFECT in biases

    def test_sunk_cost_fallacy(self, bias_detector: BiasDetector) -> None:
        biases = bias_detector.detect("We've already invested too much to change now.")
        assert BiasType.SUNK_COST_FALLACY in biases

    def test_straw_man(self, bias_detector: BiasDetector) -> None:
        biases = bias_detector.detect("So you're saying we should just abandon everything?")
        assert BiasType.STRAW_MAN in biases

    def test_multiple_biases(self, bias_detector: BiasDetector) -> None:
        biases = bias_detector.detect(
            "Obviously everyone knows this is right. "
            "We've already invested heavily, so it's too late to change."
        )
        assert len(biases) >= 2

    def test_clean_argument_no_biases(self, bias_detector: BiasDetector) -> None:
        biases = bias_detector.detect(
            "The data suggests a 15% improvement in throughput. "
            "However, the migration cost is estimated at 3 months. "
            "We should weigh both factors carefully."
        )
        # This is a well-reasoned argument; may or may not trigger heuristics
        # but should not trigger many
        non_none = [b for b in biases if b != BiasType.NONE_DETECTED]
        assert len(non_none) <= 1  # At most one false positive


# ===========================================================================
# ConsensusTracker tests
# ===========================================================================


class TestConsensusTracker:
    """Tests for consensus tracking and computation."""

    def test_empty_debate_no_consensus(self, consensus_tracker: ConsensusTracker) -> None:
        consensus = consensus_tracker.compute_consensus([], [])
        assert not consensus.reached
        assert consensus.confidence == 0.0

    def test_agreement_markers_increase_confidence(
        self, consensus_tracker: ConsensusTracker
    ) -> None:
        participants = [_make_proponent(), _make_opponent()]
        arguments = [
            _make_argument("pro-1", "I agree with the previous point about scalability."),
            _make_argument("opp-1", "You're right about the benefits, however the costs are high."),
        ]
        consensus = consensus_tracker.compute_consensus(participants, arguments)
        assert consensus.confidence > 0.0

    def test_disagreement_reduces_consensus(
        self, consensus_tracker: ConsensusTracker
    ) -> None:
        participants = [_make_proponent(), _make_opponent()]
        arguments = [
            _make_argument("pro-1", "I strongly disagree with the opponent's position."),
            _make_argument("opp-1", "That's wrong. The risks outweigh the benefits."),
        ]
        consensus = consensus_tracker.compute_consensus(participants, arguments)
        assert consensus.confidence < 0.5

    def test_consensus_not_reached_at_low_confidence(
        self, consensus_tracker: ConsensusTracker
    ) -> None:
        participants = [_make_proponent(), _make_opponent()]
        arguments = [
            _make_argument("pro-1", "This approach works."),
            _make_argument("opp-1", "This approach doesn't work."),
        ]
        consensus = consensus_tracker.compute_consensus(participants, arguments)
        assert not consensus.reached

    def test_key_agreements_extracted(
        self, consensus_tracker: ConsensusTracker
    ) -> None:
        participants = [_make_proponent(), _make_opponent()]
        arguments = [
            _make_argument("pro-1", "I agree that the current system needs improvement."),
            _make_argument("opp-1", "I agree, but the proposed solution is too risky."),
        ]
        consensus = consensus_tracker.compute_consensus(participants, arguments)
        assert len(consensus.key_agreements) > 0

    def test_key_disagreements_extracted(
        self, consensus_tracker: ConsensusTracker
    ) -> None:
        participants = [_make_proponent(), _make_opponent()]
        arguments = [
            _make_argument("pro-1", "I disagree with the risk assessment."),
            _make_argument("opp-1", "I strongly object to ignoring the risks."),
        ]
        consensus = consensus_tracker.compute_consensus(participants, arguments)
        assert len(consensus.key_disagreements) > 0


# ===========================================================================
# DebateStore tests
# ===========================================================================


class TestDebateStore:
    """Tests for the in-memory debate store."""

    def test_add_and_get(self, store: DebateStore) -> None:
        debate = Debate(topic="test")
        store.add(debate)
        assert store.get(debate.id) is debate

    def test_get_not_found(self, store: DebateStore) -> None:
        from uuid import uuid4
        assert store.get(uuid4()) is None

    def test_list_all(self, store: DebateStore) -> None:
        store.add(Debate(topic="a"))
        store.add(Debate(topic="b"))
        assert len(store.list_all()) == 2

    def test_list_by_status(self, store: DebateStore) -> None:
        d1 = Debate(topic="pending", status=DebateStatus.PENDING)
        d2 = Debate(topic="concluded", status=DebateStatus.CONCLUDED)
        store.add(d1)
        store.add(d2)
        assert len(store.list_by_status(DebateStatus.PENDING)) == 1
        assert len(store.list_by_status(DebateStatus.CONCLUDED)) == 1

    def test_update(self, store: DebateStore) -> None:
        debate = Debate(topic="original")
        store.add(debate)
        debate.status = DebateStatus.IN_PROGRESS
        store.update(debate)
        fetched = store.get(debate.id)
        assert fetched is not None
        assert fetched.status == DebateStatus.IN_PROGRESS

    def test_update_not_found(self, store: DebateStore) -> None:
        with pytest.raises(DebateNotFoundError):
            store.update(Debate(topic="ghost"))

    def test_remove(self, store: DebateStore) -> None:
        debate = Debate(topic="to-remove")
        store.add(debate)
        store.remove(debate.id)
        assert store.get(debate.id) is None


# ===========================================================================
# DebateArena — start_debate tests
# ===========================================================================


class TestStartDebate:
    """Tests for debate initialisation."""

    @pytest.mark.asyncio
    async def test_start_standard_debate(self, arena: DebateArena) -> None:
        debate = await arena.start_debate(
            topic="Should we adopt microservices?",
            format=DebateFormat.STANDARD,
            participants=[_make_proponent(), _make_opponent()],
            max_rounds=3,
        )
        assert debate.topic == "Should we adopt microservices?"
        assert debate.format == DebateFormat.STANDARD
        assert debate.status == DebateStatus.PENDING
        assert len(debate.participants) == 2
        assert debate.max_rounds == 3

    @pytest.mark.asyncio
    async def test_start_socratic_debate(self, arena: DebateArena) -> None:
        debate = await arena.start_debate(
            topic="What is the nature of consciousness?",
            format=DebateFormat.SOCRATIC,
            participants=[_make_participant(role=ParticipantRole.NEUTRAL)],
            max_rounds=2,
        )
        assert debate.format == DebateFormat.SOCRATIC

    @pytest.mark.asyncio
    async def test_start_adversarial_debate(self, arena: DebateArena) -> None:
        debate = await arena.start_debate(
            topic="Bull vs Bear: Is the market overvalued?",
            format=DebateFormat.ADVERSARIAL,
            participants=[_make_proponent(), _make_opponent()],
        )
        assert debate.format == DebateFormat.ADVERSARIAL

    @pytest.mark.asyncio
    async def test_start_debate_no_participants(self, arena: DebateArena) -> None:
        with pytest.raises(NoParticipantsError):
            await arena.start_debate(topic="test", participants=[])

    @pytest.mark.asyncio
    async def test_adversarial_requires_proponent_and_opponent(
        self, arena: DebateArena
    ) -> None:
        with pytest.raises(NoParticipantsError):
            await arena.start_debate(
                topic="test",
                format=DebateFormat.ADVERSARIAL,
                participants=[_make_participant(role=ParticipantRole.NEUTRAL)],
            )

    @pytest.mark.asyncio
    async def test_start_debate_logs_to_tape(self, arena: DebateArena) -> None:
        await arena.start_debate(
            topic="test topic",
            participants=[_make_proponent()],
        )
        entries = await arena._tape.get_entries(event_type="debate.started")
        assert len(entries) == 1
        assert entries[0].payload["topic"] == "test topic"

    @pytest.mark.asyncio
    async def test_start_debate_with_initiator(self, arena: DebateArena) -> None:
        debate = await arena.start_debate(
            topic="test",
            participants=[_make_proponent()],
            initiator="human-001",
        )
        assert debate.initiator == "human-001"

    @pytest.mark.asyncio
    async def test_start_debate_with_description(self, arena: DebateArena) -> None:
        debate = await arena.start_debate(
            topic="test",
            description="A detailed discussion about architecture",
            participants=[_make_proponent()],
        )
        assert debate.description == "A detailed discussion about architecture"


# ===========================================================================
# DebateArena — run_debate_round tests
# ===========================================================================


class TestRunDebateRound:
    """Tests for debate round execution."""

    @pytest.mark.asyncio
    async def test_run_first_round(self, arena: DebateArena) -> None:
        debate = await arena.start_debate(
            topic="Should we use event sourcing?",
            format=DebateFormat.STANDARD,
            participants=[_make_proponent(), _make_opponent()],
            max_rounds=3,
        )
        result = await arena.run_debate_round(debate.id)

        assert isinstance(result, DebateRoundResult)
        assert result.round_number == 1
        assert len(result.arguments) > 0

    @pytest.mark.asyncio
    async def test_round_phases_standard(self, arena: DebateArena) -> None:
        debate = await arena.start_debate(
            topic="test",
            format=DebateFormat.STANDARD,
            participants=[_make_proponent(), _make_opponent()],
            max_rounds=3,
        )
        # Round 1 = Opening
        r1 = await arena.run_debate_round(debate.id)
        assert any(a.phase == DebatePhase.OPENING for a in r1.arguments)

        # Round 2 = Rebuttal
        r2 = await arena.run_debate_round(debate.id)
        assert any(a.phase == DebatePhase.REBUTTAL for a in r2.arguments)

        # Round 3 = Closing
        r3 = await arena.run_debate_round(debate.id)
        assert any(a.phase == DebatePhase.CLOSING for a in r3.arguments)

    @pytest.mark.asyncio
    async def test_round_phases_socratic(self, arena: DebateArena) -> None:
        debate = await arena.start_debate(
            topic="test",
            format=DebateFormat.SOCRATIC,
            participants=[_make_participant(role=ParticipantRole.NEUTRAL)],
            max_rounds=3,
        )
        r1 = await arena.run_debate_round(debate.id)
        assert any(a.phase == DebatePhase.QUESTION for a in r1.arguments)

        r2 = await arena.run_debate_round(debate.id)
        assert any(a.phase == DebatePhase.CHALLENGE for a in r2.arguments)

        r3 = await arena.run_debate_round(debate.id)
        assert any(a.phase == DebatePhase.SYNTHESIS for a in r3.arguments)

    @pytest.mark.asyncio
    async def test_round_phases_adversarial(self, arena: DebateArena) -> None:
        debate = await arena.start_debate(
            topic="test",
            format=DebateFormat.ADVERSARIAL,
            participants=[_make_proponent(), _make_opponent()],
            max_rounds=3,
        )
        r1 = await arena.run_debate_round(debate.id)
        phases = {a.phase for a in r1.arguments}
        assert DebatePhase.OPENING in phases
        assert DebatePhase.REBUTTAL in phases

    @pytest.mark.asyncio
    async def test_argument_quality_scored(self, arena: DebateArena) -> None:
        debate = await arena.start_debate(
            topic="test",
            participants=[_make_proponent()],
        )
        result = await arena.run_debate_round(debate.id)
        for arg in result.arguments:
            assert 0.0 <= arg.quality_score <= 1.0

    @pytest.mark.asyncio
    async def test_bias_detection_in_round(self, arena: DebateArena) -> None:
        debate = await arena.start_debate(
            topic="test",
            participants=[_make_proponent()],
        )
        result = await arena.run_debate_round(debate.id)
        for arg in result.arguments:
            assert len(arg.biases_detected) > 0

    @pytest.mark.asyncio
    async def test_round_consensus_delta(self, arena: DebateArena) -> None:
        debate = await arena.start_debate(
            topic="test",
            participants=[_make_proponent(), _make_opponent()],
        )
        result = await arena.run_debate_round(debate.id)
        # Consensus delta can be positive, negative, or zero
        assert isinstance(result.consensus_delta, float)

    @pytest.mark.asyncio
    async def test_round_logs_to_tape(self, arena: DebateArena) -> None:
        debate = await arena.start_debate(
            topic="test",
            participants=[_make_proponent()],
        )
        await arena.run_debate_round(debate.id)
        entries = await arena._tape.get_entries(event_type="debate.round")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_max_round_limit(self, arena: DebateArena) -> None:
        debate = await arena.start_debate(
            topic="test",
            participants=[_make_proponent()],
            max_rounds=2,
        )
        await arena.run_debate_round(debate.id)  # round 1
        await arena.run_debate_round(debate.id)  # round 2
        with pytest.raises(DebateRoundLimitError):
            await arena.run_debate_round(debate.id)  # round 3 - over limit

    @pytest.mark.asyncio
    async def test_cannot_round_concluded_debate(self, arena: DebateArena) -> None:
        debate = await arena.start_debate(
            topic="test",
            participants=[_make_proponent()],
            max_rounds=1,
        )
        await arena.run_debate_round(debate.id)
        await arena.conclude_debate(debate.id)
        with pytest.raises(DebateAlreadyConcludedError):
            await arena.run_debate_round(debate.id)

    @pytest.mark.asyncio
    async def test_round_with_custom_arguments(self, arena: DebateArena) -> None:
        debate = await arena.start_debate(
            topic="test",
            participants=[_make_proponent(), _make_opponent()],
            max_rounds=2,
        )
        custom_args = [
            _make_argument("pro-1", "This is a custom proponent argument.", 1, DebatePhase.OPENING),
            _make_argument("opp-1", "This is a custom opponent counterargument.", 1, DebatePhase.REBUTTAL),
        ]
        result = await arena.run_debate_round(debate.id, arguments=custom_args)
        assert len(result.arguments) == 2
        assert result.arguments[0].content == "This is a custom proponent argument."

    @pytest.mark.asyncio
    async def test_debate_status_updates_to_in_progress(
        self, arena: DebateArena
    ) -> None:
        debate = await arena.start_debate(
            topic="test",
            participants=[_make_proponent()],
        )
        assert debate.status == DebateStatus.PENDING
        await arena.run_debate_round(debate.id)
        updated = await arena.get_debate(debate.id)
        assert updated.status == DebateStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_round_not_found(self, arena: DebateArena) -> None:
        from uuid import uuid4
        with pytest.raises(DebateNotFoundError):
            await arena.run_debate_round(uuid4())


# ===========================================================================
# DebateArena — conclude_debate tests
# ===========================================================================


class TestConcludeDebate:
    """Tests for debate conclusion and result generation."""

    @pytest.mark.asyncio
    async def test_conclude_after_rounds(self, arena: DebateArena) -> None:
        debate = await arena.start_debate(
            topic="Should we refactor the codebase?",
            format=DebateFormat.STANDARD,
            participants=[_make_proponent(), _make_opponent()],
            max_rounds=2,
        )
        await arena.run_debate_round(debate.id)
        await arena.run_debate_round(debate.id)

        result = await arena.conclude_debate(debate.id)

        assert isinstance(result, DebateResult)
        assert result.debate_id == debate.id
        assert result.total_rounds == 2
        assert result.total_arguments > 0
        assert 0.0 <= result.average_quality <= 1.0
        assert result.recommendation  # non-empty string

    @pytest.mark.asyncio
    async def test_conclude_consensus_analysis(self, arena: DebateArena) -> None:
        debate = await arena.start_debate(
            topic="test",
            participants=[_make_proponent(), _make_opponent()],
            max_rounds=2,
        )
        await arena.run_debate_round(debate.id)
        await arena.run_debate_round(debate.id)

        result = await arena.conclude_debate(debate.id)

        assert isinstance(result.consensus, DebateConsensus)
        assert 0.0 <= result.consensus.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_conclude_recommendation_confidence(self, arena: DebateArena) -> None:
        debate = await arena.start_debate(
            topic="test",
            participants=[_make_proponent(), _make_opponent()],
            max_rounds=1,
        )
        await arena.run_debate_round(debate.id)

        result = await arena.conclude_debate(debate.id)

        assert 0.0 <= result.recommendation_confidence <= 1.0

    @pytest.mark.asyncio
    async def test_conclude_risk_level(self, arena: DebateArena) -> None:
        debate = await arena.start_debate(
            topic="test",
            participants=[_make_proponent(), _make_opponent()],
            max_rounds=1,
        )
        await arena.run_debate_round(debate.id)

        result = await arena.conclude_debate(debate.id)
        assert result.risk_level in {"low", "medium", "high"}

    @pytest.mark.asyncio
    async def test_conclude_already_concluded(self, arena: DebateArena) -> None:
        debate = await arena.start_debate(
            topic="test",
            participants=[_make_proponent()],
            max_rounds=1,
        )
        await arena.run_debate_round(debate.id)
        await arena.conclude_debate(debate.id)

        with pytest.raises(DebateAlreadyConcludedError):
            await arena.conclude_debate(debate.id)

    @pytest.mark.asyncio
    async def test_conclude_logs_to_tape(self, arena: DebateArena) -> None:
        debate = await arena.start_debate(
            topic="test",
            participants=[_make_proponent()],
            max_rounds=1,
        )
        await arena.run_debate_round(debate.id)
        await arena.conclude_debate(debate.id)

        entries = await arena._tape.get_entries(event_type="debate.concluded")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_conclude_updates_debate_status(self, arena: DebateArena) -> None:
        debate = await arena.start_debate(
            topic="test",
            participants=[_make_proponent()],
            max_rounds=1,
        )
        await arena.run_debate_round(debate.id)
        await arena.conclude_debate(debate.id)

        updated = await arena.get_debate(debate.id)
        assert updated.status == DebateStatus.CONCLUDED
        assert updated.concluded_at is not None
        assert updated.result is not None

    @pytest.mark.asyncio
    async def test_conclude_not_found(self, arena: DebateArena) -> None:
        from uuid import uuid4
        with pytest.raises(DebateNotFoundError):
            await arena.conclude_debate(uuid4())


# ===========================================================================
# DebateArena — abort_debate tests
# ===========================================================================


class TestAbortDebate:
    """Tests for debate abort functionality."""

    @pytest.mark.asyncio
    async def test_abort_in_progress_debate(self, arena: DebateArena) -> None:
        debate = await arena.start_debate(
            topic="test",
            participants=[_make_proponent()],
            max_rounds=3,
        )
        await arena.run_debate_round(debate.id)

        aborted = await arena.abort_debate(debate.id, reason="Time constraint")
        assert aborted.status == DebateStatus.ABORTED

    @pytest.mark.asyncio
    async def test_abort_pending_debate(self, arena: DebateArena) -> None:
        debate = await arena.start_debate(
            topic="test",
            participants=[_make_proponent()],
        )
        aborted = await arena.abort_debate(debate.id)
        assert aborted.status == DebateStatus.ABORTED

    @pytest.mark.asyncio
    async def test_abort_concluded_debate_fails(self, arena: DebateArena) -> None:
        debate = await arena.start_debate(
            topic="test",
            participants=[_make_proponent()],
            max_rounds=1,
        )
        await arena.run_debate_round(debate.id)
        await arena.conclude_debate(debate.id)

        with pytest.raises(DebateAlreadyConcludedError):
            await arena.abort_debate(debate.id)

    @pytest.mark.asyncio
    async def test_abort_logs_to_tape(self, arena: DebateArena) -> None:
        debate = await arena.start_debate(
            topic="test",
            participants=[_make_proponent()],
        )
        await arena.abort_debate(debate.id, reason="Emergency")

        entries = await arena._tape.get_entries(event_type="debate.aborted")
        assert len(entries) == 1
        assert entries[0].payload["reason"] == "Emergency"


# ===========================================================================
# DebateArena — query tests
# ===========================================================================


class TestDebateQueries:
    """Tests for debate retrieval and listing."""

    @pytest.mark.asyncio
    async def test_get_debate(self, arena: DebateArena) -> None:
        debate = await arena.start_debate(
            topic="test",
            participants=[_make_proponent()],
        )
        fetched = await arena.get_debate(debate.id)
        assert fetched.id == debate.id

    @pytest.mark.asyncio
    async def test_get_debate_not_found(self, arena: DebateArena) -> None:
        from uuid import uuid4
        with pytest.raises(DebateNotFoundError):
            await arena.get_debate(uuid4())

    @pytest.mark.asyncio
    async def test_get_debate_transcript(self, arena: DebateArena) -> None:
        debate = await arena.start_debate(
            topic="test transcript",
            participants=[_make_proponent(), _make_opponent()],
            max_rounds=2,
        )
        await arena.run_debate_round(debate.id)
        await arena.run_debate_round(debate.id)
        await arena.conclude_debate(debate.id)

        transcript = await arena.get_debate_transcript(debate.id)
        assert transcript.id == debate.id
        assert len(transcript.arguments) > 0
        assert transcript.result is not None

    @pytest.mark.asyncio
    async def test_list_debates(self, arena: DebateArena) -> None:
        await arena.start_debate(topic="a", participants=[_make_proponent()])
        await arena.start_debate(topic="b", participants=[_make_proponent()])
        debates = await arena.list_debates()
        assert len(debates) == 2

    @pytest.mark.asyncio
    async def test_list_debates_by_status(self, arena: DebateArena) -> None:
        d1 = await arena.start_debate(topic="pending", participants=[_make_proponent()])
        d2 = await arena.start_debate(topic="in-progress", participants=[_make_proponent()], max_rounds=2)
        await arena.run_debate_round(d2.id)

        pending = await arena.list_debates(status=DebateStatus.PENDING)
        in_progress = await arena.list_debates(status=DebateStatus.IN_PROGRESS)
        assert len(pending) == 1
        assert len(in_progress) == 1
        assert pending[0].id == d1.id
        assert in_progress[0].id == d2.id


# ===========================================================================
# Phase determination tests
# ===========================================================================


class TestPhaseDetermination:
    """Tests for format-based phase assignment."""

    def test_standard_round1_opening(self) -> None:
        phases = DebateArena._get_phases_for_round(DebateFormat.STANDARD, 1, 3)
        assert phases == [DebatePhase.OPENING]

    def test_standard_middle_rebuttal(self) -> None:
        phases = DebateArena._get_phases_for_round(DebateFormat.STANDARD, 2, 3)
        assert phases == [DebatePhase.REBUTTAL]

    def test_standard_last_closing(self) -> None:
        phases = DebateArena._get_phases_for_round(DebateFormat.STANDARD, 3, 3)
        assert phases == [DebatePhase.CLOSING]

    def test_socratic_round1_question(self) -> None:
        phases = DebateArena._get_phases_for_round(DebateFormat.SOCRATIC, 1, 3)
        assert phases == [DebatePhase.QUESTION]

    def test_socratic_last_synthesis(self) -> None:
        phases = DebateArena._get_phases_for_round(DebateFormat.SOCRATIC, 3, 3)
        assert phases == [DebatePhase.SYNTHESIS]

    def test_adversarial_always_opening_rebuttal(self) -> None:
        for round_num in [1, 2, 3]:
            phases = DebateArena._get_phases_for_round(
                DebateFormat.ADVERSARIAL, round_num, 3
            )
            assert DebatePhase.OPENING in phases
            assert DebatePhase.REBUTTAL in phases


# ===========================================================================
# Full debate lifecycle integration test
# ===========================================================================


class TestDebateLifecycle:
    """Integration tests for the full debate lifecycle."""

    @pytest.mark.asyncio
    async def test_full_standard_debate_lifecycle(self, arena: DebateArena) -> None:
        """Test a complete standard debate from start to conclusion."""
        # Start
        debate = await arena.start_debate(
            topic="Should we adopt event sourcing?",
            format=DebateFormat.STANDARD,
            participants=[_make_proponent(), _make_opponent()],
            max_rounds=3,
            description="A critical architectural decision",
            initiator="prime",
        )
        assert debate.status == DebateStatus.PENDING

        # Round 1: Opening
        r1 = await arena.run_debate_round(debate.id)
        assert r1.round_number == 1

        # Round 2: Rebuttal
        r2 = await arena.run_debate_round(debate.id)
        assert r2.round_number == 2

        # Round 3: Closing
        r3 = await arena.run_debate_round(debate.id)
        assert r3.round_number == 3

        # Conclude
        result = await arena.conclude_debate(debate.id)
        assert result.total_rounds == 3
        assert result.recommendation != ""
        assert 0.0 <= result.recommendation_confidence <= 1.0

        # Transcript
        transcript = await arena.get_debate_transcript(debate.id)
        assert transcript.status == DebateStatus.CONCLUDED
        assert len(transcript.arguments) > 0

    @pytest.mark.asyncio
    async def test_full_socratic_debate_lifecycle(self, arena: DebateArena) -> None:
        """Test a complete Socratic debate from start to conclusion."""
        debate = await arena.start_debate(
            topic="What is the optimal team size?",
            format=DebateFormat.SOCRATIC,
            participants=[_make_participant(role=ParticipantRole.NEUTRAL)],
            max_rounds=3,
        )

        for _ in range(3):
            await arena.run_debate_round(debate.id)

        result = await arena.conclude_debate(debate.id)
        assert result.total_rounds == 3

    @pytest.mark.asyncio
    async def test_full_adversarial_debate_lifecycle(self, arena: DebateArena) -> None:
        """Test a complete adversarial debate from start to conclusion."""
        debate = await arena.start_debate(
            topic="Bull vs Bear: AI market overvalued?",
            format=DebateFormat.ADVERSARIAL,
            participants=[_make_proponent(), _make_opponent()],
            max_rounds=2,
        )

        for _ in range(2):
            await arena.run_debate_round(debate.id)

        result = await arena.conclude_debate(debate.id)
        assert result.total_rounds == 2

    @pytest.mark.asyncio
    async def test_all_tape_events_logged(self, arena: DebateArena) -> None:
        """Verify that all debate events are logged to the Tape."""
        debate = await arena.start_debate(
            topic="test",
            participants=[_make_proponent()],
            max_rounds=1,
        )
        await arena.run_debate_round(debate.id)
        await arena.conclude_debate(debate.id)

        started = await arena._tape.get_entries(event_type="debate.started")
        rounds = await arena._tape.get_entries(event_type="debate.round")
        concluded = await arena._tape.get_entries(event_type="debate.concluded")

        assert len(started) == 1
        assert len(rounds) == 1
        assert len(concluded) == 1

    @pytest.mark.asyncio
    async def test_early_conclusion(self, arena: DebateArena) -> None:
        """Test that a debate can be concluded before max rounds."""
        debate = await arena.start_debate(
            topic="test",
            participants=[_make_proponent()],
            max_rounds=5,
        )
        await arena.run_debate_round(debate.id)  # only 1 of 5 rounds
        result = await arena.conclude_debate(debate.id)
        assert result.total_rounds == 1
