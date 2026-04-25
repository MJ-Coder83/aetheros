"""Profile Learning Engine — Behavioral analysis and profile refinement for Prime.

This module implements Agent 2's responsibility: learning from user behavior
across Tape, Proposals, Canvas, Feedback, and Folder-Tree to continuously
refine the UserProfile.

Key components:
- TapeBehaviorAnalyzer:    Extracts interaction patterns from Tape entries
- ProposalPatternAnalyzer: Analyzes approval/rejection tendencies
- CanvasInteractionAnalyzer: Studies canvas usage patterns
- FeedbackAnalyzer:        Processes explicit feedback signals
- FolderTreeAnalyzer:      Infers organizational preferences
- ProfileLearningEngine:   Orchestrates analysis and profile updates

Design principles:
- All inferences are confidence-scored (0.0 - 1.0)
- Updates are incremental and logged to Tape
- Respects user privacy — only operational patterns, no PII
- Backward-compatible with existing profile storage
- Supports batch learning across all users

Usage::

    from packages.prime.profile_learning import ProfileLearningEngine

    learner = ProfileLearningEngine(
        tape_service=tape_svc,
        profile_storage=profile_storage,
        proposal_engine=proposal_engine,  # optional
        canvas_service=canvas_service,    # optional
        folder_tree_service=folder_tree,  # optional
    )

    # Learn from a single interaction
    await learner.learn_from_interaction(
        user_id="alice",
        interaction_type="query",
        domain="legal",
        depth=0.8,
        approved=True,
        metadata={...},
    )

    # Batch learning for all users
    await learner.batch_learn_all()

    # Generate profile refinement suggestions
    suggestions = await learner.suggest_profile_updates("alice")
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, ClassVar

from pydantic import BaseModel, Field

from packages.prime.profile import (
    AutomationPreference,
    CommunicationStyle,
    ProfileStorage,
    UserProfile,
)
from packages.tape.models import TapeEntry
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class LearningEventType(StrEnum):
    """Types of events that can trigger profile learning."""

    QUERY = "query"
    COMMAND = "command"
    APPROVAL = "approval"
    REJECTION = "rejection"
    PROPOSAL_CREATED = "proposal_created"
    PROPOSAL_APPROVED = "proposal_approved"
    PROPOSAL_REJECTED = "proposal_rejected"
    CANVAS_NODE_ADDED = "canvas_node_added"
    CANVAS_NODE_MOVED = "canvas_node_moved"
    CANVAS_LAYOUT_APPLIED = "canvas_layout_applied"
    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    FOLDER_CREATED = "folder_created"
    FEEDBACK_GIVEN = "feedback_given"


class InsightConfidence(StrEnum):
    """Confidence levels for learned insights."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ---------------------------------------------------------------------------
# Data models for learning insights
# ---------------------------------------------------------------------------


class BehavioralInsight(BaseModel):
    """A discovered behavioral pattern or preference."""

    category: str  # "working_style", "preference", "skill", "goal", "pattern"
    key: str
    value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    source: str  # Tape, Proposal, Canvas, Feedback, FolderTree
    supporting_events: list[str] = []  # Event IDs or types
    first_observed: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_observed: datetime = Field(default_factory=lambda: datetime.now(UTC))
    observation_count: int = 0
    metadata: dict[str, Any] = {}


class LearningSession(BaseModel):
    """Tracks a learning batch session."""

    id: str = Field(default_factory=lambda: str(datetime.now(UTC).timestamp()))
    user_id: str | None = None  # None = all users
    start_time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    end_time: datetime | None = None
    events_analyzed: int = 0
    insights_generated: int = 0
    profile_updates: int = 0
    errors: list[str] = []
    metadata: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Analyzer base
# ---------------------------------------------------------------------------


class BaseAnalyzer:
    """Base class for all analyzers."""

    def __init__(
        self,
        tape_service: TapeService,
        profile_storage: ProfileStorage,
        **kwargs: Any,
    ) -> None:
        self._tape = tape_service
        self._storage = profile_storage

    async def analyze(self, user_id: str, limit: int = 100) -> list[BehavioralInsight]:
        """Analyze user behavior and return insights."""
        raise NotImplementedError

    async def apply_insights(
        self,
        profile: UserProfile,
        insights: list[BehavioralInsight],
    ) -> UserProfile:
        """Apply learned insights to a profile."""
        raise NotImplementedError


# ===========================================================================
# Tape Behavior Analyzer
# ===========================================================================


class TapeBehaviorAnalyzer(BaseAnalyzer):
    """Analyzes Tape entries to extract interaction patterns and preferences."""

    # Depth thresholds for inferring preferences
    DEPTH_EXPLORATORY: ClassVar[float] = 0.7
    DEPTH_DETAILED: ClassVar[float] = 0.5

    # Interaction frequency weights
    INTERACTION_WEIGHTS: ClassVar[dict[str, float]] = {
        LearningEventType.QUERY: 1.0,
        LearningEventType.COMMAND: 1.2,
        LearningEventType.APPROVAL: 0.8,
        LearningEventType.REJECTION: 0.8,
        LearningEventType.PROPOSAL_CREATED: 1.0,
        LearningEventType.FEEDBACK_GIVEN: 1.5,
    }

    # Skill/domain inference thresholds
    MIN_INTERACTIONS_FOR_SKILL: ClassVar[int] = 5
    HIGH_DEPTH_THRESHOLD: ClassVar[float] = 0.6

    async def analyze(self, user_id: str, limit: int = 100) -> list[BehavioralInsight]:
        """Analyze Tape entries for a user."""
        entries = await self._tape.get_entries(limit=limit)
        user_entries = [e for e in entries if e.payload.get("user_id") == user_id]

        if not user_entries:
            return []

        insights: list[BehavioralInsight] = []

        # Analyze depth preference
        depth_insight = self._analyze_depth_preference(user_id, user_entries)
        if depth_insight:
            insights.append(depth_insight)

        # Analyze interaction timing patterns
        timing_insight = self._analyze_timing_patterns(user_id, user_entries)
        if timing_insight:
            insights.append(timing_insight)

        # Analyze interaction type distribution
        type_insight = self._analyze_interaction_types(user_id, user_entries)
        if type_insight:
            insights.append(type_insight)

        # Infer skills from domain interactions
        skill_insights = self._infer_skills_from_domains(user_id, user_entries)
        insights.extend(skill_insights)

        # Infer goals from sustained domain activity
        goal_insights = self._infer_goals_from_activity(user_id, user_entries)
        insights.extend(goal_insights)

        return insights

    def _infer_skills_from_domains(
        self,
        user_id: str,
        entries: list[TapeEntry],
    ) -> list[BehavioralInsight]:
        """Infer learned skills based on repeated domain interactions with high depth."""
        domain_interactions: dict[str, list[float]] = defaultdict(list)

        for e in entries:
            domain = e.payload.get("domain")
            depth = e.payload.get("depth")
            if isinstance(domain, str) and isinstance(depth, (int, float)):
                domain_interactions[domain].append(float(depth))

        insights: list[BehavioralInsight] = []

        for domain, depths in domain_interactions.items():
            if len(depths) < self.MIN_INTERACTIONS_FOR_SKILL:
                continue

            avg_depth = sum(depths) / len(depths)
            if avg_depth >= self.HIGH_DEPTH_THRESHOLD:
                # User has developed expertise in this domain
                insights.append(
                    BehavioralInsight(
                        category="skill",
                        key=f"domain_expertise_{domain}",
                        value=domain,
                        confidence=min(1.0, len(depths) / 20.0),
                        source="tape",
                        observation_count=len(depths),
                        metadata={"avg_depth": avg_depth},
                    )
                )

        return insights

    def _infer_goals_from_activity(
        self,
        user_id: str,
        entries: list[TapeEntry],
    ) -> list[BehavioralInsight]:
        """Infer potential user goals based on focused domain activity clusters."""
        # Group by domain and time windows to detect sustained focus
        from collections import defaultdict

        domain_days: dict[str, set[str]] = defaultdict(set)

        for e in entries:
            domain = e.payload.get("domain")
            if isinstance(domain, str) and e.timestamp:
                day_key = e.timestamp.strftime("%Y-%m-%d")
                domain_days[domain].add(day_key)

        insights: list[BehavioralInsight] = []

        for domain, days in domain_days.items():
            if len(days) >= 5:  # Active across at least 5 days
                # Likely working on something related to this domain
                insights.append(
                    BehavioralInsight(
                        category="goal",
                        key=f"active_focus_{domain}",
                        value=f"Mastering {domain}",
                        confidence=min(1.0, len(days) / 30.0),
                        source="tape",
                        observation_count=len(days),
                        metadata={"domain": domain, "active_days": len(days)},
                    )
                )

        return insights

    def _analyze_depth_preference(
        self,
        user_id: str,
        entries: list[TapeEntry],
    ) -> BehavioralInsight | None:
        """Infer response detail preference from average interaction depth."""
        depths = []
        for e in entries:
            depth = e.payload.get("depth")
            if isinstance(depth, (int, float)):
                depths.append(float(depth))

        if len(depths) < 5:
            return None

        avg_depth = sum(depths) / len(depths)

        # Determine preference level
        if avg_depth >= self.DEPTH_EXPLORATORY:
            value = "exploratory"  # User wants deep, detailed responses
        elif avg_depth >= self.DEPTH_DETAILED:
            value = "balanced"
        else:
            value = "concise"

        confidence = min(1.0, len(depths) / 20.0)

        return BehavioralInsight(
            category="communication_style",
            key="preferred_detail_level",
            value=value,
            confidence=confidence,
            source="tape",
            supporting_events=[e.event_type for e in entries[:10]],
            observation_count=len(depths),
        )

    def _analyze_timing_patterns(
        self,
        user_id: str,
        entries: list[TapeEntry],
    ) -> BehavioralInsight | None:
        """Detect time-of-day patterns in user activity."""
        hour_counts: Counter[int] = Counter()
        for e in entries:
            if hasattr(e, "timestamp") and e.timestamp:
                hour = e.timestamp.hour
                hour_counts[hour] += 1

        total_with_hour = sum(hour_counts.values())
        if total_with_hour < 5:
            return None

        total = sum(hour_counts.values())
        morning = sum(hour_counts.get(h, 0) for h in range(6, 12))
        afternoon = sum(hour_counts.get(h, 0) for h in range(12, 18))
        evening = sum(hour_counts.get(h, 0) for h in range(18, 24))
        night = sum(hour_counts.get(h, 0) for h in range(0, 6))

        # Find peak period
        periods = {
            "morning": morning,
            "afternoon": afternoon,
            "evening": evening,
            "night": night,
        }
        peak_period = max(periods, key=lambda k: periods[k])
        peak_ratio = periods[peak_period] / total if total > 0 else 0

        if peak_ratio < 0.3:  # No strong pattern
            return None

        confidence = min(1.0, total / 30.0)

        return BehavioralInsight(
            category="interaction_pattern",
            key="preferred_time",
            value=peak_period,
            confidence=confidence,
            source="tape",
            supporting_events=[],
            observation_count=total,
        )

    def _analyze_interaction_types(
        self,
        user_id: str,
        entries: list[TapeEntry],
    ) -> BehavioralInsight | None:
        """Analyze distribution of interaction types."""
        type_counts: dict[str, float] = {}
        total_weighted: float = 0.0

        for e in entries:
            t = e.event_type
            weight = self.INTERACTION_WEIGHTS.get(t, 0.5)
            type_counts[t] = type_counts.get(t, 0.0) + weight
            total_weighted += weight

        if total_weighted < 10:
            return None

        # Find dominant interaction type
        dominant = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:1]
        if not dominant:
            return None

        top_type, top_count = dominant[0]
        ratio = top_count / total_weighted if total_weighted > 0 else 0

        if ratio < 0.5:  # No dominant type
            return None

        return BehavioralInsight(
            category="interaction_pattern",
            key="dominant_interaction_type",
            value=top_type,
            confidence=min(1.0, total_weighted / 50.0),
            source="tape",
            observation_count=int(total_weighted),
        )

    async def apply_insights(
        self,
        profile: UserProfile,
        insights: list[BehavioralInsight],
    ) -> UserProfile:
        """Apply tape-based insights to the profile."""
        user_id = profile.user_id

        for insight in insights:
            if insight.category == "communication_style":
                style_map = {
                    "exploratory": CommunicationStyle.DETAILED,
                    "balanced": CommunicationStyle.CONVERSATIONAL,
                    "concise": CommunicationStyle.CONCISE,
                }
                new_style = style_map.get(insight.value)
                if new_style and insight.confidence > 0.6:
                    await self._storage.update_working_style(
                        user_id=user_id,
                        communication_style=new_style,
                    )

            elif insight.category == "interaction_pattern" and insight.key == "preferred_time":
                await self._storage.record_pattern(
                    user_id=user_id,
                    pattern_type="time_of_day",
                    pattern_value=insight.value,
                    confidence=insight.confidence,
                )

            elif insight.category == "skill":
                domain = insight.value
                if domain:
                    proficiency = insight.confidence * 0.5
                    await self._storage.add_or_update_skill(
                        user_id=user_id,
                        skill_id=domain.lower().replace(" ", "_"),
                        name=domain.title(),
                        proficiency=proficiency,
                        category="domain",
                    )

            elif insight.category == "goal":
                goal_title = insight.value
                # Check for duplicate
                existing = await self._storage.list_goals(user_id=user_id)
                if goal_title and not any(g.title == goal_title for g in existing):
                    await self._storage.add_goal(
                        user_id=user_id,
                        title=goal_title,
                        description="Inferred from sustained activity in related domain",
                        category="inferred",
                        priority=3,
                    )

        # Reload profile to get the latest state after all mutations
        return await self._storage.get_profile(user_id)


# ===========================================================================
# Proposal Pattern Analyzer
# ===========================================================================


class ProposalPatternAnalyzer(BaseAnalyzer):
    """Analyzes proposal approval/rejection patterns to infer risk tolerance."""

    async def analyze(self, user_id: str, limit: int = 100) -> list[BehavioralInsight]:
        """Analyze proposal review behavior."""
        # For this phase, proposals are logged to tape as events
        entries = await self._tape.get_entries(
            event_type="prime.proposal_approved",
            limit=limit,
        )

        user_approvals = [e for e in entries if e.payload.get("reviewer") == user_id]
        entries = await self._tape.get_entries(
            event_type="prime.proposal_rejected",
            limit=limit,
        )
        user_rejections = [e for e in entries if e.payload.get("reviewer") == user_id]

        total_decisions = len(user_approvals) + len(user_rejections)

        if total_decisions < 3:
            return []

        approval_rate = len(user_approvals) / total_decisions if total_decisions > 0 else 0.0

        insights: list[BehavioralInsight] = []

        # Infer risk tolerance from approval rate
        if approval_rate >= 0.75:
            risk_value = "risk_tolerant"
            confidence = 0.7
        elif approval_rate >= 0.5:
            risk_value = "moderate"
            confidence = 0.6
        else:
            risk_value = "risk_averse"
            confidence = 0.7

        insights.append(
            BehavioralInsight(
                category="preference",
                key="risk_tolerance",
                value=risk_value,
                confidence=confidence,
                source="proposals",
                observation_count=total_decisions,
            )
        )

        return insights

    async def apply_insights(
        self,
        profile: UserProfile,
        insights: list[BehavioralInsight],
    ) -> UserProfile:
        """Apply proposal-based insights to the profile."""
        for insight in insights:
            if insight.category == "preference" and insight.key == "risk_tolerance":
                # Map to automation preference heuristically
                risk_to_auto = {
                    "risk_tolerant": AutomationPreference.SEMI_AUTOMATED,
                    "moderate": AutomationPreference.ASSISTED,
                    "risk_averse": AutomationPreference.MANUAL,
                }
                auto_pref = risk_to_auto.get(insight.value)
                if auto_pref:
                    profile = await self._storage.update_working_style(
                        user_id=profile.user_id,
                        automation_preference=auto_pref,
                    )
        return profile


# ===========================================================================
# Canvas Interaction Analyzer
# ===========================================================================


class CanvasInteractionAnalyzer(BaseAnalyzer):
    """Analyzes canvas usage to infer visual workflow preferences."""

    async def analyze(self, user_id: str, limit: int = 100) -> list[BehavioralInsight]:
        """Analyze canvas interaction patterns."""
        entries = await self._tape.get_entries(
            event_type="canvas.node_added",
            limit=limit,
        )

        # Assume user_id in metadata
        user_entries = [e for e in entries if e.metadata.get("user_id") == user_id]

        if len(user_entries) < 5:
            return []

        insights: list[BehavioralInsight] = []

        # Count node types used
        node_types: Counter[str] = Counter()
        for e in user_entries:
            node_type_raw = e.payload.get("node_type", "")
            node_type = str(node_type_raw) if isinstance(node_type_raw, str) else ""
            node_types[node_type] += 1

        if node_types:
            dominant_type, _ = node_types.most_common(1)[0]
            insights.append(
                BehavioralInsight(
                    category="workflow_preference",
                    key="preferred_node_type",
                    value=dominant_type,
                    confidence=min(1.0, len(user_entries) / 30.0),
                    source="canvas",
                    observation_count=len(user_entries),
                )
            )

        return insights

    async def apply_insights(
        self,
        profile: UserProfile,
        insights: list[BehavioralInsight],
    ) -> UserProfile:
        """Apply canvas-based insights to the profile."""
        for insight in insights:
            if insight.category == "workflow_preference":
                await self._storage.record_pattern(
                    user_id=profile.user_id,
                    pattern_type="canvas_usage",
                    pattern_value=insight.value,
                    confidence=insight.confidence,
                )
        # Reload to get updated pattern
        return await self._storage.get_profile(profile.user_id)


# ===========================================================================
# Feedback Analyzer
# ===========================================================================


class FeedbackAnalyzer(BaseAnalyzer):
    """Analyzes explicit user feedback to refine profile."""

    async def analyze(self, user_id: str, limit: int = 100) -> list[BehavioralInsight]:
        """Analyze feedback events."""
        entries = await self._tape.get_entries(
            event_type="feedback.given",
            limit=limit,
        )

        user_feedback = [e for e in entries if e.payload.get("user_id") == user_id]

        if not user_feedback:
            return []

        insights: list[BehavioralInsight] = []

        # Aggregate sentiment/rating
        ratings = []
        for e in user_feedback:
            rating = e.payload.get("rating")
            if isinstance(rating, (int, float)):
                ratings.append(float(rating))

        if ratings:
            avg_rating = sum(ratings) / len(ratings)
            if avg_rating >= 4.0:
                sentiment = "highly_satisfied"
            elif avg_rating >= 3.0:
                sentiment = "satisfied"
            elif avg_rating >= 2.0:
                sentiment = "neutral"
            else:
                sentiment = "dissatisfied"

            insights.append(
                BehavioralInsight(
                    category="feedback",
                    key="satisfaction_sentiment",
                    value=sentiment,
                    confidence=min(1.0, len(ratings) / 10.0),
                    source="feedback",
                    observation_count=len(ratings),
                )
            )

        return insights

    async def apply_insights(
        self,
        profile: UserProfile,
        insights: list[BehavioralInsight],
    ) -> UserProfile:
        """Apply feedback-based insights to the profile."""
        # Currently feedback doesn't directly change profile, but logs as pattern
        # Future: could adjust preferences, trigger follow-up
        return profile


# ===========================================================================
# Folder Tree Analyzer
# ===========================================================================


class FolderTreeAnalyzer(BaseAnalyzer):
    """Analyzes folder-tree changes to infer organizational preferences."""

    async def analyze(self, user_id: str, limit: int = 100) -> list[BehavioralInsight]:
        """Analyze folder-tree modification patterns."""
        entries = await self._tape.get_entries(
            event_type="prime.file_modified",
            limit=limit,
        )

        user_edits = [e for e in entries if e.payload.get("user_id") == user_id]

        if len(user_edits) < 3:
            return []

        insights: list[BehavioralInsight] = []

        # Calculate editing frequency
        if user_edits:
            first = min(e.timestamp for e in user_edits if e.timestamp)
            last = max(e.timestamp for e in user_edits if e.timestamp)
            if first and last:
                days = (last - first).days + 1
                edits_per_day = len(user_edits) / max(1, days)
                if edits_per_day >= 2:
                    behavior = "frequent_editor"
                elif edits_per_day >= 0.5:
                    behavior = "regular_editor"
                else:
                    behavior = "occasional_editor"

                insights.append(
                    BehavioralInsight(
                        category="workflow_preference",
                        key="editing_behavior",
                        value=behavior,
                        confidence=min(1.0, len(user_edits) / 20.0),
                        source="folder_tree",
                        observation_count=len(user_edits),
                    )
                )

        return insights

    async def apply_insights(
        self,
        profile: UserProfile,
        insights: list[BehavioralInsight],
    ) -> UserProfile:
        """Apply folder-tree-based insights to the profile."""
        for insight in insights:
            # Heuristic: frequent editors prefer detailed communications
            if insight.key == "editing_behavior" and insight.value == "frequent_editor":
                    profile = await self._storage.update_working_style(
                        user_id=profile.user_id,
                        communication_style=CommunicationStyle.DETAILED,
                    )
        return profile


# ===========================================================================
# Profile Learning Engine — Main Orchestrator
# ===========================================================================


class ProfileLearningEngine:
    """Orchestrates multi-source behavioral analysis for user profile learning.

    The engine coordinates multiple analyzers to:
    1. Pull recent Tape events for a user (or all users)
    2. Query Proposals for approval/rejection patterns
    3. Check Canvas interaction logs
    4. Incorporate explicit feedback
    5. Factor in folder-tree edit history

    It then computes updates to:
    - Working style (methodical, exploratory, collaborative, etc.)
    - Preferences (automation level, communication style, etc.)
    - Goals (derived from domain activity)
    - Skills (inferred from tool usage and depth)
    - Interaction patterns (timing, frequency, domain affinity)
    - History summary (aggregate statistics)

    All updates are applied incrementally and logged to Tape.
    """

    def __init__(
        self,
        tape_service: TapeService,
        profile_storage: ProfileStorage,
        proposal_engine: Any = None,
        canvas_service: Any = None,
        folder_tree_service: Any = None,
        **kwargs: Any,
    ) -> None:
        self._tape = tape_service
        self._storage = profile_storage
        self._proposal_engine = proposal_engine
        self._canvas_service = canvas_service
        self._folder_tree_service = folder_tree_service

        # Initialize analyzers
        self._tape_analyzer = TapeBehaviorAnalyzer(tape_service, profile_storage)
        self._proposal_analyzer = ProposalPatternAnalyzer(tape_service, profile_storage)
        self._canvas_analyzer = CanvasInteractionAnalyzer(tape_service, profile_storage)
        self._feedback_analyzer = FeedbackAnalyzer(tape_service, profile_storage)
        self._folder_analyzer = FolderTreeAnalyzer(tape_service, profile_storage)

    # ------------------------------------------------------------------
    # Per-user learning
    # ------------------------------------------------------------------

    async def learn_for_user(
        self,
        user_id: str,
        limit: int = 100,
        apply_immediately: bool = True,
    ) -> dict[str, Any]:
        """Run full behavioral analysis for a single user.

        Parameters
        ----------
        user_id:
            The user to analyze.
        limit:
            Maximum recent events to analyze per source.
        apply_immediately:
            If True, updates the profile in storage; if False, returns
            a dict of suggested updates for review.

        Returns
        -------
        dict
            Summary of insights and updates applied.
        """
        session = LearningSession(user_id=user_id)
        all_insights: list[BehavioralInsight] = []

        # Run all analyzers
        analyzers: list[BaseAnalyzer] = [
            self._tape_analyzer,
            self._proposal_analyzer,
            self._canvas_analyzer,
            self._feedback_analyzer,
            self._folder_analyzer,
        ]

        for analyzer in analyzers:
            try:
                insights = await analyzer.analyze(user_id, limit=limit)
                all_insights.extend(insights)
                session.events_analyzed += len(insights)
            except Exception as e:
                session.errors.append(f"{analyzer.__class__.__name__}: {e}")

        if not apply_immediately:
            return {
                "user_id": user_id,
                "insights": all_insights,
                "session": session,
            }

        # Fetch current profile (or create if missing)
        profile = await self._storage.get_or_create_profile(user_id)

        original_version = profile.version

        # Apply insights through each analyzer (each analyzer filters its own insights)
        for analyzer in analyzers:
            try:
                result = await analyzer.apply_insights(profile, all_insights)
                if isinstance(result, tuple):
                    profile, _changes = result
                else:
                    profile = result
            except Exception as e:
                session.errors.append(f"apply {analyzer.__class__.__name__}: {e}")

        # Check if profile was updated by comparing versions
        if profile.version > original_version:
            session.profile_updates = 1

        session.end_time = datetime.now(UTC)
        session.insights_generated = len(all_insights)

        return {
            "user_id": user_id,
            "insights": all_insights,
            "session": session,
            "profile_version": profile.version,
        }

    # ------------------------------------------------------------------
    # Batch learning
    # ------------------------------------------------------------------

    async def batch_learn_all(
        self,
        limit_per_user: int = 50,
        batch_size: int = 10,
    ) -> dict[str, Any]:
        """Run learning for all users in batches.

        Parameters
        ----------
        limit_per_user:
            Events to analyze per user.
        batch_size:
            Number of concurrent user analyses.

        Returns
        -------
        dict
            Summary with per-user results.
        """
        profiles = await self._storage.list_profiles()
        if not profiles:
            return {"users_processed": 0, "results": {}}

        results: dict[str, Any] = {}
        total_updates = 0

        for i in range(0, len(profiles), batch_size):
            batch = profiles[i : i + batch_size]
            for profile in batch:
                try:
                    result = await self.learn_for_user(
                        user_id=profile.user_id,
                        limit=limit_per_user,
                        apply_immediately=True,
                    )
                    results[profile.user_id] = result
                    if result.get("profile_version", 0) > profile.version:
                        total_updates += 1
                except Exception as e:
                    results[profile.user_id] = {"error": str(e)}

        return {
            "users_processed": len(profiles),
            "users_updated": total_updates,
            "results": results,
        }

    # ------------------------------------------------------------------
    # Suggestion generation (for UI review)
    # ------------------------------------------------------------------

    async def suggest_profile_updates(
        self,
        user_id: str,
        min_confidence: float = 0.7,
    ) -> dict[str, Any]:
        """Generate profile update suggestions for human review.

        Unlike ``learn_for_user`` which applies changes immediately,
        this method returns potential updates with confidence scores,
        allowing a UI or human to approve them first.

        Parameters
        ----------
        user_id:
            The user to analyze.
        min_confidence:
            Only return insights with confidence >= this threshold.

        Returns
        -------
        dict
            Suggested updates keyed by profile field.
        """
        result = await self.learn_for_user(user_id, apply_immediately=False)
        insights = result["insights"]

        suggestions: dict[str, Any] = {
            "user_id": user_id,
            "suggestions": [],
        }

        for insight in insights:
            if insight.confidence < min_confidence:
                continue

            suggestion = {
                "category": insight.category,
                "key": insight.key,
                "current_value": None,
                "suggested_value": insight.value,
                "confidence": insight.confidence,
                "source": insight.source,
                "reason": f"Based on {insight.observation_count} observations",
            }
            suggestions["suggestions"].append(suggestion)

        return suggestions

    # ------------------------------------------------------------------
    # Utility: Incremental learning from a single event
    # ------------------------------------------------------------------

    async def learn_from_event(
        self,
        user_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        """Incrementally update profile from a single event.

        This is intended to be called as a callback when a significant
        event occurs (e.g., after a proposal decision or canvas edit).
        It performs lightweight incremental updates without a full re-analysis.

        Parameters
        ----------
        user_id:
            The user affected.
        event_type:
            The Tape event type.
        payload:
            Event payload.
        """
        profile = await self._storage.get_or_create_profile(user_id)

        # Update history summary incrementally
        summary = profile.history_summary
        summary.total_interactions += 1
        summary.last_session_at = datetime.now(UTC)

        # Update domain affinity if domain in payload
        domain = payload.get("domain")
        if domain and isinstance(domain, str):
            if domain not in summary.favorite_domains:
                summary.favorite_domains.append(domain)
            summary.total_domains = len(set(summary.favorite_domains))

        # Use internal store to save directly
        await self._storage._store.save_profile(profile)

    # ------------------------------------------------------------------
    # Utility: Get learning diagnostics
    # ------------------------------------------------------------------

    async def get_learning_diagnostics(self, user_id: str) -> dict[str, Any]:
        """Return debugging info about profile learning for a user."""
        profile = await self._storage.get_profile(user_id)
        if profile is None:
            return {"error": "Profile not found"}

        recent_entries = await self._tape.get_entries(limit=50)
        user_entries = [e for e in recent_entries if e.payload.get("user_id") == user_id]

        return {
            "user_id": user_id,
            "profile_version": profile.version,
            "recent_events_analyzed": len(user_entries),
            "interaction_patterns": [
                p.model_dump() for p in profile.interaction_patterns
            ],
            "total_skills": len(profile.learned_skills),
            "total_goals": len(profile.goals),
            "last_updated": profile.updated_at.isoformat(),
        }
