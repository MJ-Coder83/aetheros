"""Semantic Tape Querying -- Natural language interface over the Tape.

This module enables Prime (and users) to ask complex questions about system
history using natural language. It translates NL queries into structured Tape
filters, ranks results by semantic relevance, and produces human-readable
answers.

Design principles:
- All NL queries are logged to the Tape (full auditability)
- Query translation uses keyword extraction + pattern matching (no LLM required)
- Semantic relevance scoring ranks results by how well they match the query
- Results include both structured data and natural language summaries
- The interface is extensible -- LLM-powered translation can be plugged in later

Usage::

    from packages.tape.nlq import SemanticTapeQueryEngine

    engine = SemanticTapeQueryEngine(tape_service=tape_svc)
    result = await engine.ask("What errors occurred in the last hour?")
    # result.entries contains matching Tape entries
    # result.summary contains a natural language summary
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from packages.tape.models import TapeEntry
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class QueryIntent(StrEnum):
    """Detected intent of a natural language query."""

    WHAT = "what"  # What happened?
    WHEN = "when"  # When did X happen?
    WHO = "who"  # Who/which agent did X?
    HOW_MANY = "how_many"  # Count/frequency questions
    TREND = "trend"  # Trend/pattern questions
    LATEST = "latest"  # Most recent events
    ERRORS = "errors"  # Error-related queries
    PROPOSALS = "proposals"  # Proposal-related queries
    GENERAL = "general"  # Fallback for unclassified queries


class RelevanceLevel(StrEnum):
    """How relevant a result is to the query."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class ParsedQuery(BaseModel):
    """Structured representation of a parsed NL query."""

    original_query: str
    intent: QueryIntent = QueryIntent.GENERAL
    event_types: list[str] = []
    agent_ids: list[str] = []
    time_range_start: datetime | None = None
    time_range_end: datetime | None = None
    keywords: list[str] = []
    negation: bool = False
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ScoredEntry(BaseModel):
    """A Tape entry with a semantic relevance score."""

    entry: TapeEntry
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    relevance_level: RelevanceLevel = RelevanceLevel.MEDIUM
    match_reasons: list[str] = []


class QueryResult(BaseModel):
    """Result of a semantic Tape query."""

    id: UUID = Field(default_factory=uuid4)
    query: str
    parsed: ParsedQuery
    entries: list[ScoredEntry] = []
    total_matches: int = 0
    summary: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class QueryStore:
    """In-memory store for query results."""

    def __init__(self) -> None:
        self._results: dict[UUID, QueryResult] = {}

    def add(self, result: QueryResult) -> None:
        self._results[result.id] = result

    def get(self, result_id: UUID) -> QueryResult | None:
        return self._results.get(result_id)

    def list_all(self) -> list[QueryResult]:
        return list(self._results.values())


# ---------------------------------------------------------------------------
# Query parser
# ---------------------------------------------------------------------------


class NLQueryParser:
    """Parses natural language queries into structured ParsedQuery objects.

    Uses keyword extraction and pattern matching to identify:
    - Query intent (what, when, who, how many, etc.)
    - Event type filters (from known event type patterns)
    - Agent filters (from known agent IDs or "agent" mentions)
    - Time range filters (from temporal expressions)
    - Keywords for semantic relevance scoring
    """

    # Event type keyword mapping
    _EVENT_TYPE_KEYWORDS: ClassVar[dict[str, list[str]]] = {
        "prime.introspection": ["introspect", "snapshot", "system state"],
        "prime.tape_query": ["tape query", "search tape", "look up"],
        "prime.agent_lookup": ["agent lookup", "agent status", "agent search"],
        "prime.skill_list": ["skill list", "skills"],
        "prime.domain_list": ["domain list", "domains"],
        "plan.created": ["plan created", "new plan", "plan made"],
        "plan.activated": ["plan started", "plan activated"],
        "plan.completed": ["plan finished", "plan done", "plan completed"],
        "plan.step_started": ["step started", "step began"],
        "plan.step_completed": ["step finished", "step done", "step completed"],
        "plan.step_failed": ["step failed", "step error", "step errored"],
        "proposal.created": ["proposal created", "new proposal", "proposed"],
        "proposal.approved": ["proposal approved", "accepted"],
        "proposal.rejected": ["proposal rejected", "denied"],
        "domain.blueprint_generated": ["blueprint generated", "domain blueprint"],
        "domain.registered": ["domain registered", "domain created"],
        "knowledge.extracted": ["knowledge extracted", "extracted knowledge"],
        "knowledge.transfer_completed": ["transfer completed", "knowledge transferred"],
        "profile.created": ["profile created", "new profile"],
        "profile.interaction_recorded": ["interaction recorded", "user interaction"],
        "debate.started": ["debate started", "new debate"],
        "debate.concluded": ["debate concluded", "debate finished"],
        "simulation.started": ["simulation started", "new simulation"],
        "simulation.completed": ["simulation completed", "simulation done"],
        "explainability.explanation_generated": ["explanation generated", "explained"],
    }

    # Time expression patterns
    _TIME_PATTERNS: ClassVar[list[tuple[str, re.Pattern[str]]]] = [
        ("last_hour", re.compile(r"last\s+(?:1\s+)?hour", re.IGNORECASE)),
        ("last_24h", re.compile(r"last\s+(?:24\s+hours?|day)", re.IGNORECASE)),
        ("last_7d", re.compile(r"last\s+(?:7\s+days?|week)", re.IGNORECASE)),
        ("last_30d", re.compile(r"last\s+(?:30\s+days?|month)", re.IGNORECASE)),
        ("today", re.compile(r"today", re.IGNORECASE)),
        ("yesterday", re.compile(r"yesterday", re.IGNORECASE)),
    ]

    # Intent patterns
    _INTENT_PATTERNS: ClassVar[list[tuple[QueryIntent, re.Pattern[str]]]] = [
        (QueryIntent.WHAT, re.compile(r"what\s+(happened|events|occurred)", re.IGNORECASE)),
        (QueryIntent.WHEN, re.compile(r"when\s+(did|was|were)", re.IGNORECASE)),
        (QueryIntent.WHO, re.compile(r"who\s+(did|made|created|performed)", re.IGNORECASE)),
        (QueryIntent.HOW_MANY, re.compile(r"how\s+many", re.IGNORECASE)),
        (QueryIntent.TREND, re.compile(r"(trend|pattern|over\s+time|increasing|decreasing)", re.IGNORECASE)),
        (QueryIntent.LATEST, re.compile(r"(latest|recent|last|newest)", re.IGNORECASE)),
        (QueryIntent.ERRORS, re.compile(r"(error|fail|bug|crash|exception)", re.IGNORECASE)),
        (QueryIntent.PROPOSALS, re.compile(r"(proposal|approve|reject|governance)", re.IGNORECASE)),
    ]

    def parse(self, query: str) -> ParsedQuery:
        """Parse a natural language query into a structured representation."""
        query_lower = query.lower().strip()

        # Detect intent
        intent = self._detect_intent(query_lower)

        # Detect event types
        event_types = self._detect_event_types(query_lower)

        # Detect time range
        time_start, time_end = self._detect_time_range(query_lower)

        # Detect agent references
        agent_ids = self._detect_agents(query)

        # Extract keywords
        keywords = self._extract_keywords(query_lower)

        # Detect negation
        negation = any(neg in query_lower for neg in ["not", "no ", "never", "except", "without"])

        # Compute confidence based on how many signals we detected
        signals = 0
        if intent != QueryIntent.GENERAL:
            signals += 1
        if event_types:
            signals += 1
        if time_start is not None or time_end is not None:
            signals += 1
        if agent_ids:
            signals += 1
        confidence = min(1.0, signals / 4.0 + 0.2)

        return ParsedQuery(
            original_query=query,
            intent=intent,
            event_types=event_types,
            agent_ids=agent_ids,
            time_range_start=time_start,
            time_range_end=time_end,
            keywords=keywords,
            negation=negation,
            confidence=confidence,
        )

    def _detect_intent(self, query_lower: str) -> QueryIntent:
        """Detect the primary intent of the query."""
        for intent, pattern in self._INTENT_PATTERNS:
            if pattern.search(query_lower):
                return intent
        return QueryIntent.GENERAL

    def _detect_event_types(self, query_lower: str) -> list[str]:
        """Detect event type filters from the query."""
        matched: list[str] = []
        for event_type, keywords in self._EVENT_TYPE_KEYWORDS.items():
            for kw in keywords:
                if kw in query_lower:
                    matched.append(event_type)
                    break
        return matched

    def _detect_time_range(
        self, query_lower: str
    ) -> tuple[datetime | None, datetime | None]:
        """Detect time range from temporal expressions."""
        now = datetime.now(UTC)

        for pattern_name, pattern in self._TIME_PATTERNS:
            if pattern.search(query_lower):
                if pattern_name == "last_hour":
                    return now - timedelta(hours=1), now
                if pattern_name == "last_24h":
                    return now - timedelta(hours=24), now
                if pattern_name == "last_7d":
                    return now - timedelta(days=7), now
                if pattern_name == "last_30d":
                    return now - timedelta(days=30), now
                if pattern_name == "today":
                    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    return start, now
                if pattern_name == "yesterday":
                    start = (now - timedelta(days=1)).replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                    end = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    return start, end

        return None, None

    def _detect_agents(self, query: str) -> list[str]:
        """Detect agent ID references in the query."""
        # Look for quoted agent IDs
        quoted = re.findall(r'"([^"]+)"', query)
        agents: list[str] = []
        for q in quoted:
            if q.startswith("agent-") or q.startswith("prime"):
                agents.append(q)
        return agents

    def _extract_keywords(self, query_lower: str) -> list[str]:
        """Extract meaningful keywords from the query."""
        # Remove stop words
        stop_words = {
            "what", "when", "who", "how", "many", "the", "a", "an",
            "is", "are", "was", "were", "did", "do", "does", "in",
            "on", "at", "to", "from", "of", "for", "with", "by",
            "last", "past", "over", "about", "any", "all", "some",
        }
        words = re.findall(r"[a-z_]+", query_lower)
        return [w for w in words if w not in stop_words and len(w) > 2]


# ---------------------------------------------------------------------------
# Relevance scorer
# ---------------------------------------------------------------------------


class RelevanceScorer:
    """Scores Tape entries for semantic relevance to a parsed query.

    Uses a combination of:
    - Event type match (highest weight)
    - Agent ID match
    - Keyword match in payload
    - Temporal proximity
    """

    def score(
        self,
        entry: TapeEntry,
        parsed: ParsedQuery,
    ) -> ScoredEntry:
        """Score a single Tape entry against the parsed query."""
        score = 0.0
        reasons: list[str] = []

        # Event type match (0-0.4)
        if parsed.event_types and entry.event_type in parsed.event_types:
            score += 0.4
            reasons.append(f"Event type match: {entry.event_type}")

        # Agent ID match (0-0.2)
        if parsed.agent_ids and entry.agent_id in parsed.agent_ids:
            score += 0.2
            reasons.append(f"Agent match: {entry.agent_id}")

        # Keyword match in event_type + payload (0-0.3)
        if parsed.keywords:
            searchable = (
                entry.event_type.lower()
                + " "
                + str(entry.payload).lower()
                + " "
                + str(entry.metadata).lower()
            )
            keyword_matches = sum(
                1 for kw in parsed.keywords if kw in searchable
            )
            keyword_score = min(0.3, keyword_matches * 0.1)
            score += keyword_score
            if keyword_matches > 0:
                reasons.append(f"{keyword_matches} keyword(s) matched")

        # Temporal proximity bonus (0-0.1)
        if (
            parsed.time_range_start is not None
            and parsed.time_range_start
            <= entry.timestamp
            <= (parsed.time_range_end or datetime.now(UTC))
        ):
            score += 0.1
            reasons.append("Within time range")

        # Clamp score
        score = max(0.0, min(1.0, score))

        # Determine relevance level
        if score >= 0.5:
            level = RelevanceLevel.HIGH
        elif score >= 0.2:
            level = RelevanceLevel.MEDIUM
        elif score > 0.0:
            level = RelevanceLevel.LOW
        else:
            level = RelevanceLevel.NONE

        return ScoredEntry(
            entry=entry,
            relevance_score=round(score, 3),
            relevance_level=level,
            match_reasons=reasons,
        )


# ---------------------------------------------------------------------------
# Result summarizer
# ---------------------------------------------------------------------------


class ResultSummarizer:
    """Generates natural language summaries of query results."""

    def summarize(self, result: QueryResult) -> str:
        """Generate a summary of the query result."""
        parsed = result.parsed
        entries = result.entries
        total = result.total_matches

        if total == 0:
            return f"No results found for query: \"{parsed.original_query}\""

        high_relevance = [e for e in entries if e.relevance_level == RelevanceLevel.HIGH]
        medium_relevance = [e for e in entries if e.relevance_level == RelevanceLevel.MEDIUM]

        # Build summary based on intent
        intent = parsed.intent
        if intent == QueryIntent.HOW_MANY:
            return f"Found {total} matching events."
        if intent == QueryIntent.LATEST:
            if high_relevance:
                latest = high_relevance[0].entry
                return (
                    f"Most recent match: {latest.event_type} "
                    f"at {latest.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}"
                )
            return f"Found {total} recent events."

        if intent == QueryIntent.ERRORS:
            error_count = sum(
                1 for e in entries
                if "error" in e.entry.event_type
                or "fail" in e.entry.event_type.lower()
            )
            return (
                f"Found {error_count} error/failure events "
                f"out of {total} total matches."
            )

        if intent == QueryIntent.WHEN:
            if entries:
                first = entries[0].entry
                last = entries[-1].entry
                return (
                    f"Matching events span from "
                    f"{first.timestamp.strftime('%Y-%m-%d %H:%M')} to "
                    f"{last.timestamp.strftime('%Y-%m-%d %H:%M')} "
                    f"({total} events total)"
                )
            return f"Found {total} events."

        # General summary
        parts = [f"Found {total} matching events"]
        if high_relevance:
            parts.append(f"{len(high_relevance)} highly relevant")
        if medium_relevance:
            parts.append(f"{len(medium_relevance)} moderately relevant")

        # Top event types
        type_counts: dict[str, int] = {}
        for se in entries:
            type_counts[se.entry.event_type] = type_counts.get(se.entry.event_type, 0) + 1
        if type_counts:
            top_type = str(max(type_counts, key=lambda k: type_counts[k]))
            parts.append(f"Most common: {top_type} ({type_counts[top_type]})")

        return ". ".join(parts) + "."


# ---------------------------------------------------------------------------
# Semantic Tape Query Engine -- the main public API
# ---------------------------------------------------------------------------


class SemanticTapeQueryEngine:
    """Natural language querying interface over the Tape.

    SemanticTapeQueryEngine allows Prime (and users) to ask complex questions
    about system history using natural language. It translates queries into
    structured filters, scores results by relevance, and generates summaries.

    Usage::

        engine = SemanticTapeQueryEngine(tape_service=tape_svc)
        result = await engine.ask("What errors occurred in the last hour?")
        print(result.summary)  # Natural language summary
        for scored_entry in result.entries:
            print(scored_entry.entry.event_type, scored_entry.relevance_score)
    """

    def __init__(
        self,
        tape_service: TapeService,
        parser: NLQueryParser | None = None,
        scorer: RelevanceScorer | None = None,
        summarizer: ResultSummarizer | None = None,
        store: QueryStore | None = None,
    ) -> None:
        self._tape = tape_service
        self._parser = parser or NLQueryParser()
        self._scorer = scorer or RelevanceScorer()
        self._summarizer = summarizer or ResultSummarizer()
        self._store = store or QueryStore()

    async def ask(
        self,
        query: str,
        max_results: int = 50,
    ) -> QueryResult:
        """Ask a natural language question about the Tape.

        Args:
            query: Natural language query (e.g. "What errors occurred recently?").
            max_results: Maximum number of results to return.

        Returns:
            A QueryResult with scored entries and a natural language summary.
        """
        if not query.strip():
            raise ValueError("Query must not be empty")

        # Parse the query
        parsed = self._parser.parse(query)

        # Fetch candidate entries from the Tape
        candidates = await self._fetch_candidates(parsed, max_results=max_results * 3)

        # Score each entry
        scored = [self._scorer.score(entry, parsed) for entry in candidates]

        # Filter out NONE relevance and sort by score
        relevant = [
            s for s in scored if s.relevance_level != RelevanceLevel.NONE
        ]
        relevant.sort(key=lambda s: s.relevance_score, reverse=True)
        relevant = relevant[:max_results]

        # Build result
        result = QueryResult(
            query=query,
            parsed=parsed,
            entries=relevant,
            total_matches=len(relevant),
            confidence=parsed.confidence,
        )

        # Generate summary
        result = result.model_copy(
            update={"summary": self._summarizer.summarize(result)}
        )

        # Store result
        self._store.add(result)

        # Log to Tape
        await self._tape.log_event(
            event_type="tape.nl_query",
            payload={
                "query_id": str(result.id),
                "query": query,
                "intent": parsed.intent.value,
                "total_matches": result.total_matches,
                "confidence": result.confidence,
            },
            agent_id="semantic-tape-query-engine",
        )

        return result

    async def _fetch_candidates(
        self,
        parsed: ParsedQuery,
        max_results: int = 150,
    ) -> list[TapeEntry]:
        """Fetch candidate Tape entries based on the parsed query."""
        from_time = (
            parsed.time_range_start.isoformat()
            if parsed.time_range_start
            else None
        )
        to_time = (
            parsed.time_range_end.isoformat()
            if parsed.time_range_end
            else None
        )

        # If specific event types are detected, filter by first one
        event_type: str | None = None
        if parsed.event_types:
            event_type = parsed.event_types[0]

        # If specific agents are detected, filter by first one
        agent_id: str | None = None
        if parsed.agent_ids:
            agent_id = parsed.agent_ids[0]

        return await self._tape.get_entries(
            event_type=event_type,
            agent_id=agent_id,
            from_time=from_time,
            to_time=to_time,
            limit=max_results,
        )

    async def get_query_result(self, result_id: UUID) -> QueryResult:
        """Retrieve a stored query result by ID."""
        result = self._store.get(result_id)
        if result is None:
            raise ValueError(f"Query result {result_id} not found")
        return result

    async def list_query_results(self) -> list[QueryResult]:
        """List all stored query results."""
        return self._store.list_all()
