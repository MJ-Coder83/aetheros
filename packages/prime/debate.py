"""Multi-Agent Debate Arena — Structured debate for higher-quality decisions.

This module enables multiple specialised agents to engage in structured debates
to reach higher-quality decisions, especially for complex or high-stakes tasks.

Debate formats:

- **Standard** (Opening -> Rebuttal -> Closing): Traditional debate structure
  where participants present their case, challenge others, and summarise.

- **Socratic** (Question -> Challenge -> Synthesis): Collaborative inquiry
  where participants question assumptions, challenge reasoning, and synthesise
  insights into a unified position.

- **Adversarial** (Bull vs Bear): Two participants take diametrically opposed
  positions and argue forcefully; the arena evaluates which side is more
  convincing based on evidence and reasoning quality.

Key guarantees:

- **Auditability**: All debate events are logged to the Tape with
  ``debate.*`` event types for full traceability.

- **Safety**: Max round limits prevent infinite loops; early termination
  when consensus is reached.

- **Quality**: Argument quality scoring and bias detection ensure debates
  produce meaningful, well-reasoned outcomes.

- **Consensus detection**: The engine tracks position convergence across
  rounds and can conclude early when participants reach agreement.

Architecture::

    DebateArena
    +-- start_debate()          -- Initialise a structured debate
    +-- run_debate_round()      -- Execute one round of arguments
    +-- conclude_debate()       -- Summarise, extract consensus, recommend
    +-- get_debate_transcript() -- Full debate history
    +-- list_debates()          -- List all debates (optionally by status)
    +-- get_debate()            -- Retrieve a single debate

Usage::

    arena = DebateArena(tape_service=tape_svc)

    debate = await arena.start_debate(
        topic="Should we migrate to event-sourced architecture?",
        format=DebateFormat.STANDARD,
        participants=[
            DebateParticipant(
                agent_id="arch-1", name="Architect", role="proponent",
                persona="Experienced systems architect who values scalability",
                argument_style="evidence-based",
            ),
            DebateParticipant(
                agent_id="ops-1", name="Operator", role="opponent",
                persona="Pragmatic ops engineer who values stability",
                argument_style="risk-focused",
            ),
        ],
        max_rounds=3,
    )

    # Run rounds
    round_result = await arena.run_debate_round(debate.id)

    # Conclude
    result = await arena.conclude_debate(debate.id)

    # Full transcript
    transcript = await arena.get_debate_transcript(debate.id)
"""

import contextlib
import re
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from packages.llm import LLMProvider
from packages.prime.intelligence_profile import IntelligenceProfileEngine, InteractionType
from packages.prime.proposals import RiskLevel
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DebateFormat(StrEnum):
    """Supported debate formats."""

    STANDARD = "standard"        # Opening -> Rebuttal -> Closing
    SOCRATIC = "socratic"        # Question -> Challenge -> Synthesis
    ADVERSARIAL = "adversarial"  # Bull vs Bear


class DebateStatus(StrEnum):
    """Lifecycle states for a debate."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    CONCLUDED = "concluded"
    ABORTED = "aborted"


class DebatePhase(StrEnum):
    """Phases within a single debate round (format-dependent)."""

    OPENING = "opening"
    QUESTION = "question"
    REBUTTAL = "rebuttal"
    CHALLENGE = "challenge"
    CLOSING = "closing"
    SYNTHESIS = "synthesis"


class ParticipantRole(StrEnum):
    """Role of a participant in the debate."""

    PROPONENT = "proponent"    # Argues in favour
    OPPONENT = "opponent"      # Argues against
    MODERATOR = "moderator"    # Facilitates and summarises
    NEUTRAL = "neutral"        # Provides balanced analysis


class ArgumentStyle(StrEnum):
    """Argument style of a participant."""

    EVIDENCE_BASED = "evidence-based"
    RISK_FOCUSED = "risk-focused"
    PRAGMATIC = "pragmatic"
    VISIONARY = "visionary"
    ANALYTICAL = "analytical"
    DEVILS_ADVOCATE = "devils-advocate"


class BiasType(StrEnum):
    """Types of cognitive bias that can be detected in arguments."""

    CONFIRMATION_BIAS = "confirmation_bias"
    ANCHORING_BIAS = "anchoring_bias"
    APPEAL_TO_AUTHORITY = "appeal_to_authority"
    BANDWAGON_EFFECT = "bandwagon_effect"
    SUNK_COST_FALLACY = "sunk_cost_fallacy"
    STRAW_MAN = "straw_man"
    NONE_DETECTED = "none_detected"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class DebateParticipant(BaseModel):
    """A participant in a debate with their role and persona."""

    agent_id: str
    name: str
    role: ParticipantRole = ParticipantRole.NEUTRAL
    persona: str = ""
    argument_style: ArgumentStyle = ArgumentStyle.ANALYTICAL
    expertise: list[str] = []
    initial_position: str = ""


class DebateArgument(BaseModel):
    """A single argument made by a participant during a debate round."""

    id: UUID = Field(default_factory=uuid4)
    participant_agent_id: str
    round_number: int
    phase: DebatePhase
    content: str
    evidence: list[str] = []
    quality_score: float = Field(default=0.5, ge=0.0, le=1.0)
    biases_detected: list[BiasType] = []
    responds_to: UUID | None = None  # ID of the argument this responds to
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DebateRoundResult(BaseModel):
    """Result of executing a single debate round."""

    round_number: int
    arguments: list[DebateArgument] = []
    consensus_delta: float = 0.0  # How much positions converged this round
    round_quality: float = 0.0    # Average argument quality for the round
    biases_detected_count: int = 0


class DebateConsensus(BaseModel):
    """Consensus analysis from a concluded debate."""

    reached: bool = False
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    agreed_position: str = ""
    dissenting_positions: list[str] = []
    key_agreements: list[str] = []
    key_disagreements: list[str] = []


class DebateResult(BaseModel):
    """Final result of a concluded debate."""

    id: UUID = Field(default_factory=uuid4)
    debate_id: UUID
    total_rounds: int = 0
    total_arguments: int = 0
    average_quality: float = 0.0
    total_biases_detected: int = 0
    consensus: DebateConsensus = Field(default_factory=DebateConsensus)
    recommendation: str = ""
    recommendation_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    risk_level: RiskLevel = RiskLevel.LOW
    concluded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Debate(BaseModel):
    """A structured debate between multiple agents on a given topic.

    Tracks the full lifecycle: participants, rounds, arguments, and
    the current status of the debate.
    """

    id: UUID = Field(default_factory=uuid4)
    topic: str
    description: str = ""
    format: DebateFormat = DebateFormat.STANDARD
    status: DebateStatus = DebateStatus.PENDING
    participants: list[DebateParticipant] = []
    max_rounds: int = 3
    current_round: int = 0
    arguments: list[DebateArgument] = []
    rounds: list[DebateRoundResult] = []
    result: DebateResult | None = None
    initiator: str = "prime"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    concluded_at: datetime | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class DebateError(Exception):
    """Base exception for debate operations."""


class DebateNotFoundError(DebateError):
    """Raised when a requested debate does not exist."""


class DebateAlreadyConcludedError(DebateError):
    """Raised when trying to modify a debate that has already concluded."""


class DebateRoundLimitError(DebateError):
    """Raised when the maximum round limit has been reached."""


class NoParticipantsError(DebateError):
    """Raised when a debate has no participants."""


# ---------------------------------------------------------------------------
# DebateStore — in-memory persistence
# ---------------------------------------------------------------------------


class DebateStore:
    """In-memory store for debates.

    Will be replaced by a PostgreSQL-backed repository in a future phase.
    """

    def __init__(self) -> None:
        self._debates: dict[UUID, Debate] = {}

    def add(self, debate: Debate) -> None:
        self._debates[debate.id] = debate

    def get(self, debate_id: UUID) -> Debate | None:
        return self._debates.get(debate_id)

    def update(self, debate: Debate) -> None:
        if debate.id not in self._debates:
            raise DebateNotFoundError(f"Debate {debate.id} not found")
        self._debates[debate.id] = debate

    def list_all(self) -> list[Debate]:
        return list(self._debates.values())

    def list_by_status(self, status: DebateStatus) -> list[Debate]:
        return [d for d in self._debates.values() if d.status == status]

    def remove(self, debate_id: UUID) -> None:
        self._debates.pop(debate_id, None)


# ---------------------------------------------------------------------------
# Argument quality scorer
# ---------------------------------------------------------------------------


class ArgumentQualityScorer:
    """Scores the quality of debate arguments based on heuristics.

    Quality signals:
    - Length: Arguments that are too short (<20 chars) lack substance
    - Evidence: Arguments that cite evidence score higher
    - Specificity: Arguments with concrete details score higher
    - Structure: Arguments with logical connectors score higher
    - Balance: Arguments that acknowledge counterpoints score higher

    This will be replaced by an LLM-based quality scorer in a future phase.
    """

    @staticmethod
    def score(
        content: str,
        evidence: list[str],
        biases: list[BiasType],
    ) -> float:
        """Score an argument from 0.0 to 1.0.

        Args:
            content: The argument text.
            evidence: List of evidence citations.
            biases: Biases detected in the argument.

        Returns:
            A quality score between 0.0 and 1.0.
        """
        score = 0.3  # base score

        # Length signal (0-0.15)
        if len(content) >= 20:
            score += 0.05
        if len(content) >= 50:
            score += 0.05
        if len(content) >= 100:
            score += 0.05

        # Evidence signal (0-0.25)
        evidence_bonus = min(len(evidence) * 0.1, 0.25)
        score += evidence_bonus

        # Specificity signal: concrete numbers, names, or references (0-0.15)
        specificity_patterns = [
            r"\d+%?",          # Numbers/percentages
            r"\b[A-Z][a-z]+\b",  # Capitalised names/terms
            r"\b(e\.g\.|i\.e\.)\b",  # Clarifying abbreviations
            r"\b(because|therefore|consequently|thus)\b",  # Causal connectors
        ]
        for pattern in specificity_patterns:
            if re.search(pattern, content):
                score += 0.03

        # Structure signal: logical connectors (0-0.1)
        structure_patterns = [
            r"\b(however|moreover|furthermore|additionally|nevertheless)\b",
            r"\b(on the other hand|in contrast|conversely)\b",
            r"\b(first|second|third|finally)\b",
        ]
        for pattern in structure_patterns:
            if re.search(pattern, content.lower()):
                score += 0.03

        # Balance signal: acknowledges counterpoints (0-0.1)
        balance_patterns = [
            r"\b(although|while|even though|despite|admittedly)\b",
            r"\b(I understand|one could argue|it is true that)\b",
            r"\b(on one hand|trade-?off|downside)\b",
        ]
        for pattern in balance_patterns:
            if re.search(pattern, content.lower()):
                score += 0.03

        # Bias penalty: each detected bias reduces score
        bias_penalty = len([b for b in biases if b != BiasType.NONE_DETECTED]) * 0.05
        score -= bias_penalty

        return max(0.0, min(1.0, round(score, 3)))


# ---------------------------------------------------------------------------
# Bias detector
# ---------------------------------------------------------------------------


class BiasDetector:
    """Detects cognitive biases in debate arguments using heuristic patterns.

    This will be replaced by an LLM-based bias detector in a future phase.
    The current heuristic approach looks for linguistic patterns associated
    with common cognitive biases.
    """

    @staticmethod
    def detect(content: str) -> list[BiasType]:
        """Detect biases in argument content.

        Returns a list of detected bias types (may be empty if none found).
        """
        biases: list[BiasType] = []
        lower = content.lower()

        # Confirmation bias: "obviously", "clearly", "everyone knows", "it's obvious"
        confirmation_patterns = [
            r"\b(obviously|clearly|everyone knows|it's obvious|without doubt)\b",
            r"\b(undeniably|self-evident|goes without saying)\b",
        ]
        if any(re.search(p, lower) for p in confirmation_patterns):
            biases.append(BiasType.CONFIRMATION_BIAS)

        # Anchoring bias: "as we already established", "building on X"
        anchoring_patterns = [
            r"\b(as (we |you )?already (established|decided|agreed))\b",
            r"\b(given that .+ is (fixed|certain|established))\b",
        ]
        if any(re.search(p, lower) for p in anchoring_patterns):
            biases.append(BiasType.ANCHORING_BIAS)

        # Appeal to authority: "expert says", "studies show" without specifics
        authority_patterns = [
            r"\b(experts say|studies show|research proves)\b(?!.+\b\d+\b)",
            r"\b(according to (renowned|leading|top) (expert|authority|researcher))\b",
        ]
        if any(re.search(p, lower) for p in authority_patterns):
            biases.append(BiasType.APPEAL_TO_AUTHORITY)

        # Bandwagon effect: "most people", "widely accepted", "industry standard"
        bandwagon_patterns = [
            r"\b(most (people|experts|teams)|widely accepted|industry standard)\b",
            r"\b(everyone (is doing|agrees|believes)|mainstream)\b",
        ]
        if any(re.search(p, lower) for p in bandwagon_patterns):
            biases.append(BiasType.BANDWAGON_EFFECT)

        # Sunk cost fallacy: "we've already invested", "too much effort to change"
        sunk_cost_patterns = [
            r"\b(already (invested|spent|committed|poured).+)\b",
            r"\b(too (much|late) to (change|turn back|switch|abandon))\b",
        ]
        if any(re.search(p, lower) for p in sunk_cost_patterns):
            biases.append(BiasType.SUNK_COST_FALLACY)

        # Straw man: misrepresenting the opposing view
        straw_man_patterns = [
            r"\b(so you'?re? saying (that )?we should (just )?)\b",
            r"\b(your (argument|position) (basically |essentially )?(is|means))\b",
        ]
        if any(re.search(p, lower) for p in straw_man_patterns):
            biases.append(BiasType.STRAW_MAN)

        if not biases:
            biases.append(BiasType.NONE_DETECTED)

        return biases


# ---------------------------------------------------------------------------
# Consensus tracker
# ---------------------------------------------------------------------------


class ConsensusTracker:
    """Tracks position convergence across debate rounds.

    Computes a consensus score based on the similarity and convergence
    of participants' positions. A higher score indicates more agreement.
    """

    @staticmethod
    def compute_consensus(
        participants: list[DebateParticipant],
        arguments: list[DebateArgument],
    ) -> DebateConsensus:
        """Compute the current consensus state of a debate.

        Uses heuristic signals from the arguments:
        - Language similarity between participants (shared terms)
        - Explicit agreement markers ("I agree", "you're right")
        - Explicit disagreement markers ("I disagree", "that's wrong")
        - Convergence of evidence citations

        Returns:
            DebateConsensus with reached flag, confidence, and key points.
        """
        if not participants or not arguments:
            return DebateConsensus(
                reached=False,
                confidence=0.0,
                agreed_position="No arguments yet",
            )

        # Extract proponent and opponent arguments
        proponent_args: list[str] = []
        opponent_args: list[str] = []

        for arg in arguments:
            participant = next(
                (p for p in participants if p.agent_id == arg.participant_agent_id),
                None,
            )
            if participant is None:
                continue
            if participant.role == ParticipantRole.PROPONENT:
                proponent_args.append(arg.content.lower())
            elif participant.role == ParticipantRole.OPPONENT:
                opponent_args.append(arg.content.lower())

        # Count agreement and disagreement markers
        agreement_count = 0
        disagreement_count = 0

        agreement_patterns = [
            r"\b(i agree|you'?re? right|that'?s? correct|good point|exactly)\b",
            r"\b(i concede|fair point|you have a point)\b",
        ]
        disagreement_patterns = [
            r"\b(i disagree|that'?s? wrong|incorrect|i (strongly )?object)\b",
            r"\b(that (doesn'?t|does not) (make sense|hold|work|address))\b",
        ]

        all_content = " ".join(a.content.lower() for a in arguments)
        for pattern in agreement_patterns:
            agreement_count += len(re.findall(pattern, all_content))
        for pattern in disagreement_patterns:
            disagreement_count += len(re.findall(pattern, all_content))

        # Compute shared vocabulary ratio between positions
        all_proponent_words: set[str] = set()
        all_opponent_words: set[str] = set()
        for text in proponent_args:
            all_proponent_words.update(text.split())
        for text in opponent_args:
            all_opponent_words.update(text.split())

        shared_words = all_proponent_words & all_opponent_words
        total_words = all_proponent_words | all_opponent_words
        vocabulary_overlap = len(shared_words) / len(total_words) if total_words else 0.0

        # Compute consensus confidence (0.0 - 1.0)
        # Higher agreement markers + higher vocabulary overlap = higher consensus
        agreement_signal = min(agreement_count / max(len(arguments), 1), 1.0)
        disagreement_signal = min(disagreement_count / max(len(arguments), 1), 1.0)

        confidence = (
            vocabulary_overlap * 0.3
            + agreement_signal * 0.5
            - disagreement_signal * 0.3
        )
        confidence = max(0.0, min(1.0, round(confidence, 3)))

        # Determine if consensus is reached
        reached = confidence >= 0.7 and agreement_count > disagreement_count

        # Extract key agreements and disagreements
        key_agreements: list[str] = []
        key_disagreements: list[str] = []

        for arg in arguments:
            content_lower = arg.content.lower()
            is_agreement = any(
                re.search(p, content_lower) for p in agreement_patterns
            )
            is_disagreement = any(
                re.search(p, content_lower) for p in disagreement_patterns
            )
            if is_agreement and len(key_agreements) < 5:
                key_agreements.append(arg.content[:100])
            if is_disagreement and len(key_disagreements) < 5:
                key_disagreements.append(arg.content[:100])

        # Determine agreed position
        if reached:
            agreed_position = (
                "Participants reached consensus through shared reasoning "
                "and explicit agreement markers."
            )
        elif confidence > 0.4:
            agreed_position = "Partial consensus on some points; disagreement on others."
        else:
            agreed_position = "Participants maintain fundamentally different positions."

        # Collect dissenting positions
        dissenting_positions: list[str] = []
        for p in participants:
            if p.role == ParticipantRole.OPPONENT and p.initial_position:
                dissenting_positions.append(f"{p.name}: {p.initial_position}")

        return DebateConsensus(
            reached=reached,
            confidence=confidence,
            agreed_position=agreed_position,
            dissenting_positions=dissenting_positions,
            key_agreements=key_agreements,
            key_disagreements=key_disagreements,
        )


# ---------------------------------------------------------------------------
# DebateArena — the main public API
# ---------------------------------------------------------------------------


class DebateArena:
    """Engine for structured multi-agent debates.

    DebateArena enables multiple specialised agents to engage in structured
    debates to reach higher-quality decisions. Every debate is logged to the
    Tape for full auditability.

    Usage::

        arena = DebateArena(tape_service=tape_svc)

        debate = await arena.start_debate(
            topic="Should we adopt microservices?",
            format=DebateFormat.STANDARD,
            participants=[...],
            max_rounds=3,
        )

        while debate.status == DebateStatus.IN_PROGRESS:
            round_result = await arena.run_debate_round(debate.id)

        result = await arena.conclude_debate(debate.id)
    """

    def __init__(
        self,
        tape_service: TapeService,
        store: DebateStore | None = None,
        quality_scorer: ArgumentQualityScorer | None = None,
        bias_detector: BiasDetector | None = None,
        consensus_tracker: ConsensusTracker | None = None,
        profile_engine: IntelligenceProfileEngine | None = None,
    ) -> None:
        self._tape = tape_service
        self._store = store or DebateStore()
        self._scorer = quality_scorer or ArgumentQualityScorer()
        self._bias_detector = bias_detector or BiasDetector()
        self._consensus = consensus_tracker or ConsensusTracker()
        self._profile_engine = profile_engine

    # ------------------------------------------------------------------
    # Start debate
    # ------------------------------------------------------------------

    async def start_debate(
        self,
        topic: str,
        format: DebateFormat = DebateFormat.STANDARD,
        participants: list[DebateParticipant] | None = None,
        max_rounds: int = 3,
        description: str = "",
        initiator: str = "prime",
        metadata: dict[str, object] | None = None,
    ) -> Debate:
        """Initialise a structured debate between multiple agents.

        Creates a new Debate in PENDING status, validates that there are
        enough participants for the chosen format, and logs the start event
        to the Tape.

        Args:
            topic: The question or topic to debate.
            format: The debate format (Standard, Socratic, Adversarial).
            participants: List of debate participants with roles and personas.
            max_rounds: Maximum number of rounds before forced conclusion.
            description: Optional longer description of the debate context.
            initiator: Who started the debate (default: "prime").
            metadata: Optional key-value metadata.

        Returns:
            The newly created Debate object.

        Raises:
            NoParticipantsError: if no participants are provided.
        """
        if not participants:
            raise NoParticipantsError("A debate requires at least one participant")

        # Adversarial format requires at least a proponent and opponent
        if format == DebateFormat.ADVERSARIAL:
            roles = {p.role for p in participants}
            if ParticipantRole.PROPONENT not in roles or ParticipantRole.OPPONENT not in roles:
                raise NoParticipantsError(
                    "Adversarial debates require at least one proponent and one opponent"
                )

        debate = Debate(
            topic=topic,
            description=description,
            format=format,
            participants=participants,
            max_rounds=max_rounds,
            initiator=initiator,
            metadata=metadata or {},
        )

        self._store.add(debate)

        await self._tape.log_event(
            event_type="debate.started",
            payload={
                "debate_id": str(debate.id),
                "topic": topic,
                "format": format.value,
                "participant_count": len(participants),
                "max_rounds": max_rounds,
                "initiator": initiator,
            },
            agent_id="prime",
            metadata={
                "participants": [p.name for p in participants],
            },
        )

        # Record debate start in user profile
        if self._profile_engine and initiator:
            with contextlib.suppress(Exception):
                await self._profile_engine.record_interaction(
                    user_id=initiator,
                    interaction_type=InteractionType.DEBATE_STARTED,
                    domain=None,
                    depth=0.5,
                    approved=None,
                )

        return debate

    # ------------------------------------------------------------------
    # Run debate round
    # ------------------------------------------------------------------

    async def run_debate_round(
        self,
        debate_id: UUID,
        arguments: list[DebateArgument] | None = None,
    ) -> DebateRoundResult:
        """Execute one round of the debate.

        If ``arguments`` is provided, those are used (e.g., from real agents
        or a mock). Otherwise, placeholder arguments are generated based on
        the participants' roles, personas, and argument styles.

        Each argument is scored for quality and checked for biases. The round
        result includes a consensus delta showing how much positions converged.

        Args:
            debate_id: ID of the debate to advance.
            arguments: Optional pre-built arguments for this round.

        Returns:
            DebateRoundResult with all arguments, quality scores, and consensus delta.

        Raises:
            DebateNotFoundError: if the debate does not exist.
            DebateAlreadyConcludedError: if the debate has already concluded.
            DebateRoundLimitError: if the max round limit has been reached.
        """
        debate = self._get_debate_or_raise(debate_id)

        if debate.status == DebateStatus.CONCLUDED:
            raise DebateAlreadyConcludedError(
                f"Debate {debate_id} has already concluded"
            )
        if debate.status == DebateStatus.ABORTED:
            raise DebateAlreadyConcludedError(
                f"Debate {debate_id} has been aborted"
            )

        if debate.current_round >= debate.max_rounds:
            raise DebateRoundLimitError(
                f"Debate {debate_id} has reached the maximum of {debate.max_rounds} rounds"
            )

        # Advance round
        debate.current_round += 1
        round_number = debate.current_round

        # Determine phases for this round based on format
        phases = self._get_phases_for_round(debate.format, round_number, debate.max_rounds)

        # If no arguments provided, generate arguments (LLM or heuristic)
        if arguments is None:
            arguments = await self._generate_placeholder_arguments(debate, round_number, phases)

        # Score each argument and detect biases
        all_biases_count = 0
        for arg in arguments:
            biases = self._bias_detector.detect(arg.content)
            quality = self._scorer.score(arg.content, arg.evidence, biases)
            arg.biases_detected = biases
            arg.quality_score = quality
            arg.round_number = round_number
            if arg.phase in phases or not arg.phase:
                arg.phase = arg.phase or phases[0] if phases else DebatePhase.OPENING
            all_biases_count += len([b for b in biases if b != BiasType.NONE_DETECTED])

        # Add arguments to the debate
        debate.arguments.extend(arguments)

        # Compute consensus delta (how much positions converged this round)
        prev_consensus = self._consensus.compute_consensus(
            debate.participants,
            debate.arguments[: -len(arguments)] if arguments else [],
        )
        new_consensus = self._consensus.compute_consensus(
            debate.participants,
            debate.arguments,
        )
        consensus_delta = round(new_consensus.confidence - prev_consensus.confidence, 3)

        # Compute round quality (average of all argument quality scores)
        quality_scores = [a.quality_score for a in arguments]
        round_quality = (
            sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        )

        round_result = DebateRoundResult(
            round_number=round_number,
            arguments=arguments,
            consensus_delta=consensus_delta,
            round_quality=round_quality,
            biases_detected_count=all_biases_count,
        )

        debate.rounds.append(round_result)
        debate.status = DebateStatus.IN_PROGRESS

        self._store.update(debate)

        # Check for early consensus
        if new_consensus.reached and round_number < debate.max_rounds:
            # Consensus reached before max rounds — can conclude early
            pass  # Caller decides whether to conclude; we just note it

        await self._tape.log_event(
            event_type="debate.round",
            payload={
                "debate_id": str(debate_id),
                "round_number": round_number,
                "argument_count": len(arguments),
                "consensus_delta": consensus_delta,
                "round_quality": round_quality,
                "biases_detected": all_biases_count,
                "consensus_reached": new_consensus.reached,
            },
            agent_id="prime",
        )

        return round_result

    # ------------------------------------------------------------------
    # Conclude debate
    # ------------------------------------------------------------------

    async def conclude_debate(self, debate_id: UUID) -> DebateResult:
        """Conclude a debate and produce a final result.

        Summarises the debate, extracts consensus (or identifies irreconcilable
        positions), and produces a final recommendation with a confidence score.

        Args:
            debate_id: ID of the debate to conclude.

        Returns:
            DebateResult with consensus analysis, recommendation, and confidence.

        Raises:
            DebateNotFoundError: if the debate does not exist.
            DebateAlreadyConcludedError: if the debate has already concluded.
        """
        debate = self._get_debate_or_raise(debate_id)

        if debate.status == DebateStatus.CONCLUDED:
            raise DebateAlreadyConcludedError(
                f"Debate {debate_id} has already concluded"
            )

        # Compute final consensus
        consensus = self._consensus.compute_consensus(
            debate.participants,
            debate.arguments,
        )

        # Compute overall quality
        all_scores = [a.quality_score for a in debate.arguments]
        avg_quality = sum(all_scores) / len(all_scores) if all_scores else 0.0

        # Count total biases
        total_biases = sum(
            len([b for b in a.biases_detected if b != BiasType.NONE_DETECTED])
            for a in debate.arguments
        )

        # Generate recommendation based on consensus and quality
        recommendation, rec_confidence, risk = self._generate_recommendation(
            debate, consensus, avg_quality
        )

        result = DebateResult(
            debate_id=debate_id,
            total_rounds=debate.current_round,
            total_arguments=len(debate.arguments),
            average_quality=round(avg_quality, 3),
            total_biases_detected=total_biases,
            consensus=consensus,
            recommendation=recommendation,
            recommendation_confidence=rec_confidence,
            risk_level=risk,
        )

        # Update the debate
        debate.result = result
        debate.status = DebateStatus.CONCLUDED
        debate.concluded_at = datetime.now(UTC)
        self._store.update(debate)

        await self._tape.log_event(
            event_type="debate.concluded",
            payload={
                "debate_id": str(debate_id),
                "total_rounds": debate.current_round,
                "total_arguments": len(debate.arguments),
                "consensus_reached": consensus.reached,
                "consensus_confidence": consensus.confidence,
                "average_quality": round(avg_quality, 3),
                "recommendation_confidence": rec_confidence,
                "risk_level": risk.value,
            },
            agent_id="prime",
        )

        return result

    # ------------------------------------------------------------------
    # Abort debate
    # ------------------------------------------------------------------

    async def abort_debate(self, debate_id: UUID, reason: str = "") -> Debate:
        """Abort a debate before its natural conclusion.

        Args:
            debate_id: ID of the debate to abort.
            reason: Optional reason for the abort.

        Raises:
            DebateNotFoundError: if the debate does not exist.
            DebateAlreadyConcludedError: if the debate has already concluded.
        """
        debate = self._get_debate_or_raise(debate_id)

        if debate.status == DebateStatus.CONCLUDED:
            raise DebateAlreadyConcludedError(
                f"Debate {debate_id} has already concluded"
            )

        debate.status = DebateStatus.ABORTED
        debate.concluded_at = datetime.now(UTC)
        self._store.update(debate)

        await self._tape.log_event(
            event_type="debate.aborted",
            payload={
                "debate_id": str(debate_id),
                "reason": reason,
                "rounds_completed": debate.current_round,
            },
            agent_id="prime",
        )

        return debate

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    async def get_debate(self, debate_id: UUID) -> Debate:
        """Retrieve a single debate by ID.

        Raises:
            DebateNotFoundError: if not found.
        """
        return self._get_debate_or_raise(debate_id)

    async def get_debate_transcript(self, debate_id: UUID) -> Debate:
        """Retrieve the full debate transcript (all arguments and rounds).

        This is the same as ``get_debate()`` but named explicitly for
        transcript use cases.

        Raises:
            DebateNotFoundError: if not found.
        """
        return self._get_debate_or_raise(debate_id)

    async def list_debates(
        self, status: DebateStatus | None = None
    ) -> list[Debate]:
        """List all debates, optionally filtered by status."""
        if status is not None:
            return self._store.list_by_status(status)
        return self._store.list_all()

    # ------------------------------------------------------------------
    # Internal: phase determination
    # ------------------------------------------------------------------

    @staticmethod
    def _get_phases_for_round(
        format: DebateFormat,
        round_number: int,
        max_rounds: int,
    ) -> list[DebatePhase]:
        """Determine which phases occur in a given round based on format.

        Standard: Round 1 = Opening, Middle = Rebuttal, Last = Closing
        Socratic: Round 1 = Question, Middle = Challenge, Last = Synthesis
        Adversarial: All rounds = Opening + Rebuttal (continuous debate)
        """
        match format:
            case DebateFormat.STANDARD:
                if round_number == 1:
                    return [DebatePhase.OPENING]
                if round_number == max_rounds:
                    return [DebatePhase.CLOSING]
                return [DebatePhase.REBUTTAL]

            case DebateFormat.SOCRATIC:
                if round_number == 1:
                    return [DebatePhase.QUESTION]
                if round_number == max_rounds:
                    return [DebatePhase.SYNTHESIS]
                return [DebatePhase.CHALLENGE]

            case DebateFormat.ADVERSARIAL:
                return [DebatePhase.OPENING, DebatePhase.REBUTTAL]

            case _:
                return [DebatePhase.OPENING]

    # ------------------------------------------------------------------
    # Internal: placeholder argument generation
    # ------------------------------------------------------------------

    async def _generate_placeholder_arguments(
        self,
        debate: Debate,
        round_number: int,
        phases: list[DebatePhase],
    ) -> list[DebateArgument]:
        """Generate arguments for participants.

        When ``USE_REAL_LLM=true``, arguments are generated via DSPy using
        the participant's persona and role. Otherwise, heuristic placeholders
        are used.
        """
        from packages.llm import get_llm_provider, is_llm_enabled

        arguments: list[DebateArgument] = []
        llm = get_llm_provider()
        use_llm = is_llm_enabled()

        for participant in debate.participants:
            for phase in phases:
                if use_llm:
                    content = await self._generate_llm_argument(
                        llm=llm,
                        participant=participant,
                        topic=debate.topic,
                        phase=phase,
                        round_number=round_number,
                        format=debate.format,
                        prior_arguments=debate.arguments,
                    )
                else:
                    content = self._generate_argument_content(
                        participant=participant,
                        topic=debate.topic,
                        phase=phase,
                        round_number=round_number,
                        format=debate.format,
                    )
                arg = DebateArgument(
                    participant_agent_id=participant.agent_id,
                    round_number=round_number,
                    phase=phase,
                    content=content,
                    evidence=self._generate_evidence(participant, phase),
                )
                arguments.append(arg)

        return arguments

    @staticmethod
    async def _generate_llm_argument(
        llm: "LLMProvider",
        participant: DebateParticipant,
        topic: str,
        phase: DebatePhase,
        round_number: int,
        format: DebateFormat,
        prior_arguments: list[DebateArgument],
    ) -> str:
        """Generate an argument using an LLM."""
        role = participant.role.value
        persona = participant.persona or "a knowledgeable participant"
        style = participant.argument_style.value

        prior = ""
        if prior_arguments:
            last = prior_arguments[-3:]
            prior = "\n".join(
                f"- {a.participant_agent_id}: {a.content[:200]}"
                for a in last
            )

        prompt = (
            f"You are {persona} participating in a {format.value} debate.\n"
            f"Your role: {role}. Argument style: {style}.\n"
            f"Topic: '{topic}'\n"
            f"Round {round_number}, Phase: {phase.value}\n"
            f"{'Recent arguments:\n' + prior if prior else ''}\n\n"
            f"Write a concise, persuasive argument (2-4 sentences) for this phase."
        )

        try:
            response = await llm.generate(prompt, max_tokens=256)
            return response.strip() or "[LLM returned empty response]"
        except Exception as exc:
            return f"[LLM generation failed: {exc}]"

    @staticmethod
    def _generate_argument_content(
        participant: DebateParticipant,
        topic: str,
        phase: DebatePhase,
        round_number: int,
        format: DebateFormat,
    ) -> str:
        """Generate placeholder argument content based on role and phase."""
        role_stance = {
            ParticipantRole.PROPONENT: "supports",
            ParticipantRole.OPPONENT: "opposes",
            ParticipantRole.MODERATOR: "moderates",
            ParticipantRole.NEUTRAL: "analyses",
        }.get(participant.role, "analyses")

        stance = role_stance

        match phase:
            case DebatePhase.OPENING:
                return (
                    f"[Round {round_number} - Opening] {participant.name} "
                    f"({participant.role.value}) {stance} the proposition: "
                    f"'{topic}'. As {participant.persona or 'a participant'}, "
                    f"I believe this is important because of the evidence "
                    f"and reasoning I will present."
                )
            case DebatePhase.QUESTION:
                return (
                    f"[Round {round_number} - Question] {participant.name} asks: "
                    f"What are the fundamental assumptions behind '{topic}'? "
                    f"Should we {stance} this based on the available evidence?"
                )
            case DebatePhase.REBUTTAL:
                return (
                    f"[Round {round_number} - Rebuttal] {participant.name} "
                    f"counters the previous arguments. While there are valid "
                    f"points, I maintain that {stance} this proposition is "
                    f"the correct position because of practical considerations."
                )
            case DebatePhase.CHALLENGE:
                return (
                    f"[Round {round_number} - Challenge] {participant.name} "
                    f"challenges the reasoning presented so far. "
                    f"The evidence does not fully support the claims made, "
                    f"and alternative explanations should be considered."
                )
            case DebatePhase.CLOSING:
                return (
                    f"[Round {round_number} - Closing] {participant.name} "
                    f"summarises their position: I {stance} the proposition "
                    f"'{topic}'. The debate has shown that while there are "
                    f"risks, the overall evidence supports this position."
                )
            case DebatePhase.SYNTHESIS:
                return (
                    f"[Round {round_number} - Synthesis] {participant.name} "
                    f"synthesises the discussion: Both sides have presented "
                    f"compelling arguments. A balanced approach may be "
                    f"the most prudent path forward."
                )
            case _:
                return (
                    f"[Round {round_number}] {participant.name} presents "
                    f"their argument on '{topic}'."
                )

    @staticmethod
    def _generate_evidence(
        participant: DebateParticipant,
        phase: DebatePhase,
    ) -> list[str]:
        """Generate placeholder evidence citations for an argument."""
        if phase in {DebatePhase.CLOSING, DebatePhase.SYNTHESIS}:
            # Closing/synthesis rounds reference earlier evidence
            return ["See arguments from previous rounds"]

        if participant.argument_style == ArgumentStyle.EVIDENCE_BASED:
            return [f"Data point from {participant.expertise[0] if participant.expertise else 'domain'} analysis"]

        if participant.argument_style == ArgumentStyle.RISK_FOCUSED:
            return [f"Risk assessment from {participant.expertise[0] if participant.expertise else 'ops'} review"]

        return []

    # ------------------------------------------------------------------
    # Internal: recommendation generation
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_recommendation(
        debate: Debate,
        consensus: DebateConsensus,
        avg_quality: float,
    ) -> tuple[str, float, RiskLevel]:
        """Generate a recommendation from the debate outcome.

        Returns:
            (recommendation_text, confidence, risk_level)
        """
        if consensus.reached:
            confidence = round((consensus.confidence + avg_quality) / 2, 3)
            recommendation = (
                f"Consensus reached on '{debate.topic}'. "
                f"{consensus.agreed_position} "
                "Proceed with implementing the agreed position, "
                "noting the key agreements identified during the debate."
            )
            risk = RiskLevel.LOW if confidence > 0.7 else RiskLevel.MEDIUM
        elif consensus.confidence > 0.4:
            confidence = round(consensus.confidence * 0.8, 3)
            recommendation = (
                f"Partial consensus on '{debate.topic}'. "
                f"{consensus.agreed_position} "
                "Implement the areas of agreement while continuing "
                "deliberation on the remaining disagreements."
            )
            risk = RiskLevel.MEDIUM
        else:
            confidence = round(consensus.confidence * 0.6, 3)
            recommendation = (
                f"No consensus on '{debate.topic}'. "
                f"{consensus.agreed_position} "
                "Consider gathering additional evidence or conducting "
                "a simulation before making a decision."
            )
            risk = RiskLevel.HIGH

        return recommendation, confidence, risk

    # ------------------------------------------------------------------
    # Internal: utility
    # ------------------------------------------------------------------

    def _get_debate_or_raise(self, debate_id: UUID) -> Debate:
        """Look up a debate or raise DebateNotFoundError."""
        debate = self._store.get(debate_id)
        if debate is None:
            raise DebateNotFoundError(f"Debate {debate_id} not found")
        return debate
