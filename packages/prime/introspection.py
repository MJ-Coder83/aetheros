"""Prime Introspection -- Deep system self-awareness.

PrimeIntrospector allows the Prime meta-agent to query the full state of the
InkosAI system: Tape history, AetherGit commits, registered agents, skills,
and domains. Every introspection call is itself logged to the Tape, creating
a recursive self-awareness loop.

This module also provides rich historical analysis over the full Tape:
temporal queries, pattern detection, trend analysis, and anomaly detection.

Design principles:
- Every introspection call is logged to the Tape (Prime observes itself)
- All queries go through the TapeService so the audit trail is complete
- SystemSnapshot is a Pydantic model -- serialisable, versionable, queryable
- Historical analysis methods operate over the full Tape, not just snapshots
"""

from __future__ import annotations

import platform
import sys
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from packages.tape.models import TapeEntry
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class AgentDescriptor(BaseModel):
    """Metadata about a registered agent in the system."""

    agent_id: str
    name: str
    capabilities: list[str] = []
    status: str = "unknown"
    last_seen: datetime | None = None


class SkillDescriptor(BaseModel):
    """Metadata about a registered skill."""

    skill_id: str
    name: str
    version: str = "0.1.0"
    description: str = ""


class DomainDescriptor(BaseModel):
    """Metadata about a registered domain (problem space)."""

    domain_id: str
    name: str
    description: str = ""
    agent_count: int = 0


class SystemSnapshot(BaseModel):
    """Complete point-in-time snapshot of the InkosAI system state.

    Prime uses this to understand what the system looks like right now —
    its agents, skills, domains, recent Tape activity, and infrastructure.
    """

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    system_info: dict[str, str] = {}
    tape_stats: dict[str, int] = {}
    recent_tape_entries: list[TapeEntry] = []
    agents: list[AgentDescriptor] = []
    skills: list[SkillDescriptor] = []
    domains: list[DomainDescriptor] = []
    active_worktrees: list[str] = []
    health_status: str = "unknown"


# ---------------------------------------------------------------------------
# Registry (in-memory for now; will be backed by Postgres later)
# ---------------------------------------------------------------------------


class AgentRegistry:
    """In-memory registry of known agents.

    In production this will be backed by PostgreSQL. For now, agents are
    registered at startup or via the API.
    """

    def __init__(self) -> None:
        self._agents: dict[str, AgentDescriptor] = {}

    def register(self, agent: AgentDescriptor) -> None:
        self._agents[agent.agent_id] = agent

    def unregister(self, agent_id: str) -> None:
        self._agents.pop(agent_id, None)

    def get_agent(self, agent_id: str) -> AgentDescriptor | None:
        return self._agents.get(agent_id)

    def list_agents(self) -> list[AgentDescriptor]:
        return list(self._agents.values())


class SkillRegistry:
    """In-memory registry of known skills."""

    def __init__(self) -> None:
        self._skills: dict[str, SkillDescriptor] = {}

    def register(self, skill: SkillDescriptor) -> None:
        self._skills[skill.skill_id] = skill

    def unregister(self, skill_id: str) -> None:
        self._skills.pop(skill_id, None)

    def get_skill(self, skill_id: str) -> SkillDescriptor | None:
        return self._skills.get(skill_id)

    def list_skills(self) -> list[SkillDescriptor]:
        return list(self._skills.values())


class DomainRegistry:
    """In-memory registry of known domains."""

    def __init__(self) -> None:
        self._domains: dict[str, DomainDescriptor] = {}

    def register(self, domain: DomainDescriptor) -> None:
        self._domains[domain.domain_id] = domain

    def unregister(self, domain_id: str) -> None:
        self._domains.pop(domain_id, None)

    def get_domain(self, domain_id: str) -> DomainDescriptor | None:
        return self._domains.get(domain_id)

    def list_domains(self) -> list[DomainDescriptor]:
        return list(self._domains.values())


# ---------------------------------------------------------------------------
# PrimeIntrospector
# ---------------------------------------------------------------------------


class PrimeIntrospector:
    """Deep system introspection engine for the Prime meta-agent.

    PrimeIntrospector gives Prime the ability to observe and understand the
    entire system state. Every introspection call is logged to the Tape so
    that Prime's self-observation is itself part of the audit trail.

    Usage::

        tape_svc = TapeService(InMemoryTapeRepository())
        introspector = PrimeIntrospector(tape_service=tape_svc)
        snapshot = await introspector.snapshot()
        # snapshot contains the full system state
    """

    def __init__(
        self,
        tape_service: TapeService,
        agent_registry: AgentRegistry | None = None,
        skill_registry: SkillRegistry | None = None,
        domain_registry: DomainRegistry | None = None,
    ) -> None:
        self._tape = tape_service
        self._agents = agent_registry or AgentRegistry()
        self._skills = skill_registry or SkillRegistry()
        self._domains = domain_registry or DomainRegistry()

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    async def snapshot(self) -> SystemSnapshot:
        """Capture a full point-in-time snapshot of the system.

        This is Prime's primary self-awareness method. It queries every
        subsystem and returns a unified view.
        """
        recent_entries = await self._tape.get_recent_entries(limit=20)
        tape_stats = await self._compute_tape_stats()

        snapshot = SystemSnapshot(
            system_info=self._collect_system_info(),
            tape_stats=tape_stats,
            recent_tape_entries=recent_entries,
            agents=self._agents.list_agents(),
            skills=self._skills.list_skills(),
            domains=self._domains.list_domains(),
            active_worktrees=self._list_worktrees(),
            health_status="healthy",
        )

        # Log the introspection event to the Tape
        await self._tape.log_event(
            event_type="prime.introspection",
            payload={"snapshot_id": str(snapshot.timestamp.isoformat())},
            agent_id="prime",
            metadata={"entry_count": len(recent_entries)},
        )

        return snapshot

    async def query_tape(
        self,
        event_type: str | None = None,
        agent_id: str | None = None,
        limit: int = 50,
    ) -> list[TapeEntry]:
        """Query the Tape with optional filters.

        Prime can search for specific event types, agent actions, or
        just browse the most recent activity.
        """
        entries = await self._tape.get_entries(
            event_type=event_type,
            agent_id=agent_id,
            limit=limit,
        )
        await self._tape.log_event(
            event_type="prime.tape_query",
            payload={
                "filters": {
                    "event_type": event_type,
                    "agent_id": agent_id,
                    "limit": limit,
                }
            },
            agent_id="prime",
        )
        return entries

    async def get_agent_status(self, agent_id: str) -> AgentDescriptor | None:
        """Look up a specific agent's status."""
        agent = self._agents.get_agent(agent_id)
        await self._tape.log_event(
            event_type="prime.agent_lookup",
            payload={"target_agent_id": agent_id, "found": agent is not None},
            agent_id="prime",
        )
        return agent

    async def list_skills(self) -> list[SkillDescriptor]:
        """List all registered skills in the system."""
        skills = self._skills.list_skills()
        await self._tape.log_event(
            event_type="prime.skill_list",
            payload={"skill_count": len(skills)},
            agent_id="prime",
        )
        return skills

    async def list_domains(self) -> list[DomainDescriptor]:
        """List all registered domains in the system."""
        domains = self._domains.list_domains()
        await self._tape.log_event(
            event_type="prime.domain_list",
            payload={"domain_count": len(domains)},
            agent_id="prime",
        )
        return domains

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    async def _compute_tape_stats(self) -> dict[str, int]:
        """Compute summary statistics from the Tape."""
        all_entries = await self._tape.get_recent_entries(limit=1000)
        event_type_counts: dict[str, int] = {}
        agent_counts: dict[str, int] = {}
        for entry in all_entries:
            event_type_counts[entry.event_type] = event_type_counts.get(entry.event_type, 0) + 1
            if entry.agent_id is not None:
                agent_counts[entry.agent_id] = agent_counts.get(entry.agent_id, 0) + 1
        return {
            "total_entries": len(all_entries),
            "unique_event_types": len(event_type_counts),
            "unique_agents": len(agent_counts),
        }

    @staticmethod
    def _collect_system_info() -> dict[str, str]:
        """Collect runtime environment information."""
        return {
            "python_version": sys.version,
            "platform": platform.platform(),
            "platform_node": platform.node(),
            "python_implementation": platform.python_implementation(),
        }

    @staticmethod
    def _list_worktrees() -> list[str]:
        """List active git worktrees (best-effort, non-fatal on failure)."""
        import subprocess

        try:
            result = subprocess.run(
                ["git", "worktree", "list", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return []
            worktrees: list[str] = []
            for line in result.stdout.strip().splitlines():
                if line.startswith("worktree "):
                    worktrees.append(line.removeprefix("worktree "))
            return worktrees
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return []

    async def historical_analysis(
        self,
        from_time: str | None = None,
        to_time: str | None = None,
        bucket_size_minutes: int = 60,
    ) -> HistoricalAnalysis:
        """Perform a comprehensive historical analysis over the Tape.

        This is Prime's deep introspection method -- it analyses the full
        Tape history to detect patterns, trends, anomalies, and provide
        temporal insights into system behaviour.

        Args:
            from_time: ISO format start time (optional).
            to_time: ISO format end time (optional).
            bucket_size_minutes: Size of temporal buckets for aggregation.

        Returns:
            A HistoricalAnalysis with patterns, trends, and rankings.
        """
        analyzer = HistoricalAnalyzer()

        entries = await self._tape.get_entries(
            from_time=from_time,
            to_time=to_time,
            limit=1000,
        )

        if not entries:
            return HistoricalAnalysis()

        entries = sorted(entries, key=lambda e: e.timestamp)

        buckets = analyzer.bucket_by_time(entries, bucket_size_minutes)
        patterns = analyzer.detect_patterns(entries)
        trends = analyzer.analyse_trends(entries)
        _type_ranking, agent_ranking = analyzer.rank_activity(entries)

        event_type_dist: dict[str, int] = {}
        for entry in entries:
            event_type_dist[entry.event_type] = (
                event_type_dist.get(entry.event_type, 0) + 1
            )

        anomaly_count = sum(
            1 for p in patterns if p.pattern_type == "anomaly"
        )

        time_start = entries[0].timestamp if entries else None
        time_end = entries[-1].timestamp if entries else None

        result = HistoricalAnalysis(
            total_events_analysed=len(entries),
            time_range_start=time_start,
            time_range_end=time_end,
            temporal_buckets=buckets,
            patterns=patterns,
            trends=trends,
            event_type_distribution=event_type_dist,
            agent_activity_ranking=agent_ranking,
            anomaly_count=anomaly_count,
        )

        await self._tape.log_event(
            event_type="prime.historical_analysis",
            payload={
                "total_events": len(entries),
                "patterns_found": len(patterns),
                "trends_analysed": len(trends),
                "anomaly_count": anomaly_count,
            },
            agent_id="prime",
        )

        return result

    async def temporal_query(
        self,
        from_time: str | None = None,
        to_time: str | None = None,
        event_type: str | None = None,
        agent_id: str | None = None,
        limit: int = 200,
    ) -> list[TapeEntry]:
        """Query the Tape with temporal filters.

        This is a richer temporal query interface than the basic query_tape,
        supporting time range filtering and sorting.

        Args:
            from_time: ISO format start time.
            to_time: ISO format end time.
            event_type: Filter by event type.
            agent_id: Filter by agent ID.
            limit: Maximum entries to return.

        Returns:
            Chronologically sorted list of Tape entries.
        """
        entries = await self._tape.get_entries(
            event_type=event_type,
            agent_id=agent_id,
            from_time=from_time,
            to_time=to_time,
            limit=limit,
        )

        entries = sorted(entries, key=lambda e: e.timestamp)

        await self._tape.log_event(
            event_type="prime.temporal_query",
            payload={
                "from_time": from_time,
                "to_time": to_time,
                "event_type": event_type,
                "agent_id": agent_id,
                "result_count": len(entries),
            },
            agent_id="prime",
        )

        return entries


# ---------------------------------------------------------------------------
# Historical analysis models
# ---------------------------------------------------------------------------


class TemporalBucket(BaseModel):
    """A time-bucketed aggregation of Tape events."""

    period_start: datetime
    period_end: datetime
    event_count: int = 0
    event_types: dict[str, int] = Field(default_factory=dict)
    agent_ids: dict[str, int] = Field(default_factory=dict)
    top_event_type: str = ""
    top_agent_id: str = ""


class EventPattern(BaseModel):
    """A detected pattern in the Tape history."""

    pattern_type: str  # "burst", "periodic", "trend", "anomaly"
    event_type: str
    description: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    start_time: datetime | None = None
    end_time: datetime | None = None
    frequency: int = 0  # How many times this pattern occurs
    metadata: dict[str, object] = Field(default_factory=dict)


class TrendPoint(BaseModel):
    """A single data point in a trend analysis."""

    timestamp: datetime
    value: float


class TrendAnalysis(BaseModel):
    """Result of a trend analysis over Tape data."""

    metric: str
    direction: str = "stable"  # "increasing", "decreasing", "stable", "volatile"
    slope: float = 0.0
    points: list[TrendPoint] = []
    anomaly_indices: list[int] = []  # Indices into points[] where anomalies detected


class HistoricalAnalysis(BaseModel):
    """Complete historical analysis result."""

    total_events_analysed: int = 0
    time_range_start: datetime | None = None
    time_range_end: datetime | None = None
    temporal_buckets: list[TemporalBucket] = []
    patterns: list[EventPattern] = []
    trends: list[TrendAnalysis] = []
    event_type_distribution: dict[str, int] = Field(default_factory=dict)
    agent_activity_ranking: list[dict[str, object]] = []
    anomaly_count: int = 0



# ---------------------------------------------------------------------------
# Historical analysis engine (extends PrimeIntrospector)
# ---------------------------------------------------------------------------


class HistoricalAnalyzer:
    """Analyse Tape history for temporal patterns, trends, and anomalies.

    Provides methods for:
    - Temporal bucketing: Group events by time period
    - Pattern detection: Identify bursts, periodicity, anomalies
    - Trend analysis: Detect increasing/decreasing/stable trends
    - Activity ranking: Rank agents and event types by frequency
    """

    def bucket_by_time(
        self,
        entries: list[TapeEntry],
        bucket_size_minutes: int = 60,
    ) -> list[TemporalBucket]:
        """Bucket Tape entries into time periods.

        Args:
            entries: Tape entries to bucket (must be chronologically ordered).
            bucket_size_minutes: Size of each time bucket in minutes.

        Returns:
            List of TemporalBucket with aggregated statistics.
        """
        if not entries:
            return []

        buckets: list[TemporalBucket] = []
        from datetime import timedelta

        # Find time range
        min_time = min(e.timestamp for e in entries)
        max_time = max(e.timestamp for e in entries)

        current_start = min_time.replace(
            minute=0, second=0, microsecond=0
        )
        delta = timedelta(minutes=bucket_size_minutes)

        while current_start <= max_time:
            current_end = current_start + delta
            bucket_entries = [
                e for e in entries
                if current_start <= e.timestamp < current_end
            ]

            event_types: dict[str, int] = {}
            agent_ids: dict[str, int] = {}
            for entry in bucket_entries:
                event_types[entry.event_type] = (
                    event_types.get(entry.event_type, 0) + 1
                )
                if entry.agent_id is not None:
                    agent_ids[entry.agent_id] = (
                        agent_ids.get(entry.agent_id, 0) + 1
                    )

            top_event = (
                str(max(event_types, key=lambda k: event_types[k]))
                if event_types
                else ""
            )
            top_agent = (
                str(max(agent_ids, key=lambda k: agent_ids[k]))
                if agent_ids
                else ""
            )

            buckets.append(
                TemporalBucket(
                    period_start=current_start,
                    period_end=current_end,
                    event_count=len(bucket_entries),
                    event_types=event_types,
                    agent_ids=agent_ids,
                    top_event_type=top_event,
                    top_agent_id=top_agent,
                )
            )
            current_start = current_end

        return buckets

    def detect_patterns(
        self,
        entries: list[TapeEntry],
        min_confidence: float = 0.5,
    ) -> list[EventPattern]:
        """Detect patterns in Tape event history.

        Detects:
        - Bursts: Sudden spikes in event frequency
        - Periodic: Regularly recurring event types
        - Trends: Sustained increases or decreases
        - Anomalies: Events that deviate from normal patterns
        """
        if not entries:
            return []

        patterns: list[EventPattern] = []

        # Group entries by event type
        by_type: dict[str, list[TapeEntry]] = {}
        for entry in entries:
            by_type.setdefault(entry.event_type, []).append(entry)

        # Detect bursts per event type
        for event_type, type_entries in by_type.items():
            burst_pattern = self._detect_bursts(event_type, type_entries)
            if burst_pattern is not None and burst_pattern.confidence >= min_confidence:
                patterns.append(burst_pattern)

        # Detect periodic patterns
        for event_type, type_entries in by_type.items():
            periodic = self._detect_periodicity(event_type, type_entries)
            if periodic is not None and periodic.confidence >= min_confidence:
                patterns.append(periodic)

        # Detect anomalies (events with unusual payloads or timing)
        anomaly_pattern = self._detect_anomalies(entries)
        if anomaly_pattern is not None and anomaly_pattern.confidence >= min_confidence:
            patterns.append(anomaly_pattern)

        return patterns

    def analyse_trends(
        self,
        entries: list[TapeEntry],
        event_type: str | None = None,
    ) -> list[TrendAnalysis]:
        """Analyse trends in event frequency over time.

        Args:
            entries: Tape entries to analyse.
            event_type: If specified, analyse trends for this event type only.

        Returns:
            List of TrendAnalysis results per event type.
        """
        if not entries:
            return []

        # Group by type
        by_type: dict[str, list[TapeEntry]] = {}
        for entry in entries:
            if event_type is None or entry.event_type == event_type:
                by_type.setdefault(entry.event_type, []).append(entry)

        trends: list[TrendAnalysis] = []
        for et, type_entries in by_type.items():
            trend = self._compute_trend(et, type_entries)
            trends.append(trend)

        return trends

    def rank_activity(
        self,
        entries: list[TapeEntry],
    ) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        """Rank event types and agents by activity frequency.

        Returns:
            Tuple of (event_type_ranking, agent_ranking), each sorted
            descending by count.
        """
        type_counts: dict[str, int] = {}
        agent_counts: dict[str, int] = {}
        for entry in entries:
            type_counts[entry.event_type] = type_counts.get(entry.event_type, 0) + 1
            if entry.agent_id is not None:
                agent_counts[entry.agent_id] = agent_counts.get(entry.agent_id, 0) + 1

        type_ranking = [
            {"name": k, "count": v} for k, v in sorted(
                type_counts.items(), key=lambda x: x[1], reverse=True
            )
        ]
        agent_ranking = [
            {"name": k, "count": v} for k, v in sorted(
                agent_counts.items(), key=lambda x: x[1], reverse=True
            )
        ]

        return type_ranking, agent_ranking

    # --- Internal pattern detection methods ---

    def _detect_bursts(
        self,
        event_type: str,
        entries: list[TapeEntry],
    ) -> EventPattern | None:
        """Detect burst patterns in a single event type."""
        if len(entries) < 5:
            return None

        # Sort by timestamp
        sorted_entries = sorted(entries, key=lambda e: e.timestamp)

        # Calculate intervals between consecutive events
        intervals: list[float] = []
        for i in range(1, len(sorted_entries)):
            delta = (
                sorted_entries[i].timestamp - sorted_entries[i - 1].timestamp
            ).total_seconds()
            intervals.append(delta)

        if not intervals:
            return None

        avg_interval = sum(intervals) / len(intervals)

        # A burst is when we see 3+ consecutive very short intervals
        short_threshold = avg_interval * 0.2
        consecutive_short = 0
        max_consecutive = 0
        burst_start: datetime | None = None
        burst_end: datetime | None = None

        for i, interval in enumerate(intervals):
            if interval < short_threshold:
                consecutive_short += 1
                if consecutive_short == 1:
                    burst_start = sorted_entries[i].timestamp
                if consecutive_short > max_consecutive:
                    max_consecutive = consecutive_short
                    burst_end = sorted_entries[i + 1].timestamp
            else:
                consecutive_short = 0

        if max_consecutive < 3:
            return None

        confidence = min(1.0, max_consecutive / 10.0)
        return EventPattern(
            pattern_type="burst",
            event_type=event_type,
            description=(
                f"Burst detected: {max_consecutive + 1} rapid '{event_type}' events "
                f"within a short period"
            ),
            confidence=confidence,
            start_time=burst_start,
            end_time=burst_end,
            frequency=1,
            metadata={"max_consecutive": max_consecutive + 1},
        )

    def _detect_periodicity(
        self,
        event_type: str,
        entries: list[TapeEntry],
    ) -> EventPattern | None:
        """Detect periodic patterns in event timing."""
        if len(entries) < 4:
            return None

        sorted_entries = sorted(entries, key=lambda e: e.timestamp)
        intervals: list[float] = []
        for i in range(1, len(sorted_entries)):
            delta = (
                sorted_entries[i].timestamp - sorted_entries[i - 1].timestamp
            ).total_seconds()
            intervals.append(delta)

        if not intervals:
            return None

        avg_interval = sum(intervals) / len(intervals)

        # Check if intervals are relatively consistent (within 30% of average)
        consistent_count = sum(
            1 for iv in intervals if abs(iv - avg_interval) < avg_interval * 0.3
        )
        consistency_ratio = consistent_count / len(intervals)

        if consistency_ratio < 0.6:
            return None

        return EventPattern(
            pattern_type="periodic",
            event_type=event_type,
            description=(
                f"Periodic pattern: '{event_type}' events occurring roughly "
                f"every {round(avg_interval / 60, 1)} minutes"
            ),
            confidence=round(consistency_ratio, 3),
            start_time=sorted_entries[0].timestamp,
            end_time=sorted_entries[-1].timestamp,
            frequency=len(sorted_entries),
            metadata={"avg_interval_seconds": round(avg_interval, 1)},
        )

    def _detect_anomalies(
        self,
        entries: list[TapeEntry],
    ) -> EventPattern | None:
        """Detect anomalous events (unusual payloads or timing)."""
        if len(entries) < 10:
            return None

        # Anomaly: event types that appear only once (rare events)
        type_counts: dict[str, int] = {}
        for entry in entries:
            type_counts[entry.event_type] = type_counts.get(entry.event_type, 0) + 1

        rare_types = [t for t, c in type_counts.items() if c == 1]

        if not rare_types:
            return None

        rare_ratio = len(rare_types) / len(type_counts)
        confidence = min(1.0, rare_ratio * 2)

        return EventPattern(
            pattern_type="anomaly",
            event_type="*",
            description=(
                f"Detected {len(rare_types)} rare event type(s): "
                f"{', '.join(rare_types[:5])}"
            ),
            confidence=confidence,
            frequency=len(rare_types),
            metadata={"rare_types": rare_types[:10]},
        )

    def _compute_trend(
        self,
        event_type: str,
        entries: list[TapeEntry],
    ) -> TrendAnalysis:
        """Compute a trend analysis for a single event type."""
        if len(entries) < 2:
            return TrendAnalysis(
                metric=event_type,
                direction="stable",
                points=[],
            )

        # Group entries by day and count per day
        from collections import defaultdict
        from datetime import date

        daily_counts: dict[date, int] = defaultdict(int)
        for entry in entries:
            daily_counts[entry.timestamp.date()] += 1

        # Convert to trend points
        points: list[TrendPoint] = []
        for day in sorted(daily_counts):
            day_dt = datetime.combine(day, datetime.min.time().replace(tzinfo=UTC))
            points.append(
                TrendPoint(
                    timestamp=day_dt,
                    value=float(daily_counts[day]),
                )
            )

        if len(points) < 2:
            return TrendAnalysis(
                metric=event_type,
                direction="stable",
                points=points,
            )

        # Simple linear regression for slope
        n = len(points)
        x_vals = list(range(n))
        y_vals = [p.value for p in points]
        x_mean = sum(x_vals) / n
        y_mean = sum(y_vals) / n

        numerator = sum(
            (x - x_mean) * (y - y_mean)
            for x, y in zip(x_vals, y_vals, strict=True)
        )
        denominator = sum((x - x_mean) ** 2 for x in x_vals)

        slope = numerator / denominator if denominator != 0 else 0.0

        # Determine direction
        if abs(slope) < 0.1:
            direction = "stable"
        elif slope > 0:
            direction = "increasing"
        else:
            direction = "decreasing"

        # Detect volatility (high variance)
        variance = sum((y - y_mean) ** 2 for y in y_vals) / n
        if variance > y_mean * 2 and y_mean > 0:
            direction = "volatile"

        # Detect anomalies (points > 2 standard deviations from mean)
        import math

        std_dev = math.sqrt(variance) if variance > 0 else 0
        anomaly_indices: list[int] = []
        if std_dev > 0:
            for i, y in enumerate(y_vals):
                if abs(y - y_mean) > 2 * std_dev:
                    anomaly_indices.append(i)

        return TrendAnalysis(
            metric=event_type,
            direction=direction,
            slope=round(slope, 4),
            points=points,
            anomaly_indices=anomaly_indices,
        )



