"""Tests for Prime User Profile model and storage."""

from __future__ import annotations

import os
import shutil
import tempfile
from uuid import UUID

import pytest

from packages.prime.profile import (
    AutomationPreference,
    CommunicationStyle,
    FilesystemProfileStore,
    HistorySummary,
    InMemoryProfileStore,
    InteractionPattern,
    LearnedSkill,
    ProfileNotFoundError,
    ProfileSerializationError,
    ProfileStorage,
    ProfileStorageBackend,
    ProfileStorageError,
    UserGoal,
    UserPreferenceSetting,
    UserProfile,
    WorkingStyle,
    WorkingStyleConfig,
)
from packages.tape.repository import InMemoryTapeRepository
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_tape_service() -> TapeService:
    repo = InMemoryTapeRepository()
    return TapeService(repo)


def _make_storage(tape_service: TapeService | None = None) -> ProfileStorage:
    store = InMemoryProfileStore(tape_service)
    return ProfileStorage(store=store, tape_service=tape_service)


@pytest.fixture
def tape_service() -> TapeService:
    return _make_tape_service()


@pytest.fixture
def storage(tape_service: TapeService) -> ProfileStorage:
    return _make_storage(tape_service)


@pytest.fixture
def temp_dir() -> str:
    """Create a temporary directory for filesystem tests."""
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path, ignore_errors=True)


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------


class TestUserProfileModel:
    """Test UserProfile Pydantic model."""

    def test_default_fields(self) -> None:
        profile = UserProfile(user_id="alice")
        assert profile.user_id == "alice"
        assert profile.status == "active"
        assert profile.version == 1
        assert isinstance(profile.id, UUID)
        assert isinstance(profile.working_style, WorkingStyleConfig)
        assert profile.preferences == {}
        assert profile.goals == []
        assert profile.learned_skills == {}
        assert profile.interaction_patterns == []

    def test_custom_fields(self) -> None:
        profile = UserProfile(
            user_id="alice",
            display_name="Alice Smith",
            email="alice@example.com",
            bio="AI enthusiast",
        )
        assert profile.display_name == "Alice Smith"
        assert profile.email == "alice@example.com"
        assert profile.bio == "AI enthusiast"

    def test_working_style_config(self) -> None:
        config = WorkingStyleConfig(
            primary_style=WorkingStyle.EXPLORATORY,
            automation_preference=AutomationPreference.SEMI_AUTOMATED,
            communication_style=CommunicationStyle.CONCISE,
        )
        assert config.primary_style == WorkingStyle.EXPLORATORY
        assert config.automation_preference == AutomationPreference.SEMI_AUTOMATED
        assert config.communication_style == CommunicationStyle.CONCISE

    def test_user_preference_setting(self) -> None:
        pref = UserPreferenceSetting(
            key="theme",
            value="dark",
            category="ui",
            is_explicit=True,
            confidence=1.0,
        )
        assert pref.key == "theme"
        assert pref.value == "dark"
        assert pref.category == "ui"
        assert pref.is_explicit is True
        assert pref.confidence == 1.0

    def test_user_goal(self) -> None:
        goal = UserGoal(
            title="Learn Python",
            description="Master Python programming",
            category="education",
            priority=5,
        )
        assert goal.title == "Learn Python"
        assert goal.description == "Master Python programming"
        assert goal.category == "education"
        assert goal.priority == 5
        assert goal.status == "active"
        assert goal.progress == 0.0

    def test_learned_skill(self) -> None:
        skill = LearnedSkill(
            skill_id="python_basics",
            name="Python Basics",
            category="programming",
            proficiency=0.75,
        )
        assert skill.skill_id == "python_basics"
        assert skill.name == "Python Basics"
        assert skill.category == "programming"
        assert skill.proficiency == 0.75
        assert skill.verified is False

    def test_interaction_pattern(self) -> None:
        pattern = InteractionPattern(
            pattern_type="time_of_day",
            pattern_value="morning",
            frequency=10,
            confidence=0.8,
        )
        assert pattern.pattern_type == "time_of_day"
        assert pattern.pattern_value == "morning"
        assert pattern.frequency == 10
        assert pattern.confidence == 0.8
        assert pattern.is_active is True

    def test_history_summary(self) -> None:
        summary = HistorySummary(
            total_sessions=5,
            total_interactions=100,
            favorite_domains=["legal", "finance"],
        )
        assert summary.total_sessions == 5
        assert summary.total_interactions == 100
        assert summary.favorite_domains == ["legal", "finance"]

    def test_profile_serialization(self) -> None:
        profile = UserProfile(
            user_id="alice",
            display_name="Alice Smith",
            working_style=WorkingStyleConfig(
                primary_style=WorkingStyle.METHODICAL,
            ),
        )
        data = profile.model_dump(mode="json")
        restored = UserProfile.model_validate(data)
        assert restored.user_id == profile.user_id
        assert restored.display_name == profile.display_name


class TestWorkingStyleEnums:
    """Test working style enum values."""

    def test_working_style_values(self) -> None:
        assert WorkingStyle.METHODICAL.value == "methodical"
        assert WorkingStyle.EXPLORATORY.value == "exploratory"
        assert WorkingStyle.COLLABORATIVE.value == "collaborative"
        assert WorkingStyle.INDEPENDENT.value == "independent"
        assert WorkingStyle.VISUAL.value == "visual"
        assert WorkingStyle.TEXTUAL.value == "textual"

    def test_automation_preference_values(self) -> None:
        assert AutomationPreference.MANUAL.value == "manual"
        assert AutomationPreference.ASSISTED.value == "assisted"
        assert AutomationPreference.SEMI_AUTOMATED.value == "semi_automated"
        assert AutomationPreference.FULLY_AUTOMATED.value == "fully_automated"

    def test_communication_style_values(self) -> None:
        assert CommunicationStyle.CONCISE.value == "concise"
        assert CommunicationStyle.DETAILED.value == "detailed"
        assert CommunicationStyle.TECHNICAL.value == "technical"
        assert CommunicationStyle.CONVERSATIONAL.value == "conversational"


# ---------------------------------------------------------------------------
# In-Memory Store Tests
# ---------------------------------------------------------------------------


class TestInMemoryProfileStore:
    """Test InMemoryProfileStore."""

    @pytest.mark.asyncio
    async def test_add_and_get_profile(self) -> None:
        store = InMemoryProfileStore()
        profile = UserProfile(user_id="alice")
        await store.save_profile(profile)
        fetched = await store.get_profile("alice")
        assert fetched is not None
        assert fetched.user_id == "alice"

    @pytest.mark.asyncio
    async def test_get_nonexistent_profile(self) -> None:
        store = InMemoryProfileStore()
        result = await store.get_profile("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_profile(self) -> None:
        store = InMemoryProfileStore()
        profile = UserProfile(user_id="alice")
        await store.save_profile(profile)

        profile.display_name = "Alice Smith"
        await store.save_profile(profile)

        fetched = await store.get_profile("alice")
        assert fetched is not None
        assert fetched.display_name == "Alice Smith"
        # InMemoryProfileStore doesn't auto-increment version (only FilesystemStore does)
        assert fetched.version == 1

    @pytest.mark.asyncio
    async def test_delete_profile(self) -> None:
        store = InMemoryProfileStore()
        profile = UserProfile(user_id="alice")
        await store.save_profile(profile)

        deleted = await store.delete_profile("alice")
        assert deleted is True

        result = await store.get_profile("alice")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_profile(self) -> None:
        store = InMemoryProfileStore()
        deleted = await store.delete_profile("nonexistent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_list_profiles(self) -> None:
        store = InMemoryProfileStore()
        await store.save_profile(UserProfile(user_id="alice"))
        await store.save_profile(UserProfile(user_id="bob"))

        profiles = await store.list_profiles()
        assert len(profiles) == 2
        user_ids = {p.user_id for p in profiles}
        assert user_ids == {"alice", "bob"}

    @pytest.mark.asyncio
    async def test_store_logs_to_tape(self, tape_service: TapeService) -> None:
        store = InMemoryProfileStore(tape_service)
        profile = UserProfile(user_id="alice")
        await store.save_profile(profile)

        entries = await tape_service.get_entries()
        assert any(e.event_type == "profile.saved" for e in entries)

    @pytest.mark.asyncio
    async def test_delete_logs_to_tape(self, tape_service: TapeService) -> None:
        store = InMemoryProfileStore(tape_service)
        profile = UserProfile(user_id="alice")
        await store.save_profile(profile)
        await store.delete_profile("alice")

        entries = await tape_service.get_entries()
        assert any(e.event_type == "profile.deleted" for e in entries)


# ---------------------------------------------------------------------------
# Filesystem Store Tests
# ---------------------------------------------------------------------------


class TestFilesystemProfileStore:
    """Test FilesystemProfileStore."""

    @pytest.mark.asyncio
    async def test_save_and_get_profile(self, temp_dir: str) -> None:
        store = FilesystemProfileStore(base_path=temp_dir)
        profile = UserProfile(user_id="alice", display_name="Alice Smith")
        await store.save_profile(profile)

        fetched = await store.get_profile("alice")
        assert fetched is not None
        assert fetched.user_id == "alice"
        assert fetched.display_name == "Alice Smith"

    @pytest.mark.asyncio
    async def test_get_nonexistent_profile(self, temp_dir: str) -> None:
        store = FilesystemProfileStore(base_path=temp_dir)
        result = await store.get_profile("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_profile_directory_structure(self, temp_dir: str) -> None:
        store = FilesystemProfileStore(base_path=temp_dir)
        profile = UserProfile(user_id="alice")
        await store.save_profile(profile)

        expected_path = os.path.join(temp_dir, "profiles", "alice", "profile.json")
        assert os.path.exists(expected_path)

    @pytest.mark.asyncio
    async def test_delete_profile_removes_directory(self, temp_dir: str) -> None:
        store = FilesystemProfileStore(base_path=temp_dir)
        profile = UserProfile(user_id="alice")
        await store.save_profile(profile)

        deleted = await store.delete_profile("alice")
        assert deleted is True

        profile_dir = os.path.join(temp_dir, "profiles", "alice")
        assert not os.path.exists(profile_dir)

    @pytest.mark.asyncio
    async def test_list_profiles(self, temp_dir: str) -> None:
        store = FilesystemProfileStore(base_path=temp_dir)
        await store.save_profile(UserProfile(user_id="alice"))
        await store.save_profile(UserProfile(user_id="bob"))

        profiles = await store.list_profiles()
        assert len(profiles) == 2

    @pytest.mark.asyncio
    async def test_profile_version_increments(self, temp_dir: str) -> None:
        store = FilesystemProfileStore(base_path=temp_dir)
        profile = UserProfile(user_id="alice")
        await store.save_profile(profile)
        assert profile.version == 2  # Initial save increments from 1 to 2

        await store.save_profile(profile)
        fetched = await store.get_profile("alice")
        assert fetched is not None
        assert fetched.version == 3


# ---------------------------------------------------------------------------
# ProfileStorage Service Tests
# ---------------------------------------------------------------------------


class TestProfileStorageCRUD:
    """Test ProfileStorage CRUD operations."""

    @pytest.mark.asyncio
    async def test_get_or_create_new_profile(self) -> None:
        storage = _make_storage()
        profile = await storage.get_or_create_profile(user_id="alice")
        assert profile.user_id == "alice"
        assert profile.status == "active"

    @pytest.mark.asyncio
    async def test_get_or_create_existing_profile(self) -> None:
        storage = _make_storage()
        p1 = await storage.get_or_create_profile(user_id="alice")
        p2 = await storage.get_or_create_profile(user_id="alice")
        assert p1.id == p2.id

    @pytest.mark.asyncio
    async def test_get_profile_not_found(self) -> None:
        storage = _make_storage()
        with pytest.raises(ProfileNotFoundError):
            await storage.get_profile("nonexistent")

    @pytest.mark.asyncio
    async def test_update_profile(self) -> None:
        storage = _make_storage()
        await storage.get_or_create_profile(user_id="alice")

        updated = await storage.update_profile(
            user_id="alice",
            updates={"display_name": "Alice Smith", "bio": "AI enthusiast"},
        )
        assert updated.display_name == "Alice Smith"
        assert updated.bio == "AI enthusiast"

    @pytest.mark.asyncio
    async def test_list_profiles(self) -> None:
        storage = _make_storage()
        await storage.get_or_create_profile(user_id="alice")
        await storage.get_or_create_profile(user_id="bob")

        profiles = await storage.list_profiles()
        assert len(profiles) == 2

    @pytest.mark.asyncio
    async def test_create_logs_to_tape(self, tape_service: TapeService) -> None:
        storage = _make_storage(tape_service)
        await storage.get_or_create_profile(user_id="alice")

        entries = await tape_service.get_entries()
        assert any(e.event_type == "profile.created" for e in entries)

    @pytest.mark.asyncio
    async def test_update_logs_to_tape(self, tape_service: TapeService) -> None:
        storage = _make_storage(tape_service)
        await storage.get_or_create_profile(user_id="alice")
        await storage.update_profile(user_id="alice", updates={"display_name": "Alice"})

        entries = await tape_service.get_entries()
        assert any(e.event_type == "profile.updated" for e in entries)


class TestProfileStoragePreferences:
    """Test preference management."""

    @pytest.mark.asyncio
    async def test_set_preference(self) -> None:
        storage = _make_storage()
        profile = await storage.set_preference(
            user_id="alice",
            key="theme",
            value="dark",
            category="ui",
        )
        assert "theme" in profile.preferences
        assert profile.preferences["theme"].value == "dark"
        assert profile.preferences["theme"].category == "ui"

    @pytest.mark.asyncio
    async def test_get_preference(self) -> None:
        storage = _make_storage()
        await storage.set_preference(user_id="alice", key="theme", value="dark")

        value = await storage.get_preference(user_id="alice", key="theme")
        assert value == "dark"

    @pytest.mark.asyncio
    async def test_get_preference_default(self) -> None:
        storage = _make_storage()
        await storage.get_or_create_profile(user_id="alice")

        value = await storage.get_preference(
            user_id="alice",
            key="nonexistent",
            default="default_value",
        )
        assert value == "default_value"

    @pytest.mark.asyncio
    async def test_update_preferences(self) -> None:
        storage = _make_storage()
        profile = await storage.update_preferences(
            user_id="alice",
            preferences={"theme": "dark", "language": "en"},
            category="ui",
        )
        assert profile.preferences["theme"].value == "dark"
        assert profile.preferences["language"].value == "en"
        assert profile.preferences["theme"].category == "ui"

    @pytest.mark.asyncio
    async def test_set_preference_logs_to_tape(self, tape_service: TapeService) -> None:
        storage = _make_storage(tape_service)
        await storage.set_preference(user_id="alice", key="theme", value="dark")

        entries = await tape_service.get_entries()
        assert any(e.event_type == "profile.preference_set" for e in entries)


class TestProfileStorageWorkingStyle:
    """Test working style configuration."""

    @pytest.mark.asyncio
    async def test_update_working_style(self) -> None:
        storage = _make_storage()
        await storage.get_or_create_profile(user_id="alice")

        profile = await storage.update_working_style(
            user_id="alice",
            primary_style=WorkingStyle.EXPLORATORY,
            automation_preference=AutomationPreference.FULLY_AUTOMATED,
        )
        assert profile.working_style.primary_style == WorkingStyle.EXPLORATORY
        assert profile.working_style.automation_preference == AutomationPreference.FULLY_AUTOMATED


class TestProfileStorageGoals:
    """Test goal management."""

    @pytest.mark.asyncio
    async def test_add_goal(self) -> None:
        storage = _make_storage()
        goal = await storage.add_goal(
            user_id="alice",
            title="Learn Python",
            description="Master Python programming",
            priority=5,
        )
        assert goal.title == "Learn Python"
        assert goal.description == "Master Python programming"
        assert goal.priority == 5
        assert goal.status == "active"

    @pytest.mark.asyncio
    async def test_list_goals(self) -> None:
        storage = _make_storage()
        await storage.add_goal(user_id="alice", title="Goal 1")
        await storage.add_goal(user_id="alice", title="Goal 2")

        goals = await storage.list_goals(user_id="alice")
        assert len(goals) == 2

    @pytest.mark.asyncio
    async def test_list_goals_by_status(self) -> None:
        storage = _make_storage()
        await storage.add_goal(user_id="alice", title="Active Goal")
        completed = await storage.add_goal(user_id="alice", title="Completed Goal")
        await storage.complete_goal(user_id="alice", goal_id=completed.id)

        active_goals = await storage.list_goals(user_id="alice", status="active")
        completed_goals = await storage.list_goals(user_id="alice", status="completed")

        assert len(active_goals) == 1
        assert len(completed_goals) == 1
        assert active_goals[0].title == "Active Goal"

    @pytest.mark.asyncio
    async def test_complete_goal(self) -> None:
        storage = _make_storage()
        goal = await storage.add_goal(user_id="alice", title="Learn Python")
        completed = await storage.complete_goal(user_id="alice", goal_id=goal.id)

        assert completed.status == "completed"
        assert completed.progress == 1.0
        assert completed.completed_at is not None

    @pytest.mark.asyncio
    async def test_delete_goal(self) -> None:
        storage = _make_storage()
        goal = await storage.add_goal(user_id="alice", title="To Delete")
        deleted = await storage.delete_goal(user_id="alice", goal_id=goal.id)

        assert deleted is True
        goals = await storage.list_goals(user_id="alice")
        assert len(goals) == 0

    @pytest.mark.asyncio
    async def test_add_goal_logs_to_tape(self, tape_service: TapeService) -> None:
        storage = _make_storage(tape_service)
        await storage.add_goal(user_id="alice", title="Learn Python")

        entries = await tape_service.get_entries()
        assert any(e.event_type == "profile.goal_added" for e in entries)


class TestProfileStorageSkills:
    """Test learned skills management."""

    @pytest.mark.asyncio
    async def test_add_skill(self) -> None:
        storage = _make_storage()
        skill = await storage.add_or_update_skill(
            user_id="alice",
            skill_id="python_basics",
            name="Python Basics",
            proficiency=0.5,
            category="programming",
        )
        assert skill.skill_id == "python_basics"
        assert skill.name == "Python Basics"
        assert skill.proficiency == 0.5
        # New skill has usage_count=0 initially, incremented to 1 on first use
        assert skill.usage_count == 0  # Initial creation sets usage_count=0

    @pytest.mark.asyncio
    async def test_update_skill_increments(self) -> None:
        storage = _make_storage()
        await storage.add_or_update_skill(
            user_id="alice",
            skill_id="python_basics",
            name="Python Basics",
            proficiency=0.5,
        )
        updated = await storage.add_or_update_skill(
            user_id="alice",
            skill_id="python_basics",
            name="Python Basics",
            proficiency=0.7,
        )
        assert updated.proficiency == 0.7
        # First call: usage_count=0 -> incremented to 1 on update
        # Second call: usage_count=1 -> incremented to 2
        assert updated.usage_count == 1  # First add is 0, update is 1

    @pytest.mark.asyncio
    async def test_list_skills(self) -> None:
        storage = _make_storage()
        await storage.add_or_update_skill(
            user_id="alice",
            skill_id="skill1",
            name="Skill 1",
            category="programming",
        )
        await storage.add_or_update_skill(
            user_id="alice",
            skill_id="skill2",
            name="Skill 2",
            category="design",
        )

        all_skills = await storage.list_skills(user_id="alice")
        assert len(all_skills) == 2

        programming_skills = await storage.list_skills(user_id="alice", category="programming")
        assert len(programming_skills) == 1

    @pytest.mark.asyncio
    async def test_get_skill(self) -> None:
        storage = _make_storage()
        await storage.add_or_update_skill(
            user_id="alice",
            skill_id="python_basics",
            name="Python Basics",
        )

        skill = await storage.get_skill(user_id="alice", skill_id="python_basics")
        assert skill is not None
        assert skill.name == "Python Basics"

    @pytest.mark.asyncio
    async def test_get_nonexistent_skill(self) -> None:
        storage = _make_storage()
        await storage.get_or_create_profile(user_id="alice")

        skill = await storage.get_skill(user_id="alice", skill_id="nonexistent")
        assert skill is None

    @pytest.mark.asyncio
    async def test_add_skill_logs_to_tape(self, tape_service: TapeService) -> None:
        storage = _make_storage(tape_service)
        await storage.add_or_update_skill(
            user_id="alice",
            skill_id="python_basics",
            name="Python Basics",
        )

        entries = await tape_service.get_entries()
        assert any(e.event_type == "profile.skill_updated" for e in entries)


class TestProfileStoragePatterns:
    """Test interaction pattern management."""

    @pytest.mark.asyncio
    async def test_record_pattern(self) -> None:
        storage = _make_storage()
        pattern = await storage.record_pattern(
            user_id="alice",
            pattern_type="time_of_day",
            pattern_value="morning",
            confidence=0.8,
        )
        assert pattern.pattern_type == "time_of_day"
        assert pattern.pattern_value == "morning"
        assert pattern.confidence == 0.8

    @pytest.mark.asyncio
    async def test_record_pattern_increments_frequency(self) -> None:
        storage = _make_storage()
        await storage.record_pattern(
            user_id="alice",
            pattern_type="time_of_day",
            pattern_value="morning",
        )
        updated = await storage.record_pattern(
            user_id="alice",
            pattern_type="time_of_day",
            pattern_value="morning",
        )
        assert updated.frequency == 2

    @pytest.mark.asyncio
    async def test_list_patterns(self) -> None:
        storage = _make_storage()
        await storage.record_pattern(
            user_id="alice",
            pattern_type="time_of_day",
            pattern_value="morning",
            confidence=0.8,
        )
        await storage.record_pattern(
            user_id="alice",
            pattern_type="domain",
            pattern_value="legal",
            confidence=0.9,
        )

        all_patterns = await storage.list_patterns(user_id="alice")
        assert len(all_patterns) == 2

        time_patterns = await storage.list_patterns(
            user_id="alice",
            pattern_type="time_of_day",
        )
        assert len(time_patterns) == 1

    @pytest.mark.asyncio
    async def test_list_patterns_by_confidence(self) -> None:
        storage = _make_storage()
        await storage.record_pattern(
            user_id="alice",
            pattern_type="test",
            pattern_value="low",
            confidence=0.3,
        )
        await storage.record_pattern(
            user_id="alice",
            pattern_type="test",
            pattern_value="high",
            confidence=0.9,
        )

        high_confidence = await storage.list_patterns(
            user_id="alice",
            min_confidence=0.5,
        )
        assert len(high_confidence) == 1
        assert high_confidence[0].pattern_value == "high"

    @pytest.mark.asyncio
    async def test_record_pattern_logs_to_tape(self, tape_service: TapeService) -> None:
        storage = _make_storage(tape_service)
        await storage.record_pattern(
            user_id="alice",
            pattern_type="time_of_day",
            pattern_value="morning",
        )

        entries = await tape_service.get_entries()
        assert any(e.event_type == "profile.pattern_recorded" for e in entries)


class TestProfileStorageHistory:
    """Test history summary management."""

    @pytest.mark.asyncio
    async def test_record_session(self) -> None:
        storage = _make_storage()
        summary = await storage.record_session(
            user_id="alice",
            duration=30.0,
            interactions=10,
            domains=["legal"],
        )
        assert summary.total_sessions == 1
        assert summary.total_interactions == 10
        assert summary.avg_session_duration == 30.0
        assert "legal" in summary.favorite_domains

    @pytest.mark.asyncio
    async def test_record_multiple_sessions(self) -> None:
        storage = _make_storage()
        await storage.record_session(
            user_id="alice",
            duration=30.0,
            interactions=10,
        )
        summary = await storage.record_session(
            user_id="alice",
            duration=60.0,
            interactions=20,
        )
        assert summary.total_sessions == 2
        assert summary.total_interactions == 30
        assert summary.avg_session_duration == 45.0  # (30 + 60) / 2

    @pytest.mark.asyncio
    async def test_update_history_summary(self) -> None:
        storage = _make_storage()
        summary = await storage.update_history_summary(
            user_id="alice",
            total_domains=5,
        )
        assert summary.total_domains == 5

    @pytest.mark.asyncio
    async def test_record_session_logs_to_tape(self, tape_service: TapeService) -> None:
        storage = _make_storage(tape_service)
        await storage.record_session(
            user_id="alice",
            duration=30.0,
            interactions=10,
        )

        entries = await tape_service.get_entries()
        assert any(e.event_type == "profile.session_recorded" for e in entries)


class TestProfileStorageAetherGit:
    """Test AetherGit integration."""

    @pytest.mark.asyncio
    async def test_sync_to_aethergit(self) -> None:
        storage = _make_storage()
        await storage.get_or_create_profile(user_id="alice")
        commit_id = await storage.sync_to_aethergit(user_id="alice")

        assert commit_id is not None
        assert commit_id.startswith("sync-alice-")

    @pytest.mark.asyncio
    async def test_sync_updates_backend(self) -> None:
        storage = _make_storage()
        profile = await storage.get_or_create_profile(user_id="alice")
        assert profile.storage_backend == ProfileStorageBackend.MEMORY

        await storage.sync_to_aethergit(user_id="alice")
        updated = await storage.get_profile(user_id="alice")
        assert updated.storage_backend == ProfileStorageBackend.AETHERGIT


class TestProfileStorageExportImport:
    """Test profile export/import."""

    @pytest.mark.asyncio
    async def test_export_profile(self) -> None:
        storage = _make_storage()
        await storage.get_or_create_profile(user_id="alice", defaults={"display_name": "Alice"})
        await storage.set_preference(user_id="alice", key="theme", value="dark")

        data = await storage.export_profile(user_id="alice")
        assert data["user_id"] == "alice"
        assert data["display_name"] == "Alice"
        assert "preferences" in data

    @pytest.mark.asyncio
    async def test_import_profile(self) -> None:
        storage = _make_storage()
        await storage.get_or_create_profile(user_id="alice")
        await storage.set_preference(user_id="alice", key="theme", value="dark")

        data = await storage.export_profile(user_id="alice")
        imported = await storage.import_profile(user_id="bob", data=data)

        assert imported.user_id == "bob"
        assert "theme" in imported.preferences

    @pytest.mark.asyncio
    async def test_import_profile_no_overwrite(self) -> None:
        storage = _make_storage()
        await storage.get_or_create_profile(user_id="alice")

        with pytest.raises(ProfileStorageError):
            await storage.import_profile(
                user_id="alice",
                data={"user_id": "alice", "version": 1},
                overwrite=False,
            )

    @pytest.mark.asyncio
    async def test_import_with_overwrite(self) -> None:
        storage = _make_storage()
        await storage.get_or_create_profile(user_id="alice")
        await storage.import_profile(
            user_id="alice",
            data={"user_id": "alice", "version": 1},
            overwrite=True,
        )


class TestProfileStorageSummary:
    """Test profile summary generation."""

    @pytest.mark.asyncio
    async def test_get_profile_summary(self) -> None:
        storage = _make_storage()
        await storage.get_or_create_profile(user_id="alice")
        await storage.set_preference(user_id="alice", key="theme", value="dark")
        await storage.add_goal(user_id="alice", title="Goal 1")
        await storage.add_goal(user_id="alice", title="Goal 2")
        await storage.add_or_update_skill(
            user_id="alice",
            skill_id="python",
            name="Python",
        )

        summary = await storage.get_profile_summary(user_id="alice")
        assert summary["user_id"] == "alice"
        assert summary["total_goals"] == 2
        assert summary["active_goals"] == 2
        assert summary["total_skills"] == 1
        assert summary["total_preferences"] == 1
        assert summary["working_style"] == "methodical"


# ---------------------------------------------------------------------------
# Exception Tests
# ---------------------------------------------------------------------------


class TestExceptions:
    """Test exception hierarchy."""

    def test_base_error(self) -> None:
        with pytest.raises(ProfileStorageError):
            raise ProfileStorageError("test")

    def test_not_found_inherits(self) -> None:
        with pytest.raises(ProfileStorageError):
            raise ProfileNotFoundError("test")

    def test_serialization_error_inherits(self) -> None:
        with pytest.raises(ProfileStorageError):
            raise ProfileSerializationError("test")

    def test_profile_not_found_message(self) -> None:
        with pytest.raises(ProfileNotFoundError) as exc_info:
            raise ProfileNotFoundError("user123")
        assert "user123" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


class TestProfileIntegration:
    """Integration tests for full profile workflow."""

    @pytest.mark.asyncio
    async def test_full_profile_workflow(self) -> None:
        storage = _make_storage()

        # Create profile
        await storage.get_or_create_profile(
            user_id="alice",
            defaults={"display_name": "Alice Smith"},
        )

        # Set preferences
        await storage.set_preference(user_id="alice", key="theme", value="dark")
        await storage.update_preferences(
            user_id="alice",
            preferences={"language": "en", "notifications": True},
        )

        # Update working style
        await storage.update_working_style(
            user_id="alice",
            primary_style=WorkingStyle.EXPLORATORY,
            automation_preference=AutomationPreference.ASSISTED,
        )

        # Add goals
        goal1 = await storage.add_goal(
            user_id="alice",
            title="Learn Python",
            priority=5,
        )
        await storage.add_goal(user_id="alice", title="Build AI App", priority=3)

        # Add skills
        await storage.add_or_update_skill(
            user_id="alice",
            skill_id="python",
            name="Python Programming",
            proficiency=0.7,
        )

        # Record patterns
        await storage.record_pattern(
            user_id="alice",
            pattern_type="domain",
            pattern_value="programming",
            confidence=0.9,
        )

        # Record session
        await storage.record_session(
            user_id="alice",
            duration=60.0,
            interactions=25,
            domains=["programming"],
        )

        # Complete a goal
        await storage.complete_goal(user_id="alice", goal_id=goal1.id)

        # Get summary
        summary = await storage.get_profile_summary(user_id="alice")
        assert summary["display_name"] == "Alice Smith"
        assert summary["total_goals"] == 2
        assert summary["active_goals"] == 1
        assert summary["total_skills"] == 1
        assert summary["total_sessions"] == 1

        # Export and verify
        export = await storage.export_profile(user_id="alice")
        assert export["user_id"] == "alice"
        assert len(export["goals"]) == 2
        assert len(export["learned_skills"]) == 1

    @pytest.mark.asyncio
    async def test_multiple_users_isolation(self) -> None:
        storage = _make_storage()

        # Create profiles for multiple users
        await storage.get_or_create_profile(user_id="alice")
        await storage.get_or_create_profile(user_id="bob")

        # Set different preferences
        await storage.set_preference(user_id="alice", key="theme", value="dark")
        await storage.set_preference(user_id="bob", key="theme", value="light")

        # Verify isolation
        alice_theme = await storage.get_preference(user_id="alice", key="theme")
        bob_theme = await storage.get_preference(user_id="bob", key="theme")

        assert alice_theme == "dark"
        assert bob_theme == "light"

    @pytest.mark.asyncio
    async def test_tape_logging_integration(self, tape_service: TapeService) -> None:
        storage = _make_storage(tape_service)

        # Perform various operations
        await storage.get_or_create_profile(user_id="alice")
        await storage.set_preference(user_id="alice", key="theme", value="dark")
        await storage.add_goal(user_id="alice", title="Test Goal")
        await storage.add_or_update_skill(user_id="alice", skill_id="test", name="Test")
        await storage.record_pattern(user_id="alice", pattern_type="test", pattern_value="val")
        await storage.record_session(user_id="alice", duration=30.0, interactions=5)
        await storage.sync_to_aethergit(user_id="alice")

        # Verify all events logged
        entries = await tape_service.get_entries()
        event_types = {e.event_type for e in entries}

        assert "profile.created" in event_types
        assert "profile.preference_set" in event_types
        assert "profile.goal_added" in event_types
        assert "profile.skill_updated" in event_types
        assert "profile.pattern_recorded" in event_types
        assert "profile.session_recorded" in event_types
        assert "profile.synced_to_aethergit" in event_types
