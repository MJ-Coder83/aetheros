"""Prime User Profile -- Persistent user preferences and personalization storage.

This module provides a UserProfile model that captures user preferences,
working style, goals, history summary, learned skills, and interaction patterns.
Profiles are stored persistently and linked to the folder-tree and AetherGit
for full auditability and version control.

Design principles:
- Profiles are persisted to both local storage and AetherGit
- Every profile update is logged to the Tape (full auditability)
- Profile data is stored in the folder-tree for version control
- Privacy-first: only operational patterns, not personal data
- Backward compatible with existing IntelligenceProfile system

Usage::

    from packages.prime.profile import UserProfile, ProfileStorage

    storage = ProfileStorage(tape_service=tape_svc, folder_tree=ft_svc)
    profile = await storage.get_or_create_profile(user_id="alice")
    await storage.update_preferences(user_id="alice", preferences={...})
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


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
# Data models
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
    context_retention: int = Field(default=10, ge=1, le=100)  # number of contexts


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
    summary_generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UserProfile(BaseModel):
    """Complete user profile for Prime personalization.

    The UserProfile aggregates user preferences, working style, goals,
    history summary, learned skills, and interaction patterns to enable
    personalized AI responses and suggestions.
    """

    model_config = ConfigDict(extra="allow")

    id: UUID = Field(default_factory=uuid4)
    user_id: str
    version: int = 1
    status: str = "active"  # active, archived, suspended

    # Core profile data
    display_name: str = ""
    email: str = ""
    bio: str = ""

    # Working style and preferences
    working_style: WorkingStyleConfig = Field(default_factory=WorkingStyleConfig)
    preferences: dict[str, UserPreferenceSetting] = Field(default_factory=dict)

    # Goals and skills
    goals: list[UserGoal] = []
    learned_skills: dict[str, LearnedSkill] = Field(default_factory=dict)

    # Patterns and history
    interaction_patterns: list[InteractionPattern] = []
    history_summary: HistorySummary = Field(default_factory=HistorySummary)

    # Storage metadata
    storage_backend: ProfileStorageBackend = ProfileStorageBackend.MEMORY
    folder_tree_path: str = ""  # Path in folder-tree where profile is stored
    aethergit_commit_id: str | None = None  # Last AetherGit commit for this profile

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


class ProfileStorageError(Exception):
    """Base exception for profile storage operations."""


class ProfileNotFoundError(ProfileStorageError):
    """Raised when a profile does not exist."""


class ProfileSerializationError(ProfileStorageError):
    """Raised when profile serialization fails."""


class ProfileSyncError(ProfileStorageError):
    """Raised when profile synchronization fails."""


# ---------------------------------------------------------------------------
# Profile Storage -- Abstract base
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
        """Get a profile by user ID."""
        raise NotImplementedError

    async def save_profile(self, profile: UserProfile) -> None:
        """Save a profile."""
        raise NotImplementedError

    async def delete_profile(self, user_id: str) -> bool:
        """Delete a profile. Returns True if deleted, False if not found."""
        raise NotImplementedError

    async def list_profiles(self) -> list[UserProfile]:
        """List all profiles."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# In-Memory Store (for testing)
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

    Profiles are stored as JSON files in a folder-tree structure:
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
    PREFERENCES_FILENAME: ClassVar[str] = "preferences.json"
    GOALS_FILENAME: ClassVar[str] = "goals.json"
    SKILLS_FILENAME: ClassVar[str] = "skills.json"

    def __init__(
        self,
        base_path: str,
        tape_service: TapeService | None = None,
    ) -> None:
        super().__init__(tape_service)
        self._base_path = base_path

    def _get_profile_dir(self, user_id: str) -> str:
        """Get the profile directory for a user."""
        import os

        return os.path.join(self._base_path, "profiles", user_id)

    def _get_profile_path(self, user_id: str) -> str:
        """Get the full path to a profile file."""
        import os

        return os.path.join(self._get_profile_dir(user_id), self.PROFILE_FILENAME)

    def _ensure_dir(self, path: str) -> None:
        """Ensure a directory exists."""
        import os

        os.makedirs(os.path.dirname(path), exist_ok=True)

    async def get_profile(self, user_id: str) -> UserProfile | None:
        import os

        profile_path = self._get_profile_path(user_id)
        if not os.path.exists(profile_path):
            return None

        try:
            with open(profile_path, encoding="utf-8") as f:
                data = json.load(f)
            return UserProfile.model_validate(data)
        except (json.JSONDecodeError, Exception) as e:
            raise ProfileSerializationError(f"Failed to load profile: {e}") from e

    async def save_profile(self, profile: UserProfile) -> None:

        profile_path = self._get_profile_path(profile.user_id)
        self._ensure_dir(profile_path)

        # Update timestamps
        profile.updated_at = datetime.now(UTC)
        profile.version += 1
        profile.folder_tree_path = self._get_profile_dir(profile.user_id)

        try:
            with open(profile_path, "w", encoding="utf-8") as f:
                json.dump(profile.model_dump(mode="json"), f, indent=2)
        except Exception as e:
            raise ProfileSerializationError(f"Failed to save profile: {e}") from e

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
        import os
        import shutil

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
            raise ProfileStorageError(f"Failed to delete profile: {e}") from e

    async def list_profiles(self) -> list[UserProfile]:
        import os

        profiles_dir = os.path.join(self._base_path, "profiles")
        if not os.path.exists(profiles_dir):
            return []

        profiles = []
        for user_id in os.listdir(profiles_dir):
            profile = await self.get_profile(user_id)
            if profile is not None:
                profiles.append(profile)

        return profiles


# ---------------------------------------------------------------------------
# Profile Storage Service -- Main API
# ---------------------------------------------------------------------------


class ProfileStorage:
    """Main service for user profile storage and management.

    This service provides a unified interface for profile CRUD operations
    with support for multiple storage backends and automatic Tape logging.

    Usage::

        storage = ProfileStorage(
            store=InMemoryProfileStore(tape_service),
            tape_service=tape_service,
        )
        profile = await storage.get_or_create_profile(user_id="alice")
        await storage.update_preferences(user_id="alice", preferences={...})
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

        profile = UserProfile(
            user_id=user_id,
            **(defaults or {}),
        )
        await self._store.save_profile(profile)

        if self._tape:
            await self._tape.log_event(
                event_type="profile.created",
                payload={"user_id": user_id, "profile_id": str(profile.id)},
                agent_id="profile-storage",
            )

        return profile

    async def get_profile(self, user_id: str) -> UserProfile:
        """Get a profile, raising if not found."""
        profile = await self._store.get_profile(user_id)
        if profile is None:
            raise ProfileNotFoundError(f"Profile for user '{user_id}' not found")
        return profile

    async def update_profile(
        self,
        user_id: str,
        updates: dict[str, Any],
    ) -> UserProfile:
        """Update a profile with new values."""
        profile = await self.get_profile(user_id)

        # Apply updates
        for key, value in updates.items():
            if hasattr(profile, key) and key != "id":
                setattr(profile, key, value)

        profile.updated_at = datetime.now(UTC)
        await self._store.save_profile(profile)

        if self._tape:
            await self._tape.log_event(
                event_type="profile.updated",
                payload={"user_id": user_id, "updated_fields": list(updates.keys())},
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
                payload={"user_id": user_id, "key": key, "value": str(value)},
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

        current = profile.working_style
        updates = {}

        for key, value in kwargs.items():
            if hasattr(current, key):
                updates[key] = value

        if updates:
            profile.working_style = current.model_copy(update=updates)
            await self._store.save_profile(profile)

        if self._tape:
            await self._tape.log_event(
                event_type="profile.working_style_updated",
                payload={"user_id": user_id, "updates": list(updates.keys())},
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

        raise ProfileNotFoundError(f"Goal '{goal_id}' not found for user '{user_id}'")

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
                        payload={"user_id": user_id, "goal_id": goal_id},
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

    async def get_skill(self, user_id: str, skill_id: str) -> LearnedSkill | None:
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

        # Check for existing pattern
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

        # Create new pattern
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

        current = profile.history_summary
        for key, value in updates.items():
            if hasattr(current, key):
                setattr(current, key, value)

        current.summary_generated_at = datetime.now(UTC)
        await self._store.save_profile(profile)

        return current

    async def record_session(
        self,
        user_id: str,
        duration: float,  # minutes
        interactions: int = 0,
        domains: list[str] | None = None,
    ) -> HistorySummary:
        """Record a completed session in the history summary."""
        profile = await self.get_or_create_profile(user_id)

        summary = profile.history_summary
        summary.total_sessions += 1
        summary.total_interactions += interactions
        summary.last_session_at = datetime.now(UTC)

        # Update average session duration
        total_duration = summary.avg_session_duration * (summary.total_sessions - 1)
        summary.avg_session_duration = (total_duration + duration) / summary.total_sessions

        # Update favorite domains
        if domains:
            summary.total_domains = len(set(summary.favorite_domains + domains))
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
        Note: This is a placeholder for full AetherGit integration.
        """
        profile = await self.get_profile(user_id)

        # Update sync timestamp
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

        # Return placeholder commit ID (real integration would create actual commit)
        return f"sync-{profile.user_id}-{int(datetime.now(UTC).timestamp())}"

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
                raise ProfileStorageError(f"Profile for '{user_id}' already exists")

        profile = UserProfile.model_validate(data)
        profile.user_id = user_id  # Ensure user_id matches
        profile.id = uuid4()  # Generate new ID
        profile.version = 1
        profile.updated_at = datetime.now(UTC)

        await self._store.save_profile(profile)

        if self._tape:
            await self._tape.log_event(
                event_type="profile.imported",
                payload={"user_id": user_id, "source_version": data.get("version")},
                agent_id="profile-storage",
            )

        return profile

    # ------------------------------------------------------------------
    # Profile Analysis
    # ------------------------------------------------------------------

    async def get_profile_summary(self, user_id: str) -> dict[str, Any]:
        """Get a summary of the user's profile."""
        profile = await self.get_profile(user_id)

        active_goals = len([g for g in profile.goals if g.status == "active"])
        verified_skills = len([s for s in profile.learned_skills.values() if s.verified])

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
            "last_sync": profile.last_sync_at.isoformat() if profile.last_sync_at else None,
        }
