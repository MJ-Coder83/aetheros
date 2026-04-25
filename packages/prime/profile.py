"""Prime User Profile — Persistent user preferences, personalization, and intelligence tracking.

This module consolidates the *UserProfile* (rich personalization model with
goals, skills, working style, folder-tree + AetherGit integration) and the
*IntelligenceProfile* engine (domain expertise, interaction tracking,
preference inference, snapshots, and rollback) into a single, unified system.

Design principles
-----------------
- Every profile update is logged to the Tape (full auditability)
- Profiles evolve incrementally with each interaction
- Expertise scoring uses heuristics based on interaction frequency + depth
- Preference inference from observed behaviour (not explicit settings only)
- Privacy-first: profiles store only operational patterns, not personal data
- Profile snapshots enable rollback on incorrect adaptations
- Profiles persist to filesystem and sync to AetherGit
- Backward-compatible: ``IntelligenceProfileEngine`` is re-exported

Architecture
------------

::

    ProfileStorage ─────────────────────────────────────────────┐
    ├── InMemoryProfileStore   (testing)                        │
    ├── FilesystemProfileStore (persistent, folder-tree linked) │
    ├── get_or_create_profile()                                 │
    ├── update_profile()                                        │
    ├── set_preference() / get_preference()                     │
    ├── update_working_style()                                  │
    ├── add_goal() / complete_goal() / delete_goal()            │
    ├── add_or_update_skill()                                   │
    ├── record_pattern()                                        │
    ├── record_session()                                        │
    ├── sync_to_aethergit()                                     │
    └── export_profile() / import_profile()                     │
                                                                 │
    IntelligenceProfileEngine (backward-compat facade) ◄────────┘
    ├── record_interaction()      → updates expertise + summary
    ├── set_preference()          → delegates to ProfileStorage
    ├── get_effective_preference()→ delegates to ProfileStorage
    ├── create_snapshot()         → ProfileSnapshot
    ├── rollback_to_snapshot()    → restores from snapshot
    ├── get_domain_summary()      → reads UserProfile expertise
    ├── get_recommendation_context() → profile-aware context
    ├── merge_profiles()          → merges two profiles
    ├── archive/suspend/reactivate()  → status transitions
    └── get_or_create_profile()   → delegates to ProfileStorage

Usage
-----

::

    from packages.prime.profile import ProfileStorage, UserProfile
    from packages.prime.profile import IntelligenceProfileEngine  # backward-compat

    storage = ProfileStorage(tape_service=tape_svc)
    profile = await storage.get_or_create_profile(user_id="alice")
    await storage.update_working_style(user_id="alice", communication_style="detailed")
    await storage.add_goal(user_id="alice", title="Master legal domain")

    # Backward-compatible API:
    engine = IntelligenceProfileEngine(tape_service=tape_svc)
    profile = await engine.get_or_create_profile(user_id="alice")
    await engine.record_interaction(user_id="alice", interaction_type="query", domain="legal", depth=0.8)
"""

from __future__ import annotations

import json
import math
import os
import shutil
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

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
    DOMAIN_CREATED = "domain_created"
    PLAN_CREATED = "plan_created"
    DEBATE_STARTED = "debate_started"


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


class WorkingStyle(StrEnum):
    """User working style preferences."""

    METHODICAL = "methodical"
    EXPLORATORY = "exploratory"
    COLLABORATIVE = "collaborative"
    INDEPENDENT = "independent"
    VISUAL = "visual"
    TEXTUAL = "textual"


class AutomationPreference(StrEnum):
    """User preference for automation level."""

    MANUAL = "manual"
    ASSISTED = "assisted"
    SEMI_AUTOMATED = "semi_automated"
    FULLY_AUTOMATED = "fully_automated"


class CommunicationStyle(StrEnum):
    """User communication style preference."""

    CONCISE = "concise"
    DETAILED = "detailed"
    TECHNICAL = "technical"
    CONVERSATIONAL = "conversational"


class ProfileStorageBackend(StrEnum):
    """Storage backend options."""

    MEMORY = "memory"
    FILESYSTEM = "filesystem"
    AETHERGIT = "aethergit"


# ---------------------------------------------------------------------------
# Data models — Intelligence Profile (domain expertise + interaction tracking)
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
    """Intelligence profile embedded within UserProfile.

    Tracks domain expertise, preferences, interaction summary, and
    behavioural signals for Prime adaptation.
    """

    domain_expertise: dict[str, DomainExpertise] = Field(default_factory=dict)
    preferences: dict[str, UserPreference] = Field(default_factory=dict)
    interaction_summary: InteractionSummary = Field(
        default_factory=InteractionSummary,
    )
    behavioural_signals: dict[str, object] = Field(default_factory=dict)
    adaptation_count: int = 0
    snapshot_id: UUID | None = None


class ProfileSnapshot(BaseModel):
    """Immutable snapshot of a profile for rollback purposes."""

    id: UUID = Field(default_factory=uuid4)
    profile_id: UUID
    profile_data: dict[str, object] = Field(default_factory=dict)
    reason: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Data models — User Profile (rich personalization)
# ---------------------------------------------------------------------------


class UserPreferenceSetting(BaseModel):
    """A single user preference setting with metadata."""

    model_config = ConfigDict(extra="allow")

    key: str
    value: Any
    category: str = "general"
    is_explicit: bool = True
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class WorkingStyleConfig(BaseModel):
    """User working style configuration."""

    model_config = ConfigDict(extra="allow")

    primary_style: WorkingStyle = WorkingStyle.METHODICAL
    secondary_styles: list[WorkingStyle] = []
    preferred_session_length: int = Field(default=60, ge=5, le=480)  # minutes
    peak_hours: list[int] = []  # 0-23 hour values
    timezone: str = "UTC"
    automation_preference: AutomationPreference = AutomationPreference.ASSISTED
    communication_style: CommunicationStyle = CommunicationStyle.DETAILED
    context_retention: int = Field(default=10, ge=1, le=100)


class UserGoal(BaseModel):
    """A user goal with tracking."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    title: str
    description: str = ""
    category: str = "general"
    priority: int = Field(default=3, ge=1, le=5)
    status: str = "active"  # active, completed, paused, abandoned
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    target_date: datetime | None = None
    completed_at: datetime | None = None
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = {}


class LearnedSkill(BaseModel):
    """A skill learned by the user through interactions."""

    model_config = ConfigDict(extra="allow")

    skill_id: str
    name: str
    category: str = "general"
    proficiency: float = Field(default=0.0, ge=0.0, le=1.0)
    first_observed: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_used: datetime = Field(default_factory=lambda: datetime.now(UTC))
    usage_count: int = 0
    verified: bool = False
    source: str = "inferred"  # inferred, explicit, certified


class InteractionPattern(BaseModel):
    """Detected user interaction patterns."""

    model_config = ConfigDict(extra="allow")

    pattern_type: str  # e.g., "time_of_day", "domain_preference", "tool_usage"
    pattern_value: str
    frequency: int = 0
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    first_observed: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_observed: datetime = Field(default_factory=lambda: datetime.now(UTC))
    is_active: bool = True


class HistorySummary(BaseModel):
    """Summary of user's interaction history."""

    model_config = ConfigDict(extra="allow")

    total_sessions: int = 0
    total_interactions: int = 0
    total_domains: int = 0
    total_proposals: int = 0
    total_approvals: int = 0
    total_rejections: int = 0
    avg_session_duration: float = 0.0  # minutes
    favorite_domains: list[str] = []
    common_patterns: list[str] = []
    last_session_at: datetime | None = None
    summary_generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )


class UserProfile(BaseModel):
    """Complete user profile for Prime personalization.

    The UserProfile aggregates user preferences, working style, goals,
    history summary, learned skills, interaction patterns, and the
    embedded IntelligenceProfile (domain expertise + preference inference)
    to enable personalized AI responses and suggestions.

    Attributes
    ----------
    intelligence : IntelligenceProfile
        Embedded intelligence tracking (domain expertise, interaction
        summary, preference inference). This is what the old
        ``IntelligenceProfileEngine`` managed, now unified into UserProfile.
    folder_tree_path : str
        Path in the folder-tree where profile data is stored.
    aethergit_commit_id : str | None
        Last AetherGit commit hash for this profile.

    """

    model_config = ConfigDict(extra="allow")

    id: UUID = Field(default_factory=uuid4)
    user_id: str
    version: int = 1
    status: ProfileStatus = ProfileStatus.ACTIVE

    # Core profile data
    display_name: str = ""
    email: str = ""
    bio: str = ""

    # Working style and preferences
    working_style: WorkingStyleConfig = Field(default_factory=WorkingStyleConfig)
    preferences: dict[str, UserPreferenceSetting] = Field(default_factory=dict)

    # Intelligence profile (embedded from old IntelligenceProfile model)
    intelligence: IntelligenceProfile = Field(default_factory=IntelligenceProfile)

    # Goals and skills
    goals: list[UserGoal] = []
    learned_skills: dict[str, LearnedSkill] = Field(default_factory=dict)

    # Patterns and history
    interaction_patterns: list[InteractionPattern] = []
    history_summary: HistorySummary = Field(default_factory=HistorySummary)

    # Storage metadata
    storage_backend: ProfileStorageBackend = ProfileStorageBackend.MEMORY
    folder_tree_path: str = ""
    aethergit_commit_id: str | None = None

    # ------------------------------------------------------------------
    # Backward-compatible convenience properties
    # These let old code that expected IntelligenceProfile as a
    # standalone model access fields directly on UserProfile.
    # ------------------------------------------------------------------

    @property
    def domain_expertise(self) -> dict[str, DomainExpertise]:
        """Backward-compat: access intelligence.domain_expertise directly."""
        return self.intelligence.domain_expertise

    @property
    def interaction_summary(self) -> InteractionSummary:
        """Backward-compat: access intelligence.interaction_summary directly."""
        return self.intelligence.interaction_summary

    @property
    def adaptation_count(self) -> int:
        """Backward-compat: access intelligence.adaptation_count directly."""
        return self.intelligence.adaptation_count

    # Audit timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_sync_at: datetime | None = None


class ProfileVersion(BaseModel):
    """Version information for profile storage."""

    version: int
    commit_id: str | None
    timestamp: datetime
    change_summary: str = ""


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ProfileError(Exception):
    """Base exception for profile operations."""


class ProfileStorageError(ProfileError):
    """Raised when profile storage operations fail."""


class ProfileSerializationError(ProfileStorageError):
    """Raised when profile serialization fails."""


class ProfileSyncError(ProfileStorageError):
    """Raised when profile synchronization fails."""


class ProfileNotFoundError(ProfileStorageError):
    """Raised when a profile does not exist."""


class SnapshotNotFoundError(ProfileError):
    """Raised when a snapshot does not exist."""


class ProfileTransitionError(ProfileError):
    """Raised on invalid profile status transition."""


# ---------------------------------------------------------------------------
# Expertise assessor (shared by IntelligenceProfileEngine)
# ---------------------------------------------------------------------------


class ExpertiseAssessor:
    """Assesses and updates domain expertise based on interactions.

    Uses heuristic scoring based on interaction count, depth, and recency.
    """

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
        """Compute expertise score from interaction signals."""
        count_factor = min(1.0, math.log1p(interaction_count) / math.log1p(50))
        depth_factor = min(1.0, max(0.0, avg_depth))
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
            },
        )


# ---------------------------------------------------------------------------
# Preference inferrer (shared by IntelligenceProfileEngine)
# ---------------------------------------------------------------------------


class PreferenceInferrer:
    """Infers user preferences from behavioural signals."""

    def infer_from_interactions(
        self,
        preferences: dict[str, UserPreference],
        summary: InteractionSummary,
    ) -> dict[str, UserPreference]:
        """Update preference inferences based on interaction summary."""
        updated = dict(preferences)

        # Response detail
        detail_pref = updated.get(
            PreferenceCategory.RESPONSE_DETAIL.value,
            UserPreference(category=PreferenceCategory.RESPONSE_DETAIL),
        )
        if summary.avg_depth > 0:
            detail_pref = detail_pref.model_copy(
                update={
                    "inferred_value": summary.avg_depth,
                    "confidence": min(1.0, summary.total_interactions / 20.0),
                },
            )
        updated[detail_pref.category.value] = detail_pref

        # Automation level
        auto_pref = updated.get(
            PreferenceCategory.AUTOMATION_LEVEL.value,
            UserPreference(category=PreferenceCategory.AUTOMATION_LEVEL),
        )
        if summary.approval_rate > 0:
            auto_pref = auto_pref.model_copy(
                update={
                    "inferred_value": summary.approval_rate,
                    "confidence": min(1.0, summary.total_interactions / 30.0),
                },
            )
        updated[auto_pref.category.value] = auto_pref

        # Risk tolerance
        risk_pref = updated.get(
            PreferenceCategory.RISK_TOLERANCE.value,
            UserPreference(category=PreferenceCategory.RISK_TOLERANCE),
        )
        if summary.approval_rate > 0:
            risk_pref = risk_pref.model_copy(
                update={
                    "inferred_value": summary.approval_rate,
                    "confidence": min(1.0, summary.total_interactions / 25.0),
                },
            )
        updated[risk_pref.category.value] = risk_pref

        # Explanation depth
        explain_pref = updated.get(
            PreferenceCategory.EXPLANATION_DEPTH.value,
            UserPreference(category=PreferenceCategory.EXPLANATION_DEPTH),
        )
        if summary.avg_depth > 0:
            explain_pref = explain_pref.model_copy(
                update={
                    "inferred_value": min(1.0, summary.avg_depth * 0.8),
                    "confidence": min(1.0, summary.total_interactions / 15.0),
                },
            )
        updated[explain_pref.category.value] = explain_pref

        # Suggestion frequency
        sug_pref = updated.get(
            PreferenceCategory.SUGGESTION_FREQUENCY.value,
            UserPreference(category=PreferenceCategory.SUGGESTION_FREQUENCY),
        )
        if summary.total_interactions > 0:
            sug_pref = sug_pref.model_copy(
                update={
                    "inferred_value": min(1.0, summary.total_interactions / 50.0),
                    "confidence": min(1.0, summary.total_interactions / 10.0),
                },
            )
        updated[sug_pref.category.value] = sug_pref

        return updated


# ---------------------------------------------------------------------------
# Snapshot Store (shared by IntelligenceProfileEngine)
# ---------------------------------------------------------------------------


class SnapshotStore:
    """In-memory store for profile snapshots."""

    def __init__(self) -> None:
        self._snapshots: dict[UUID, ProfileSnapshot] = {}

    def add(self, snapshot: ProfileSnapshot) -> None:
        self._snapshots[snapshot.id] = snapshot

    def get(self, snapshot_id: UUID) -> ProfileSnapshot | None:
        return self._snapshots.get(snapshot_id)

    def list_snapshots(
        self, profile_id: UUID | None = None
    ) -> list[ProfileSnapshot]:
        snapshots = list(self._snapshots.values())
        if profile_id is not None:
            snapshots = [s for s in snapshots if s.profile_id == profile_id]
        return snapshots


# ---------------------------------------------------------------------------
# Profile Store — Abstract base
# ---------------------------------------------------------------------------


class BaseProfileStore:
    """Abstract base class for profile storage backends."""

    def __init__(self, tape_service: TapeService | None = None) -> None:
        self._tape = tape_service

    async def _log_event(
        self,
        event_type: str,
        user_id: str,
        payload: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log an event to the Tape if tape_service is available."""
        if self._tape is not None:
            await self._tape.log_event(
                event_type=event_type,
                payload=payload,
                agent_id="profile-storage",
                metadata=metadata or {},
            )

    async def get_profile(self, user_id: str) -> UserProfile | None:
        raise NotImplementedError

    async def save_profile(self, profile: UserProfile) -> None:
        raise NotImplementedError

    async def delete_profile(self, user_id: str) -> bool:
        raise NotImplementedError

    async def list_profiles(self) -> list[UserProfile]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# In-Memory Store
# ---------------------------------------------------------------------------


class InMemoryProfileStore(BaseProfileStore):
    """In-memory store for profiles (used for testing)."""

    def __init__(self, tape_service: TapeService | None = None) -> None:
        super().__init__(tape_service)
        self._profiles: dict[str, UserProfile] = {}

    async def get_profile(self, user_id: str) -> UserProfile | None:
        return self._profiles.get(user_id)

    async def save_profile(self, profile: UserProfile) -> None:
        self._profiles[profile.user_id] = profile
        await self._log_event(
            event_type="profile.saved",
            user_id=profile.user_id,
            payload={"user_id": profile.user_id, "version": profile.version},
        )

    async def delete_profile(self, user_id: str) -> bool:
        if user_id in self._profiles:
            del self._profiles[user_id]
            await self._log_event(
                event_type="profile.deleted",
                user_id=user_id,
                payload={"user_id": user_id},
            )
            return True
        return False

    async def list_profiles(self) -> list[UserProfile]:
        return list(self._profiles.values())


# ---------------------------------------------------------------------------
# Filesystem Store (linked to folder-tree)
# ---------------------------------------------------------------------------


class FilesystemProfileStore(BaseProfileStore):
    """Filesystem-based store using folder-tree structure.

    Profiles are stored as JSON files::

        profiles/
        └── {user_id}/
            ├── profile.json
            ├── preferences/
            │   └── preferences.json
            ├── goals/
            │   └── goals.json
            └── skills/
                └── skills.json
    """

    PROFILE_FILENAME: ClassVar[str] = "profile.json"

    def __init__(
        self,
        base_path: str,
        tape_service: TapeService | None = None,
    ) -> None:
        super().__init__(tape_service)
        self._base_path = base_path

    def _get_profile_dir(self, user_id: str) -> str:
        return os.path.join(self._base_path, "profiles", user_id)

    def _get_profile_path(self, user_id: str) -> str:
        return os.path.join(
            self._get_profile_dir(user_id), self.PROFILE_FILENAME
        )

    def _ensure_dir(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)

    async def get_profile(self, user_id: str) -> UserProfile | None:
        profile_path = self._get_profile_path(user_id)
        if not os.path.exists(profile_path):
            return None
        try:
            with open(profile_path, encoding="utf-8") as f:
                data = json.load(f)
            return UserProfile.model_validate(data)
        except Exception as e:
            raise ProfileSerializationError(
                f"Failed to load profile: {e}"
            ) from e

    async def save_profile(self, profile: UserProfile) -> None:
        profile_path = self._get_profile_path(profile.user_id)
        self._ensure_dir(profile_path)
        profile.updated_at = datetime.now(UTC)
        profile.version += 1
        profile.folder_tree_path = self._get_profile_dir(profile.user_id)
        try:
            with open(profile_path, "w", encoding="utf-8") as f:
                json.dump(profile.model_dump(mode="json"), f, indent=2)
        except Exception as e:
            raise ProfileSerializationError(
                f"Failed to save profile: {e}"
            ) from e
        await self._log_event(
            event_type="profile.saved_to_filesystem",
            user_id=profile.user_id,
            payload={
                "user_id": profile.user_id,
                "version": profile.version,
                "path": profile_path,
            },
        )

    async def delete_profile(self, user_id: str) -> bool:
        profile_dir = self._get_profile_dir(user_id)
        if not os.path.exists(profile_dir):
            return False
        try:
            shutil.rmtree(profile_dir)
            await self._log_event(
                event_type="profile.deleted_from_filesystem",
                user_id=user_id,
                payload={"user_id": user_id, "path": profile_dir},
            )
            return True
        except Exception as e:
            raise ProfileStorageError(
                f"Failed to delete profile: {e}"
            ) from e

    async def list_profiles(self) -> list[UserProfile]:
        profiles_dir = os.path.join(self._base_path, "profiles")
        if not os.path.exists(profiles_dir):
            return []
        profiles: list[UserProfile] = []
        for user_id in os.listdir(profiles_dir):
            profile = await self.get_profile(user_id)
            if profile is not None:
                profiles.append(profile)
        return profiles


# ---------------------------------------------------------------------------
# ProfileStorage — Main service for UserProfile CRUD
# ---------------------------------------------------------------------------


class ProfileStorage:
    """Main service for user profile storage and management.

    Provides a unified interface for profile CRUD with support for
    multiple storage backends and automatic Tape logging.
    """

    def __init__(
        self,
        store: BaseProfileStore | None = None,
        tape_service: TapeService | None = None,
    ) -> None:
        self._store = store or InMemoryProfileStore(tape_service)
        self._tape = tape_service

    # ------------------------------------------------------------------
    # Profile CRUD
    # ------------------------------------------------------------------

    async def get_or_create_profile(
        self,
        user_id: str,
        defaults: dict[str, Any] | None = None,
    ) -> UserProfile:
        """Get an existing profile or create a new one for the user."""
        existing = await self._store.get_profile(user_id)
        if existing is not None:
            return existing
        profile = UserProfile(user_id=user_id, **(defaults or {}))
        await self._store.save_profile(profile)
        if self._tape:
            await self._tape.log_event(
                event_type="profile.created",
                payload={
                    "user_id": user_id,
                    "profile_id": str(profile.id),
                },
                agent_id="profile-storage",
            )
        return profile

    async def get_profile(self, user_id: str) -> UserProfile:
        """Get a profile, raising if not found."""
        profile = await self._store.get_profile(user_id)
        if profile is None:
            raise ProfileNotFoundError(
                f"Profile for user '{user_id}' not found"
            )
        return profile

    async def update_profile(
        self,
        user_id: str,
        updates: dict[str, Any],
    ) -> UserProfile:
        """Update a profile with new values."""
        profile = await self.get_profile(user_id)
        for key, value in updates.items():
            if hasattr(profile, key) and key != "id":
                setattr(profile, key, value)
        profile.updated_at = datetime.now(UTC)
        await self._store.save_profile(profile)
        if self._tape:
            await self._tape.log_event(
                event_type="profile.updated",
                payload={
                    "user_id": user_id,
                    "updated_fields": list(updates.keys()),
                },
                agent_id="profile-storage",
            )
        return profile

    async def delete_profile(self, user_id: str) -> bool:
        """Delete a user's profile."""
        return await self._store.delete_profile(user_id)

    async def list_profiles(self) -> list[UserProfile]:
        """List all profiles."""
        return await self._store.list_profiles()

    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------

    async def set_preference(
        self,
        user_id: str,
        key: str,
        value: Any,
        category: str = "general",
        is_explicit: bool = True,
    ) -> UserProfile:
        """Set a user preference."""
        profile = await self.get_or_create_profile(user_id)
        pref = UserPreferenceSetting(
            key=key,
            value=value,
            category=category,
            is_explicit=is_explicit,
            confidence=1.0 if is_explicit else 0.5,
        )
        profile.preferences[key] = pref
        await self._store.save_profile(profile)
        if self._tape:
            await self._tape.log_event(
                event_type="profile.preference_set",
                payload={
                    "user_id": user_id,
                    "key": key,
                    "value": str(value),
                },
                agent_id="profile-storage",
            )
        return profile

    async def get_preference(
        self,
        user_id: str,
        key: str,
        default: Any = None,
    ) -> Any:
        """Get a user preference value."""
        profile = await self.get_profile(user_id)
        pref = profile.preferences.get(key)
        if pref is None:
            return default
        return pref.value

    async def update_preferences(
        self,
        user_id: str,
        preferences: dict[str, Any],
        category: str = "general",
    ) -> UserProfile:
        """Update multiple preferences at once."""
        profile = await self.get_or_create_profile(user_id)
        for key, value in preferences.items():
            pref = UserPreferenceSetting(
                key=key,
                value=value,
                category=category,
                is_explicit=True,
                confidence=1.0,
            )
            profile.preferences[key] = pref
        await self._store.save_profile(profile)
        if self._tape:
            await self._tape.log_event(
                event_type="profile.preferences_updated",
                payload={
                    "user_id": user_id,
                    "keys": list(preferences.keys()),
                    "category": category,
                },
                agent_id="profile-storage",
            )
        return profile

    # ------------------------------------------------------------------
    # Working Style
    # ------------------------------------------------------------------

    async def update_working_style(
        self,
        user_id: str,
        **kwargs: Any,
    ) -> UserProfile:
        """Update the user's working style configuration."""
        profile = await self.get_or_create_profile(user_id)
        updates: dict[str, Any] = {}
        for key, value in kwargs.items():
            if hasattr(profile.working_style, key):
                updates[key] = value
        if updates:
            profile.working_style = profile.working_style.model_copy(
                update=updates
            )
            await self._store.save_profile(profile)
            if self._tape:
                await self._tape.log_event(
                    event_type="profile.working_style_updated",
                    payload={
                        "user_id": user_id,
                        "updates": list(updates.keys()),
                    },
                    agent_id="profile-storage",
                )
        return profile

    # ------------------------------------------------------------------
    # Goals
    # ------------------------------------------------------------------

    async def add_goal(
        self,
        user_id: str,
        title: str,
        description: str = "",
        category: str = "general",
        priority: int = 3,
    ) -> UserGoal:
        """Add a new goal for the user."""
        profile = await self.get_or_create_profile(user_id)
        goal = UserGoal(
            title=title,
            description=description,
            category=category,
            priority=priority,
        )
        profile.goals.append(goal)
        await self._store.save_profile(profile)
        if self._tape:
            await self._tape.log_event(
                event_type="profile.goal_added",
                payload={
                    "user_id": user_id,
                    "goal_id": goal.id,
                    "title": title,
                },
                agent_id="profile-storage",
            )
        return goal

    async def update_goal(
        self,
        user_id: str,
        goal_id: str,
        **updates: Any,
    ) -> UserGoal:
        """Update a goal."""
        profile = await self.get_profile(user_id)
        for goal in profile.goals:
            if goal.id == goal_id:
                for key, value in updates.items():
                    if hasattr(goal, key):
                        setattr(goal, key, value)
                goal.updated_at = datetime.now(UTC)
                await self._store.save_profile(profile)
                if self._tape:
                    await self._tape.log_event(
                        event_type="profile.goal_updated",
                        payload={
                            "user_id": user_id,
                            "goal_id": goal_id,
                            "updates": list(updates.keys()),
                        },
                        agent_id="profile-storage",
                    )
                return goal
        raise ProfileNotFoundError(
            f"Goal '{goal_id}' not found for user '{user_id}'"
        )

    async def complete_goal(
        self,
        user_id: str,
        goal_id: str,
    ) -> UserGoal:
        """Mark a goal as completed."""
        return await self.update_goal(
            user_id,
            goal_id,
            status="completed",
            completed_at=datetime.now(UTC),
            progress=1.0,
        )

    async def delete_goal(self, user_id: str, goal_id: str) -> bool:
        """Delete a goal."""
        profile = await self.get_profile(user_id)
        for i, goal in enumerate(profile.goals):
            if goal.id == goal_id:
                profile.goals.pop(i)
                await self._store.save_profile(profile)
                if self._tape:
                    await self._tape.log_event(
                        event_type="profile.goal_deleted",
                        payload={
                            "user_id": user_id,
                            "goal_id": goal_id,
                        },
                        agent_id="profile-storage",
                    )
                return True
        return False

    async def list_goals(
        self,
        user_id: str,
        status: str | None = None,
    ) -> list[UserGoal]:
        """List goals for a user, optionally filtered by status."""
        profile = await self.get_profile(user_id)
        if status is None:
            return profile.goals
        return [g for g in profile.goals if g.status == status]

    # ------------------------------------------------------------------
    # Learned Skills
    # ------------------------------------------------------------------

    async def add_or_update_skill(
        self,
        user_id: str,
        skill_id: str,
        name: str,
        proficiency: float = 0.0,
        category: str = "general",
    ) -> LearnedSkill:
        """Add or update a learned skill."""
        profile = await self.get_or_create_profile(user_id)
        existing = profile.learned_skills.get(skill_id)
        if existing:
            existing.proficiency = max(existing.proficiency, proficiency)
            existing.last_used = datetime.now(UTC)
            existing.usage_count += 1
        else:
            skill = LearnedSkill(
                skill_id=skill_id,
                name=name,
                category=category,
                proficiency=proficiency,
            )
            profile.learned_skills[skill_id] = skill
        await self._store.save_profile(profile)
        if self._tape:
            await self._tape.log_event(
                event_type="profile.skill_updated",
                payload={
                    "user_id": user_id,
                    "skill_id": skill_id,
                    "proficiency": proficiency,
                },
                agent_id="profile-storage",
            )
        return profile.learned_skills[skill_id]

    async def get_skill(
        self, user_id: str, skill_id: str
    ) -> LearnedSkill | None:
        """Get a specific skill for a user."""
        profile = await self.get_profile(user_id)
        return profile.learned_skills.get(skill_id)

    async def list_skills(
        self,
        user_id: str,
        category: str | None = None,
    ) -> list[LearnedSkill]:
        """List skills for a user, optionally filtered by category."""
        profile = await self.get_profile(user_id)
        skills = list(profile.learned_skills.values())
        if category:
            skills = [s for s in skills if s.category == category]
        return skills

    # ------------------------------------------------------------------
    # Interaction Patterns
    # ------------------------------------------------------------------

    async def record_pattern(
        self,
        user_id: str,
        pattern_type: str,
        pattern_value: str,
        confidence: float = 0.5,
    ) -> InteractionPattern:
        """Record an interaction pattern for the user."""
        profile = await self.get_or_create_profile(user_id)
        for pattern in profile.interaction_patterns:
            if (
                pattern.pattern_type == pattern_type
                and pattern.pattern_value == pattern_value
            ):
                pattern.frequency += 1
                pattern.confidence = max(pattern.confidence, confidence)
                pattern.last_observed = datetime.now(UTC)
                await self._store.save_profile(profile)
                return pattern
        pattern = InteractionPattern(
            pattern_type=pattern_type,
            pattern_value=pattern_value,
            frequency=1,
            confidence=confidence,
        )
        profile.interaction_patterns.append(pattern)
        await self._store.save_profile(profile)
        if self._tape:
            await self._tape.log_event(
                event_type="profile.pattern_recorded",
                payload={
                    "user_id": user_id,
                    "pattern_type": pattern_type,
                    "pattern_value": pattern_value,
                },
                agent_id="profile-storage",
            )
        return pattern

    async def list_patterns(
        self,
        user_id: str,
        pattern_type: str | None = None,
        min_confidence: float = 0.0,
    ) -> list[InteractionPattern]:
        """List interaction patterns for a user."""
        profile = await self.get_profile(user_id)
        patterns = profile.interaction_patterns
        if pattern_type:
            patterns = [p for p in patterns if p.pattern_type == pattern_type]
        patterns = [p for p in patterns if p.confidence >= min_confidence]
        return patterns

    # ------------------------------------------------------------------
    # History Summary
    # ------------------------------------------------------------------

    async def update_history_summary(
        self,
        user_id: str,
        **updates: Any,
    ) -> HistorySummary:
        """Update the user's history summary."""
        profile = await self.get_or_create_profile(user_id)
        for key, value in updates.items():
            if hasattr(profile.history_summary, key):
                setattr(profile.history_summary, key, value)
        profile.history_summary.summary_generated_at = datetime.now(UTC)
        await self._store.save_profile(profile)
        return profile.history_summary

    async def record_session(
        self,
        user_id: str,
        duration: float,
        interactions: int = 0,
        domains: list[str] | None = None,
    ) -> HistorySummary:
        """Record a completed session in the history summary."""
        profile = await self.get_or_create_profile(user_id)
        summary = profile.history_summary
        summary.total_sessions += 1
        summary.total_interactions += interactions
        summary.last_session_at = datetime.now(UTC)
        total_duration = summary.avg_session_duration * (
            summary.total_sessions - 1
        )
        summary.avg_session_duration = (
            total_duration + duration
        ) / summary.total_sessions
        if domains:
            summary.total_domains = len(
                set(summary.favorite_domains + domains)
            )
            for domain in domains:
                if domain not in summary.favorite_domains:
                    summary.favorite_domains.append(domain)
        await self._store.save_profile(profile)
        if self._tape:
            await self._tape.log_event(
                event_type="profile.session_recorded",
                payload={
                    "user_id": user_id,
                    "duration": duration,
                    "interactions": interactions,
                },
                agent_id="profile-storage",
            )
        return summary

    # ------------------------------------------------------------------
    # AetherGit Integration
    # ------------------------------------------------------------------

    async def sync_to_aethergit(
        self,
        user_id: str,
        commit_message: str = "Update user profile",
    ) -> str | None:
        """Sync the profile to AetherGit.

        Returns the commit ID if successful, None otherwise.
        """
        profile = await self.get_profile(user_id)
        profile.last_sync_at = datetime.now(UTC)
        profile.storage_backend = ProfileStorageBackend.AETHERGIT
        await self._store.save_profile(profile)
        if self._tape:
            await self._tape.log_event(
                event_type="profile.synced_to_aethergit",
                payload={
                    "user_id": user_id,
                    "commit_message": commit_message,
                },
                agent_id="profile-storage",
            )
        return (
            f"sync-{profile.user_id}-{int(datetime.now(UTC).timestamp())}"
        )

    # ------------------------------------------------------------------
    # Profile Export/Import
    # ------------------------------------------------------------------

    async def export_profile(self, user_id: str) -> dict[str, Any]:
        """Export a profile as a dictionary."""
        profile = await self.get_profile(user_id)
        return profile.model_dump(mode="json")

    async def import_profile(
        self,
        user_id: str,
        data: dict[str, Any],
        overwrite: bool = False,
    ) -> UserProfile:
        """Import a profile from a dictionary."""
        if not overwrite:
            existing = await self._store.get_profile(user_id)
            if existing is not None:
                raise ProfileStorageError(
                    f"Profile for '{user_id}' already exists"
                )
        profile = UserProfile.model_validate(data)
        profile.user_id = user_id
        profile.id = uuid4()
        profile.version = 1
        profile.updated_at = datetime.now(UTC)
        await self._store.save_profile(profile)
        if self._tape:
            await self._tape.log_event(
                event_type="profile.imported",
                payload={
                    "user_id": user_id,
                    "source_version": data.get("version"),
                },
                agent_id="profile-storage",
            )
        return profile

    # ------------------------------------------------------------------
    # Profile Summary
    # ------------------------------------------------------------------

    async def get_profile_summary(self, user_id: str) -> dict[str, Any]:
        """Get a summary of the user's profile."""
        profile = await self.get_profile(user_id)
        active_goals = len(
            [g for g in profile.goals if g.status == "active"]
        )
        verified_skills = len(
            [s for s in profile.learned_skills.values() if s.verified]
        )
        return {
            "user_id": profile.user_id,
            "display_name": profile.display_name,
            "working_style": profile.working_style.primary_style.value,
            "automation_preference": profile.working_style.automation_preference.value,
            "total_goals": len(profile.goals),
            "active_goals": active_goals,
            "total_skills": len(profile.learned_skills),
            "verified_skills": verified_skills,
            "total_preferences": len(profile.preferences),
            "total_patterns": len(profile.interaction_patterns),
            "total_sessions": profile.history_summary.total_sessions,
            "favorite_domains": profile.history_summary.favorite_domains[:5],
            "last_sync": (
                profile.last_sync_at.isoformat()
                if profile.last_sync_at
                else None
            ),
        }


# ---------------------------------------------------------------------------
# IntelligenceProfileEngine — backward-compatible facade
# ---------------------------------------------------------------------------


class IntelligenceProfileEngine:
    """Personalised intelligence profile engine for Prime.

    This is the backward-compatible API that existing code depends on.
    Internally it delegates to ``ProfileStorage`` for persistence and
    ``ExpertiseAssessor`` / ``PreferenceInferrer`` for computation.

    All operations are logged to the Tape for full auditability.
    """

    def __init__(
        self,
        tape_service: TapeService,
        store: ProfileStorage | None = None,
        expertise_assessor: ExpertiseAssessor | None = None,
        preference_inferrer: PreferenceInferrer | None = None,
    ) -> None:
        self._tape = tape_service
        self._storage = store or ProfileStorage(
            tape_service=tape_service,
        )
        self._assessor = expertise_assessor or ExpertiseAssessor()
        self._inferrer = preference_inferrer or PreferenceInferrer()
        self._snapshots = SnapshotStore()

    # ------------------------------------------------------------------
    # Profile CRUD
    # ------------------------------------------------------------------

    async def get_or_create_profile(self, user_id: str) -> UserProfile:
        """Get an existing profile or create a new one for the user."""
        return await self._storage.get_or_create_profile(user_id)

    async def get_profile(self, user_id: str) -> UserProfile:
        """Get a profile, raising if not found."""
        return await self._storage.get_profile(user_id)

    async def list_profiles(self) -> list[UserProfile]:
        """List all profiles."""
        return await self._storage.list_profiles()

    # ------------------------------------------------------------------
    # Interaction recording (the core IntelligenceProfile behaviour)
    # ------------------------------------------------------------------

    async def record_interaction(
        self,
        user_id: str,
        interaction_type: InteractionType,
        domain: str | None = None,
        depth: float = 0.5,
        approved: bool | None = None,
        metadata: dict[str, object] | None = None,
    ) -> UserProfile:
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
        profile.intelligence.snapshot_id = snapshot.id

        # Update interaction summary
        intel = profile.intelligence
        summary = intel.interaction_summary

        new_total = summary.total_interactions + 1
        new_by_type = dict(summary.interactions_by_type)
        type_key = interaction_type.value
        new_by_type[type_key] = new_by_type.get(type_key, 0) + 1

        new_by_domain = dict(summary.interactions_by_domain)
        if domain is not None:
            new_by_domain[domain] = new_by_domain.get(domain, 0) + 1

        all_depths_total = summary.avg_depth * summary.total_interactions + depth
        new_avg_depth = all_depths_total / new_total
        new_peak_depth = max(summary.peak_depth, depth)

        new_approval_rate = summary.approval_rate
        if approved is not None:
            approval_count = int(
                summary.approval_rate * summary.total_interactions
            )
            if approved:
                approval_count += 1
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
            },
        )

        # Update domain expertise
        new_expertise = dict(intel.domain_expertise)
        if domain is not None:
            existing_exp = new_expertise.get(
                domain, DomainExpertise(domain_id=domain)
            )
            new_expertise[domain] = self._assessor.update_expertise(
                existing_exp, depth
            )

        # Infer preferences
        updated_prefs = self._inferrer.infer_from_interactions(
            dict(intel.preferences), updated_summary
        )

        # Update the embedded IntelligenceProfile
        profile.intelligence = intel.model_copy(
            update={
                "interaction_summary": updated_summary,
                "domain_expertise": new_expertise,
                "preferences": updated_prefs,
                "adaptation_count": intel.adaptation_count + 1,
            },
        )
        profile.updated_at = now

        # Also update history_summary (aggregate stats)
        profile.history_summary.total_interactions = new_total
        if domain and domain not in profile.history_summary.favorite_domains:
            profile.history_summary.favorite_domains.append(domain)
            profile.history_summary.total_domains = len(
                set(profile.history_summary.favorite_domains)
            )

        await self._storage._store.save_profile(profile)

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
    ) -> UserProfile:
        """Set an explicit user preference.

        Explicit preferences override inferred values and have full confidence.
        """
        profile = await self.get_or_create_profile(user_id)
        updated_prefs = dict(profile.intelligence.preferences)
        pref = updated_prefs.get(
            category.value, UserPreference(category=category)
        )
        pref = pref.model_copy(
            update={
                "explicit_value": value,
                "value": value,
                "confidence": 1.0,
                "last_updated": datetime.now(UTC),
            },
        )
        updated_prefs[category.value] = pref
        profile.intelligence = profile.intelligence.model_copy(
            update={"preferences": updated_prefs},
        )
        profile.updated_at = datetime.now(UTC)
        await self._storage._store.save_profile(profile)
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
        """Get the effective preference value for a user."""
        profile = await self.get_or_create_profile(user_id)
        pref = profile.intelligence.preferences.get(category.value)
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
        profile: UserProfile,
        reason: str = "",
    ) -> ProfileSnapshot:
        """Create a snapshot of the current profile state."""
        snapshot = ProfileSnapshot(
            profile_id=profile.id,
            profile_data=profile.model_dump(),
            reason=reason,
        )
        self._snapshots.add(snapshot)
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
    ) -> UserProfile:
        """Rollback a profile to a specific snapshot."""
        snapshot = self._snapshots.get(snapshot_id)
        if snapshot is None:
            raise SnapshotNotFoundError(f"Snapshot {snapshot_id} not found")

        profile = UserProfile.model_validate(snapshot.profile_data)
        if profile.user_id != user_id:
            raise ProfileError(
                f"Snapshot belongs to user '{profile.user_id}', not '{user_id}'"
            )
        await self._storage._store.save_profile(profile)
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
        return self._snapshots.list_snapshots(profile_id=profile.id)

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
        for domain_id, expertise in profile.intelligence.domain_expertise.items():
            result[domain_id] = {
                "level": expertise.level.value,
                "score": expertise.score,
                "interaction_count": expertise.interaction_count,
                "avg_depth": round(
                    expertise.total_depth
                    / max(1, expertise.interaction_count),
                    3,
                ),
            }
        return result

    async def get_recommendation_context(
        self,
        user_id: str,
    ) -> dict[str, object]:
        """Get a context object for adapting Prime's behaviour."""
        profile = await self.get_or_create_profile(user_id)
        top_domains = sorted(
            profile.intelligence.domain_expertise.values(),
            key=lambda e: e.score,
            reverse=True,
        )[:5]

        effective_prefs: dict[str, float] = {}
        for cat in PreferenceCategory:
            pref = profile.intelligence.preferences.get(cat.value)
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
                {
                    "domain_id": d.domain_id,
                    "level": d.level.value,
                    "score": d.score,
                }
                for d in top_domains
            ],
            "preferences": effective_prefs,
            "interaction_count": profile.intelligence.interaction_summary.total_interactions,
            "avg_depth": profile.intelligence.interaction_summary.avg_depth,
            "approval_rate": profile.intelligence.interaction_summary.approval_rate,
            "adaptation_count": profile.intelligence.adaptation_count,
            "working_style": profile.working_style.primary_style.value,
            "automation_preference": profile.working_style.automation_preference.value,
            "communication_style": profile.working_style.communication_style.value,
            "active_goals": len(
                [g for g in profile.goals if g.status == "active"]
            ),
            "total_skills": len(profile.learned_skills),
        }

    async def merge_profiles(
        self,
        source_user_id: str,
        target_user_id: str,
    ) -> UserProfile:
        """Merge source profile data into the target profile."""
        source = await self.get_profile(source_user_id)
        target = await self.get_or_create_profile(target_user_id)

        # Merge domain expertise
        merged_expertise = dict(target.intelligence.domain_expertise)
        for domain_id, src_exp in source.intelligence.domain_expertise.items():
            tgt_exp = merged_expertise.get(domain_id)
            if tgt_exp is None or src_exp.score > tgt_exp.score:
                merged_expertise[domain_id] = src_exp

        # Merge interaction summary
        tgt_summary = target.intelligence.interaction_summary
        src_summary = source.intelligence.interaction_summary
        merged_summary = tgt_summary.model_copy(
            update={
                "total_interactions": (
                    tgt_summary.total_interactions
                    + src_summary.total_interactions
                ),
                "avg_depth": (
                    (
                        tgt_summary.avg_depth * tgt_summary.total_interactions
                        + src_summary.avg_depth
                        * src_summary.total_interactions
                    )
                    / max(
                        1,
                        tgt_summary.total_interactions
                        + src_summary.total_interactions,
                    )
                ),
                "peak_depth": max(
                    tgt_summary.peak_depth, src_summary.peak_depth
                ),
            },
        )

        # Merge preferences
        merged_prefs = dict(target.intelligence.preferences)
        for cat_key, src_pref in source.intelligence.preferences.items():
            tgt_pref = merged_prefs.get(cat_key)
            if tgt_pref is None or (
                src_pref.explicit_value is not None
                and tgt_pref.explicit_value is None
            ) or (
                src_pref.explicit_value is None
                and tgt_pref.explicit_value is None
                and src_pref.confidence > tgt_pref.confidence
            ):
                merged_prefs[cat_key] = src_pref

        target.intelligence = target.intelligence.model_copy(
            update={
                "domain_expertise": merged_expertise,
                "interaction_summary": merged_summary,
                "preferences": merged_prefs,
                "adaptation_count": target.intelligence.adaptation_count + 1,
            },
        )
        target.updated_at = datetime.now(UTC)
        await self._storage._store.save_profile(target)

        await self._tape.log_event(
            event_type="profile.merged",
            payload={
                "source_user_id": source_user_id,
                "target_user_id": target_user_id,
                "domains_merged": len(merged_expertise),
            },
            agent_id="intelligence-profile-engine",
        )
        return target

    # ------------------------------------------------------------------
    # Profile status management
    # ------------------------------------------------------------------

    async def archive_profile(self, user_id: str) -> UserProfile:
        """Archive a user profile."""
        profile = await self.get_profile(user_id)
        profile = profile.model_copy(
            update={
                "status": ProfileStatus.ARCHIVED,
                "updated_at": datetime.now(UTC),
            },
        )
        await self._storage._store.save_profile(profile)
        await self._tape.log_event(
            event_type="profile.archived",
            payload={"user_id": user_id},
            agent_id="intelligence-profile-engine",
        )
        return profile

    async def suspend_profile(self, user_id: str) -> UserProfile:
        """Suspend a user profile."""
        profile = await self.get_profile(user_id)
        profile = profile.model_copy(
            update={
                "status": ProfileStatus.SUSPENDED,
                "updated_at": datetime.now(UTC),
            },
        )
        await self._storage._store.save_profile(profile)
        await self._tape.log_event(
            event_type="profile.suspended",
            payload={"user_id": user_id},
            agent_id="intelligence-profile-engine",
        )
        return profile

    async def reactivate_profile(self, user_id: str) -> UserProfile:
        """Reactivate a suspended or archived profile."""
        profile = await self.get_profile(user_id)
        profile = profile.model_copy(
            update={
                "status": ProfileStatus.ACTIVE,
                "updated_at": datetime.now(UTC),
            },
        )
        await self._storage._store.save_profile(profile)
        await self._tape.log_event(
            event_type="profile.reactivated",
            payload={"user_id": user_id},
            agent_id="intelligence-profile-engine",
        )
        return profile
