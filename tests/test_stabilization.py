"""Tests for LLM Planning, Historical Analysis, NLQ, and Auth modules."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from packages.auth import (
    AuthService,
    DuplicateUserError,
    InactiveUserError,
    InsufficientPermissionError,
    InvalidCredentialsError,
    TokenInvalidError,
    UserNotFoundError,
    UserRole,
)
from packages.prime.introspection import (
    HistoricalAnalyzer,
    PrimeIntrospector,
)
from packages.prime.llm_planning import (
    DecompositionStrategy,
    LLMPlanner,
    LLMProviderType,
    MockLLMProvider,
)
from packages.tape.nlq import (
    NLQueryParser,
    ParsedQuery,
    QueryIntent,
    RelevanceScorer,
    ResultSummarizer,
    SemanticTapeQueryEngine,
)
from packages.tape.repository import InMemoryTapeRepository
from packages.tape.service import TapeService


def _make_tape_service() -> TapeService:
    return TapeService(InMemoryTapeRepository())


# ===========================================================================
# LLM Planning tests
# ===========================================================================


class TestMockLLMProvider:
    @pytest.mark.asyncio
    async def test_decompose_error_goal(self) -> None:
        provider = MockLLMProvider()
        result = await provider.decompose("Fix system errors and bugs")
        assert len(result.steps) >= 3
        assert result.provider_type == LLMProviderType.MOCK
        assert result.overall_confidence > 0

    @pytest.mark.asyncio
    async def test_decompose_performance_goal(self) -> None:
        provider = MockLLMProvider()
        result = await provider.decompose("Improve system performance and speed")
        assert len(result.steps) >= 2

    @pytest.mark.asyncio
    async def test_decompose_migration_goal(self) -> None:
        provider = MockLLMProvider()
        result = await provider.decompose("Migrate database to new schema")
        assert len(result.steps) >= 2

    @pytest.mark.asyncio
    async def test_decompose_security_goal(self) -> None:
        provider = MockLLMProvider()
        result = await provider.decompose("Fix security vulnerabilities")
        assert len(result.steps) >= 2

    @pytest.mark.asyncio
    async def test_decompose_generic_goal(self) -> None:
        provider = MockLLMProvider()
        result = await provider.decompose("Something completely new and different")
        assert len(result.steps) >= 2

    @pytest.mark.asyncio
    async def test_decompose_respects_max_steps(self) -> None:
        provider = MockLLMProvider()
        result = await provider.decompose("Fix all the errors", max_steps=2)
        assert len(result.steps) <= 2

    @pytest.mark.asyncio
    async def test_step_confidence_in_range(self) -> None:
        provider = MockLLMProvider()
        result = await provider.decompose("Fix system errors")
        for step in result.steps:
            assert 0.0 <= step.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_step_has_reasoning(self) -> None:
        provider = MockLLMProvider()
        result = await provider.decompose("Fix system errors")
        assert all(s.reasoning for s in result.steps)


class TestLLMPlanner:
    @pytest.mark.asyncio
    async def test_decompose_goal_llm(self) -> None:
        tape = _make_tape_service()
        planner = LLMPlanner(tape_service=tape)
        result = await planner.decompose_goal(
            goal="Fix system errors",
            strategy=DecompositionStrategy.LLM,
        )
        assert len(result.steps) > 0
        assert result.strategy == DecompositionStrategy.LLM

    @pytest.mark.asyncio
    async def test_decompose_goal_heuristic(self) -> None:
        tape = _make_tape_service()
        planner = LLMPlanner(tape_service=tape)
        result = await planner.decompose_goal(
            goal="Fix system errors",
            strategy=DecompositionStrategy.HEURISTIC,
        )
        assert result.strategy == DecompositionStrategy.HEURISTIC

    @pytest.mark.asyncio
    async def test_decompose_goal_hybrid(self) -> None:
        tape = _make_tape_service()
        planner = LLMPlanner(tape_service=tape)
        result = await planner.decompose_goal(
            goal="Fix system errors",
            strategy=DecompositionStrategy.HYBRID,
        )
        assert result.strategy == DecompositionStrategy.HYBRID
        assert result.overall_confidence > 0

    @pytest.mark.asyncio
    async def test_decompose_empty_goal_raises(self) -> None:
        planner = LLMPlanner()
        with pytest.raises(ValueError):
            await planner.decompose_goal(goal="")

    @pytest.mark.asyncio
    async def test_decompose_logs_to_tape(self) -> None:
        tape = _make_tape_service()
        planner = LLMPlanner(tape_service=tape)
        await planner.decompose_goal(goal="Fix errors")
        entries = await tape.get_entries()
        assert any("llm_decomposition" in e.event_type for e in entries)

    @pytest.mark.asyncio
    async def test_should_use_llm_complex(self) -> None:
        planner = LLMPlanner()
        # Goals with "and" clause and no heuristic keywords should use LLM
        assert await planner.should_use_llm("Migrate architecture while improving security posture") is True

    @pytest.mark.asyncio
    async def test_should_use_llm_simple(self) -> None:
        planner = LLMPlanner()
        assert await planner.should_use_llm("Reduce error rate") is False

    @pytest.mark.asyncio
    async def test_list_decompositions(self) -> None:
        tape = _make_tape_service()
        planner = LLMPlanner(tape_service=tape)
        await planner.decompose_goal(goal="Goal 1")
        await planner.decompose_goal(goal="Goal 2")
        results = await planner.list_decompositions()
        assert len(results) >= 2


# ===========================================================================
# Historical Analysis tests
# ===========================================================================


class TestHistoricalAnalyzer:
    def test_bucket_by_time(self) -> None:
        from packages.tape.models import TapeEntry

        analyzer = HistoricalAnalyzer()
        now = datetime.now(UTC)
        entries = [
            TapeEntry(
                id=UUID(int=i + 1),
                timestamp=now - timedelta(hours=10 - i),
                event_type="test.event",
                agent_id="agent",
                payload={"i": i},
                metadata={},
            )
            for i in range(10)
        ]
        buckets = analyzer.bucket_by_time(entries, bucket_size_minutes=60)
        assert len(buckets) >= 1
        assert sum(b.event_count for b in buckets) == 10

    def test_bucket_empty(self) -> None:
        analyzer = HistoricalAnalyzer()
        assert len(analyzer.bucket_by_time([], 60)) == 0

    def test_rank_activity(self) -> None:
        from packages.tape.models import TapeEntry

        analyzer = HistoricalAnalyzer()
        now = datetime.now(UTC)
        entries = [
            TapeEntry(
                id=UUID(int=i + 1),
                timestamp=now,
                event_type="type_a" if i < 7 else "type_b",
                agent_id="agent_x" if i < 5 else "agent_y",
                payload={},
                metadata={},
            )
            for i in range(10)
        ]
        type_ranking, agent_ranking = analyzer.rank_activity(entries)
        assert type_ranking[0][0] == "type_a"
        assert agent_ranking[0][0] == "agent_x"

    def test_compute_trend_stable(self) -> None:
        from packages.tape.models import TapeEntry

        analyzer = HistoricalAnalyzer()
        now = datetime.now(UTC)
        entries: list[TapeEntry] = []
        for day in range(5):
            for _ in range(3):
                entries.append(
                    TapeEntry(
                        id=UUID(int=len(entries) + 1),
                        timestamp=now - timedelta(days=4 - day),
                        event_type="test.stable",
                        agent_id="agent",
                        payload={},
                        metadata={},
                    )
                )
        trend = analyzer._compute_trend("test.stable", entries)
        assert trend.direction in ("stable", "increasing")

    def test_detect_patterns_empty(self) -> None:
        analyzer = HistoricalAnalyzer()
        assert analyzer.detect_patterns([]) == []


class TestPrimeIntrospectorHistorical:
    @pytest.mark.asyncio
    async def test_historical_analysis(self) -> None:
        tape = _make_tape_service()
        introspector = PrimeIntrospector(tape_service=tape)
        for i in range(10):
            await tape.log_event(
                event_type=f"test.event_{i % 3}",
                payload={"i": i},
                agent_id="test-agent",
            )
        result = await introspector.historical_analysis()
        assert result.total_events_analysed >= 10

    @pytest.mark.asyncio
    async def test_temporal_query(self) -> None:
        tape = _make_tape_service()
        introspector = PrimeIntrospector(tape_service=tape)
        await tape.log_event(
            event_type="test.query_event",
            payload={},
            agent_id="test-agent",
        )
        entries = await introspector.temporal_query(
            event_type="test.query_event",
        )
        assert len(entries) >= 1


# ===========================================================================
# NLQ tests
# ===========================================================================


class TestNLQueryParser:
    def test_parse_what_intent(self) -> None:
        parser = NLQueryParser()
        assert parser.parse("What happened recently?").intent == QueryIntent.WHAT

    def test_parse_when_intent(self) -> None:
        parser = NLQueryParser()
        assert parser.parse("When did the plan complete?").intent == QueryIntent.WHEN

    def test_parse_how_many_intent(self) -> None:
        parser = NLQueryParser()
        assert parser.parse("How many errors occurred?").intent == QueryIntent.HOW_MANY

    def test_parse_latest_intent(self) -> None:
        parser = NLQueryParser()
        assert parser.parse("Show me the latest events").intent == QueryIntent.LATEST

    def test_parse_error_intent(self) -> None:
        parser = NLQueryParser()
        assert parser.parse("What errors have occurred?").intent == QueryIntent.ERRORS

    def test_parse_proposal_intent(self) -> None:
        parser = NLQueryParser()
        result = parser.parse("Show me all proposals that were rejected")
        assert result.intent == QueryIntent.PROPOSALS

    def test_parse_time_range_last_hour(self) -> None:
        parser = NLQueryParser()
        result = parser.parse("What happened in the last hour?")
        assert result.time_range_start is not None
        assert result.time_range_end is not None

    def test_parse_time_range_today(self) -> None:
        parser = NLQueryParser()
        result = parser.parse("What events occurred today?")
        assert result.time_range_start is not None

    def test_parse_event_type_detection(self) -> None:
        parser = NLQueryParser()
        result = parser.parse("Show me plan created events")
        assert "plan.created" in result.event_types

    def test_parse_keyword_extraction(self) -> None:
        parser = NLQueryParser()
        result = parser.parse("What errors occurred in the legal domain?")
        assert len(result.keywords) > 0

    def test_parse_negation(self) -> None:
        parser = NLQueryParser()
        result = parser.parse("What events are not from the test agent?")
        assert result.negation is True

    def test_parse_general_intent(self) -> None:
        parser = NLQueryParser()
        assert parser.parse("system status").intent == QueryIntent.GENERAL

    def test_parse_confidence(self) -> None:
        parser = NLQueryParser()
        result = parser.parse("How many errors occurred in the last hour?")
        assert result.confidence > 0.0


class TestRelevanceScorer:
    def test_score_event_type_match(self) -> None:
        from packages.tape.models import TapeEntry

        scorer = RelevanceScorer()
        entry = TapeEntry(
            id=UUID(int=1),
            timestamp=datetime.now(UTC),
            event_type="plan.step_failed",
            agent_id="agent",
            payload={"error": "test"},
            metadata={},
        )
        parsed = ParsedQuery(
            original_query="show me errors",
            intent=QueryIntent.ERRORS,
            event_types=["plan.step_failed"],
        )
        scored = scorer.score(entry, parsed)
        assert scored.relevance_score > 0.3

    def test_score_no_match(self) -> None:
        from packages.tape.models import TapeEntry

        scorer = RelevanceScorer()
        entry = TapeEntry(
            id=UUID(int=1),
            timestamp=datetime.now(UTC),
            event_type="plan.created",
            agent_id="agent",
            payload={},
            metadata={},
        )
        parsed = ParsedQuery(
            original_query="show me errors",
            intent=QueryIntent.ERRORS,
            event_types=["plan.step_failed"],
        )
        scored = scorer.score(entry, parsed)
        assert scored.relevance_score < 0.5


class TestResultSummarizer:
    def test_summarize_no_results(self) -> None:
        from packages.tape.nlq import QueryResult

        summarizer = ResultSummarizer()
        result = QueryResult(
            query="test",
            parsed=ParsedQuery(original_query="test"),
            entries=[],
            total_matches=0,
        )
        assert "No results" in summarizer.summarize(result)

    def test_summarize_how_many(self) -> None:
        from packages.tape.nlq import QueryResult

        summarizer = ResultSummarizer()
        result = QueryResult(
            query="how many",
            parsed=ParsedQuery(
                original_query="how many errors", intent=QueryIntent.HOW_MANY
            ),
            entries=[],
            total_matches=5,
        )
        assert "5" in summarizer.summarize(result)


class TestSemanticTapeQueryEngine:
    @pytest.mark.asyncio
    async def test_ask_simple_query(self) -> None:
        tape = _make_tape_service()
        await tape.log_event(
            event_type="plan.step_failed",
            payload={"error": "test"},
            agent_id="test-agent",
        )
        engine = SemanticTapeQueryEngine(tape_service=tape)
        result = await engine.ask("show me errors")
        assert result.summary != ""

    @pytest.mark.asyncio
    async def test_ask_empty_raises(self) -> None:
        tape = _make_tape_service()
        engine = SemanticTapeQueryEngine(tape_service=tape)
        with pytest.raises(ValueError):
            await engine.ask("")

    @pytest.mark.asyncio
    async def test_ask_logs_to_tape(self) -> None:
        tape = _make_tape_service()
        engine = SemanticTapeQueryEngine(tape_service=tape)
        await engine.ask("what happened recently?")
        entries = await tape.get_entries()
        assert any(e.event_type == "tape.nl_query" for e in entries)


# ===========================================================================
# Auth tests
# ===========================================================================


class TestAuthRegistration:
    @pytest.mark.asyncio
    async def test_register_user(self) -> None:
        svc = AuthService()
        user = await svc.register("alice", "password123")
        assert user.username == "alice"
        assert user.role == UserRole.VIEWER
        assert user.is_active is True

    @pytest.mark.asyncio
    async def test_register_with_role(self) -> None:
        svc = AuthService()
        user = await svc.register("admin1", "password123", role="admin")
        assert user.role == UserRole.ADMIN

    @pytest.mark.asyncio
    async def test_register_duplicate_raises(self) -> None:
        svc = AuthService()
        await svc.register("alice", "password123")
        with pytest.raises(DuplicateUserError):
            await svc.register("alice", "other_pass")

    @pytest.mark.asyncio
    async def test_register_empty_username_raises(self) -> None:
        svc = AuthService()
        with pytest.raises(ValueError):
            await svc.register("", "password123")

    @pytest.mark.asyncio
    async def test_register_short_password_raises(self) -> None:
        svc = AuthService()
        with pytest.raises(ValueError):
            await svc.register("alice", "abc")

    @pytest.mark.asyncio
    async def test_register_logs_to_tape(self) -> None:
        tape = _make_tape_service()
        svc = AuthService(tape_service=tape)
        await svc.register("alice", "password123")
        entries = await tape.get_entries()
        assert any(e.event_type == "auth.registered" for e in entries)


class TestAuthLogin:
    @pytest.mark.asyncio
    async def test_login_success(self) -> None:
        svc = AuthService()
        await svc.register("alice", "password123")
        token = await svc.login("alice", "password123")
        assert token.access_token != ""
        assert token.token_type == "bearer"
        assert token.refresh_token is not None

    @pytest.mark.asyncio
    async def test_login_wrong_password(self) -> None:
        svc = AuthService()
        await svc.register("alice", "password123")
        with pytest.raises(InvalidCredentialsError):
            await svc.login("alice", "wrong_password")

    @pytest.mark.asyncio
    async def test_login_unknown_user(self) -> None:
        svc = AuthService()
        with pytest.raises(InvalidCredentialsError):
            await svc.login("unknown", "password")

    @pytest.mark.asyncio
    async def test_login_inactive_user(self) -> None:
        svc = AuthService()
        await svc.register("alice", "password123")
        await svc.deactivate_user("alice")
        with pytest.raises(InactiveUserError):
            await svc.login("alice", "password123")

    @pytest.mark.asyncio
    async def test_login_updates_last_login(self) -> None:
        svc = AuthService()
        await svc.register("alice", "password123")
        await svc.login("alice", "password123")
        user = await svc.get_user("alice")
        assert user.last_login is not None

    @pytest.mark.asyncio
    async def test_login_logs_to_tape(self) -> None:
        tape = _make_tape_service()
        svc = AuthService(tape_service=tape)
        await svc.register("alice", "password123")
        await svc.login("alice", "password123")
        entries = await tape.get_entries()
        assert any(e.event_type == "auth.login" for e in entries)

    @pytest.mark.asyncio
    async def test_login_failed_logs_to_tape(self) -> None:
        tape = _make_tape_service()
        svc = AuthService(tape_service=tape)
        with pytest.raises(InvalidCredentialsError):
            await svc.login("nobody", "wrong")
        entries = await tape.get_entries()
        assert any(e.event_type == "auth.login_failed" for e in entries)


class TestAuthTokenValidation:
    @pytest.mark.asyncio
    async def test_validate_token(self) -> None:
        svc = AuthService()
        await svc.register("alice", "password123")
        token = await svc.login("alice", "password123")
        payload = await svc.validate_token(token.access_token)
        assert "sub" in payload
        assert "role" in payload

    @pytest.mark.asyncio
    async def test_get_current_user(self) -> None:
        svc = AuthService()
        await svc.register("alice", "password123")
        token = await svc.login("alice", "password123")
        user = await svc.get_current_user(token.access_token)
        assert user.username == "alice"

    @pytest.mark.asyncio
    async def test_invalid_token_raises(self) -> None:
        svc = AuthService()
        with pytest.raises(TokenInvalidError):
            await svc.validate_token("invalid.token.here")

    @pytest.mark.asyncio
    async def test_require_role_admin_sufficient(self) -> None:
        svc = AuthService()
        await svc.register("admin1", "password123", role="admin")
        token = await svc.login("admin1", "password123")
        user = await svc.require_role(token.access_token, UserRole.VIEWER)
        assert user.role == UserRole.ADMIN

    @pytest.mark.asyncio
    async def test_require_role_insufficient(self) -> None:
        svc = AuthService()
        await svc.register("viewer1", "password123", role="viewer")
        token = await svc.login("viewer1", "password123")
        with pytest.raises(InsufficientPermissionError):
            await svc.require_role(token.access_token, UserRole.ADMIN)


class TestAuthRefreshToken:
    @pytest.mark.asyncio
    async def test_refresh_token(self) -> None:
        svc = AuthService()
        await svc.register("alice", "password123")
        token = await svc.login("alice", "password123")
        assert token.refresh_token is not None
        new_token = await svc.refresh_token(token.refresh_token)
        assert new_token.access_token != ""
        assert new_token.refresh_token is not None

    @pytest.mark.asyncio
    async def test_refresh_token_single_use(self) -> None:
        svc = AuthService()
        await svc.register("alice", "password123")
        token = await svc.login("alice", "password123")
        assert token.refresh_token is not None
        await svc.refresh_token(token.refresh_token)
        with pytest.raises(TokenInvalidError):
            await svc.refresh_token(token.refresh_token)


class TestAuthUserManagement:
    @pytest.mark.asyncio
    async def test_change_password(self) -> None:
        svc = AuthService()
        await svc.register("alice", "password123")
        await svc.change_password("alice", "password123", "newpassword456")
        token = await svc.login("alice", "newpassword456")
        assert token.access_token != ""

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self) -> None:
        svc = AuthService()
        await svc.register("alice", "password123")
        with pytest.raises(InvalidCredentialsError):
            await svc.change_password("alice", "wrong", "newpassword456")

    @pytest.mark.asyncio
    async def test_change_role(self) -> None:
        svc = AuthService()
        await svc.register("alice", "password123")
        user = await svc.change_role("alice", "admin")
        assert user.role == UserRole.ADMIN

    @pytest.mark.asyncio
    async def test_deactivate_and_reactivate(self) -> None:
        svc = AuthService()
        await svc.register("alice", "password123")
        user = await svc.deactivate_user("alice")
        assert user.is_active is False
        user = await svc.reactivate_user("alice")
        assert user.is_active is True

    @pytest.mark.asyncio
    async def test_list_users(self) -> None:
        svc = AuthService()
        await svc.register("alice", "password123")
        await svc.register("bob", "password456")
        users = await svc.list_users()
        assert len(users) == 2

    @pytest.mark.asyncio
    async def test_get_user_not_found(self) -> None:
        svc = AuthService()
        with pytest.raises(UserNotFoundError):
            await svc.get_user("nonexistent")

    @pytest.mark.asyncio
    async def test_change_role_not_found(self) -> None:
        svc = AuthService()
        with pytest.raises(UserNotFoundError):
            await svc.change_role("nonexistent", "admin")

    @pytest.mark.asyncio
    async def test_password_change_logs_to_tape(self) -> None:
        tape = _make_tape_service()
        svc = AuthService(tape_service=tape)
        await svc.register("alice", "password123")
        await svc.change_password("alice", "password123", "newpassword456")
        entries = await tape.get_entries()
        assert any(e.event_type == "auth.password_changed" for e in entries)
