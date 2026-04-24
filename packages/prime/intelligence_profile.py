"""Prime Personalized Intelligence Profile -- User-adaptive intelligence tracking.

This module builds and maintains a personalised intelligence profile for each
user of the InkosAI system. The profile captures interaction patterns, domain
expertise, preferred workflows, and behavioural signals so that Prime can
adapt its responses, suggestions, and automation strategies to each user.

Design principles:
- Every profile update is logged to the Tape (full auditability)
- Profiles evolve incrementally with each interaction
- Expertise scoring uses heuristics based on interaction frequency + depth
- Preference inference from observed behaviour (not explicit settings only)
- Privacy-first: profiles store only operational patterns, not personal data
- Profile snapshots enable rollback on incorrect adaptations

Usage::

    from packages.prime.intelligence_profile import IntelligenceProfileEngine

    engine = IntelligenceProfileEngine(tape_service=tape_svc)
    profile = await engine.get_or_create_profile(user_id="alice")
    await engine.record_interaction(user_id="alice", interaction_type="query",
                                    domain="legal", depth=0.8)
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ExpertiseLevel(StrEnum):
    """Domain expertise levels."""

    NOVICE = "novice"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class InteractionType(StrEnum):
    """Types of user interactions tracked by the profile."""

    QUERY = "query"
    COMMAND = "command"
    APPROVAL = "approval"
    REJECTION = "rejection"
    PROPOSAL = "proposal"
    SIMULATION = "simulation"
    DEBATE = "debate"
    BROWSER = "browser"
    FEEDBACK = "feedback"


class PreferenceCategory(StrEnum):
    """Categories of user preferences."""

    RESPONSE_DETAIL = "response_detail"
    AUTOMATION_LEVEL = "automation_level"
    NOTIFICATION_FREQUENCY = "notification_frequency"
    RISK_TOLERANCE = "risk_tolerance"
    WORKFLOW_STYLE = "workflow_style"
    EXPLANATION_DEPTH = "explanation_depth"
    SUGGESTION_FREQUENCY = "suggestion_frequency"


class ProfileStatus(StrEnum):
    """Profile lifecycle status."""

    ACTIVE = "active"
    ARCHIVED = "archived"
    SUSPENDED = "suspended"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class DomainExpertise(BaseModel):
    """Expertise assessment for a single domain."""

    domain_id: str
    level: ExpertiseLevel = ExpertiseLevel.NOVICE
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    interaction_count: int = 0
    total_depth: float = 0.0
    last_interaction: datetime | None = None
    skills_used: list[str] = []
    preferred_workflows: list[str] = []


class UserPreference(BaseModel):
    """A single user preference with inferred and explicit values."""

    category: PreferenceCategory
    value: float = Field(default=0.5, ge=0.0, le=1.0)
    explicit_value: float | None = None
    inferred_value: float = 0.5
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))


class InteractionSummary(BaseModel):
    """Summary statistics for user interactions."""

    total_interactions: int = 0
    interactions_by_type: dict[str, int] = Field(default_factory=dict)
    interactions_by_domain: dict[str, int] = Field(default_factory=dict)
    avg_depth: float = 0.0
    peak_depth: float = 0.0
    last_interaction: datetime | None = None
    approval_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    most_active_hour: int = 0
    daily_streak: int = 0


class IntelligenceProfile(BaseModel):
    """Complete personalised intelligence profile for a user.

    The profile aggregates domain expertise, preferences, interaction
    patterns, and behavioural signals to enable user-adaptive AI.
    """

    id: UUID = Field(default_factory=uuid4)
    user_id: str
    status: ProfileStatus = ProfileStatus.ACTIVE
    domain_expertise: dict[str, DomainExpertise] = Field(default_factory=dict)
    preferences: dict[str, UserPreference] = Field(default_factory=dict)
    interaction_summary: InteractionSummary = Field(
        default_factory=InteractionSummary
    )
    behavioural_signals: dict[str, object] = Field(default_factory=dict)
    adaptation_count: int = 0
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    snapshot_id: UUID | None = None


class ProfileSnapshot(BaseModel):
    """Immutable snapshot of a profile for rollback purposes."""

    id: UUID = Field(default_factory=uuid4)
    profile_id: UUID
    profile_data: dict[str, object] = Field(default_factory=dict)
    reason: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ProfileError(Exception):
    """Base exception for intelligence profile operations."""


class ProfileNotFoundError(ProfileError):
    """Raised when a profile does not exist."""


class SnapshotNotFoundError(ProfileError):
    """Raised when a snapshot does not exist."""


class ProfileTransitionError(ProfileError):
    """Raised on invalid profile status transition."""


# ---------------------------------------------------------------------------
# Profile store (in-memory; Postgres later)
# ---------------------------------------------------------------------------


class ProfileStore:
    """In-memory store for intelligence profiles and snapshots."""

    def __init__(self) -> None:
        self._profiles: dict[str, IntelligenceProfile] = {}
        self._snapshots: dict[UUID, ProfileSnapshot] = {}

    def add_profile(self, profile: IntelligenceProfile) -> None:
        self._profiles[profile.user_id] = profile

    def get_profile(self, user_id: str) -> IntelligenceProfile | None:
        return self._profiles.get(user_id)

    def list_profiles(self) -> list[IntelligenceProfile]:
        return list(self._profiles.values())

    def update_profile(self, profile: IntelligenceProfile) -> None:
        if profile.user_id not in self._profiles:
            raise ProfileNotFoundError(f"Profile for {profile.user_id} not found")
        self._profiles[profile.user_id] = profile

    def add_snapshot(self, snapshot: ProfileSnapshot) -> None:
        self._snapshots[snapshot.id] = snapshot

    def get_snapshot(self, snapshot_id: UUID) -> ProfileSnapshot | None:
        return self._snapshots.get(snapshot_id)

    def list_snapshots(self, profile_id: UUID | None = None) -> list[ProfileSnapshot]:
        snapshots = list(self._snapshots.values())
        if profile_id is not None:
            snapshots = [s for s in snapshots if s.profile_id == profile_id]
        return snapshots


# ---------------------------------------------------------------------------
# Expertise assessor
# ---------------------------------------------------------------------------


class ExpertiseAssessor:
    """Assesses and updates domain expertise based on interactions.

    Uses heuristic scoring based on interaction count, depth, and
    recency. In production, this could use ML models for more
    accurate expertise estimation.
    """

    # Thresholds for expertise levels (cumulative score)
    LEVEL_THRESHOLDS: ClassVar[list[tuple[float, ExpertiseLevel]]] = [
        (0.8, ExpertiseLevel.EXPERT),
        (0.5, ExpertiseLevel.ADVANCED),
        (0.2, ExpertiseLevel.INTERMEDIATE),
        (0.0, ExpertiseLevel.NOVICE),
    ]

    def compute_score(
        self,
        interaction_count: int,
        avg_depth: float,
        recency_boost: float = 1.0,
    ) -> float:
        """Compute expertise score from interaction signals.

        Score formula: f(count) * g(depth) * recency_boost
        where f uses diminishing returns (log) and g is linear.
        """
        import math

        # Diminishing returns on count
        count_factor = min(1.0, math.log1p(interaction_count) / math.log1p(50))
        # Depth is directly proportional (0-1 scale)
        depth_factor = min(1.0, max(0.0, avg_depth))
        # Combine
        score = count_factor * depth_factor * recency_boost
        return max(0.0, min(1.0, round(score, 3)))

    def score_to_level(self, score: float) -> ExpertiseLevel:
        """Map a score to an expertise level."""
        for threshold, level in self.LEVEL_THRESHOLDS:
            if score >= threshold:
                return level
        return ExpertiseLevel.NOVICE

    def update_expertise(
        self,
        expertise: DomainExpertise,
        depth: float,
    ) -> DomainExpertise:
        """Update domain expertise after a new interaction."""
        new_count = expertise.interaction_count + 1
        new_total_depth = expertise.total_depth + depth
        new_avg_depth = new_total_depth / new_count

        score = self.compute_score(new_count, new_avg_depth)
        level = self.score_to_level(score)

        return expertise.model_copy(
            update={
                "interaction_count": new_count,
                "total_depth": new_total_depth,
                "level": level,
                "score": score,
                "last_interaction": datetime.now(UTC),
            }
        )


# ---------------------------------------------------------------------------
# Preference inferrer
# ---------------------------------------------------------------------------


class PreferenceInferrer:
    """Infers user preferences from behavioural signals.

    Rather than requiring explicit settings, the inferrer derives
    preference values from observed interaction patterns.
    """

    def infer_from_interactions(
        self,
        preferences: dict[str, UserPreference],
        summary: InteractionSummary,
    ) -> dict[str, UserPreference]:
        """Update preference inferences based on interaction summary."""
        updated = dict(preferences)

        # Response detail: inferred from average depth
        detail_pref = updated.get(
            PreferenceCategory.RESPONSE_DETAIL.value,
            UserPreference(category=PreferenceCategory.RESPONSE_DETAIL),
        )
        if summary.avg_depth > 0:
            new_inferred = summary.avg_depth
            confidence = min(1.0, summary.total_interactions / 20.0)
            detail_pref = detail_pref.model_copy(
                update={
                    "inferred_value": new_inferred,
                    "confidence": confidence,
                }
            )
        updated[detail_pref.category.value] = detail_pref

        # Automation level: inferred from approval rate
        auto_pref = updated.get(
            PreferenceCategory.AUTOMATION_LEVEL.value,
            UserPreference(category=PreferenceCategory.AUTOMATION_LEVEL),
        )
        if summary.approval_rate > 0:
            new_inferred = summary.approval_rate
            confidence = min(1.0, summary.total_interactions / 30.0)
            auto_pref = auto_pref.model_copy(
                update={
                    "inferred_value": new_inferred,
                    "confidence": confidence,
                }
            )
        updated[auto_pref.category.value] = auto_pref

        # Risk tolerance: inferred from rejection rate (inverse of approval)
        risk_pref = updated.get(
            PreferenceCategory.RISK_TOLERANCE.value,
            UserPreference(category=PreferenceCategory.RISK_TOLERANCE),
        )
        if summary.approval_rate > 0:
            # Higher approval = higher risk tolerance
            new_inferred = summary.approval_rate
            confidence = min(1.0, summary.total_interactions / 25.0)
            risk_pref = risk_pref.model_copy(
                update={
                    "inferred_value": new_inferred,
                    "confidence": confidence,
                }
            )
        updated[risk_pref.category.value] = risk_pref

        # Explanation depth: correlated with response detail
        explain_pref = updated.get(
            PreferenceCategory.EXPLANATION_DEPTH.value,
            UserPreference(category=PreferenceCategory.EXPLANATION_DEPTH),
        )
        if summary.avg_depth > 0:
            new_inferred = min(1.0, summary.avg_depth * 0.8)
            confidence = min(1.0, summary.total_interactions / 15.0)
            explain_pref = explain_pref.model_copy(
                update={
                    "inferred_value": new_inferred,
                    "confidence": confidence,
                }
            )
        updated[explain_pref.category.value] = explain_pref

        # Suggestion frequency: high interaction count = more suggestions welcome
        sug_pref = updated.get(
            PreferenceCategory.SUGGESTION_FREQUENCY.value,
            UserPreference(category=PreferenceCategory.SUGGESTION_FREQUENCY),
        )
        if summary.total_interactions > 0:
            new_inferred = min(1.0, summary.total_interactions / 50.0)
            confidence = min(1.0, summary.total_interactions / 10.0)
            sug_pref = sug_pref.model_copy(
                update={
                    "inferred_value": new_inferred,
                    "confidence": confidence,
                }
            )
        updated[sug_pref.category.value] = sug_pref

        return updated


# ---------------------------------------------------------------------------
# Intelligence Profile Engine -- the main public API
# ---------------------------------------------------------------------------


class IntelligenceProfileEngine:
    """Personalised intelligence profile engine for the Prime meta-agent.

    IntelligenceProfileEngine enables Prime to:
    - Build and maintain per-user intelligence profiles
    - Track domain expertise across interactions
    - Infer preferences from behavioural signals
    - Create profile snapshots for rollback
    - Adapt Prime behaviour based on profile data

    Usage::

        engine = IntelligenceProfileEngine(tape_service=tape_svc)
        profile = await engine.get_or_create_profile(user_id="alice")
        await engine.record_interaction(
            user_id="alice",
            interaction_type="query",
            domain="legal",
            depth=0.8,
        )
    """

    def __init__(
        self,
        tape_service: TapeService,
        store: ProfileStore | None = None,
        expertise_assessor: ExpertiseAssessor | None = None,
        preference_inferrer: PreferenceInferrer | None = None,
    ) -> None:
        self._tape = tape_service
        self._store = store or ProfileStore()
        self._assessor = expertise_assessor or ExpertiseAssessor()
        self._inferrer = preference_inferrer or PreferenceInferrer()

    # ------------------------------------------------------------------
    # Profile CRUD
    # ------------------------------------------------------------------

    async def get_or_create_profile(self, user_id: str) -> IntelligenceProfile:
        """Get an existing profile or create a new one for the user."""
        existing = self._store.get_profile(user_id)
        if existing is not None:
            return existing

        profile = IntelligenceProfile(user_id=user_id)
        self._store.add_profile(profile)

        await self._tape.log_event(
            event_type="profile.created",
            payload={"user_id": user_id, "profile_id": str(profile.id)},
            agent_id="intelligence-profile-engine",
        )

        return profile

    async def get_profile(self, user_id: str) -> IntelligenceProfile:
        """Get a profile, raising if not found."""
        profile = self._store.get_profile(user_id)
        if profile is None:
            raise ProfileNotFoundError(f"Profile for user '{user_id}' not found")
        return profile

    async def list_profiles(self) -> list[IntelligenceProfile]:
        """List all profiles."""
        return self._store.list_profiles()

    # ------------------------------------------------------------------
    # Interaction recording
    # ------------------------------------------------------------------

    async def record_interaction(
        self,
        user_id: str,
        interaction_type: InteractionType,
        domain: str | None = None,
        depth: float = 0.5,
        approved: bool | None = None,
        metadata: dict[str, object] | None = None,
    ) -> IntelligenceProfile:
        """Record a user interaction and update the profile.

        This is the primary method for building the profile incrementally.
        Each interaction updates domain expertise, interaction summaries,
        and inferred preferences.
        """
        profile = await self.get_or_create_profile(user_id)

        # Take a snapshot before major changes
        snapshot = await self._create_snapshot(
            profile, reason=f"Before interaction: {interaction_type.value}"
        )
        profile = profile.model_copy(update={"snapshot_id": snapshot.id})

        # Update interaction summary
        summary = profile.interaction_summary
        new_total = summary.total_interactions + 1
        new_by_type = dict(summary.interactions_by_type)
        type_key = interaction_type.value
        new_by_type[type_key] = new_by_type.get(type_key, 0) + 1

        new_by_domain = dict(summary.interactions_by_domain)
        if domain is not None:
            new_by_domain[domain] = new_by_domain.get(domain, 0) + 1

        # Update depth statistics
        all_depths_total = summary.avg_depth * summary.total_interactions + depth
        new_avg_depth = all_depths_total / new_total
        new_peak_depth = max(summary.peak_depth, depth)

        # Update approval rate
        new_approval_rate = summary.approval_rate
        if approved is not None:
            approval_count = int(
                summary.approval_rate * summary.total_interactions
            )
            if approved:
                approval_count += 1
            # Only update rate if we have enough data
            if summary.total_interactions > 0:
                new_approval_rate = approval_count / new_total

        now = datetime.now(UTC)
        updated_summary = summary.model_copy(
            update={
                "total_interactions": new_total,
                "interactions_by_type": new_by_type,
                "interactions_by_domain": new_by_domain,
                "avg_depth": round(new_avg_depth, 3),
                "peak_depth": new_peak_depth,
                "last_interaction": now,
                "approval_rate": round(new_approval_rate, 3),
            }
        )

        # Update domain expertise
        new_expertise = dict(profile.domain_expertise)
        if domain is not None:
            existing_exp = new_expertise.get(
                domain,
                DomainExpertise(domain_id=domain),
            )
            new_expertise[domain] = self._assessor.update_expertise(
                existing_exp, depth
            )

        # Infer preferences
        updated_prefs = self._inferrer.infer_from_interactions(
            dict(profile.preferences), updated_summary
        )

        profile = profile.model_copy(
            update={
                "interaction_summary": updated_summary,
                "domain_expertise": new_expertise,
                "preferences": updated_prefs,
                "updated_at": now,
                "adaptation_count": profile.adaptation_count + 1,
            }
        )
        self._store.update_profile(profile)

        await self._tape.log_event(
            event_type="profile.interaction_recorded",
            payload={
                "user_id": user_id,
                "interaction_type": interaction_type.value,
                "domain": domain,
                "depth": depth,
                "approved": approved,
                "total_interactions": new_total,
            },
            agent_id="intelligence-profile-engine",
            metadata=metadata or {},
        )

        return profile

    # ------------------------------------------------------------------
    # Preference management
    # ------------------------------------------------------------------

    async def set_preference(
        self,
        user_id: str,
        category: PreferenceCategory,
        value: float,
    ) -> IntelligenceProfile:
        """Set an explicit user preference.

        Explicit preferences override inferred values and have
        full confidence.
        """
        profile = await self.get_or_create_profile(user_id)

        updated_prefs = dict(profile.preferences)
        pref = updated_prefs.get(
            category.value,
            UserPreference(category=category),
        )
        pref = pref.model_copy(
            update={
                "explicit_value": value,
                "value": value,
                "confidence": 1.0,  # explicit = full confidence
                "last_updated": datetime.now(UTC),
            }
        )
        updated_prefs[category.value] = pref

        profile = profile.model_copy(
            update={
                "preferences": updated_prefs,
                "updated_at": datetime.now(UTC),
            }
        )
        self._store.update_profile(profile)

        await self._tape.log_event(
            event_type="profile.preference_set",
            payload={
                "user_id": user_id,
                "category": category.value,
                "value": value,
            },
            agent_id="intelligence-profile-engine",
        )

        return profile

    async def get_effective_preference(
        self,
        user_id: str,
        category: PreferenceCategory,
    ) -> float:
        """Get the effective preference value for a user.

        Returns the explicit value if set, otherwise the inferred value.
        If neither exists, returns the default (0.5).
        """
        profile = await self.get_or_create_profile(user_id)
        pref = profile.preferences.get(category.value)
        if pref is None:
            return 0.5

        if pref.explicit_value is not None:
            return pref.explicit_value
        return pref.inferred_value

    # ------------------------------------------------------------------
    # Snapshots and rollback
    # ------------------------------------------------------------------

    async def _create_snapshot(
        self,
        profile: IntelligenceProfile,
        reason: str = "",
    ) -> ProfileSnapshot:
        """Create a snapshot of the current profile state."""
        snapshot = ProfileSnapshot(
            profile_id=profile.id,
            profile_data=profile.model_dump(),
            reason=reason,
        )
        self._store.add_snapshot(snapshot)
        return snapshot

    async def create_snapshot(
        self,
        user_id: str,
        reason: str = "",
    ) -> ProfileSnapshot:
        """Create a named snapshot of a user's profile."""
        profile = await self.get_profile(user_id)
        snapshot = await self._create_snapshot(profile, reason)

        await self._tape.log_event(
            event_type="profile.snapshot_created",
            payload={
                "user_id": user_id,
                "snapshot_id": str(snapshot.id),
                "reason": reason,
            },
            agent_id="intelligence-profile-engine",
        )

        return snapshot

    async def rollback_to_snapshot(
        self,
        user_id: str,
        snapshot_id: UUID,
    ) -> IntelligenceProfile:
        """Rollback a profile to a specific snapshot."""
        snapshot = self._store.get_snapshot(snapshot_id)
        if snapshot is None:
            raise SnapshotNotFoundError(f"Snapshot {snapshot_id} not found")

        # Reconstruct profile from snapshot data
        profile = IntelligenceProfile.model_validate(snapshot.profile_data)

        # Verify it belongs to the right user
        if profile.user_id != user_id:
            raise ProfileError(
                f"Snapshot belongs to user '{profile.user_id}', not '{user_id}'"
            )

        self._store.update_profile(profile)

        await self._tape.log_event(
            event_type="profile.rolled_back",
            payload={
                "user_id": user_id,
                "snapshot_id": str(snapshot_id),
            },
            agent_id="intelligence-profile-engine",
        )

        return profile

    async def list_snapshots(
        self,
        user_id: str,
    ) -> list[ProfileSnapshot]:
        """List all snapshots for a user's profile."""
        profile = await self.get_profile(user_id)
        return self._store.list_snapshots(profile_id=profile.id)

    # ------------------------------------------------------------------
    # Profile analysis
    # ------------------------------------------------------------------

    async def get_domain_summary(
        self,
        user_id: str,
    ) -> dict[str, dict[str, object]]:
        """Get a summary of all domain expertise for a user."""
        profile = await self.get_profile(user_id)
        result: dict[str, dict[str, object]] = {}
        for domain_id, expertise in profile.domain_expertise.items():
            result[domain_id] = {
                "level": expertise.level.value,
                "score": expertise.score,
                "interaction_count": expertise.interaction_count,
                "avg_depth": round(
                    expertise.total_depth / max(1, expertise.interaction_count), 3
                ),
            }
        return result

    async def get_recommendation_context(
        self,
        user_id: str,
    ) -> dict[str, object]:
        """Get a context object for adapting Prime's behaviour.

        This returns the key profile signals that Prime should use
        to personalise its responses and suggestions.
        """
        profile = await self.get_or_create_profile(user_id)

        # Top domains by expertise
        top_domains = sorted(
            profile.domain_expertise.values(),
            key=lambda e: e.score,
            reverse=True,
        )[:5]

        # Effective preferences
        effective_prefs: dict[str, float] = {}
        for cat in PreferenceCategory:
            pref = profile.preferences.get(cat.value)
            if pref is not None:
                effective_prefs[cat.value] = (
                    pref.explicit_value
                    if pref.explicit_value is not None
                    else pref.inferred_value
                )

        return {
            "user_id": user_id,
            "expertise_level": (
                top_domains[0].level.value if top_domains else "novice"
            ),
            "top_domains": [
                {"domain_id": d.domain_id, "level": d.level.value, "score": d.score}
                for d in top_domains
            ],
            "preferences": effective_prefs,
            "interaction_count": profile.interaction_summary.total_interactions,
            "avg_depth": profile.interaction_summary.avg_depth,
            "approval_rate": profile.interaction_summary.approval_rate,
            "adaptation_count": profile.adaptation_count,
        }

    async def merge_profiles(
        self,
        source_user_id: str,
        target_user_id: str,
    ) -> IntelligenceProfile:
        """Merge source profile data into the target profile.

        Used when a user has multiple profiles or when migrating
        profile data between accounts.
        """
        source = await self.get_profile(source_user_id)
        target = await self.get_or_create_profile(target_user_id)

        # Merge domain expertise (take max score per domain)
        merged_expertise = dict(target.domain_expertise)
        for domain_id, src_exp in source.domain_expertise.items():
            tgt_exp = merged_expertise.get(domain_id)
            if tgt_exp is None or src_exp.score > tgt_exp.score:
                merged_expertise[domain_id] = src_exp

        # Merge interaction summary (additive)
        merged_summary = target.interaction_summary.model_copy(
            update={
                "total_interactions": (
                    target.interaction_summary.total_interactions
                    + source.interaction_summary.total_interactions
                ),
                "avg_depth": (
                    (
                        target.interaction_summary.avg_depth
                        * target.interaction_summary.total_interactions
                        + source.interaction_summary.avg_depth
                        * source.interaction_summary.total_interactions
                    )
                    / max(
                        1,
                        target.interaction_summary.total_interactions
                        + source.interaction_summary.total_interactions,
                    )
                ),
                "peak_depth": max(
                    target.interaction_summary.peak_depth,
                    source.interaction_summary.peak_depth,
                ),
            }
        )

        # Merge preferences (prefer explicit, then higher confidence)
        merged_prefs = dict(target.preferences)
        for cat_key, src_pref in source.preferences.items():
            tgt_pref = merged_prefs.get(cat_key)
            if tgt_pref is None or (src_pref.explicit_value is not None and tgt_pref.explicit_value is None) or (
                src_pref.explicit_value is None
                and tgt_pref.explicit_value is None
                and src_pref.confidence > tgt_pref.confidence
            ):
                merged_prefs[cat_key] = src_pref

        merged = target.model_copy(
            update={
                "domain_expertise": merged_expertise,
                "interaction_summary": merged_summary,
                "preferences": merged_prefs,
                "updated_at": datetime.now(UTC),
                "adaptation_count": target.adaptation_count + 1,
            }
        )
        self._store.update_profile(merged)

        await self._tape.log_event(
            event_type="profile.merged",
            payload={
                "source_user_id": source_user_id,
                "target_user_id": target_user_id,
                "domains_merged": len(merged_expertise),
            },
            agent_id="intelligence-profile-engine",
        )

        return merged

    # ------------------------------------------------------------------
    # Profile status management
    # ------------------------------------------------------------------

    async def archive_profile(self, user_id: str) -> IntelligenceProfile:
        """Archive a user profile."""
        profile = await self.get_profile(user_id)
        profile = profile.model_copy(
            update={
                "status": ProfileStatus.ARCHIVED,
                "updated_at": datetime.now(UTC),
            }
        )
        self._store.update_profile(profile)

        await self._tape.log_event(
            event_type="profile.archived",
            payload={"user_id": user_id},
            agent_id="intelligence-profile-engine",
        )

        return profile

    async def suspend_profile(self, user_id: str) -> IntelligenceProfile:
        """Suspend a user profile."""
        profile = await self.get_profile(user_id)
        profile = profile.model_copy(
            update={
                "status": ProfileStatus.SUSPENDED,
                "updated_at": datetime.now(UTC),
            }
        )
        self._store.update_profile(profile)

        await self._tape.log_event(
            event_type="profile.suspended",
            payload={"user_id": user_id},
            agent_id="intelligence-profile-engine",
        )

        return profile

    async def reactivate_profile(self, user_id: str) -> IntelligenceProfile:
        """Reactivate a suspended or archived profile."""
        profile = await self.get_profile(user_id)
        profile = profile.model_copy(
            update={
                "status": ProfileStatus.ACTIVE,
                "updated_at": datetime.now(UTC),
            }
        )
        self._store.update_profile(profile)

        await self._tape.log_event(
            event_type="profile.reactivated",
            payload={"user_id": user_id},
            agent_id="intelligence-profile-engine",
        )

        return profile
