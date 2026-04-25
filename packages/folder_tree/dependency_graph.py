"""GitNexus-inspired Dependency Graph for InkosAI folder trees.

Provides a ``DependencyGraphBuilder`` that extracts cross-file, cross-agent,
and cross-skill dependencies from a domain's folder tree and produces a
``DependencyGraph`` model suitable for rendering as a Sigma.js-style
interactive knowledge graph.

The dependency graph is used by:

- **Folder Mode** — toggle a visual dependency graph view
- **Prime** — semantic dependency resolution and impact analysis
- **AetherGit** — branch-level dependency change tracking

Architecture::

    DependencyGraphBuilder
    ├── build_graph()          — FolderTree → DependencyGraph
    ├── _extract_imports()     — Parse Python imports for skill files
    ├── _extract_markdown_refs() — Parse markdown links/references
    ├── _extract_structural()  — Parent-child and sibling relationships
    └── _infer_semantic()      — Keyword-based semantic linking

    DependencyGraph      — Complete graph model (nodes + edges)
    DependencyNode       — A single node in the dependency graph
    DependencyEdge       — A directed edge between two nodes
    DependencyEdgeType   — IMPORT / REFERENCE / STRUCTURAL / SEMANTIC
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from packages.folder_tree import (
    FolderTreeNode,
    FolderTreeService,
    NodeType,
)
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DependencyEdgeType(StrEnum):
    """Types of dependency edges in the graph."""

    IMPORT = "import"          # Python import / module dependency
    REFERENCE = "reference"    # Markdown link / explicit reference
    STRUCTURAL = "structural"  # Parent-child / directory containment
    SEMANTIC = "semantic"      # Inferred from content similarity


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class DependencyNode(BaseModel):
    """A single node in the dependency graph.

    Maps 1:1 to a ``FolderTreeNode`` but with graph-specific metadata.
    """

    id: str  # Same as FolderTreeNode.path
    label: str  # Human-readable name
    node_type: str  # "file" or "directory"
    group: str  # "agents", "skills", "workflows", "config", etc.
    path: str  # Full path in the folder tree


class DependencyEdge(BaseModel):
    """A directed edge in the dependency graph."""

    id: UUID = Field(default_factory=uuid4)
    source: str  # Source node path
    target: str  # Target node path (the dependency)
    edge_type: DependencyEdgeType = DependencyEdgeType.REFERENCE
    label: str = ""  # Optional edge label


class DependencyGraph(BaseModel):
    """Complete dependency graph for a domain.

    This model can be serialised to JSON and consumed by a Sigma.js
    front-end for interactive rendering.
    """

    id: UUID = Field(default_factory=uuid4)
    domain_id: str
    nodes: list[DependencyNode] = []
    edges: list[DependencyEdge] = []
    node_count: int = 0
    edge_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Pre-computed group counts for UI rendering
    group_counts: dict[str, int] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# DependencyGraphBuilder
# ---------------------------------------------------------------------------

# Regex patterns for dependency extraction
_IMPORT_PATTERN: re.Pattern[str] = re.compile(
    r"^(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_.]*)", re.MULTILINE
)
_MARKDOWN_LINK_PATTERN: re.Pattern[str] = re.compile(
    r"\[([^\]]*)\]\(([^)]+)\)"
)
_MARKDOWN_REF_PATTERN: re.Pattern[str] = re.compile(
    r"`([^`]+/[^\s`]+)`"
)


class DependencyGraphBuilder:
    """Build a ``DependencyGraph`` from a domain's folder tree.

    Extracts four types of dependencies:

    1. **IMPORT** — Python ``import`` / ``from ... import`` in skill files.
    2. **REFERENCE** — Markdown links and backtick-wrapped paths.
    3. **STRUCTURAL** — Parent-child directory containment.
    4. **SEMANTIC** — Keyword-based inference from file content.

    Parameters
    ----------
    folder_tree_service:
        The folder tree service to read domain trees from.
    tape_service:
        Tape service for audit logging.
    """

    def __init__(
        self,
        folder_tree_service: FolderTreeService,
        tape_service: TapeService,
    ) -> None:
        self._fts = folder_tree_service
        self._tape = tape_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def build_graph(
        self,
        domain_id: str,
        include_semantic: bool = True,
    ) -> DependencyGraph:
        """Build a dependency graph for a domain.

        Parameters
        ----------
        domain_id:
            The domain to build the graph for.
        include_semantic:
            Whether to include keyword-inferred semantic edges.
            Set to ``False`` for a strictly structural graph.

        Returns
        -------
        DependencyGraph
            Complete dependency graph ready for rendering.
        """
        tree = await self._fts.get_tree(domain_id)
        nodes = tree.nodes
        root = tree.root_path

        dep_nodes: list[DependencyNode] = []
        dep_edges: list[DependencyEdge] = []

        # -- Build nodes --
        group_counts: dict[str, int] = {}
        for path, node_obj in nodes.items():
            node = node_obj
            name = node.name
            node_type_val = node.node_type
            nt = node_type_val.value if node_type_val else "unknown"

            # Determine group from path
            group = self._infer_group(path, root)
            group_counts[group] = group_counts.get(group, 0) + 1

            dep_nodes.append(DependencyNode(
                id=path,
                label=name,
                node_type=nt,
                group=group,
                path=path,
            ))

        # -- Build edges --
        seen_edges: set[tuple[str, str, str]] = set()  # (source, target, type)

        for path, node_obj in nodes.items():
            node = node_obj
            content = node.content
            name = node.name
            node_type_val = node.node_type

            # Structural edges (parent ↔ child)
            structural_edges = self._extract_structural(path, nodes, root)
            for src, tgt in structural_edges:
                key = (src, tgt, "structural")
                if key not in seen_edges:
                    seen_edges.add(key)
                    dep_edges.append(DependencyEdge(
                        source=src,
                        target=tgt,
                        edge_type=DependencyEdgeType.STRUCTURAL,
                        label="contains",
                    ))

            # Import edges (Python files)
            if node_type_val == NodeType.FILE and name.endswith(".py") and content:
                import_edges = self._extract_imports(path, content, nodes, root)
                for src, tgt, lbl in import_edges:
                    key = (src, tgt, "import")
                    if key not in seen_edges:
                        seen_edges.add(key)
                        dep_edges.append(DependencyEdge(
                            source=src,
                            target=tgt,
                            edge_type=DependencyEdgeType.IMPORT,
                            label=lbl,
                        ))

            # Reference edges (Markdown and all files)
            if node_type_val == NodeType.FILE and content:
                ref_edges = self._extract_markdown_refs(path, content, nodes)
                for src, tgt, lbl in ref_edges:
                    key = (src, tgt, "reference")
                    if key not in seen_edges:
                        seen_edges.add(key)
                        dep_edges.append(DependencyEdge(
                            source=src,
                            target=tgt,
                            edge_type=DependencyEdgeType.REFERENCE,
                            label=lbl,
                        ))

            # Semantic edges (keyword-based inference)
            if include_semantic and node_type_val == NodeType.FILE and content:
                sem_edges = self._infer_semantic(path, content, nodes, root)
                for src, tgt, lbl in sem_edges:
                    key = (src, tgt, "semantic")
                    if key not in seen_edges:
                        seen_edges.add(key)
                        dep_edges.append(DependencyEdge(
                            source=src,
                            target=tgt,
                            edge_type=DependencyEdgeType.SEMANTIC,
                            label=lbl,
                        ))

        graph = DependencyGraph(
            domain_id=domain_id,
            nodes=dep_nodes,
            edges=dep_edges,
            node_count=len(dep_nodes),
            edge_count=len(dep_edges),
            group_counts=group_counts,
        )

        await self._tape.log_event(
            event_type="prime.dependency_graph_built",
            payload={
                "domain_id": domain_id,
                "node_count": graph.node_count,
                "edge_count": graph.edge_count,
                "group_counts": group_counts,
                "include_semantic": include_semantic,
            },
            agent_id="dependency-graph-builder",
        )

        return graph

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _infer_group(self, path: str, root: str) -> str:
        """Determine the group of a node from its path."""
        relative = path.removeprefix(root + "/") if path.startswith(root + "/") else path
        parts = relative.split("/")
        if len(parts) >= 2:
            top = parts[0]
            if top in ("agents", "skills", "workflows", "config",
                        "templates", "data_sources", "evaluation", "canvas"):
                return top
        if path == root:
            return "root"
        return "other"

    def _extract_structural(
        self,
        path: str,
        nodes: dict[str, FolderTreeNode],
        root: str,
    ) -> list[tuple[str, str]]:
        """Extract structural (parent-child) edges."""
        edges: list[tuple[str, str]] = []

        node_obj = nodes.get(path)
        if node_obj is None:
            return edges

        node_type_val = node_obj.node_type
        if node_type_val == NodeType.DIRECTORY:
            children = node_obj.children
            for child_path in children:
                edges.append((path, child_path))

        return edges

    def _extract_imports(
        self,
        path: str,
        content: str,
        nodes: dict[str, FolderTreeNode],
        root: str,
    ) -> list[tuple[str, str, str]]:
        """Extract Python import dependencies from skill files."""
        edges: list[tuple[str, str, str]] = []

        for match in _IMPORT_PATTERN.finditer(content):
            module = match.group(1)
            # Map module name to folder tree path
            for node_path in nodes:
                node_name = node_path.rsplit("/", 1)[-1] if "/" in node_path else node_path
                # Match skill file names to imports
                if (
                    node_name.replace(".py", "") == module.split(".")[-1]
                    and node_path != path
                ):
                    edges.append((path, node_path, f"imports {module}"))
                    break

        return edges

    def _extract_markdown_refs(
        self,
        path: str,
        content: str,
        nodes: dict[str, FolderTreeNode],
    ) -> list[tuple[str, str, str]]:
        """Extract markdown link and backtick reference edges."""
        edges: list[tuple[str, str, str]] = []

        # Markdown links: [text](url)
        for match in _MARKDOWN_LINK_PATTERN.finditer(content):
            link_text = match.group(1)
            link_target = match.group(2)
            if link_target.startswith("http"):
                continue
            for node_path in nodes:
                if (
                    (node_path.endswith(link_target) or link_target in node_path)
                    and node_path != path
                ):
                    edges.append((path, node_path, f"links to {link_text}"))
                    break

        # Backtick-wrapped paths: `agents/analyst/role.md`
        for match in _MARKDOWN_REF_PATTERN.finditer(content):
            ref = match.group(1)
            for node_path in nodes:
                if (
                    (node_path.endswith(ref) or ref in node_path)
                    and node_path != path
                ):
                    edges.append((path, node_path, f"references {ref}"))
                    break

        return edges

    def _infer_semantic(
        self,
        path: str,
        content: str,
        nodes: dict[str, FolderTreeNode],
        root: str,
    ) -> list[tuple[str, str, str]]:
        """Infer semantic dependencies from keyword overlap.

        Two files are semantically linked if they share significant
        domain-specific keywords (e.g. both mention "contract_analysis").
        """
        edges: list[tuple[str, str, str]] = []

        # Extract significant keywords from content
        keywords = self._extract_keywords(content)
        if not keywords:
            return edges

        for node_path, node_obj in nodes.items():
            if node_path == path:
                continue
            node_type_val = node_obj.node_type
            if node_type_val != NodeType.FILE:
                continue

            other_content = node_obj.content
            if not other_content:
                continue

            other_keywords = self._extract_keywords(other_content)
            overlap = keywords & other_keywords

            # Need at least 2 shared keywords to establish a semantic link
            if len(overlap) >= 2:
                shared = ", ".join(sorted(overlap)[:3])
                edges.append((path, node_path, f"shared: {shared}"))

        return edges

    @staticmethod
    def _extract_keywords(content: str) -> set[str]:
        """Extract significant keywords from file content.

        Filters out common English stop words and very short tokens.
        """
        stop_words: set[str] = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "above",
            "below", "between", "out", "off", "over", "under", "again",
            "further", "then", "once", "here", "there", "when", "where",
            "why", "how", "all", "both", "each", "few", "more", "most",
            "other", "some", "such", "no", "nor", "not", "only", "own",
            "same", "so", "than", "too", "very", "just", "because",
            "but", "and", "or", "if", "while", "about", "up", "it",
            "its", "this", "that", "these", "those", "he", "she", "they",
            "we", "you", "i", "me", "my", "your", "his", "her", "our",
            "their", "what", "which", "who", "whom", "any", "also",
            "def", "class", "return", "import", "pass", "none",
        }

        tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{2,}", content.lower())
        return {t for t in tokens if t not in stop_words}
