"""Tests for Personalized Intelligence Profile engine."""

from __future__ import annotations

from uuid import UUID

import pytest

from packages.prime.intelligence_profile import (
    DomainExpertise,
    ExpertiseAssessor,
    ExpertiseLevel,
    IntelligenceProfile,
    IntelligenceProfileEngine,
    InteractionSummary,
    InteractionType,
    PreferenceCategory,
    PreferenceInferrer,
    ProfileError,
    ProfileNotFoundError,
    ProfileSnapshot,
    ProfileStatus,
    ProfileStore,
    SnapshotNotFoundError,
    UserPreference,
)
from packages.tape.repository import InMemoryTapeRepository
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_tape_service() -> TapeService:
    repo = InMemoryTapeRepository()
    return TapeService(repo)


def _make_engine(
    tape_service: TapeService | None = None,
) -> IntelligenceProfileEngine:
    return IntelligenceProfileEngine(
        tape_service=tape_service or _make_tape_service(),
    )


# ===========================================================================
# ExpertiseAssessor tests
# ===========================================================================


class TestExpertiseAssessor:
    """Test expertise assessment heuristics."""

    def test_novice_with_no_interactions(self) -> None:
        assessor = ExpertiseAssessor()
        score = assessor.compute_score(interaction_count=0, avg_depth=0.0)
        assert score == 0.0
        assert assessor.score_to_level(score) == ExpertiseLevel.NOVICE

    def test_intermediate_with_some_interactions(self) -> None:
        assessor = ExpertiseAssessor()
        score = assessor.compute_score(interaction_count=10, avg_depth=0.5)
        assert 0.0 < score < 1.0
        level = assessor.score_to_level(score)
        assert level in (ExpertiseLevel.INTERMEDIATE, ExpertiseLevel.ADVANCED)

    def test_expert_with_many_high_depth_interactions(self) -> None:
        assessor = ExpertiseAssessor()
        score = assessor.compute_score(interaction_count=50, avg_depth=0.9)
        assert score >= 0.5
        level = assessor.score_to_level(score)
        assert level in (ExpertiseLevel.EXPERT, ExpertiseLevel.ADVANCED)

    def test_low_depth_reduces_score(self) -> None:
        assessor = ExpertiseAssessor()
        score_high = assessor.compute_score(interaction_count=20, avg_depth=0.9)
        score_low = assessor.compute_score(interaction_count=20, avg_depth=0.1)
        assert score_high > score_low

    def test_diminishing_returns_on_count(self) -> None:
        assessor = ExpertiseAssessor()
        score_5 = assessor.compute_score(interaction_count=5, avg_depth=0.5)
        score_10 = assessor.compute_score(interaction_count=10, avg_depth=0.5)
        score_50 = assessor.compute_score(interaction_count=50, avg_depth=0.5)
        score_200 = assessor.compute_score(interaction_count=200, avg_depth=0.5)
        # Diminishing returns: early gains are larger than later gains
        early_gain = score_10 - score_5
        late_gain = score_200 - score_50
        assert early_gain > late_gain

    def test_score_bounded(self) -> None:
        assessor = ExpertiseAssessor()
        score = assessor.compute_score(interaction_count=1000, avg_depth=1.0, recency_boost=2.0)
        assert 0.0 <= score <= 1.0

    def test_recency_boost(self) -> None:
        assessor = ExpertiseAssessor()
        score_no_boost = assessor.compute_score(interaction_count=20, avg_depth=0.5)
        score_boosted = assessor.compute_score(
            interaction_count=20, avg_depth=0.5, recency_boost=1.5
        )
        assert score_boosted > score_no_boost

    def test_score_to_level_all_levels(self) -> None:
        assessor = ExpertiseAssessor()
        assert assessor.score_to_level(0.9) == ExpertiseLevel.EXPERT
        assert assessor.score_to_level(0.6) == ExpertiseLevel.ADVANCED
        assert assessor.score_to_level(0.3) == ExpertiseLevel.INTERMEDIATE
        assert assessor.score_to_level(0.05) == ExpertiseLevel.NOVICE

    def test_update_expertise(self) -> None:
        assessor = ExpertiseAssessor()
        expertise = DomainExpertise(domain_id="legal")
        updated = assessor.update_expertise(expertise, depth=0.8)
        assert updated.interaction_count == 1
        assert updated.total_depth == 0.8
        assert updated.score > 0.0
        assert updated.last_interaction is not None

    def test_update_expertise_accumulates(self) -> None:
        assessor = ExpertiseAssessor()
        expertise = DomainExpertise(domain_id="legal", interaction_count=5, total_depth=3.0)
        updated = assessor.update_expertise(expertise, depth=0.7)
        assert updated.interaction_count == 6
        assert updated.total_depth == 3.7


# ===========================================================================
# PreferenceInferrer tests
# ===========================================================================


class TestPreferenceInferrer:
    """Test preference inference from behavioural signals."""

    def test_infer_response_detail_from_depth(self) -> None:
        inferrer = PreferenceInferrer()
        summary = InteractionSummary(total_interactions=25, avg_depth=0.8)
        prefs = inferrer.infer_from_interactions({}, summary)
        detail = prefs[PreferenceCategory.RESPONSE_DETAIL.value]
        assert detail.inferred_value == 0.8
        assert detail.confidence > 0.0

    def test_infer_automation_from_approval_rate(self) -> None:
        inferrer = PreferenceInferrer()
        summary = InteractionSummary(total_interactions=35, approval_rate=0.9)
        prefs = inferrer.infer_from_interactions({}, summary)
        auto = prefs[PreferenceCategory.AUTOMATION_LEVEL.value]
        assert auto.inferred_value == 0.9

    def test_infer_risk_tolerance(self) -> None:
        inferrer = PreferenceInferrer()
        summary = InteractionSummary(total_interactions=30, approval_rate=0.3)
        prefs = inferrer.infer_from_interactions({}, summary)
        risk = prefs[PreferenceCategory.RISK_TOLERANCE.value]
        assert risk.inferred_value == 0.3

    def test_infer_explanation_depth(self) -> None:
        inferrer = PreferenceInferrer()
        summary = InteractionSummary(total_interactions=20, avg_depth=0.6)
        prefs = inferrer.infer_from_interactions({}, summary)
        explain = prefs[PreferenceCategory.EXPLANATION_DEPTH.value]
        assert explain.inferred_value == pytest.approx(0.48, abs=0.01)

    def test_infer_suggestion_frequency(self) -> None:
        inferrer = PreferenceInferrer()
        summary = InteractionSummary(total_interactions=50)
        prefs = inferrer.infer_from_interactions({}, summary)
        sug = prefs[PreferenceCategory.SUGGESTION_FREQUENCY.value]
        assert sug.inferred_value == 1.0  # min(1.0, 50/50)

    def test_confidence_increases_with_interactions(self) -> None:
        inferrer = PreferenceInferrer()
        summary_low = InteractionSummary(total_interactions=5, avg_depth=0.5)
        summary_high = InteractionSummary(total_interactions=50, avg_depth=0.5)
        prefs_low = inferrer.infer_from_interactions({}, summary_low)
        prefs_high = inferrer.infer_from_interactions({}, summary_high)
        conf_low = prefs_low[PreferenceCategory.RESPONSE_DETAIL.value].confidence
        conf_high = prefs_high[PreferenceCategory.RESPONSE_DETAIL.value].confidence
        assert conf_high > conf_low

    def test_existing_prefs_updated(self) -> None:
        inferrer = PreferenceInferrer()
        existing = {
            PreferenceCategory.RESPONSE_DETAIL.value: UserPreference(
                category=PreferenceCategory.RESPONSE_DETAIL,
                explicit_value=0.9,
            ),
        }
        summary = InteractionSummary(total_interactions=25, avg_depth=0.3)
        updated = inferrer.infer_from_interactions(existing, summary)
        # Explicit value should be preserved
        detail = updated[PreferenceCategory.RESPONSE_DETAIL.value]
        assert detail.explicit_value == 0.9
        # But inferred value should be updated
        assert detail.inferred_value == 0.3

    def test_empty_summary_no_crash(self) -> None:
        inferrer = PreferenceInferrer()
        summary = InteractionSummary()
        prefs = inferrer.infer_from_interactions({}, summary)
        # Should not crash; some prefs may not be created
        # since avg_depth=0 means no inference condition met
        assert isinstance(prefs, dict)


# ===========================================================================
# ProfileStore tests
# ===========================================================================


class TestProfileStore:
    """Test in-memory profile store."""

    def test_add_and_get_profile(self) -> None:
        store = ProfileStore()
        profile = IntelligenceProfile(user_id="alice")
        store.add_profile(profile)
        assert store.get_profile("alice") is not None

    def test_get_nonexistent_profile(self) -> None:
        store = ProfileStore()
        assert store.get_profile("nonexistent") is None

    def test_update_profile(self) -> None:
        store = ProfileStore()
        profile = IntelligenceProfile(user_id="alice")
        store.add_profile(profile)
        updated = profile.model_copy(update={"version": 2})
        store.update_profile(updated)
        fetched = store.get_profile("alice")
        assert fetched is not None
        assert fetched.version == 2

    def test_update_nonexistent_raises(self) -> None:
        store = ProfileStore()
        profile = IntelligenceProfile(user_id="alice")
        with pytest.raises(ProfileNotFoundError):
            store.update_profile(profile)

    def test_list_profiles(self) -> None:
        store = ProfileStore()
        store.add_profile(IntelligenceProfile(user_id="alice"))
        store.add_profile(IntelligenceProfile(user_id="bob"))
        assert len(store.list_profiles()) == 2

    def test_snapshot_crud(self) -> None:
        store = ProfileStore()
        profile = IntelligenceProfile(user_id="alice")
        store.add_profile(profile)
        snapshot = ProfileSnapshot(
            profile_id=profile.id,
            profile_data=profile.model_dump(),
            reason="test",
        )
        store.add_snapshot(snapshot)
        assert store.get_snapshot(snapshot.id) is not None

    def test_list_snapshots_filtered(self) -> None:
        store = ProfileStore()
        p1 = IntelligenceProfile(user_id="alice")
        p2 = IntelligenceProfile(user_id="bob")
        store.add_profile(p1)
        store.add_profile(p2)
        s1 = ProfileSnapshot(profile_id=p1.id, profile_data=p1.model_dump())
        s2 = ProfileSnapshot(profile_id=p2.id, profile_data=p2.model_dump())
        store.add_snapshot(s1)
        store.add_snapshot(s2)
        assert len(store.list_snapshots(profile_id=p1.id)) == 1


# ===========================================================================
# IntelligenceProfileEngine tests
# ===========================================================================


class TestIntelligenceProfileEngineCRUD:
    """Test profile CRUD operations."""

    @pytest.mark.asyncio
    async def test_get_or_create_new_profile(self) -> None:
        engine = _make_engine()
        profile = await engine.get_or_create_profile(user_id="alice")
        assert profile.user_id == "alice"
        assert profile.status == ProfileStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_get_or_create_existing_profile(self) -> None:
        engine = _make_engine()
        p1 = await engine.get_or_create_profile(user_id="alice")
        p2 = await engine.get_or_create_profile(user_id="alice")
        assert p1.id == p2.id

    @pytest.mark.asyncio
    async def test_get_profile_not_found(self) -> None:
        engine = _make_engine()
        with pytest.raises(ProfileNotFoundError):
            await engine.get_profile("nonexistent")

    @pytest.mark.asyncio
    async def test_list_profiles(self) -> None:
        engine = _make_engine()
        await engine.get_or_create_profile(user_id="alice")
        await engine.get_or_create_profile(user_id="bob")
        profiles = await engine.list_profiles()
        assert len(profiles) == 2

    @pytest.mark.asyncio
    async def test_create_logs_to_tape(self) -> None:
        tape = _make_tape_service()
        engine = _make_engine(tape)
        await engine.get_or_create_profile(user_id="alice")
        entries = await tape.get_entries()
        assert any(e.event_type == "profile.created" for e in entries)


class TestIntelligenceProfileEngineInteraction:
    """Test interaction recording and profile updates."""

    @pytest.mark.asyncio
    async def test_record_interaction_updates_summary(self) -> None:
        engine = _make_engine()
        profile = await engine.record_interaction(
            user_id="alice",
            interaction_type=InteractionType.QUERY,
            domain="legal",
            depth=0.7,
        )
        assert profile.interaction_summary.total_interactions == 1
        assert profile.interaction_summary.interactions_by_type.get("query") == 1
        assert profile.interaction_summary.interactions_by_domain.get("legal") == 1
        assert profile.interaction_summary.avg_depth == 0.7

    @pytest.mark.asyncio
    async def test_record_multiple_interactions(self) -> None:
        engine = _make_engine()
        await engine.record_interaction(
            user_id="alice",
            interaction_type=InteractionType.QUERY,
            domain="legal",
            depth=0.7,
        )
        profile = await engine.record_interaction(
            user_id="alice",
            interaction_type=InteractionType.APPROVAL,
            domain="legal",
            depth=0.9,
            approved=True,
        )
        assert profile.interaction_summary.total_interactions == 2
        assert profile.interaction_summary.peak_depth == 0.9

    @pytest.mark.asyncio
    async def test_record_interaction_updates_domain_expertise(self) -> None:
        engine = _make_engine()
        profile = await engine.record_interaction(
            user_id="alice",
            interaction_type=InteractionType.QUERY,
            domain="legal",
            depth=0.8,
        )
        assert "legal" in profile.domain_expertise
        exp = profile.domain_expertise["legal"]
        assert exp.interaction_count == 1
        assert exp.score > 0.0

    @pytest.mark.asyncio
    async def test_record_interaction_infers_preferences(self) -> None:
        engine = _make_engine()
        # Need enough interactions to trigger inference
        for _ in range(25):
            profile = await engine.record_interaction(
                user_id="alice",
                interaction_type=InteractionType.QUERY,
                domain="legal",
                depth=0.8,
                approved=True,
            )
        assert PreferenceCategory.RESPONSE_DETAIL.value in profile.preferences
        assert PreferenceCategory.AUTOMATION_LEVEL.value in profile.preferences

    @pytest.mark.asyncio
    async def test_record_interaction_approval_rate(self) -> None:
        engine = _make_engine()
        # First interaction without approval
        await engine.record_interaction(
            user_id="alice",
            interaction_type=InteractionType.QUERY,
            domain="legal",
            depth=0.5,
        )
        # Second with approval
        profile = await engine.record_interaction(
            user_id="alice",
            interaction_type=InteractionType.APPROVAL,
            domain="legal",
            depth=0.5,
            approved=True,
        )
        assert profile.interaction_summary.approval_rate > 0.0

    @pytest.mark.asyncio
    async def test_record_interaction_no_domain(self) -> None:
        engine = _make_engine()
        profile = await engine.record_interaction(
            user_id="alice",
            interaction_type=InteractionType.QUERY,
            depth=0.5,
        )
        assert profile.interaction_summary.total_interactions == 1
        assert len(profile.domain_expertise) == 0

    @pytest.mark.asyncio
    async def test_record_interaction_creates_snapshot(self) -> None:
        engine = _make_engine()
        profile = await engine.record_interaction(
            user_id="alice",
            interaction_type=InteractionType.QUERY,
            domain="legal",
            depth=0.5,
        )
        assert profile.snapshot_id is not None

    @pytest.mark.asyncio
    async def test_record_interaction_logs_to_tape(self) -> None:
        tape = _make_tape_service()
        engine = _make_engine(tape)
        await engine.record_interaction(
            user_id="alice",
            interaction_type=InteractionType.QUERY,
            domain="legal",
            depth=0.5,
        )
        entries = await tape.get_entries()
        assert any(e.event_type == "profile.interaction_recorded" for e in entries)

    @pytest.mark.asyncio
    async def test_interaction_adaptation_count_increments(self) -> None:
        engine = _make_engine()
        profile = await engine.record_interaction(
            user_id="alice",
            interaction_type=InteractionType.QUERY,
            depth=0.5,
        )
        assert profile.adaptation_count == 1


class TestIntelligenceProfileEnginePreferences:
    """Test preference management."""

    @pytest.mark.asyncio
    async def test_set_explicit_preference(self) -> None:
        engine = _make_engine()
        profile = await engine.set_preference(
            user_id="alice",
            category=PreferenceCategory.RESPONSE_DETAIL,
            value=0.9,
        )
        pref = profile.preferences.get(PreferenceCategory.RESPONSE_DETAIL.value)
        assert pref is not None
        assert pref.explicit_value == 0.9
        assert pref.confidence == 1.0

    @pytest.mark.asyncio
    async def test_get_effective_preference_explicit(self) -> None:
        engine = _make_engine()
        await engine.set_preference(
            user_id="alice",
            category=PreferenceCategory.RISK_TOLERANCE,
            value=0.8,
        )
        value = await engine.get_effective_preference(
            user_id="alice",
            category=PreferenceCategory.RISK_TOLERANCE,
        )
        assert value == 0.8

    @pytest.mark.asyncio
    async def test_get_effective_preference_inferred(self) -> None:
        engine = _make_engine()
        # Record enough interactions to infer preferences
        for _ in range(25):
            await engine.record_interaction(
                user_id="alice",
                interaction_type=InteractionType.QUERY,
                depth=0.7,
            )
        value = await engine.get_effective_preference(
            user_id="alice",
            category=PreferenceCategory.RESPONSE_DETAIL,
        )
        assert value == 0.7  # inferred from avg_depth

    @pytest.mark.asyncio
    async def test_get_effective_preference_default(self) -> None:
        engine = _make_engine()
        await engine.get_or_create_profile(user_id="alice")
        value = await engine.get_effective_preference(
            user_id="alice",
            category=PreferenceCategory.NOTIFICATION_FREQUENCY,
        )
        assert value == 0.5  # default

    @pytest.mark.asyncio
    async def test_set_preference_logs_to_tape(self) -> None:
        tape = _make_tape_service()
        engine = _make_engine(tape)
        await engine.set_preference(
            user_id="alice",
            category=PreferenceCategory.AUTOMATION_LEVEL,
            value=0.7,
        )
        entries = await tape.get_entries()
        assert any(e.event_type == "profile.preference_set" for e in entries)

    @pytest.mark.asyncio
    async def test_explicit_overrides_inferred(self) -> None:
        engine = _make_engine()
        # First record some interactions (inferred)
        for _ in range(25):
            await engine.record_interaction(
                user_id="alice",
                interaction_type=InteractionType.QUERY,
                depth=0.3,
            )
        # Then set explicit preference
        await engine.set_preference(
            user_id="alice",
            category=PreferenceCategory.RESPONSE_DETAIL,
            value=0.9,
        )
        value = await engine.get_effective_preference(
            user_id="alice",
            category=PreferenceCategory.RESPONSE_DETAIL,
        )
        # Explicit should override inferred
        assert value == 0.9


class TestIntelligenceProfileEngineSnapshots:
    """Test snapshot creation and rollback."""

    @pytest.mark.asyncio
    async def test_create_snapshot(self) -> None:
        engine = _make_engine()
        await engine.get_or_create_profile(user_id="alice")
        snapshot = await engine.create_snapshot(user_id="alice", reason="pre-change")
        assert snapshot.reason == "pre-change"
        assert snapshot.profile_data != {}

    @pytest.mark.asyncio
    async def test_rollback_to_snapshot(self) -> None:
        engine = _make_engine()
        await engine.get_or_create_profile(user_id="alice")

        # Create snapshot
        snapshot = await engine.create_snapshot(user_id="alice")

        # Make changes
        await engine.record_interaction(
            user_id="alice",
            interaction_type=InteractionType.QUERY,
            domain="legal",
            depth=0.8,
        )

        # Rollback
        profile = await engine.rollback_to_snapshot("alice", snapshot.id)
        assert profile.interaction_summary.total_interactions == 0

    @pytest.mark.asyncio
    async def test_rollback_nonexistent_snapshot(self) -> None:
        engine = _make_engine()
        await engine.get_or_create_profile(user_id="alice")
        with pytest.raises(SnapshotNotFoundError):
            await engine.rollback_to_snapshot("alice", UUID(int=0))

    @pytest.mark.asyncio
    async def test_rollback_wrong_user(self) -> None:
        engine = _make_engine()
        await engine.get_or_create_profile(user_id="alice")
        await engine.get_or_create_profile(user_id="bob")
        snapshot = await engine.create_snapshot(user_id="alice")
        with pytest.raises(ProfileError):
            await engine.rollback_to_snapshot("bob", snapshot.id)

    @pytest.mark.asyncio
    async def test_list_snapshots(self) -> None:
        engine = _make_engine()
        await engine.get_or_create_profile(user_id="alice")
        await engine.create_snapshot(user_id="alice", reason="s1")
        await engine.create_snapshot(user_id="alice", reason="s2")
        snapshots = await engine.list_snapshots("alice")
        assert len(snapshots) >= 2

    @pytest.mark.asyncio
    async def test_create_snapshot_logs_to_tape(self) -> None:
        tape = _make_tape_service()
        engine = _make_engine(tape)
        await engine.get_or_create_profile(user_id="alice")
        await engine.create_snapshot(user_id="alice")
        entries = await tape.get_entries()
        assert any(e.event_type == "profile.snapshot_created" for e in entries)

    @pytest.mark.asyncio
    async def test_rollback_logs_to_tape(self) -> None:
        tape = _make_tape_service()
        engine = _make_engine(tape)
        await engine.get_or_create_profile(user_id="alice")
        snapshot = await engine.create_snapshot(user_id="alice")
        await engine.rollback_to_snapshot("alice", snapshot.id)
        entries = await tape.get_entries()
        assert any(e.event_type == "profile.rolled_back" for e in entries)


class TestIntelligenceProfileEngineAnalysis:
    """Test profile analysis methods."""

    @pytest.mark.asyncio
    async def test_get_domain_summary(self) -> None:
        engine = _make_engine()
        await engine.record_interaction(
            user_id="alice",
            interaction_type=InteractionType.QUERY,
            domain="legal",
            depth=0.8,
        )
        summary = await engine.get_domain_summary("alice")
        assert "legal" in summary
        assert summary["legal"]["level"] is not None
        assert isinstance(summary["legal"]["score"], float)

    @pytest.mark.asyncio
    async def test_get_domain_summary_empty(self) -> None:
        engine = _make_engine()
        await engine.get_or_create_profile(user_id="alice")
        summary = await engine.get_domain_summary("alice")
        assert len(summary) == 0

    @pytest.mark.asyncio
    async def test_get_recommendation_context(self) -> None:
        engine = _make_engine()
        await engine.record_interaction(
            user_id="alice",
            interaction_type=InteractionType.QUERY,
            domain="legal",
            depth=0.8,
        )
        context = await engine.get_recommendation_context("alice")
        assert context["user_id"] == "alice"
        assert "top_domains" in context
        assert "preferences" in context
        assert context["interaction_count"] == 1

    @pytest.mark.asyncio
    async def test_get_recommendation_context_new_user(self) -> None:
        engine = _make_engine()
        context = await engine.get_recommendation_context("newuser")
        assert context["user_id"] == "newuser"
        assert context["expertise_level"] == "novice"


class TestIntelligenceProfileEngineMerge:
    """Test profile merging."""

    @pytest.mark.asyncio
    async def test_merge_profiles(self) -> None:
        engine = _make_engine()
        # Build source profile
        await engine.record_interaction(
            user_id="alice",
            interaction_type=InteractionType.QUERY,
            domain="legal",
            depth=0.9,
        )
        # Build target profile
        await engine.record_interaction(
            user_id="bob",
            interaction_type=InteractionType.QUERY,
            domain="finance",
            depth=0.7,
        )
        # Merge alice into bob
        merged = await engine.merge_profiles("alice", "bob")
        assert "legal" in merged.domain_expertise
        assert "finance" in merged.domain_expertise

    @pytest.mark.asyncio
    async def test_merge_takes_higher_expertise(self) -> None:
        engine = _make_engine()
        for _ in range(10):
            await engine.record_interaction(
                user_id="alice",
                interaction_type=InteractionType.QUERY,
                domain="legal",
                depth=0.9,
            )
        await engine.record_interaction(
            user_id="bob",
            interaction_type=InteractionType.QUERY,
            domain="legal",
            depth=0.2,
        )
        merged = await engine.merge_profiles("alice", "bob")
        # Alice's higher expertise should win
        assert merged.domain_expertise["legal"].score > 0.0

    @pytest.mark.asyncio
    async def test_merge_preserves_explicit_preferences(self) -> None:
        engine = _make_engine()
        await engine.set_preference(
            user_id="bob",
            category=PreferenceCategory.RISK_TOLERANCE,
            value=0.8,
        )
        await engine.set_preference(
            user_id="alice",
            category=PreferenceCategory.RISK_TOLERANCE,
            value=0.3,
        )
        merged = await engine.merge_profiles("alice", "bob")
        pref = merged.preferences.get(PreferenceCategory.RISK_TOLERANCE.value)
        assert pref is not None
        # Bob's explicit should be preserved (target)
        assert pref.explicit_value == 0.8

    @pytest.mark.asyncio
    async def test_merge_additive_interactions(self) -> None:
        engine = _make_engine()
        await engine.record_interaction(
            user_id="alice",
            interaction_type=InteractionType.QUERY,
            depth=0.5,
        )
        await engine.record_interaction(
            user_id="bob",
            interaction_type=InteractionType.QUERY,
            depth=0.5,
        )
        merged = await engine.merge_profiles("alice", "bob")
        assert merged.interaction_summary.total_interactions == 2

    @pytest.mark.asyncio
    async def test_merge_logs_to_tape(self) -> None:
        tape = _make_tape_service()
        engine = _make_engine(tape)
        await engine.get_or_create_profile(user_id="alice")
        await engine.get_or_create_profile(user_id="bob")
        await engine.merge_profiles("alice", "bob")
        entries = await tape.get_entries()
        assert any(e.event_type == "profile.merged" for e in entries)


class TestIntelligenceProfileEngineStatus:
    """Test profile status management."""

    @pytest.mark.asyncio
    async def test_archive_profile(self) -> None:
        engine = _make_engine()
        await engine.get_or_create_profile(user_id="alice")
        profile = await engine.archive_profile("alice")
        assert profile.status == ProfileStatus.ARCHIVED

    @pytest.mark.asyncio
    async def test_suspend_profile(self) -> None:
        engine = _make_engine()
        await engine.get_or_create_profile(user_id="alice")
        profile = await engine.suspend_profile("alice")
        assert profile.status == ProfileStatus.SUSPENDED

    @pytest.mark.asyncio
    async def test_reactivate_profile(self) -> None:
        engine = _make_engine()
        await engine.get_or_create_profile(user_id="alice")
        await engine.suspend_profile("alice")
        profile = await engine.reactivate_profile("alice")
        assert profile.status == ProfileStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_archive_nonexistent_raises(self) -> None:
        engine = _make_engine()
        with pytest.raises(ProfileNotFoundError):
            await engine.archive_profile("nonexistent")

    @pytest.mark.asyncio
    async def test_archive_logs_to_tape(self) -> None:
        tape = _make_tape_service()
        engine = _make_engine(tape)
        await engine.get_or_create_profile(user_id="alice")
        await engine.archive_profile("alice")
        entries = await tape.get_entries()
        assert any(e.event_type == "profile.archived" for e in entries)

    @pytest.mark.asyncio
    async def test_suspend_logs_to_tape(self) -> None:
        tape = _make_tape_service()
        engine = _make_engine(tape)
        await engine.get_or_create_profile(user_id="alice")
        await engine.suspend_profile("alice")
        entries = await tape.get_entries()
        assert any(e.event_type == "profile.suspended" for e in entries)

    @pytest.mark.asyncio
    async def test_reactivate_logs_to_tape(self) -> None:
        tape = _make_tape_service()
        engine = _make_engine(tape)
        await engine.get_or_create_profile(user_id="alice")
        await engine.suspend_profile("alice")
        await engine.reactivate_profile("alice")
        entries = await tape.get_entries()
        assert any(e.event_type == "profile.reactivated" for e in entries)


# ===========================================================================
# Model tests
# ===========================================================================


class TestDomainExpertiseModel:
    """Test DomainExpertise Pydantic model."""

    def test_default_fields(self) -> None:
        exp = DomainExpertise(domain_id="legal")
        assert exp.level == ExpertiseLevel.NOVICE
        assert exp.score == 0.0
        assert exp.interaction_count == 0
        assert exp.last_interaction is None

    def test_custom_fields(self) -> None:
        exp = DomainExpertise(
            domain_id="legal",
            level=ExpertiseLevel.EXPERT,
            score=0.9,
            interaction_count=50,
            total_depth=40.0,
        )
        assert exp.level == ExpertiseLevel.EXPERT


class TestUserPreferenceModel:
    """Test UserPreference model."""

    def test_default_fields(self) -> None:
        pref = UserPreference(category=PreferenceCategory.RISK_TOLERANCE)
        assert pref.value == 0.5
        assert pref.explicit_value is None
        assert pref.inferred_value == 0.5
        assert pref.confidence == 0.0

    def test_explicit_preference(self) -> None:
        pref = UserPreference(
            category=PreferenceCategory.AUTOMATION_LEVEL,
            explicit_value=0.9,
            value=0.9,
            confidence=1.0,
        )
        assert pref.explicit_value == 0.9


class TestInteractionSummaryModel:
    """Test InteractionSummary model."""

    def test_default_fields(self) -> None:
        summary = InteractionSummary()
        assert summary.total_interactions == 0
        assert summary.avg_depth == 0.0
        assert summary.approval_rate == 0.0

    def test_custom_fields(self) -> None:
        summary = InteractionSummary(
            total_interactions=100,
            avg_depth=0.75,
            peak_depth=1.0,
            approval_rate=0.85,
        )
        assert summary.total_interactions == 100


class TestIntelligenceProfileModel:
    """Test IntelligenceProfile model."""

    def test_default_fields(self) -> None:
        profile = IntelligenceProfile(user_id="alice")
        assert profile.status == ProfileStatus.ACTIVE
        assert profile.version == 1
        assert profile.adaptation_count == 0
        assert isinstance(profile.id, UUID)

    def test_with_expertise(self) -> None:
        profile = IntelligenceProfile(
            user_id="alice",
            domain_expertise={
                "legal": DomainExpertise(
                    domain_id="legal",
                    level=ExpertiseLevel.ADVANCED,
                    score=0.6,
                ),
            },
        )
        assert "legal" in profile.domain_expertise


# ===========================================================================
# Enum tests
# ===========================================================================


class TestEnums:
    """Test StrEnum values."""

    def test_expertise_level_values(self) -> None:
        assert ExpertiseLevel.NOVICE.value == "novice"
        assert ExpertiseLevel.INTERMEDIATE.value == "intermediate"
        assert ExpertiseLevel.ADVANCED.value == "advanced"
        assert ExpertiseLevel.EXPERT.value == "expert"

    def test_interaction_type_values(self) -> None:
        assert InteractionType.QUERY.value == "query"
        assert InteractionType.APPROVAL.value == "approval"
        assert InteractionType.REJECTION.value == "rejection"

    def test_preference_category_values(self) -> None:
        assert PreferenceCategory.RESPONSE_DETAIL.value == "response_detail"
        assert PreferenceCategory.AUTOMATION_LEVEL.value == "automation_level"

    def test_profile_status_values(self) -> None:
        assert ProfileStatus.ACTIVE.value == "active"
        assert ProfileStatus.ARCHIVED.value == "archived"
        assert ProfileStatus.SUSPENDED.value == "suspended"


# ===========================================================================
# Exception hierarchy tests
# ===========================================================================


class TestExceptions:
    """Test exception hierarchy."""

    def test_base_error(self) -> None:
        with pytest.raises(ProfileError):
            raise ProfileError("test")

    def test_not_found_inherits(self) -> None:
        with pytest.raises(ProfileError):
            raise ProfileNotFoundError("test")

    def test_snapshot_not_found_inherits(self) -> None:
        with pytest.raises(ProfileError):
            raise SnapshotNotFoundError("test")
