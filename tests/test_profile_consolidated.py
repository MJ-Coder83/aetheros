"""Comprehensive tests for the consolidated Profile system.

Tests cover:
- UserProfile model (new fields: intelligence embedding, folder_tree_path, aethergit_commit_id)
- ProfileStorage CRUD (get_or_create, update, delete, list)
- ProfileStorage preferences (set, get, update_preferences)
- ProfileStorage working style
- ProfileStorage goals (add, update, complete, delete, list)
- ProfileStorage skills (add_or_update, get, list)
- ProfileStorage patterns (record, list)
- ProfileStorage history (update_summary, record_session)
- ProfileStorage AetherGit sync
- ProfileStorage export/import
- ProfileStorage summary
- IntelligenceProfileEngine facade (backward-compat API)
- IntelligenceProfileEngine interaction recording → updates embedded intelligence
- IntelligenceProfileEngine snapshots and rollback
- IntelligenceProfileEngine merge
- IntelligenceProfileEngine status management
- IntelligenceProfileEngine recommendation context
- FilesystemProfileStore
- Backward-compatible property access (profile.domain_expertise, etc.)
- Intelligence profile shim imports

Run with: pytest tests/test_profile_consolidated.py -v
"""

from __future__ import annotations

import tempfile

import pytest

from packages.prime.intelligence_profile import (
    InteractionType as ShimInteractionType,
)
from packages.prime.intelligence_profile import (
    PreferenceCategory as ShimPreferenceCategory,
)
from packages.prime.intelligence_profile import (
    ProfileNotFoundError as ShimProfileNotFoundError,
)
from packages.prime.intelligence_profile import (
    ProfileStatus as ShimProfileStatus,
)
from packages.prime.profile import (
    AutomationPreference,
    CommunicationStyle,
    DomainExpertise,
    ExpertiseAssessor,
    ExpertiseLevel,
    FilesystemProfileStore,
    HistorySummary,
    InMemoryProfileStore,
    IntelligenceProfile,
    IntelligenceProfileEngine,
    InteractionPattern,
    InteractionType,
    LearnedSkill,
    PreferenceCategory,
    ProfileError,
    ProfileNotFoundError,
    ProfileStatus,
    ProfileStorage,
    ProfileStorageBackend,
    ProfileStorageError,
    SnapshotNotFoundError,
    UserGoal,
    UserProfile,
    WorkingStyle,
    WorkingStyleConfig,
)
from packages.tape.repository import InMemoryTapeRepository
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_tape() -> TapeService:
    return TapeService(InMemoryTapeRepository())


def _make_storage(tape: TapeService | None = None) -> ProfileStorage:
    store = InMemoryProfileStore(tape)
    return ProfileStorage(store=store, tape_service=tape)


def _make_engine(tape: TapeService | None = None) -> IntelligenceProfileEngine:
    tape = tape or _make_tape()
    storage = _make_storage(tape)
    return IntelligenceProfileEngine(tape_service=tape, store=storage)


@pytest.fixture
def tape() -> TapeService:
    return _make_tape()


@pytest.fixture
def storage(tape: TapeService) -> ProfileStorage:
    return _make_storage(tape)


@pytest.fixture
def engine(tape: TapeService) -> IntelligenceProfileEngine:
    return _make_engine(tape)


# ===========================================================================
# UserProfile Model Tests
# ===========================================================================


class TestUserProfileModel:
    """Test UserProfile model defaults and fields."""

    def test_default_fields(self) -> None:
        profile = UserProfile(user_id="alice")
        assert profile.user_id == "alice"
        assert profile.version == 1
        assert profile.status == ProfileStatus.ACTIVE
        assert profile.display_name == ""
        assert profile.intelligence is not None
        assert profile.intelligence.adaptation_count == 0
        assert profile.folder_tree_path == ""
        assert profile.aethergit_commit_id is None
        assert profile.storage_backend == ProfileStorageBackend.MEMORY

    def test_intelligence_embedding(self) -> None:
        intel = IntelligenceProfile(
            domain_expertise={
                "legal": DomainExpertise(domain_id="legal", score=0.8, level=ExpertiseLevel.ADVANCED)
            },
            adaptation_count=5,
        )
        profile = UserProfile(user_id="alice", intelligence=intel)
        assert "legal" in profile.intelligence.domain_expertise
        assert profile.intelligence.adaptation_count == 5
        assert profile.intelligence.domain_expertise["legal"].level == ExpertiseLevel.ADVANCED

    def test_working_style_config(self) -> None:
        ws = WorkingStyleConfig(
            primary_style=WorkingStyle.EXPLORATORY,
            communication_style=CommunicationStyle.CONCISE,
            automation_preference=AutomationPreference.SEMI_AUTOMATED,
        )
        profile = UserProfile(user_id="alice", working_style=ws)
        assert profile.working_style.primary_style == WorkingStyle.EXPLORATORY
        assert profile.working_style.communication_style == CommunicationStyle.CONCISE

    def test_goals_field(self) -> None:
        goal = UserGoal(title="Master legal domain", priority=4)
        profile = UserProfile(user_id="alice", goals=[goal])
        assert len(profile.goals) == 1
        assert profile.goals[0].title == "Master legal domain"

    def test_learned_skills_field(self) -> None:
        skill = LearnedSkill(skill_id="contract-analysis", name="Contract Analysis", proficiency=0.7)
        profile = UserProfile(user_id="alice", learned_skills={"contract-analysis": skill})
        assert "contract-analysis" in profile.learned_skills
        assert profile.learned_skills["contract-analysis"].proficiency == 0.7

    def test_interaction_patterns_field(self) -> None:
        pattern = InteractionPattern(pattern_type="time_of_day", pattern_value="morning")
        profile = UserProfile(user_id="alice", interaction_patterns=[pattern])
        assert len(profile.interaction_patterns) == 1

    def test_history_summary_field(self) -> None:
        hs = HistorySummary(total_sessions=10, total_interactions=100)
        profile = UserProfile(user_id="alice", history_summary=hs)
        assert profile.history_summary.total_sessions == 10

    def test_folder_tree_path_and_aethergit(self) -> None:
        profile = UserProfile(
            user_id="alice",
            folder_tree_path="profiles/alice",
            aethergit_commit_id="abc123",
        )
        assert profile.folder_tree_path == "profiles/alice"
        assert profile.aethergit_commit_id == "abc123"

    def test_backward_compat_domain_expertise_property(self) -> None:
        """profile.domain_expertise should proxy to profile.intelligence.domain_expertise."""
        profile = UserProfile(user_id="alice")
        assert profile.domain_expertise is profile.intelligence.domain_expertise

    def test_backward_compat_interaction_summary_property(self) -> None:
        """profile.interaction_summary should proxy to profile.intelligence.interaction_summary."""
        profile = UserProfile(user_id="alice")
        assert profile.interaction_summary is profile.intelligence.interaction_summary

    def test_backward_compat_adaptation_count_property(self) -> None:
        """profile.adaptation_count should proxy to profile.intelligence.adaptation_count."""
        profile = UserProfile(user_id="alice")
        assert profile.adaptation_count == profile.intelligence.adaptation_count

    def test_model_dump_json_roundtrip(self) -> None:
        profile = UserProfile(
            user_id="alice",
            display_name="Alice",
            working_style=WorkingStyleConfig(primary_style=WorkingStyle.COLLABORATIVE),
            intelligence=IntelligenceProfile(adaptation_count=3),
        )
        data = profile.model_dump(mode="json")
        restored = UserProfile.model_validate(data)
        assert restored.user_id == "alice"
        assert restored.display_name == "Alice"
        assert restored.intelligence.adaptation_count == 3


# ===========================================================================
# ProfileStorage CRUD Tests
# ===========================================================================


class TestProfileStorageCRUD:
    """Test ProfileStorage create/read/update/delete."""

    @pytest.mark.asyncio
    async def test_get_or_create_creates_new(self, storage: ProfileStorage) -> None:
        profile = await storage.get_or_create_profile("alice")
        assert profile.user_id == "alice"
        assert profile.version == 1

    @pytest.mark.asyncio
    async def test_get_or_create_returns_existing(self, storage: ProfileStorage) -> None:
        p1 = await storage.get_or_create_profile("alice")
        p2 = await storage.get_or_create_profile("alice")
        assert p1.id == p2.id

    @pytest.mark.asyncio
    async def test_get_profile_raises_if_not_found(self, storage: ProfileStorage) -> None:
        with pytest.raises(ProfileNotFoundError):
            await storage.get_profile("nonexistent")

    @pytest.mark.asyncio
    async def test_update_profile(self, storage: ProfileStorage) -> None:
        await storage.get_or_create_profile("alice")
        updated = await storage.update_profile("alice", {"display_name": "Alice Smith", "bio": "AI researcher"})
        assert updated.display_name == "Alice Smith"
        assert updated.bio == "AI researcher"

    @pytest.mark.asyncio
    async def test_update_profile_does_not_change_id(self, storage: ProfileStorage) -> None:
        profile = await storage.get_or_create_profile("alice")
        original_id = profile.id
        await storage.update_profile("alice", {"display_name": "New Name"})
        updated = await storage.get_profile("alice")
        assert updated.id == original_id

    @pytest.mark.asyncio
    async def test_delete_profile(self, storage: ProfileStorage) -> None:
        await storage.get_or_create_profile("alice")
        result = await storage.delete_profile("alice")
        assert result is True
        with pytest.raises(ProfileNotFoundError):
            await storage.get_profile("alice")

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self, storage: ProfileStorage) -> None:
        result = await storage.delete_profile("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_profiles(self, storage: ProfileStorage) -> None:
        await storage.get_or_create_profile("alice")
        await storage.get_or_create_profile("bob")
        profiles = await storage.list_profiles()
        assert len(profiles) == 2
        user_ids = {p.user_id for p in profiles}
        assert user_ids == {"alice", "bob"}

    @pytest.mark.asyncio
    async def test_create_logs_to_tape(self, tape: TapeService, storage: ProfileStorage) -> None:
        await storage.get_or_create_profile("alice")
        entries = await tape.get_entries(event_type="profile.created")
        assert len(entries) == 1
        assert entries[0].payload["user_id"] == "alice"


# ===========================================================================
# ProfileStorage Preferences Tests
# ===========================================================================


class TestProfileStoragePreferences:
    """Test ProfileStorage preference operations."""

    @pytest.mark.asyncio
    async def test_set_preference(self, storage: ProfileStorage) -> None:
        profile = await storage.set_preference("alice", "theme", "dark", "ui")
        assert profile.preferences["theme"].value == "dark"
        assert profile.preferences["theme"].category == "ui"

    @pytest.mark.asyncio
    async def test_get_preference(self, storage: ProfileStorage) -> None:
        await storage.set_preference("alice", "language", "en")
        value = await storage.get_preference("alice", "language")
        assert value == "en"

    @pytest.mark.asyncio
    async def test_get_preference_default(self, storage: ProfileStorage) -> None:
        await storage.get_or_create_profile("alice")
        value = await storage.get_preference("alice", "nonexistent", "default_val")
        assert value == "default_val"

    @pytest.mark.asyncio
    async def test_update_preferences_bulk(self, storage: ProfileStorage) -> None:
        await storage.update_preferences("alice", {"theme": "light", "font_size": "16"}, "ui")
        profile = await storage.get_profile("alice")
        assert profile.preferences["theme"].value == "light"
        assert profile.preferences["font_size"].value == "16"

    @pytest.mark.asyncio
    async def test_set_preference_logs_to_tape(self, tape: TapeService, storage: ProfileStorage) -> None:
        await storage.set_preference("alice", "key1", "val1")
        entries = await tape.get_entries(event_type="profile.preference_set")
        assert len(entries) == 1


# ===========================================================================
# ProfileStorage Working Style Tests
# ===========================================================================


class TestProfileStorageWorkingStyle:

    @pytest.mark.asyncio
    async def test_update_working_style(self, storage: ProfileStorage) -> None:
        profile = await storage.update_working_style(
            "alice",
            communication_style=CommunicationStyle.CONCISE,
            automation_preference=AutomationPreference.MANUAL,
        )
        assert profile.working_style.communication_style == CommunicationStyle.CONCISE
        assert profile.working_style.automation_preference == AutomationPreference.MANUAL

    @pytest.mark.asyncio
    async def test_update_working_style_ignores_unknown_keys(self, storage: ProfileStorage) -> None:
        profile = await storage.update_working_style("alice", nonexistent_field="value")
        assert profile.working_style.primary_style == WorkingStyle.METHODICAL  # unchanged


# ===========================================================================
# ProfileStorage Goals Tests
# ===========================================================================


class TestProfileStorageGoals:

    @pytest.mark.asyncio
    async def test_add_goal(self, storage: ProfileStorage) -> None:
        goal = await storage.add_goal("alice", "Master legal domain", "Become expert", "learning", 4)
        assert goal.title == "Master legal domain"
        assert goal.priority == 4
        assert goal.status == "active"

    @pytest.mark.asyncio
    async def test_update_goal(self, storage: ProfileStorage) -> None:
        goal = await storage.add_goal("alice", "Learn Python")
        updated = await storage.update_goal("alice", goal.id, status="paused", progress=0.3)
        assert updated.status == "paused"
        assert updated.progress == 0.3

    @pytest.mark.asyncio
    async def test_complete_goal(self, storage: ProfileStorage) -> None:
        goal = await storage.add_goal("alice", "Finish project")
        completed = await storage.complete_goal("alice", goal.id)
        assert completed.status == "completed"
        assert completed.progress == 1.0

    @pytest.mark.asyncio
    async def test_delete_goal(self, storage: ProfileStorage) -> None:
        goal = await storage.add_goal("alice", "Temporary goal")
        result = await storage.delete_goal("alice", goal.id)
        assert result is True
        goals = await storage.list_goals("alice")
        assert len(goals) == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent_goal(self, storage: ProfileStorage) -> None:
        await storage.get_or_create_profile("alice")
        result = await storage.delete_goal("alice", "nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_goals_by_status(self, storage: ProfileStorage) -> None:
        await storage.add_goal("alice", "Active goal 1")
        await storage.add_goal("alice", "Active goal 2")
        goal3 = await storage.add_goal("alice", "To complete")
        await storage.complete_goal("alice", goal3.id)
        active = await storage.list_goals("alice", status="active")
        completed = await storage.list_goals("alice", status="completed")
        assert len(active) == 2
        assert len(completed) == 1

    @pytest.mark.asyncio
    async def test_update_nonexistent_goal_raises(self, storage: ProfileStorage) -> None:
        with pytest.raises(ProfileNotFoundError):
            await storage.update_goal("alice", "nonexistent", status="completed")


# ===========================================================================
# ProfileStorage Skills Tests
# ===========================================================================


class TestProfileStorageSkills:

    @pytest.mark.asyncio
    async def test_add_new_skill(self, storage: ProfileStorage) -> None:
        skill = await storage.add_or_update_skill("alice", "py", "Python", 0.6, "programming")
        assert skill.skill_id == "py"
        assert skill.proficiency == 0.6

    @pytest.mark.asyncio
    async def test_update_existing_skill(self, storage: ProfileStorage) -> None:
        await storage.add_or_update_skill("alice", "py", "Python", 0.5)
        skill = await storage.add_or_update_skill("alice", "py", "Python", 0.8)
        assert skill.proficiency == 0.8  # max of 0.5 and 0.8
        assert skill.usage_count == 1  # incremented

    @pytest.mark.asyncio
    async def test_get_skill(self, storage: ProfileStorage) -> None:
        await storage.add_or_update_skill("alice", "py", "Python")
        skill = await storage.get_skill("alice", "py")
        assert skill is not None
        assert skill.name == "Python"

    @pytest.mark.asyncio
    async def test_list_skills_by_category(self, storage: ProfileStorage) -> None:
        await storage.add_or_update_skill("alice", "py", "Python", category="programming")
        await storage.add_or_update_skill("alice", "legal", "Legal Research", category="domain")
        skills = await storage.list_skills("alice", category="programming")
        assert len(skills) == 1
        assert skills[0].skill_id == "py"


# ===========================================================================
# ProfileStorage Patterns Tests
# ===========================================================================


class TestProfileStoragePatterns:

    @pytest.mark.asyncio
    async def test_record_new_pattern(self, storage: ProfileStorage) -> None:
        pattern = await storage.record_pattern("alice", "time_of_day", "morning", 0.8)
        assert pattern.pattern_type == "time_of_day"
        assert pattern.frequency == 1

    @pytest.mark.asyncio
    async def test_record_existing_pattern_increments(self, storage: ProfileStorage) -> None:
        await storage.record_pattern("alice", "time_of_day", "morning", 0.5)
        pattern = await storage.record_pattern("alice", "time_of_day", "morning", 0.8)
        assert pattern.frequency == 2
        assert pattern.confidence == 0.8  # max of 0.5 and 0.8

    @pytest.mark.asyncio
    async def test_list_patterns_by_type(self, storage: ProfileStorage) -> None:
        await storage.record_pattern("alice", "time_of_day", "morning")
        await storage.record_pattern("alice", "domain_pref", "legal")
        time_patterns = await storage.list_patterns("alice", pattern_type="time_of_day")
        assert len(time_patterns) == 1

    @pytest.mark.asyncio
    async def test_list_patterns_min_confidence(self, storage: ProfileStorage) -> None:
        await storage.record_pattern("alice", "low", "low_conf", confidence=0.2)
        await storage.record_pattern("alice", "high", "high_conf", confidence=0.9)
        filtered = await storage.list_patterns("alice", min_confidence=0.5)
        assert len(filtered) == 1
        assert filtered[0].pattern_value == "high_conf"


# ===========================================================================
# ProfileStorage History Tests
# ===========================================================================


class TestProfileStorageHistory:

    @pytest.mark.asyncio
    async def test_record_session(self, storage: ProfileStorage) -> None:
        summary = await storage.record_session("alice", duration=30.0, interactions=5)
        assert summary.total_sessions == 1
        assert summary.total_interactions == 5
        assert summary.avg_session_duration == 30.0

    @pytest.mark.asyncio
    async def test_record_multiple_sessions(self, storage: ProfileStorage) -> None:
        await storage.record_session("alice", duration=20.0, interactions=5)
        await storage.record_session("alice", duration=40.0, interactions=10)
        summary = await storage.record_session("alice", duration=60.0, interactions=15)
        assert summary.total_sessions == 3
        assert summary.total_interactions == 30
        assert abs(summary.avg_session_duration - 40.0) < 0.01

    @pytest.mark.asyncio
    async def test_record_session_with_domains(self, storage: ProfileStorage) -> None:
        await storage.record_session("alice", duration=30.0, domains=["legal", "finance"])
        profile = await storage.get_profile("alice")
        assert "legal" in profile.history_summary.favorite_domains
        assert "finance" in profile.history_summary.favorite_domains

    @pytest.mark.asyncio
    async def test_update_history_summary(self, storage: ProfileStorage) -> None:
        summary = await storage.update_history_summary("alice", total_proposals=5, total_approvals=3)
        assert summary.total_proposals == 5
        assert summary.total_approvals == 3


# ===========================================================================
# ProfileStorage AetherGit / Export / Import Tests
# ===========================================================================


class TestProfileStorageSyncExport:

    @pytest.mark.asyncio
    async def test_sync_to_aethergit(self, storage: ProfileStorage) -> None:
        await storage.get_or_create_profile("alice")
        commit_id = await storage.sync_to_aethergit("alice", "Update profile")
        assert commit_id is not None
        assert "sync-alice" in commit_id
        profile = await storage.get_profile("alice")
        assert profile.storage_backend == ProfileStorageBackend.AETHERGIT
        assert profile.last_sync_at is not None

    @pytest.mark.asyncio
    async def test_export_profile(self, storage: ProfileStorage) -> None:
        await storage.get_or_create_profile("alice")
        await storage.update_profile("alice", {"display_name": "Alice"})
        data = await storage.export_profile("alice")
        assert data["user_id"] == "alice"
        assert data["display_name"] == "Alice"

    @pytest.mark.asyncio
    async def test_import_profile(self, storage: ProfileStorage) -> None:
        data = {"user_id": "original", "display_name": "Imported", "version": 5}
        profile = await storage.import_profile("alice", data)
        assert profile.user_id == "alice"  # user_id overridden
        assert profile.display_name == "Imported"
        assert profile.version == 1  # version reset

    @pytest.mark.asyncio
    async def test_import_profile_no_overwrite(self, storage: ProfileStorage) -> None:
        await storage.get_or_create_profile("alice")
        with pytest.raises(ProfileStorageError):
            await storage.import_profile("alice", {"user_id": "alice"})

    @pytest.mark.asyncio
    async def test_import_profile_with_overwrite(self, storage: ProfileStorage) -> None:
        await storage.get_or_create_profile("alice")
        profile = await storage.import_profile("alice", {"user_id": "alice", "display_name": "New"}, overwrite=True)
        assert profile.display_name == "New"


# ===========================================================================
# ProfileStorage Summary Tests
# ===========================================================================


class TestProfileStorageSummary:

    @pytest.mark.asyncio
    async def test_get_profile_summary(self, storage: ProfileStorage) -> None:
        await storage.get_or_create_profile("alice")
        await storage.update_profile("alice", {"display_name": "Alice"})
        await storage.add_goal("alice", "Goal 1")
        await storage.add_or_update_skill("alice", "py", "Python", proficiency=0.8)
        summary = await storage.get_profile_summary("alice")
        assert summary["display_name"] == "Alice"
        assert summary["total_goals"] == 1
        assert summary["total_skills"] == 1
        assert summary["working_style"] == "methodical"


# ===========================================================================
# IntelligenceProfileEngine Facade Tests
# ===========================================================================


class TestIntelligenceProfileEngineFacade:
    """Test that IntelligenceProfileEngine delegates correctly to ProfileStorage."""

    @pytest.mark.asyncio
    async def test_get_or_create_delegates(self, engine: IntelligenceProfileEngine) -> None:
        profile = await engine.get_or_create_profile("alice")
        assert isinstance(profile, UserProfile)
        assert profile.user_id == "alice"

    @pytest.mark.asyncio
    async def test_record_interaction_updates_intelligence(self, engine: IntelligenceProfileEngine) -> None:
        profile = await engine.record_interaction(
            user_id="alice",
            interaction_type=InteractionType.QUERY,
            domain="legal",
            depth=0.8,
            approved=True,
        )
        assert profile.intelligence.interaction_summary.total_interactions == 1
        assert "legal" in profile.intelligence.domain_expertise
        assert profile.intelligence.adaptation_count == 1

    @pytest.mark.asyncio
    async def test_record_multiple_interactions(self, engine: IntelligenceProfileEngine) -> None:
        for _ in range(10):
            await engine.record_interaction(
                user_id="alice",
                interaction_type=InteractionType.QUERY,
                domain="legal",
                depth=0.7,
            )
        profile = await engine.get_profile("alice")
        assert profile.intelligence.interaction_summary.total_interactions == 10

    @pytest.mark.asyncio
    async def test_set_preference_updates_intelligence(self, engine: IntelligenceProfileEngine) -> None:
        profile = await engine.set_preference(
            user_id="alice",
            category=PreferenceCategory.RISK_TOLERANCE,
            value=0.9,
        )
        pref = profile.intelligence.preferences[PreferenceCategory.RISK_TOLERANCE.value]
        assert pref.explicit_value == 0.9
        assert pref.confidence == 1.0

    @pytest.mark.asyncio
    async def test_get_effective_preference(self, engine: IntelligenceProfileEngine) -> None:
        await engine.set_preference("alice", PreferenceCategory.AUTOMATION_LEVEL, 0.7)
        value = await engine.get_effective_preference("alice", PreferenceCategory.AUTOMATION_LEVEL)
        assert value == 0.7

    @pytest.mark.asyncio
    async def test_get_effective_preference_default(self, engine: IntelligenceProfileEngine) -> None:
        await engine.get_or_create_profile("alice")
        value = await engine.get_effective_preference("alice", PreferenceCategory.RESPONSE_DETAIL)
        assert value == 0.5  # default

    @pytest.mark.asyncio
    async def test_get_domain_summary(self, engine: IntelligenceProfileEngine) -> None:
        await engine.record_interaction("alice", InteractionType.QUERY, "legal", depth=0.8)
        summary = await engine.get_domain_summary("alice")
        assert "legal" in summary
        assert summary["legal"]["level"] in ("intermediate", "advanced", "novice")

    @pytest.mark.asyncio
    async def test_get_recommendation_context(self, engine: IntelligenceProfileEngine) -> None:
        await engine.record_interaction("alice", InteractionType.QUERY, "legal", depth=0.8)
        context = await engine.get_recommendation_context("alice")
        assert context["user_id"] == "alice"
        assert "working_style" in context
        assert "active_goals" in context
        assert "total_skills" in context

    @pytest.mark.asyncio
    async def test_merge_profiles(self, engine: IntelligenceProfileEngine) -> None:
        await engine.record_interaction("alice", InteractionType.QUERY, "legal", depth=0.8)
        await engine.record_interaction("bob", InteractionType.QUERY, "finance", depth=0.6)
        merged = await engine.merge_profiles("alice", "bob")
        assert "legal" in merged.intelligence.domain_expertise
        assert "finance" in merged.intelligence.domain_expertise

    @pytest.mark.asyncio
    async def test_snapshot_and_rollback(self, engine: IntelligenceProfileEngine) -> None:
        await engine.record_interaction("alice", InteractionType.QUERY, "legal", depth=0.8)
        snapshot = await engine.create_snapshot("alice", reason="pre-change")
        # Make more changes
        await engine.record_interaction("alice", InteractionType.APPROVAL, "legal", depth=1.0)
        # Rollback
        rolled_back = await engine.rollback_to_snapshot("alice", snapshot.id)
        assert rolled_back.intelligence.interaction_summary.total_interactions == 1  # back to 1

    @pytest.mark.asyncio
    async def test_list_snapshots(self, engine: IntelligenceProfileEngine) -> None:
        await engine.record_interaction("alice", InteractionType.QUERY, "legal", depth=0.5)
        await engine.create_snapshot("alice", reason="test1")
        await engine.create_snapshot("alice", reason="test2")
        snapshots = await engine.list_snapshots("alice")
        assert len(snapshots) >= 2

    @pytest.mark.asyncio
    async def test_archive_profile(self, engine: IntelligenceProfileEngine) -> None:
        await engine.get_or_create_profile("alice")
        profile = await engine.archive_profile("alice")
        assert profile.status == ProfileStatus.ARCHIVED

    @pytest.mark.asyncio
    async def test_suspend_and_reactivate(self, engine: IntelligenceProfileEngine) -> None:
        await engine.get_or_create_profile("alice")
        await engine.suspend_profile("alice")
        profile = await engine.get_profile("alice")
        assert profile.status == ProfileStatus.SUSPENDED
        await engine.reactivate_profile("alice")
        profile = await engine.get_profile("alice")
        assert profile.status == ProfileStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_interaction_logs_to_tape(self, tape: TapeService, engine: IntelligenceProfileEngine) -> None:
        await engine.record_interaction("alice", InteractionType.QUERY, "legal", depth=0.5)
        entries = await tape.get_entries(event_type="profile.interaction_recorded")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_interaction_also_updates_history_summary(self, engine: IntelligenceProfileEngine) -> None:
        await engine.record_interaction("alice", InteractionType.QUERY, "legal", depth=0.5)
        profile = await engine.get_profile("alice")
        assert profile.history_summary.total_interactions >= 1


# ===========================================================================
# FilesystemProfileStore Tests
# ===========================================================================


class TestFilesystemProfileStore:

    @pytest.mark.asyncio
    async def test_save_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FilesystemProfileStore(tmpdir)
            profile = UserProfile(user_id="alice", display_name="Alice")
            await store.save_profile(profile)
            loaded = await store.get_profile("alice")
            assert loaded is not None
            assert loaded.user_id == "alice"
            assert loaded.display_name == "Alice"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FilesystemProfileStore(tmpdir)
            result = await store.get_profile("nonexistent")
            assert result is None

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FilesystemProfileStore(tmpdir)
            profile = UserProfile(user_id="alice")
            await store.save_profile(profile)
            result = await store.delete_profile("alice")
            assert result is True
            assert await store.get_profile("alice") is None

    @pytest.mark.asyncio
    async def test_list_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FilesystemProfileStore(tmpdir)
            await store.save_profile(UserProfile(user_id="alice"))
            await store.save_profile(UserProfile(user_id="bob"))
            profiles = await store.list_profiles()
            assert len(profiles) == 2

    @pytest.mark.asyncio
    async def test_save_increments_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FilesystemProfileStore(tmpdir)
            profile = UserProfile(user_id="alice")
            await store.save_profile(profile)
            assert profile.version == 2  # incremented on save

    @pytest.mark.asyncio
    async def test_save_sets_folder_tree_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FilesystemProfileStore(tmpdir)
            profile = UserProfile(user_id="alice")
            await store.save_profile(profile)
            assert profile.folder_tree_path != ""


# ===========================================================================
# Backward-Compatible Shim Import Tests
# ===========================================================================


class TestShimImports:
    """Test that the intelligence_profile shim re-exports work correctly."""

    def test_import_engine_from_shim(self) -> None:
        from packages.prime.intelligence_profile import IntelligenceProfileEngine
        assert IntelligenceProfileEngine is not None

    def test_import_types_from_shim(self) -> None:
        assert ShimInteractionType.QUERY == InteractionType.QUERY
        assert ShimPreferenceCategory.RISK_TOLERANCE == PreferenceCategory.RISK_TOLERANCE
        assert ShimProfileStatus.ACTIVE == ProfileStatus.ACTIVE

    def test_import_exceptions_from_shim(self) -> None:
        assert issubclass(ShimProfileNotFoundError, ProfileError)

    def test_shim_classes_are_same_as_profile_module(self) -> None:
        """Verify shim re-exports point to the same classes."""
        from packages.prime.intelligence_profile import (
            DomainExpertise as ShimDE,
        )
        from packages.prime.intelligence_profile import (
            ExpertiseAssessor as ShimEA,
        )
        from packages.prime.intelligence_profile import (
            IntelligenceProfile as ShimIP,
        )
        from packages.prime.profile import (
            DomainExpertise,
            IntelligenceProfile,
        )
        assert ShimDE is DomainExpertise
        assert ShimEA is ExpertiseAssessor
        assert ShimIP is IntelligenceProfile


# ===========================================================================
# Exception Hierarchy Tests
# ===========================================================================


class TestExceptionHierarchy:

    def test_profile_not_found_is_storage_error(self) -> None:
        assert issubclass(ProfileNotFoundError, ProfileStorageError)

    def test_serialization_error_is_storage_error(self) -> None:
        from packages.prime.profile import ProfileSerializationError
        assert issubclass(ProfileSerializationError, ProfileStorageError)

    def test_sync_error_is_storage_error(self) -> None:
        from packages.prime.profile import ProfileSyncError
        assert issubclass(ProfileSyncError, ProfileStorageError)

    def test_snapshot_not_found_is_profile_error(self) -> None:
        assert issubclass(SnapshotNotFoundError, ProfileError)

    def test_transition_error_is_profile_error(self) -> None:
        from packages.prime.profile import ProfileTransitionError
        assert issubclass(ProfileTransitionError, ProfileError)
