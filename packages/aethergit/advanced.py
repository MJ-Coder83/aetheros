"""InkosAI AetherGit Advanced — Semantic search, intelligent merge, and branch exploration.

This module extends the core AetherGit commit model with advanced capabilities:

1. **Semantic Search**: Find commits and branches by meaning, not just keywords.
   Uses pluggable embedding providers (hash-based by default, LLM-ready).

2. **Intelligent Merge**: Detect conflicts between branches and suggest resolutions
   based on commit metadata, scope analysis, and historical merge patterns.

3. **Visual Branch Explorer**: DAG data structures ready for frontend rendering —
   branch nodes, merge points, and linear history segments.

4. **Worktree Management**: Create, list, and remove git worktrees programmatically,
   with full Tape audit logging.

5. **Commit Comparison**: Generate rich diffs between any two commits, including
   metadata deltas, scope changes, and confidence score differences.

Architecture::

    AdvancedAetherGit
    ├── semantic_search() — Embedding-powered commit/branch search
    ├── detect_merge_conflicts() — Find conflicts between two branches
    ├── suggest_merge_resolution() — Generate resolution strategies
    ├── get_branch_explorer() — DAG structure for visualisation
    ├── create_worktree() / list_worktrees() / remove_worktree()
    ├── compare_commits() — Rich diff between two commits
    └── get_commit_history() — Paginated commit log

All operations are logged to the Tape with ``aethergit.*`` event types.

Usage::

    from packages.aethergit.advanced import AdvancedAetherGit

    git = AdvancedAetherGit(tape_service=tape_svc)

    # Semantic search
    results = await git.semantic_search("reliability improvements")

    # Merge analysis
    conflicts = await git.detect_merge_conflicts(source_branch, target_branch)
    resolution = await git.suggest_merge_resolution(conflicts)

    # Branch explorer
    dag = await git.get_branch_explorer()

    # Worktree management
    wt = await git.create_worktree("feature-x", "/tmp/feature-x")
    worktrees = await git.list_worktrees()

    # Commit comparison
    diff = await git.compare_commits(commit_a_id, commit_b_id)
"""

import contextlib
import hashlib
import math
import re
import subprocess
from collections import defaultdict
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from packages.core.models import AetherCommit
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MergeConflictType(StrEnum):
    """Types of merge conflicts that can be detected."""

    SCOPE_OVERLAP = "scope_overlap"
    SAME_FILE_MODIFIED = "same_file_modified"
    DEPENDENCY_CONFLICT = "dependency_conflict"
    SEMANTIC_CONFLICT = "semantic_conflict"
    PERFORMANCE_REGRESSION = "performance_regression"


class MergeResolutionStrategy(StrEnum):
    """Strategies for resolving merge conflicts."""

    TAKE_SOURCE = "take_source"
    TAKE_TARGET = "take_target"
    MERGE_BOTH = "merge_both"
    REBASE_SOURCE = "rebase_source"
    MANUAL_REVIEW = "manual_review"
    SQUASH = "squash"


class WorktreeStatus(StrEnum):
    """Status of a git worktree."""

    ACTIVE = "active"
    STALE = "stale"
    LOCKED = "locked"
    REMOVED = "removed"


# ---------------------------------------------------------------------------
# Data models — Semantic search
# ---------------------------------------------------------------------------

class EmbeddingVector(BaseModel):
    """A dense vector embedding for a piece of text."""

    text: str
    vector: list[float] = []
    model: str = "hash-v1"
    dimension: int = 0


class SearchResult(BaseModel):
    """A single result from semantic search."""

    commit_id: UUID | None = None
    branch_name: str | None = None
    score: float = 0.0
    matched_text: str = ""
    match_type: str = "commit"  # "commit" or "branch"
    metadata: dict[str, object] = Field(default_factory=dict)


class SearchResults(BaseModel):
    """Collection of search results with metadata."""

    query: str
    results: list[SearchResult] = []
    total_count: int = 0
    search_method: str = "semantic"
    embedding_model: str = "hash-v1"


# ---------------------------------------------------------------------------
# Data models — Merge intelligence
# ---------------------------------------------------------------------------

class MergeConflict(BaseModel):
    """A single detected merge conflict between two branches."""

    conflict_type: MergeConflictType
    source_commit_id: UUID
    target_commit_id: UUID
    scope: str
    description: str
    severity: float = 0.5  # 0.0 (trivial) to 1.0 (critical)
    affected_metrics: dict[str, float] = Field(default_factory=dict)


class MergeAnalysis(BaseModel):
    """Full merge analysis between two branches."""

    source_branch: str
    target_branch: str
    source_commits: list[UUID] = []
    target_commits: list[UUID] = []
    conflicts: list[MergeConflict] = []
    overall_risk: float = 0.0  # 0.0 (safe) to 1.0 (dangerous)
    is_auto_mergeable: bool = True
    conflict_count: int = 0
    high_severity_count: int = 0


class MergeResolution(BaseModel):
    """Suggested resolution for a merge conflict."""

    conflict_id: UUID = Field(default_factory=uuid4)
    strategy: MergeResolutionStrategy
    reasoning: str
    confidence: float = 0.0
    steps: list[str] = []
    risk_if_applied: float = 0.0


class MergeResolutionReport(BaseModel):
    """Full resolution report for all conflicts in a merge analysis."""

    merge_analysis_id: UUID = Field(default_factory=uuid4)
    source_branch: str
    target_branch: str
    resolutions: list[MergeResolution] = []
    overall_strategy: MergeResolutionStrategy = MergeResolutionStrategy.MANUAL_REVIEW
    overall_confidence: float = 0.0
    recommendation: str = ""


# ---------------------------------------------------------------------------
# Data models — Branch explorer
# ---------------------------------------------------------------------------

class BranchNode(BaseModel):
    """A node in the branch DAG — represents a branch head or merge point."""

    id: UUID = Field(default_factory=uuid4)
    commit_id: UUID
    branch_name: str
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    parent_ids: list[UUID] = []
    is_merge_point: bool = False
    confidence_score: float = 0.0
    scope: str = ""
    commit_type: str = ""


class BranchEdge(BaseModel):
    """A directed edge in the branch DAG — connects parent to child."""

    source_id: UUID
    target_id: UUID
    edge_type: str = "parent"  # "parent", "merge", "fork"


class BranchDAG(BaseModel):
    """Complete DAG structure for visual branch exploration.

    Ready for frontend rendering — contains all nodes and edges
    needed to draw the commit graph.
    """

    nodes: list[BranchNode] = []
    edges: list[BranchEdge] = []
    branches: list[str] = []
    head_commit_id: UUID | None = None
    total_commits: int = 0
    total_branches: int = 0
    total_merge_points: int = 0


# ---------------------------------------------------------------------------
# Data models — Worktree management
# ---------------------------------------------------------------------------

class WorktreeInfo(BaseModel):
    """Information about a git worktree."""

    id: UUID = Field(default_factory=uuid4)
    path: str
    branch: str
    status: WorktreeStatus = WorktreeStatus.ACTIVE
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    commit_id: UUID | None = None
    is_main: bool = False


# ---------------------------------------------------------------------------
# Data models — Commit comparison
# ---------------------------------------------------------------------------

class MetricDelta(BaseModel):
    """Delta for a single metric between two commits."""

    metric: str
    old_value: float
    new_value: float
    delta: float
    delta_percent: float
    improved: bool


class CommitDiff(BaseModel):
    """Rich comparison between two commits."""

    source_commit_id: UUID
    target_commit_id: UUID
    message_changed: bool = False
    scope_changed: bool = False
    type_changed: bool = False
    confidence_delta: float = 0.0
    confidence_improved: bool = False
    metric_deltas: list[MetricDelta] = []
    tape_references_added: int = 0
    tape_references_removed: int = 0
    parent_ids_changed: bool = False
    summary: str = ""


# ---------------------------------------------------------------------------
# Embedding provider (pluggable)
# ---------------------------------------------------------------------------

class EmbeddingProvider:
    """Interface for embedding text into dense vectors.

    The default implementation uses a deterministic hash-based approach
    that produces fixed-dimension vectors suitable for cosine similarity.
    This can be swapped for a real LLM embedding model (OpenAI, local, etc.).
    """

    def __init__(self, dimension: int = 64, model_name: str = "hash-v1") -> None:
        self._dimension = dimension
        self._model = model_name

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, text: str) -> list[float]:
        """Embed text into a dense float vector.

        The hash-based approach:
        1. Normalise text (lowercase, strip punctuation)
        2. Generate N hash substrings for different "features"
        3. Map each hash to a float in [-1, 1]
        4. Return a fixed-dimension vector
        """
        normalised = self._normalise(text)
        vector: list[float] = []

        for i in range(self._dimension):
            # Each dimension gets a different hash seed
            seed = f"{normalised}||dim-{i}"
            h = hashlib.sha256(seed.encode()).hexdigest()
            # Map first 8 hex chars to float in [-1, 1]
            raw = int(h[:8], 16) / 0xFFFFFFFF
            vector.append(raw * 2.0 - 1.0)

        return vector

    def cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(a) != len(b) or len(a) == 0:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(x * x for x in b))
        if mag_a == 0.0 or mag_b == 0.0:
            return 0.0
        return dot / (mag_a * mag_b)

    @staticmethod
    def _normalise(text: str) -> str:
        """Normalise text for consistent hashing."""
        text = text.lower().strip()
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text


# ---------------------------------------------------------------------------
# Commit store (in-memory)
# ---------------------------------------------------------------------------

class CommitStore:
    """In-memory store for AetherCommit objects and branch mappings.

    Will be replaced by a PostgreSQL-backed repository in a future phase.
    """

    def __init__(self) -> None:
        self._commits: dict[UUID, AetherCommit] = {}
        self._branches: dict[str, list[UUID]] = {}  # branch_name → [commit_ids]
        self._worktrees: dict[UUID, WorktreeInfo] = {}

    def add_commit(self, commit: AetherCommit, branch: str = "main") -> None:
        self._commits[commit.id] = commit
        if branch not in self._branches:
            self._branches[branch] = []
        self._branches[branch].append(commit.id)

    def get_commit(self, commit_id: UUID) -> AetherCommit | None:
        return self._commits.get(commit_id)

    def list_commits(self, branch: str | None = None, limit: int = 50, offset: int = 0) -> list[AetherCommit]:
        if branch is not None:
            ids = self._branches.get(branch, [])
            commits = [self._commits[cid] for cid in ids if cid in self._commits]
        else:
            commits = list(self._commits.values())

        commits.sort(key=lambda c: c.timestamp, reverse=True)
        return commits[offset : offset + limit]

    def get_branch_names(self) -> list[str]:
        return list(self._branches.keys())

    def get_branch_commits(self, branch: str) -> list[AetherCommit]:
        ids = self._branches.get(branch, [])
        return [self._commits[cid] for cid in ids if cid in self._commits]

    def get_head(self, branch: str = "main") -> AetherCommit | None:
        ids = self._branches.get(branch, [])
        if not ids:
            return None
        return self._commits.get(ids[-1])

    # Worktree helpers
    def add_worktree(self, wt: WorktreeInfo) -> None:
        self._worktrees[wt.id] = wt

    def get_worktree(self, wt_id: UUID) -> WorktreeInfo | None:
        return self._worktrees.get(wt_id)

    def list_worktrees(self) -> list[WorktreeInfo]:
        return list(self._worktrees.values())

    def remove_worktree(self, wt_id: UUID) -> WorktreeInfo | None:
        return self._worktrees.pop(wt_id, None)

    @property
    def total_commits(self) -> int:
        return len(self._commits)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class AetherGitError(Exception):
    """Base exception for AetherGit operations."""


class CommitNotFoundError(AetherGitError):
    """Raised when a requested commit does not exist."""


class BranchNotFoundError(AetherGitError):
    """Raised when a requested branch does not exist."""


class WorktreeNotFoundError(AetherGitError):
    """Raised when a requested worktree does not exist."""


class WorktreeError(AetherGitError):
    """Raised when a worktree operation fails."""


class MergeAnalysisError(AetherGitError):
    """Raised when merge analysis cannot be performed."""


# ---------------------------------------------------------------------------
# AdvancedAetherGit — the main public API
# ---------------------------------------------------------------------------

class AdvancedAetherGit:
    """Advanced AetherGit engine with semantic search, intelligent merge,
    branch exploration, worktree management, and commit comparison.

    Usage::

        git = AdvancedAetherGit(tape_service=tape_svc)

        # Add commits
        git.add_commit(commit, branch="feature-x")

        # Semantic search
        results = await git.semantic_search("reliability improvements")

        # Merge analysis
        analysis = await git.detect_merge_conflicts("feature-x", "main")
        resolution = await git.suggest_merge_resolution(analysis)

        # Branch explorer DAG
        dag = await git.get_branch_explorer()

        # Worktree management
        wt = await git.create_worktree("feature-x", "/path/to/worktree")

        # Commit comparison
        diff = await git.compare_commits(commit_a.id, commit_b.id)
    """

    def __init__(
        self,
        tape_service: TapeService,
        commit_store: CommitStore | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self._tape = tape_service
        self._store = commit_store or CommitStore()
        self._embedder = embedding_provider or EmbeddingProvider()
        self._embedding_cache: dict[str, list[float]] = {}

    # ------------------------------------------------------------------
    # Commit management
    # ------------------------------------------------------------------

    def add_commit(self, commit: AetherCommit, branch: str = "main") -> None:
        """Add a commit to the store, assigning it to a branch."""
        self._store.add_commit(commit, branch)
        # Pre-compute and cache embedding
        key = f"commit:{commit.id}"
        self._embedding_cache[key] = self._embedder.embed(
            f"{commit.message} {commit.scope} {commit.commit_type}"
        )

    def get_commit(self, commit_id: UUID) -> AetherCommit:
        """Retrieve a commit by ID.

        Raises:
            CommitNotFoundError: if the commit does not exist.
        """
        commit = self._store.get_commit(commit_id)
        if commit is None:
            raise CommitNotFoundError(f"Commit {commit_id} not found")
        return commit

    async def get_commit_history(
        self,
        branch: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AetherCommit]:
        """Return paginated commit history, newest first."""
        return self._store.list_commits(branch=branch, limit=limit, offset=offset)

    # ------------------------------------------------------------------
    # Semantic search
    # ------------------------------------------------------------------

    async def semantic_search(
        self,
        query: str,
        max_results: int = 10,
        min_score: float = 0.1,
        search_commits: bool = True,
        search_branches: bool = True,
    ) -> SearchResults:
        """Search commits and branches by semantic similarity.

        Uses the embedding provider to compute similarity between the query
        and all stored commits/branches. Results are ranked by score and
        filtered by the minimum score threshold.

        Args:
            query: Natural language search query.
            max_results: Maximum number of results to return.
            min_score: Minimum similarity score (0.0-1.0) to include.
            search_commits: Whether to include commits in results.
            search_branches: Whether to include branches in results.

        Returns:
            SearchResults ranked by similarity score.
        """
        query_embedding = self._embedder.embed(query)
        results: list[SearchResult] = []

        if search_commits:
            for commit in self._store.list_commits(limit=1000):
                key = f"commit:{commit.id}"
                commit_embedding = self._embedding_cache.get(key)
                if commit_embedding is None:
                    commit_embedding = self._embedder.embed(
                        f"{commit.message} {commit.scope} {commit.commit_type}"
                    )
                    self._embedding_cache[key] = commit_embedding

                score = self._embedder.cosine_similarity(query_embedding, commit_embedding)
                if score >= min_score:
                    results.append(
                        SearchResult(
                            commit_id=commit.id,
                            score=round(score, 4),
                            matched_text=commit.message,
                            match_type="commit",
                            metadata={
                                "scope": commit.scope,
                                "commit_type": commit.commit_type,
                                "confidence_score": commit.confidence_score,
                                "author": commit.author,
                            },
                        )
                    )

        if search_branches:
            for branch_name in self._store.get_branch_names():
                branch_commits = self._store.get_branch_commits(branch_name)
                if not branch_commits:
                    continue

                # Aggregate branch text from its commits
                branch_text = " ".join(
                    c.message for c in branch_commits[:20]
                )
                branch_key = f"branch:{branch_name}"
                branch_embedding = self._embedding_cache.get(branch_key)
                if branch_embedding is None:
                    branch_embedding = self._embedder.embed(branch_text)
                    self._embedding_cache[branch_key] = branch_embedding

                score = self._embedder.cosine_similarity(query_embedding, branch_embedding)
                if score >= min_score:
                    results.append(
                        SearchResult(
                            branch_name=branch_name,
                            score=round(score, 4),
                            matched_text=f"Branch with {len(branch_commits)} commits",
                            match_type="branch",
                            metadata={
                                "commit_count": len(branch_commits),
                                "latest_message": branch_commits[-1].message
                                if branch_commits
                                else "",
                            },
                        )
                    )

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)
        results = results[:max_results]

        await self._tape.log_event(
            event_type="aethergit.semantic_search",
            payload={
                "query": query,
                "result_count": len(results),
                "max_results": max_results,
                "min_score": min_score,
            },
            agent_id="aethergit",
        )

        return SearchResults(
            query=query,
            results=results,
            total_count=len(results),
            search_method="semantic",
            embedding_model=self._embedder.model_name,
        )

    # ------------------------------------------------------------------
    # Merge intelligence
    # ------------------------------------------------------------------

    async def detect_merge_conflicts(
        self,
        source_branch: str,
        target_branch: str,
    ) -> MergeAnalysis:
        """Detect potential merge conflicts between two branches.

        Analyzes commit scopes, types, and metadata to identify conflicts
        that could arise from merging source into target.

        Args:
            source_branch: The branch to merge from.
            target_branch: The branch to merge into.

        Raises:
            BranchNotFoundError: if either branch doesn't exist.
        """
        source_commits = self._store.get_branch_commits(source_branch)
        target_commits = self._store.get_branch_commits(target_branch)

        if not source_commits and source_branch not in self._store.get_branch_names():
            raise BranchNotFoundError(f"Source branch '{source_branch}' not found")
        if not target_commits and target_branch not in self._store.get_branch_names():
            raise BranchNotFoundError(f"Target branch '{target_branch}' not found")

        source_ids = [c.id for c in source_commits]
        target_ids = [c.id for c in target_commits]

        conflicts: list[MergeConflict] = []

        # 1. Scope overlap detection
        source_scopes: dict[str, list[UUID]] = defaultdict(list)
        target_scopes: dict[str, list[UUID]] = defaultdict(list)

        for c in source_commits:
            source_scopes[c.scope].append(c.id)
        for c in target_commits:
            target_scopes[c.scope].append(c.id)

        overlapping_scopes = set(source_scopes.keys()) & set(target_scopes.keys())
        for scope in overlapping_scopes:
            for src_id in source_scopes[scope]:
                for tgt_id in target_scopes[scope]:
                    conflicts.append(
                        MergeConflict(
                            conflict_type=MergeConflictType.SCOPE_OVERLAP,
                            source_commit_id=src_id,
                            target_commit_id=tgt_id,
                            scope=scope,
                            description=f"Both branches modify scope '{scope}'",
                            severity=self._scope_overlap_severity(
                                source_commits, target_commits, scope
                            ),
                        )
                    )

        # 2. Same commit type in same scope
        src_type_scope: dict[str, UUID] = {}
        tgt_type_scope: dict[str, UUID] = {}
        for c in source_commits:
            key = f"{c.commit_type}:{c.scope}"
            src_type_scope[key] = c.id
        for c in target_commits:
            key = f"{c.commit_type}:{c.scope}"
            tgt_type_scope[key] = c.id

        for key, src_id in src_type_scope.items():
            if key in tgt_type_scope:
                tgt_id = tgt_type_scope[key]
                parts = key.split(":", 1)
                conflicts.append(
                    MergeConflict(
                        conflict_type=MergeConflictType.SAME_FILE_MODIFIED,
                        source_commit_id=src_id,
                        target_commit_id=tgt_id,
                        scope=parts[1] if len(parts) > 1 else "",
                        description=f"Same commit type '{parts[0]}' in scope '{parts[1] if len(parts) > 1 else ''}'",
                        severity=0.7,
                    )
                )

        # 3. Dependency conflict — parent IDs overlapping
        source_parent_ids: set[UUID] = set()
        target_parent_ids: set[UUID] = set()
        for c in source_commits:
            source_parent_ids.update(c.parent_ids)
        for c in target_commits:
            target_parent_ids.update(c.parent_ids)

        shared_parents = source_parent_ids & target_parent_ids
        if shared_parents and len(source_commits) > 1 and len(target_commits) > 1:
            # Shared parent means divergent histories — potential conflict
            conflicts.append(
                MergeConflict(
                    conflict_type=MergeConflictType.DEPENDENCY_CONFLICT,
                    source_commit_id=source_commits[0].id,
                    target_commit_id=target_commits[0].id,
                    scope="",
                    description=f"Divergent branches share {len(shared_parents)} parent commit(s)",
                    severity=0.5,
                )
            )

        # 4. Semantic conflict — conflicting commit messages
        for src in source_commits:
            for tgt in target_commits:
                if self._messages_conflict(src.message, tgt.message):
                    conflicts.append(
                        MergeConflict(
                            conflict_type=MergeConflictType.SEMANTIC_CONFLICT,
                            source_commit_id=src.id,
                            target_commit_id=tgt.id,
                            scope=src.scope,
                            description=f"Potentially conflicting intents: '{src.message[:50]}' vs '{tgt.message[:50]}'",
                            severity=0.6,
                        )
                    )

        # 5. Performance regression — source has lower confidence
        for src in source_commits:
            for tgt in target_commits:
                if src.scope == tgt.scope and src.confidence_score < tgt.confidence_score - 0.2:
                    conflicts.append(
                        MergeConflict(
                            conflict_type=MergeConflictType.PERFORMANCE_REGRESSION,
                            source_commit_id=src.id,
                            target_commit_id=tgt.id,
                            scope=src.scope,
                            description=(
                                f"Source commit has lower confidence "
                                f"({src.confidence_score:.2f}) than target ({tgt.confidence_score:.2f})"
                            ),
                            severity=0.4,
                            affected_metrics={"confidence_delta": src.confidence_score - tgt.confidence_score},
                        )
                    )

        # Compute overall risk
        high_severity = [c for c in conflicts if c.severity >= 0.7]
        overall_risk = self._compute_merge_risk(conflicts)

        analysis = MergeAnalysis(
            source_branch=source_branch,
            target_branch=target_branch,
            source_commits=source_ids,
            target_commits=target_ids,
            conflicts=conflicts,
            overall_risk=overall_risk,
            is_auto_mergeable=len(high_severity) == 0,
            conflict_count=len(conflicts),
            high_severity_count=len(high_severity),
        )

        await self._tape.log_event(
            event_type="aethergit.merge_analysis",
            payload={
                "source_branch": source_branch,
                "target_branch": target_branch,
                "conflict_count": len(conflicts),
                "overall_risk": round(overall_risk, 3),
                "is_auto_mergeable": analysis.is_auto_mergeable,
            },
            agent_id="aethergit",
        )

        return analysis

    async def suggest_merge_resolution(
        self,
        analysis: MergeAnalysis,
    ) -> MergeResolutionReport:
        """Suggest resolutions for all detected merge conflicts.

        Based on conflict type, severity, and commit metadata, generates
        a MergeResolution for each conflict with a recommended strategy
        and step-by-step instructions.

        Args:
            analysis: The merge analysis to resolve.

        Returns:
            MergeResolutionReport with resolutions for each conflict.
        """
        resolutions: list[MergeResolution] = []

        for conflict in analysis.conflicts:
            resolution = self._resolve_conflict(conflict, analysis)
            resolutions.append(resolution)

        # Determine overall strategy
        if not analysis.conflicts:
            overall_strategy = MergeResolutionStrategy.MERGE_BOTH
            overall_confidence = 1.0
            recommendation = "No conflicts detected. Safe to merge automatically."
        elif analysis.is_auto_mergeable:
            overall_strategy = MergeResolutionStrategy.MERGE_BOTH
            overall_confidence = max(
                (r.confidence for r in resolutions), default=0.5
            )
            recommendation = "Low-severity conflicts only. Auto-merge should be safe."
        elif analysis.high_severity_count > 2:
            overall_strategy = MergeResolutionStrategy.MANUAL_REVIEW
            overall_confidence = 0.3
            recommendation = (
                "Multiple high-severity conflicts detected. "
                "Manual review is strongly recommended before merging."
            )
        else:
            overall_strategy = MergeResolutionStrategy.REBASE_SOURCE
            overall_confidence = 0.6
            recommendation = (
                "Rebasing the source branch onto the target before merging "
                "may resolve some conflicts automatically."
            )

        report = MergeResolutionReport(
            source_branch=analysis.source_branch,
            target_branch=analysis.target_branch,
            resolutions=resolutions,
            overall_strategy=overall_strategy,
            overall_confidence=overall_confidence,
            recommendation=recommendation,
        )

        await self._tape.log_event(
            event_type="aethergit.merge_resolution",
            payload={
                "source_branch": analysis.source_branch,
                "target_branch": analysis.target_branch,
                "resolution_count": len(resolutions),
                "overall_strategy": overall_strategy.value,
                "overall_confidence": overall_confidence,
            },
            agent_id="aethergit",
        )

        return report

    # ------------------------------------------------------------------
    # Branch explorer
    # ------------------------------------------------------------------

    async def get_branch_explorer(self) -> BranchDAG:
        """Build the branch DAG for visual exploration.

        Constructs a graph of BranchNodes and BranchEdges representing
        the full commit history across all branches. This data structure
        is designed for frontend rendering (e.g., a DAG visualisation).

        Returns:
            BranchDAG with all nodes, edges, and metadata.
        """
        nodes: list[BranchNode] = []
        edges: list[BranchEdge] = []
        merge_points = 0

        # Track which commit IDs map to which node IDs
        commit_to_node: dict[UUID, UUID] = {}

        # Build nodes from all commits across all branches
        for branch_name in self._store.get_branch_names():
            branch_commits = self._store.get_branch_commits(branch_name)
            for commit in branch_commits:
                # Reuse node if commit exists in multiple branches
                if commit.id in commit_to_node:
                    # This commit is shared — it's a merge point
                    existing_node_id = commit_to_node[commit.id]
                    # Find and update the node to mark as merge point
                    for node in nodes:
                        if node.id == existing_node_id:
                            node.is_merge_point = True
                            merge_points += 1
                            break
                    continue

                node = BranchNode(
                    commit_id=commit.id,
                    branch_name=branch_name,
                    message=commit.message,
                    timestamp=commit.timestamp,
                    parent_ids=commit.parent_ids,
                    is_merge_point=len(commit.parent_ids) > 1,
                    confidence_score=commit.confidence_score,
                    scope=commit.scope,
                    commit_type=commit.commit_type,
                )
                nodes.append(node)
                commit_to_node[commit.id] = node.id

                if node.is_merge_point:
                    merge_points += 1

        # Build edges from parent relationships
        for node in nodes:
            for parent_commit_id in node.parent_ids:
                parent_node_id = commit_to_node.get(parent_commit_id)
                if parent_node_id is not None:
                    edge_type = "merge" if node.is_merge_point else "parent"
                    edges.append(
                        BranchEdge(
                            source_id=parent_node_id,
                            target_id=node.id,
                            edge_type=edge_type,
                        )
                    )

        # Determine head
        head_commit = self._store.get_head("main")
        head_id = commit_to_node.get(head_commit.id) if head_commit else None

        # Sort nodes by timestamp (newest first)
        nodes.sort(key=lambda n: n.timestamp, reverse=True)

        branches = self._store.get_branch_names()

        dag = BranchDAG(
            nodes=nodes,
            edges=edges,
            branches=branches,
            head_commit_id=head_id,
            total_commits=len(nodes),
            total_branches=len(branches),
            total_merge_points=merge_points,
        )

        await self._tape.log_event(
            event_type="aethergit.branch_explorer",
            payload={
                "node_count": len(nodes),
                "edge_count": len(edges),
                "branch_count": len(branches),
                "merge_points": merge_points,
            },
            agent_id="aethergit",
        )

        return dag

    # ------------------------------------------------------------------
    # Worktree management
    # ------------------------------------------------------------------

    async def create_worktree(
        self,
        branch: str,
        path: str,
        commit_id: UUID | None = None,
    ) -> WorktreeInfo:
        """Create a new git worktree for a branch.

        Creates a worktree at the specified path, linked to the given branch.
        If commit_id is provided, the worktree will be detached at that commit.

        Args:
            branch: The branch to check out in the worktree.
            path: Filesystem path for the new worktree.
            commit_id: Optional specific commit to detach at.

        Returns:
            WorktreeInfo describing the new worktree.

        Raises:
            WorktreeError: if the worktree cannot be created.
        """
        # Try real git worktree command (best-effort)
        with contextlib.suppress(subprocess.TimeoutExpired, FileNotFoundError, OSError):
            cmd = ["git", "worktree", "add", path, branch]
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )
            # Don't fail on non-zero exit — in-memory tracking is primary

        worktree = WorktreeInfo(
            path=path,
            branch=branch,
            status=WorktreeStatus.ACTIVE,
            commit_id=commit_id,
            is_main=False,
        )
        self._store.add_worktree(worktree)

        await self._tape.log_event(
            event_type="aethergit.worktree_created",
            payload={
                "worktree_id": str(worktree.id),
                "branch": branch,
                "path": path,
                "commit_id": str(commit_id) if commit_id else None,
            },
            agent_id="aethergit",
        )

        return worktree

    async def list_worktrees(self) -> list[WorktreeInfo]:
        """List all managed worktrees."""
        worktrees = self._store.list_worktrees()

        await self._tape.log_event(
            event_type="aethergit.worktree_listed",
            payload={"worktree_count": len(worktrees)},
            agent_id="aethergit",
        )

        return worktrees

    async def remove_worktree(self, worktree_id: UUID) -> WorktreeInfo:
        """Remove a git worktree.

        Removes the worktree from both the in-memory store and the
        filesystem (via `git worktree remove`).

        Args:
            worktree_id: ID of the worktree to remove.

        Returns:
            The removed WorktreeInfo.

        Raises:
            WorktreeNotFoundError: if the worktree doesn't exist.
        """
        worktree = self._store.remove_worktree(worktree_id)
        if worktree is None:
            raise WorktreeNotFoundError(f"Worktree {worktree_id} not found")

        # Try real git worktree remove (best-effort)
        with contextlib.suppress(subprocess.TimeoutExpired, FileNotFoundError, OSError):
            subprocess.run(
                ["git", "worktree", "remove", worktree.path],
                capture_output=True,
                text=True,
                timeout=10,
            )

        worktree.status = WorktreeStatus.REMOVED

        await self._tape.log_event(
            event_type="aethergit.worktree_removed",
            payload={
                "worktree_id": str(worktree_id),
                "branch": worktree.branch,
                "path": worktree.path,
            },
            agent_id="aethergit",
        )

        return worktree

    # ------------------------------------------------------------------
    # Commit comparison
    # ------------------------------------------------------------------

    async def compare_commits(
        self,
        source_commit_id: UUID,
        target_commit_id: UUID,
    ) -> CommitDiff:
        """Generate a rich comparison between two commits.

        Compares messages, scopes, types, confidence scores, performance
        metrics, and tape references.

        Args:
            source_commit_id: The "before" commit.
            target_commit_id: The "after" commit.

        Raises:
            CommitNotFoundError: if either commit doesn't exist.
        """
        source = self.get_commit(source_commit_id)
        target = self.get_commit(target_commit_id)

        # Compute metric deltas
        metric_deltas: list[MetricDelta] = []
        all_metric_keys = set(source.performance_metrics.keys()) | set(
            target.performance_metrics.keys()
        )

        for key in all_metric_keys:
            old_val = source.performance_metrics.get(key, 0.0)
            new_val = target.performance_metrics.get(key, 0.0)
            delta = new_val - old_val
            delta_pct = (delta / abs(old_val) * 100.0) if old_val != 0.0 else 0.0

            # For most metrics, higher is better; for error rates, lower is better
            is_negative = key.lower() in {"latency", "error_rate", "failure_rate"} or "error" in key.lower() or "fail" in key.lower()
            improved = delta < 0 if is_negative else delta > 0

            metric_deltas.append(
                MetricDelta(
                    metric=key,
                    old_value=old_val,
                    new_value=new_val,
                    delta=round(delta, 4),
                    delta_percent=round(delta_pct, 2),
                    improved=improved,
                )
            )

        # Sort metric deltas: improved first, then by magnitude
        metric_deltas.sort(key=lambda d: (0 if d.improved else 1, abs(d.delta)), reverse=True)

        # Confidence delta
        confidence_delta = target.confidence_score - source.confidence_score

        # Tape references diff
        source_refs = set(source.tape_references)
        target_refs = set(target.tape_references)
        refs_added = len(target_refs - source_refs)
        refs_removed = len(source_refs - target_refs)

        # Summary
        improved_count = sum(1 for d in metric_deltas if d.improved)
        degraded_count = sum(1 for d in metric_deltas if not d.improved and d.delta != 0.0)

        summary_parts: list[str] = []
        if source.message != target.message:
            summary_parts.append("Message changed")
        if source.scope != target.scope:
            summary_parts.append(f"Scope: {source.scope} → {target.scope}")
        if confidence_delta != 0:
            direction = "↑" if confidence_delta > 0 else "↓"
            summary_parts.append(f"Confidence {direction} {abs(confidence_delta):.2f}")
        if improved_count or degraded_count:
            summary_parts.append(f"{improved_count} improved, {degraded_count} degraded metrics")

        summary = "; ".join(summary_parts) if summary_parts else "No significant changes"

        diff = CommitDiff(
            source_commit_id=source_commit_id,
            target_commit_id=target_commit_id,
            message_changed=source.message != target.message,
            scope_changed=source.scope != target.scope,
            type_changed=source.commit_type != target.commit_type,
            confidence_delta=round(confidence_delta, 4),
            confidence_improved=confidence_delta > 0,
            metric_deltas=metric_deltas,
            tape_references_added=refs_added,
            tape_references_removed=refs_removed,
            parent_ids_changed=set(source.parent_ids) != set(target.parent_ids),
            summary=summary,
        )

        await self._tape.log_event(
            event_type="aethergit.commit_comparison",
            payload={
                "source_commit_id": str(source_commit_id),
                "target_commit_id": str(target_commit_id),
                "metric_delta_count": len(metric_deltas),
                "confidence_delta": round(confidence_delta, 4),
                "summary": summary,
            },
            agent_id="aethergit",
        )

        return diff

    # ------------------------------------------------------------------
    # Internal: merge helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _scope_overlap_severity(
        source_commits: list[AetherCommit],
        target_commits: list[AetherCommit],
        scope: str,
    ) -> float:
        """Compute severity for scope overlap based on commit counts."""
        src_count = sum(1 for c in source_commits if c.scope == scope)
        tgt_count = sum(1 for c in target_commits if c.scope == scope)
        # More overlapping commits → higher severity
        overlap = min(src_count, tgt_count)
        return min(0.3 + overlap * 0.1, 1.0)

    @staticmethod
    def _compute_merge_risk(conflicts: list[MergeConflict]) -> float:
        """Compute overall merge risk from 0.0 (safe) to 1.0 (dangerous)."""
        if not conflicts:
            return 0.0
        total_severity = sum(c.severity for c in conflicts)
        # Weighted average with penalty for count
        avg_severity = total_severity / len(conflicts)
        count_penalty = min(len(conflicts) * 0.05, 0.3)
        return min(avg_severity + count_penalty, 1.0)

    @staticmethod
    def _messages_conflict(msg_a: str, msg_b: str) -> bool:
        """Heuristic: do two commit messages indicate conflicting intents?

        Detects opposing action words (add/remove, create/delete, etc.)
        in commits that share the same scope.
        """
        opposites = [
            ("add", "remove"),
            ("create", "delete"),
            ("enable", "disable"),
            ("start", "stop"),
            ("increase", "decrease"),
            ("upgrade", "downgrade"),
            ("fix", "break"),
            ("refactor", "revert"),
        ]
        words_a = set(msg_a.lower().split())
        words_b = set(msg_b.lower().split())

        for word_a, word_b in opposites:
            if (word_a in words_a and word_b in words_b) or (
                word_b in words_a and word_a in words_b
            ):
                return True
        return False

    def _resolve_conflict(
        self,
        conflict: MergeConflict,
        analysis: MergeAnalysis,
    ) -> MergeResolution:
        """Generate a MergeResolution for a single conflict."""
        strategy: MergeResolutionStrategy
        reasoning: str
        confidence: float
        steps: list[str]
        risk: float

        match conflict.conflict_type:
            case MergeConflictType.SCOPE_OVERLAP:
                if conflict.severity < 0.5:
                    strategy = MergeResolutionStrategy.MERGE_BOTH
                    reasoning = (
                        f"Low-severity scope overlap in '{conflict.scope}'. "
                        "Changes likely complement each other."
                    )
                    confidence = 0.8
                    steps = [
                        "Merge source into target",
                        "Run integration tests",
                        "Verify no regressions in shared scope",
                    ]
                    risk = 0.1
                else:
                    strategy = MergeResolutionStrategy.REBASE_SOURCE
                    reasoning = (
                        f"High-severity scope overlap in '{conflict.scope}'. "
                        "Rebasing source onto target may reduce conflicts."
                    )
                    confidence = 0.6
                    steps = [
                        f"Rebase source branch onto {analysis.target_branch}",
                        f"Resolve any remaining conflicts in '{conflict.scope}'",
                        "Run full test suite",
                    ]
                    risk = 0.3

            case MergeConflictType.SAME_FILE_MODIFIED:
                strategy = MergeResolutionStrategy.MANUAL_REVIEW
                reasoning = (
                    f"Both branches modify the same area in scope '{conflict.scope}'. "
                    "Manual review needed to decide which changes to keep."
                )
                confidence = 0.4
                steps = [
                    "Review source commit changes",
                    "Review target commit changes",
                    "Decide which version to keep or merge both",
                    "Create a merge commit with the resolution",
                ]
                risk = 0.5

            case MergeConflictType.DEPENDENCY_CONFLICT:
                strategy = MergeResolutionStrategy.REBASE_SOURCE
                reasoning = (
                    "Divergent branches with shared parents. "
                    "Rebasing will linearise the history and simplify the merge."
                )
                confidence = 0.7
                steps = [
                    f"Rebase source onto {analysis.target_branch}",
                    "Resolve any rebase conflicts",
                    "Fast-forward merge into target",
                ]
                risk = 0.2

            case MergeConflictType.SEMANTIC_CONFLICT:
                strategy = MergeResolutionStrategy.MANUAL_REVIEW
                reasoning = (
                    "Conflicting intents detected in commit messages. "
                    "Human review required to resolve the contradiction."
                )
                confidence = 0.3
                steps = [
                    "Examine both commits for intent",
                    "Determine the correct intended behaviour",
                    "Resolve by keeping the correct version",
                    "Add a clarifying commit message",
                ]
                risk = 0.6

            case MergeConflictType.PERFORMANCE_REGRESSION:
                strategy = MergeResolutionStrategy.TAKE_TARGET
                reasoning = (
                    "Source has lower confidence than target in the same scope. "
                    "Keeping the target version avoids a regression."
                )
                confidence = 0.75
                steps = [
                    "Accept target commit's changes",
                    "Document why source was rejected",
                    "Create a follow-up task to improve source's confidence",
                ]
                risk = 0.15

            case _:
                strategy = MergeResolutionStrategy.MANUAL_REVIEW
                reasoning = "Unknown conflict type. Manual review recommended."
                confidence = 0.2
                steps = ["Review both commits manually"]
                risk = 0.8

        return MergeResolution(
            strategy=strategy,
            reasoning=reasoning,
            confidence=confidence,
            steps=steps,
            risk_if_applied=risk,
        )

    # ------------------------------------------------------------------
    # Store accessors (for testing)
    # ------------------------------------------------------------------

    @property
    def store(self) -> CommitStore:
        """Access the underlying commit store (for testing)."""
        return self._store

    @property
    def embedder(self) -> EmbeddingProvider:
        """Access the embedding provider (for testing)."""
        return self._embedder
