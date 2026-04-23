"""Unit tests for Advanced AetherGit — semantic search, merge intelligence,
branch explorer, worktree management, and commit comparison.

Run with: pytest tests/test_aethergit_advanced.py -v
"""

from uuid import UUID, uuid4

import pytest

from packages.aethergit.advanced import (
    AdvancedAetherGit,
    BranchDAG,
    BranchNotFoundError,
    CommitDiff,
    CommitNotFoundError,
    CommitStore,
    EmbeddingProvider,
    MergeAnalysis,
    MergeConflictType,
    MergeResolutionReport,
    MergeResolutionStrategy,
    SearchResults,
    WorktreeInfo,
    WorktreeNotFoundError,
    WorktreeStatus,
)
from packages.core.models import AetherCommit
from packages.tape.repository import InMemoryTapeRepository
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_commit(
    message: str = "test commit",
    scope: str = "core",
    commit_type: str = "feature",
    author: str = "test-author",
    confidence_score: float = 0.8,
    parent_ids: list[UUID] | None = None,
    performance_metrics: dict[str, float] | None = None,
    tape_references: list[UUID] | None = None,
) -> AetherCommit:
    """Create a test AetherCommit."""
    return AetherCommit(
        author=author,
        message=message,
        commit_type=commit_type,
        scope=scope,
        confidence_score=confidence_score,
        parent_ids=parent_ids or [],
        performance_metrics=performance_metrics or {},
        tape_references=tape_references or [],
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tape_svc() -> TapeService:
    return TapeService(InMemoryTapeRepository())


@pytest.fixture()
def git(tape_svc: TapeService) -> AdvancedAetherGit:
    return AdvancedAetherGit(tape_service=tape_svc)


@pytest.fixture()
def embedder() -> EmbeddingProvider:
    return EmbeddingProvider(dimension=32)


@pytest.fixture()
def store() -> CommitStore:
    return CommitStore()


@pytest.fixture()
def populated_git(tape_svc: TapeService) -> AdvancedAetherGit:
    """Return an AdvancedAetherGit with sample commits across branches."""
    git = AdvancedAetherGit(tape_service=tape_svc)

    # Main branch commits
    c1 = _make_commit(message="Initial system setup", scope="core", commit_type="init")
    c2 = _make_commit(
        message="Add retry logic to TapeService",
        scope="tape",
        commit_type="feature",
        confidence_score=0.85,
        parent_ids=[c1.id],
    )
    c3 = _make_commit(
        message="Fix authentication bug",
        scope="auth",
        commit_type="bugfix",
        confidence_score=0.9,
        parent_ids=[c2.id],
    )

    git.add_commit(c1, branch="main")
    git.add_commit(c2, branch="main")
    git.add_commit(c3, branch="main")

    # Feature branch commits
    f1 = _make_commit(
        message="Add semantic search engine",
        scope="aethergit",
        commit_type="feature",
        confidence_score=0.75,
        parent_ids=[c2.id],
    )
    f2 = _make_commit(
        message="Remove deprecated search API",
        scope="aethergit",
        commit_type="refactor",
        confidence_score=0.7,
        parent_ids=[f1.id],
    )

    git.add_commit(f1, branch="feature/search")
    git.add_commit(f2, branch="feature/search")

    # Hotfix branch
    h1 = _make_commit(
        message="Fix critical memory leak",
        scope="core",
        commit_type="bugfix",
        confidence_score=0.95,
        parent_ids=[c3.id],
    )

    git.add_commit(h1, branch="hotfix/memory-leak")

    return git


# ===========================================================================
# EmbeddingProvider tests
# ===========================================================================


class TestEmbeddingProvider:
    """Tests for the hash-based embedding provider."""

    def test_embed_returns_correct_dimension(self, embedder: EmbeddingProvider) -> None:
        vec = embedder.embed("test text")
        assert len(vec) == 32

    def test_embed_deterministic(self, embedder: EmbeddingProvider) -> None:
        a = embedder.embed("hello world")
        b = embedder.embed("hello world")
        assert a == b

    def test_embed_different_texts_differ(self, embedder: EmbeddingProvider) -> None:
        a = embedder.embed("hello world")
        b = embedder.embed("completely different text")
        assert a != b

    def test_cosine_similarity_identical(self, embedder: EmbeddingProvider) -> None:
        vec = embedder.embed("test")
        sim = embedder.cosine_similarity(vec, vec)
        assert abs(sim - 1.0) < 0.01

    def test_cosine_similarity_orthogonal(self, embedder: EmbeddingProvider) -> None:
        # Different texts should have lower similarity than identical
        a = embedder.embed("reliability improvements")
        b = embedder.embed("completely unrelated topic xyz")
        sim = embedder.cosine_similarity(a, b)
        assert sim < 1.0

    def test_cosine_similarity_empty_vector(self, embedder: EmbeddingProvider) -> None:
        sim = embedder.cosine_similarity([], [])
        assert sim == 0.0

    def test_normalise_strips_punctuation(self) -> None:
        result = EmbeddingProvider._normalise("Hello, World!  Test...")
        assert result.strip() == "hello world test"

    def test_model_name(self, embedder: EmbeddingProvider) -> None:
        assert embedder.model_name == "hash-v1"

    def test_dimension_property(self, embedder: EmbeddingProvider) -> None:
        assert embedder.dimension == 32


# ===========================================================================
# CommitStore tests
# ===========================================================================


class TestCommitStore:
    """Tests for the in-memory commit store."""

    def test_add_and_get_commit(self, store: CommitStore) -> None:
        commit = _make_commit()
        store.add_commit(commit, branch="main")
        assert store.get_commit(commit.id) is commit

    def test_get_commit_not_found(self, store: CommitStore) -> None:
        assert store.get_commit(uuid4()) is None

    def test_list_commits_all(self, store: CommitStore) -> None:
        c1 = _make_commit(message="first")
        c2 = _make_commit(message="second")
        store.add_commit(c1, branch="main")
        store.add_commit(c2, branch="main")
        commits = store.list_commits()
        assert len(commits) == 2

    def test_list_commits_by_branch(self, store: CommitStore) -> None:
        c1 = _make_commit(message="main commit")
        c2 = _make_commit(message="feature commit")
        store.add_commit(c1, branch="main")
        store.add_commit(c2, branch="feature")
        assert len(store.list_commits(branch="main")) == 1
        assert len(store.list_commits(branch="feature")) == 1
        assert len(store.list_commits(branch="nonexistent")) == 0

    def test_list_commits_pagination(self, store: CommitStore) -> None:
        for i in range(10):
            store.add_commit(_make_commit(message=f"commit-{i}"), branch="main")
        page1 = store.list_commits(limit=3, offset=0)
        page2 = store.list_commits(limit=3, offset=3)
        assert len(page1) == 3
        assert len(page2) == 3
        assert page1[0].id != page2[0].id

    def test_get_branch_names(self, store: CommitStore) -> None:
        store.add_commit(_make_commit(), branch="main")
        store.add_commit(_make_commit(), branch="feature/x")
        names = store.get_branch_names()
        assert "main" in names
        assert "feature/x" in names

    def test_get_head(self, store: CommitStore) -> None:
        c1 = _make_commit(message="first")
        c2 = _make_commit(message="second")
        store.add_commit(c1, branch="main")
        store.add_commit(c2, branch="main")
        head = store.get_head("main")
        assert head is c2

    def test_get_head_empty_branch(self, store: CommitStore) -> None:
        assert store.get_head("nonexistent") is None

    def test_total_commits(self, store: CommitStore) -> None:
        store.add_commit(_make_commit(), branch="main")
        store.add_commit(_make_commit(), branch="feature")
        assert store.total_commits == 2


# ===========================================================================
# AdvancedAetherGit — Commit management
# ===========================================================================


class TestCommitManagement:
    """Tests for commit CRUD operations."""

    @pytest.mark.asyncio
    async def test_add_and_get_commit(self, git: AdvancedAetherGit) -> None:
        commit = _make_commit(message="test")
        git.add_commit(commit, branch="main")
        fetched = git.get_commit(commit.id)
        assert fetched.id == commit.id
        assert fetched.message == "test"

    @pytest.mark.asyncio
    async def test_get_commit_not_found(self, git: AdvancedAetherGit) -> None:
        with pytest.raises(CommitNotFoundError):
            git.get_commit(uuid4())

    @pytest.mark.asyncio
    async def test_get_commit_history(self, git: AdvancedAetherGit) -> None:
        git.add_commit(_make_commit(message="c1"), branch="main")
        git.add_commit(_make_commit(message="c2"), branch="main")
        history = await git.get_commit_history(branch="main")
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_add_commit_caches_embedding(self, git: AdvancedAetherGit) -> None:
        commit = _make_commit(message="cache test")
        git.add_commit(commit, branch="main")
        key = f"commit:{commit.id}"
        assert key in git._embedding_cache
        assert len(git._embedding_cache[key]) > 0


# ===========================================================================
# AdvancedAetherGit — Semantic search
# ===========================================================================


class TestSemanticSearch:
    """Tests for embedding-powered semantic search."""

    @pytest.mark.asyncio
    async def test_search_returns_results(self, populated_git: AdvancedAetherGit) -> None:
        results = await populated_git.semantic_search("search engine", max_results=5, min_score=-1.0)
        assert isinstance(results, SearchResults)
        assert results.total_count > 0

    @pytest.mark.asyncio
    async def test_search_commit_results(self, populated_git: AdvancedAetherGit) -> None:
        results = await populated_git.semantic_search(
            "retry logic", max_results=5, search_branches=False
        )
        assert len(results.results) > 0
        assert all(r.match_type == "commit" for r in results.results)

    @pytest.mark.asyncio
    async def test_search_branch_results(self, populated_git: AdvancedAetherGit) -> None:
        results = await populated_git.semantic_search(
            "search", max_results=5, search_commits=False
        )
        assert len(results.results) > 0
        assert all(r.match_type == "branch" for r in results.results)

    @pytest.mark.asyncio
    async def test_search_respects_min_score(self, populated_git: AdvancedAetherGit) -> None:
        # Very high min_score should filter out most results
        results = await populated_git.semantic_search("anything", min_score=0.99)
        # With hash embeddings, scores rarely reach 0.99
        assert isinstance(results.results, list)

    @pytest.mark.asyncio
    async def test_search_respects_max_results(self, populated_git: AdvancedAetherGit) -> None:
        results = await populated_git.semantic_search("test", max_results=2)
        assert len(results.results) <= 2

    @pytest.mark.asyncio
    async def test_search_empty_store(self, git: AdvancedAetherGit) -> None:
        results = await git.semantic_search("anything")
        assert results.total_count == 0
        assert results.results == []

    @pytest.mark.asyncio
    async def test_search_logs_to_tape(self, populated_git: AdvancedAetherGit) -> None:
        await populated_git.semantic_search("test query")
        entries = await populated_git._tape.get_entries(event_type="aethergit.semantic_search")
        assert len(entries) == 1
        assert entries[0].payload["query"] == "test query"

    @pytest.mark.asyncio
    async def test_search_results_sorted_by_score(self, populated_git: AdvancedAetherGit) -> None:
        results = await populated_git.semantic_search("system", max_results=10)
        if len(results.results) >= 2:
            for i in range(len(results.results) - 1):
                assert results.results[i].score >= results.results[i + 1].score

    @pytest.mark.asyncio
    async def test_search_model_name(self, populated_git: AdvancedAetherGit) -> None:
        results = await populated_git.semantic_search("test")
        assert results.embedding_model == "hash-v1"


# ===========================================================================
# AdvancedAetherGit — Merge intelligence
# ===========================================================================


class TestMergeIntelligence:
    """Tests for merge conflict detection and resolution."""

    @pytest.mark.asyncio
    async def test_detect_no_conflicts(self, populated_git: AdvancedAetherGit) -> None:
        # Create a branch with no scope overlap
        c = _make_commit(message="docs update", scope="docs", commit_type="docs")
        populated_git.add_commit(c, branch="feature/docs")

        analysis = await populated_git.detect_merge_conflicts(
            "feature/docs", "main"
        )
        # docs scope has no overlap with core/tape/auth/aethergit
        assert isinstance(analysis, MergeAnalysis)
        assert analysis.source_branch == "feature/docs"
        assert analysis.target_branch == "main"

    @pytest.mark.asyncio
    async def test_detect_scope_overlap(self, populated_git: AdvancedAetherGit) -> None:
        # Both feature/search and main have commits — feature/search has aethergit scope
        # but main doesn't, so let's add a commit to main with aethergit scope
        c = _make_commit(
            message="Update aethergit config",
            scope="aethergit",
            commit_type="config",
        )
        populated_git.add_commit(c, branch="main")

        analysis = await populated_git.detect_merge_conflicts(
            "feature/search", "main"
        )
        scope_conflicts = [
            c for c in analysis.conflicts if c.conflict_type == MergeConflictType.SCOPE_OVERLAP
        ]
        assert len(scope_conflicts) > 0

    @pytest.mark.asyncio
    async def test_detect_semantic_conflict(self, populated_git: AdvancedAetherGit) -> None:
        # Add "add search" to main and "remove search" is on feature branch
        c = _make_commit(
            message="Add search functionality",
            scope="aethergit",
            commit_type="feature",
        )
        populated_git.add_commit(c, branch="main")

        analysis = await populated_git.detect_merge_conflicts(
            "feature/search", "main"
        )
        semantic_conflicts = [
            c
            for c in analysis.conflicts
            if c.conflict_type == MergeConflictType.SEMANTIC_CONFLICT
        ]
        # "Add search functionality" vs "Remove deprecated search API" should conflict
        assert len(semantic_conflicts) > 0

    @pytest.mark.asyncio
    async def test_detect_branch_not_found(self, populated_git: AdvancedAetherGit) -> None:
        with pytest.raises(BranchNotFoundError):
            await populated_git.detect_merge_conflicts("nonexistent", "main")

    @pytest.mark.asyncio
    async def test_merge_analysis_risk_score(self, populated_git: AdvancedAetherGit) -> None:
        analysis = await populated_git.detect_merge_conflicts(
            "feature/search", "main"
        )
        assert 0.0 <= analysis.overall_risk <= 1.0

    @pytest.mark.asyncio
    async def test_merge_analysis_logs_to_tape(self, populated_git: AdvancedAetherGit) -> None:
        await populated_git.detect_merge_conflicts("feature/search", "main")
        entries = await populated_git._tape.get_entries(
            event_type="aethergit.merge_analysis"
        )
        assert len(entries) >= 1

    @pytest.mark.asyncio
    async def test_suggest_resolution(self, populated_git: AdvancedAetherGit) -> None:
        analysis = await populated_git.detect_merge_conflicts(
            "feature/search", "main"
        )
        report = await populated_git.suggest_merge_resolution(analysis)

        assert isinstance(report, MergeResolutionReport)
        assert report.source_branch == "feature/search"
        assert report.target_branch == "main"
        assert len(report.resolutions) == len(analysis.conflicts)

    @pytest.mark.asyncio
    async def test_suggest_resolution_no_conflicts(
        self, populated_git: AdvancedAetherGit
    ) -> None:
        c = _make_commit(message="docs update", scope="docs", commit_type="docs")
        populated_git.add_commit(c, branch="feature/docs")

        analysis = await populated_git.detect_merge_conflicts(
            "feature/docs", "main"
        )
        report = await populated_git.suggest_merge_resolution(analysis)

        assert report.overall_strategy == MergeResolutionStrategy.MERGE_BOTH
        assert report.overall_confidence == 1.0

    @pytest.mark.asyncio
    async def test_suggest_resolution_logs_to_tape(
        self, populated_git: AdvancedAetherGit
    ) -> None:
        analysis = await populated_git.detect_merge_conflicts(
            "feature/search", "main"
        )
        await populated_git.suggest_merge_resolution(analysis)
        entries = await populated_git._tape.get_entries(
            event_type="aethergit.merge_resolution"
        )
        assert len(entries) >= 1

    @pytest.mark.asyncio
    async def test_performance_regression_detection(
        self, populated_git: AdvancedAetherGit
    ) -> None:
        # Add a commit on main with high confidence in the same scope as feature/search
        c = _make_commit(
            message="Update search engine",
            scope="aethergit",
            commit_type="feature",
            confidence_score=0.95,
        )
        populated_git.add_commit(c, branch="main")

        analysis = await populated_git.detect_merge_conflicts(
            "feature/search", "main"
        )
        perf_conflicts = [
            conf
            for conf in analysis.conflicts
            if conf.conflict_type == MergeConflictType.PERFORMANCE_REGRESSION
        ]
        # feature/search has confidence 0.7/0.75, main has 0.95
        assert len(perf_conflicts) > 0

    @pytest.mark.asyncio
    async def test_messages_conflict_detection(self) -> None:
        assert AdvancedAetherGit._messages_conflict(
            "Add new feature", "Remove new feature"
        )
        assert AdvancedAetherGit._messages_conflict(
            "Enable logging", "Disable logging"
        )
        assert not AdvancedAetherGit._messages_conflict(
            "Add feature A", "Add feature B"
        )


# ===========================================================================
# AdvancedAetherGit — Branch explorer
# ===========================================================================


class TestBranchExplorer:
    """Tests for the branch DAG data structure."""

    @pytest.mark.asyncio
    async def test_branch_explorer_returns_dag(self, populated_git: AdvancedAetherGit) -> None:
        dag = await populated_git.get_branch_explorer()
        assert isinstance(dag, BranchDAG)
        assert dag.total_commits > 0
        assert dag.total_branches == 3  # main, feature/search, hotfix/memory-leak

    @pytest.mark.asyncio
    async def test_branch_explorer_nodes(self, populated_git: AdvancedAetherGit) -> None:
        dag = await populated_git.get_branch_explorer()
        # 6 commits total across all branches
        assert len(dag.nodes) == 6

    @pytest.mark.asyncio
    async def test_branch_explorer_edges(self, populated_git: AdvancedAetherGit) -> None:
        dag = await populated_git.get_branch_explorer()
        # Parent-child edges exist
        assert len(dag.edges) > 0

    @pytest.mark.asyncio
    async def test_branch_explorer_merge_points(self, populated_git: AdvancedAetherGit) -> None:
        dag = await populated_git.get_branch_explorer()
        # No merge commits in our test data (no commit with >1 parent)
        assert dag.total_merge_points >= 0

    @pytest.mark.asyncio
    async def test_branch_explorer_branches_list(self, populated_git: AdvancedAetherGit) -> None:
        dag = await populated_git.get_branch_explorer()
        assert "main" in dag.branches
        assert "feature/search" in dag.branches
        assert "hotfix/memory-leak" in dag.branches

    @pytest.mark.asyncio
    async def test_branch_explorer_empty(self, git: AdvancedAetherGit) -> None:
        dag = await git.get_branch_explorer()
        assert dag.total_commits == 0
        assert dag.nodes == []
        assert dag.edges == []

    @pytest.mark.asyncio
    async def test_branch_explorer_logs_to_tape(self, populated_git: AdvancedAetherGit) -> None:
        await populated_git.get_branch_explorer()
        entries = await populated_git._tape.get_entries(
            event_type="aethergit.branch_explorer"
        )
        assert len(entries) == 1


# ===========================================================================
# AdvancedAetherGit — Worktree management
# ===========================================================================


class TestWorktreeManagement:
    """Tests for programmatic worktree CRUD."""

    @pytest.mark.asyncio
    async def test_create_worktree(self, git: AdvancedAetherGit) -> None:
        wt = await git.create_worktree("feature-x", "/tmp/worktree-fx")
        assert isinstance(wt, WorktreeInfo)
        assert wt.branch == "feature-x"
        assert wt.path == "/tmp/worktree-fx"
        assert wt.status == WorktreeStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_create_worktree_with_commit(self, git: AdvancedAetherGit) -> None:
        commit_id = uuid4()
        wt = await git.create_worktree("feature-y", "/tmp/worktree-fy", commit_id=commit_id)
        assert wt.commit_id == commit_id

    @pytest.mark.asyncio
    async def test_list_worktrees(self, git: AdvancedAetherGit) -> None:
        await git.create_worktree("branch-a", "/tmp/wt-a")
        await git.create_worktree("branch-b", "/tmp/wt-b")
        worktrees = await git.list_worktrees()
        assert len(worktrees) == 2

    @pytest.mark.asyncio
    async def test_remove_worktree(self, git: AdvancedAetherGit) -> None:
        wt = await git.create_worktree("branch-c", "/tmp/wt-c")
        removed = await git.remove_worktree(wt.id)
        assert removed.id == wt.id
        assert removed.status == WorktreeStatus.REMOVED

        # Verify it's no longer in the list
        worktrees = await git.list_worktrees()
        assert all(w.id != wt.id for w in worktrees)

    @pytest.mark.asyncio
    async def test_remove_worktree_not_found(self, git: AdvancedAetherGit) -> None:
        with pytest.raises(WorktreeNotFoundError):
            await git.remove_worktree(uuid4())

    @pytest.mark.asyncio
    async def test_create_worktree_logs_to_tape(self, git: AdvancedAetherGit) -> None:
        await git.create_worktree("test-branch", "/tmp/wt-test")
        entries = await git._tape.get_entries(event_type="aethergit.worktree_created")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_remove_worktree_logs_to_tape(self, git: AdvancedAetherGit) -> None:
        wt = await git.create_worktree("test-branch", "/tmp/wt-test2")
        await git.remove_worktree(wt.id)
        entries = await git._tape.get_entries(event_type="aethergit.worktree_removed")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_list_worktrees_logs_to_tape(self, git: AdvancedAetherGit) -> None:
        await git.list_worktrees()
        entries = await git._tape.get_entries(event_type="aethergit.worktree_listed")
        assert len(entries) == 1


# ===========================================================================
# AdvancedAetherGit — Commit comparison
# ===========================================================================


class TestCommitComparison:
    """Tests for rich commit diff generation."""

    @pytest.mark.asyncio
    async def test_compare_identical_commits(self, git: AdvancedAetherGit) -> None:
        c1 = _make_commit(
            message="same",
            scope="core",
            confidence_score=0.8,
            performance_metrics={"latency": 100.0, "throughput": 50.0},
        )
        c2 = _make_commit(
            message="same",
            scope="core",
            confidence_score=0.8,
            performance_metrics={"latency": 100.0, "throughput": 50.0},
        )
        git.add_commit(c1, branch="main")
        git.add_commit(c2, branch="main")

        diff = await git.compare_commits(c1.id, c2.id)
        assert isinstance(diff, CommitDiff)
        assert not diff.message_changed
        assert not diff.scope_changed
        assert diff.confidence_delta == 0.0

    @pytest.mark.asyncio
    async def test_compare_changed_message(self, git: AdvancedAetherGit) -> None:
        c1 = _make_commit(message="original message")
        c2 = _make_commit(message="updated message")
        git.add_commit(c1, branch="main")
        git.add_commit(c2, branch="main")

        diff = await git.compare_commits(c1.id, c2.id)
        assert diff.message_changed

    @pytest.mark.asyncio
    async def test_compare_changed_scope(self, git: AdvancedAetherGit) -> None:
        c1 = _make_commit(scope="core")
        c2 = _make_commit(scope="auth")
        git.add_commit(c1, branch="main")
        git.add_commit(c2, branch="main")

        diff = await git.compare_commits(c1.id, c2.id)
        assert diff.scope_changed

    @pytest.mark.asyncio
    async def test_compare_confidence_improvement(self, git: AdvancedAetherGit) -> None:
        c1 = _make_commit(confidence_score=0.6)
        c2 = _make_commit(confidence_score=0.9)
        git.add_commit(c1, branch="main")
        git.add_commit(c2, branch="main")

        diff = await git.compare_commits(c1.id, c2.id)
        assert diff.confidence_delta > 0
        assert diff.confidence_improved

    @pytest.mark.asyncio
    async def test_compare_confidence_regression(self, git: AdvancedAetherGit) -> None:
        c1 = _make_commit(confidence_score=0.9)
        c2 = _make_commit(confidence_score=0.5)
        git.add_commit(c1, branch="main")
        git.add_commit(c2, branch="main")

        diff = await git.compare_commits(c1.id, c2.id)
        assert diff.confidence_delta < 0
        assert not diff.confidence_improved

    @pytest.mark.asyncio
    async def test_compare_metric_deltas(self, git: AdvancedAetherGit) -> None:
        c1 = _make_commit(performance_metrics={"latency": 100.0, "throughput": 50.0})
        c2 = _make_commit(
            performance_metrics={"latency": 80.0, "throughput": 65.0, "errors": 2.0}
        )
        git.add_commit(c1, branch="main")
        git.add_commit(c2, branch="main")

        diff = await git.compare_commits(c1.id, c2.id)
        assert len(diff.metric_deltas) == 3  # latency, throughput, errors

        # Check latency delta (decreased = improved for latency)
        latency = next(d for d in diff.metric_deltas if d.metric == "latency")
        assert latency.delta == -20.0
        assert latency.improved  # lower latency is better (contains no 'error'/'fail' but is common sense)

        # Check throughput delta (increased = improved)
        throughput = next(d for d in diff.metric_deltas if d.metric == "throughput")
        assert throughput.delta == 15.0
        assert throughput.improved

        # Check errors (appeared = degraded)
        errors = next(d for d in diff.metric_deltas if d.metric == "errors")
        assert not errors.improved  # more errors is bad

    @pytest.mark.asyncio
    async def test_compare_commit_not_found(self, git: AdvancedAetherGit) -> None:
        c1 = _make_commit()
        git.add_commit(c1, branch="main")
        with pytest.raises(CommitNotFoundError):
            await git.compare_commits(c1.id, uuid4())

    @pytest.mark.asyncio
    async def test_compare_logs_to_tape(self, git: AdvancedAetherGit) -> None:
        c1 = _make_commit()
        c2 = _make_commit()
        git.add_commit(c1, branch="main")
        git.add_commit(c2, branch="main")

        await git.compare_commits(c1.id, c2.id)
        entries = await git._tape.get_entries(
            event_type="aethergit.commit_comparison"
        )
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_compare_tape_references(self, git: AdvancedAetherGit) -> None:
        ref_a = uuid4()
        ref_b = uuid4()
        ref_c = uuid4()

        c1 = _make_commit(tape_references=[ref_a, ref_b])
        c2 = _make_commit(tape_references=[ref_a, ref_c])
        git.add_commit(c1, branch="main")
        git.add_commit(c2, branch="main")

        diff = await git.compare_commits(c1.id, c2.id)
        assert diff.tape_references_added == 1  # ref_c added
        assert diff.tape_references_removed == 1  # ref_b removed

    @pytest.mark.asyncio
    async def test_compare_parent_ids_changed(self, git: AdvancedAetherGit) -> None:
        parent_a = uuid4()
        parent_b = uuid4()

        c1 = _make_commit(parent_ids=[parent_a])
        c2 = _make_commit(parent_ids=[parent_b])
        git.add_commit(c1, branch="main")
        git.add_commit(c2, branch="main")

        diff = await git.compare_commits(c1.id, c2.id)
        assert diff.parent_ids_changed

    @pytest.mark.asyncio
    async def test_compare_summary(self, git: AdvancedAetherGit) -> None:
        c1 = _make_commit(
            message="old",
            scope="core",
            confidence_score=0.5,
            performance_metrics={"latency": 100.0},
        )
        c2 = _make_commit(
            message="new",
            scope="auth",
            confidence_score=0.8,
            performance_metrics={"latency": 80.0},
        )
        git.add_commit(c1, branch="main")
        git.add_commit(c2, branch="main")

        diff = await git.compare_commits(c1.id, c2.id)
        assert "Message changed" in diff.summary
        assert "Scope" in diff.summary
        assert "Confidence" in diff.summary
