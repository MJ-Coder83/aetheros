"""GitNexus-inspired Impact Analysis for InkosAI folder trees.

Prime can run ``assess_impact(domain_id, path)`` to predict what will break
if a file, agent, or skill is changed.  The analysis walks the dependency
graph built by ``DependencyGraphBuilder`` and reports:

- **Direct dependents** — nodes that directly reference the target.
- **Transitive dependents** — nodes that depend on the target through
  one or more intermediate hops.
- **Impact severity** — ``LOW`` / ``MEDIUM`` / ``HIGH`` / ``CRITICAL``,
  determined by the number and type of dependents.
- **Suggested mitigations** — human-readable suggestions for safe change
  application.

All analyses are logged to the Tape for full auditability.

Architecture::

    ImpactAnalyzer
    ├── assess_impact()       — Main entry: path → ImpactReport
    ├── _classify_severity()  — Determine impact severity from dependents
    └── _generate_mitigations() — Produce human-readable mitigation steps

    ImpactReport   — Complete impact analysis result
    ImpactSeverity — LOW / MEDIUM / HIGH / CRITICAL
    DependentNode  — A single dependent with hop distance and reason
"""

from __future__ import annotations

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

class ImpactSeverity(StrEnum):
    """How severe the impact of a change would be."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class DependentNode(BaseModel):
    """A single node that depends on the target path."""

    path: str
    node_type: str  # "file" or "directory"
    hop_distance: int  # 1 = direct, 2+ = transitive
    reason: str = ""  # Why this node depends on the target


class ImpactReport(BaseModel):
    """Complete impact analysis for a proposed change."""

    id: UUID = Field(default_factory=uuid4)
    domain_id: str
    target_path: str
    direct_dependents: list[DependentNode] = []
    transitive_dependents: list[DependentNode] = []
    severity: ImpactSeverity = ImpactSeverity.LOW
    affected_node_count: int = 0
    mitigations: list[str] = []
    analysis_time: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# ImpactAnalyzer
# ---------------------------------------------------------------------------

# Severity thresholds
_SEVERITY_THRESHOLDS: dict[str, int] = {
    "LOW": 3,
    "MEDIUM": 7,
    "HIGH": 15,
}


class ImpactAnalyzer:
    """Predict what will break if a file, agent, or skill is changed.

    Walks the dependency graph (extracted from the folder tree) and reports
    direct and transitive dependents, severity, and mitigation suggestions.

    Parameters
    ----------
    folder_tree_service:
        The folder tree service to read domain trees from.
    tape_service:
        Tape service for audit logging.
    max_hop_distance:
        Maximum transitive hop depth (default 5 to prevent runaway walks).
    """

    def __init__(
        self,
        folder_tree_service: FolderTreeService,
        tape_service: TapeService,
        max_hop_distance: int = 5,
    ) -> None:
        self._fts = folder_tree_service
        self._tape = tape_service
        self._max_hops = max_hop_distance

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def assess_impact(
        self,
        domain_id: str,
        path: str,
    ) -> ImpactReport:
        """Analyse the impact of changing a path in a domain's folder tree.

        Parameters
        ----------
        domain_id:
            The domain to analyse.
        path:
            Relative path within the domain (e.g. ``"agents/analyst/role.md"``).

        Returns
        -------
        ImpactReport
            Full impact analysis with dependents, severity, and mitigations.
        """
        tree = await self._fts.get_tree(domain_id)
        full_path = f"{tree.root_path}/{path}"

        # Build a simple dependency map from the tree structure
        dep_map = self._build_dependency_map(tree.nodes)

        direct = self._find_direct_dependents(full_path, tree.nodes, dep_map)
        transitive = self._find_transitive_dependents(
            full_path, tree.nodes, dep_map
        )

        all_affected = direct + transitive
        severity = self._classify_severity(all_affected, tree.nodes, full_path)
        mitigations = self._generate_mitigations(
            severity, direct, transitive, path
        )

        report = ImpactReport(
            domain_id=domain_id,
            target_path=path,
            direct_dependents=direct,
            transitive_dependents=transitive,
            severity=severity,
            affected_node_count=len(all_affected),
            mitigations=mitigations,
        )

        await self._tape.log_event(
            event_type="prime.impact_analysis",
            payload={
                "domain_id": domain_id,
                "path": path,
                "severity": severity.value,
                "direct_count": len(direct),
                "transitive_count": len(transitive),
                "affected_total": len(all_affected),
                "mitigation_count": len(mitigations),
            },
            agent_id="impact-analyzer",
        )

        return report

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_dependency_map(
        self,
        nodes: dict[str, FolderTreeNode],
    ) -> dict[str, set[str]]:
        """Build a mapping of path -> set of paths that depend on it.

        Dependencies are inferred from the folder tree structure:

        - Directory nodes depend on their parent.
        - File nodes depend on their parent directory.
        - Cross-references are detected by scanning file content for
          path-like references (e.g. ``agents/analyst/role.md`` mentions
          ``skills/contract_analysis.py``).
        - SKILL.md files list dependencies explicitly.
        """
        # Forward map: what does each node depend ON
        depends_on: dict[str, set[str]] = {}

        for path, node_obj in nodes.items():
            node = node_obj
            depends_on.setdefault(path, set())

            # Structural dependency: child depends on parent
            parent_path = path.rsplit("/", 1)[0] if "/" in path else ""
            if parent_path and parent_path in nodes:
                depends_on[path].add(parent_path)

            # Content-based cross-references
            content = node.content
            name = node.name
            node_type = node.node_type

            if node_type == NodeType.FILE and content:
                refs = self._extract_references(content, path, nodes)
                depends_on[path].update(refs)

            # SKILL.md dependency extraction
            if name == "SKILL.md" and content:
                skill_deps = self._extract_skill_md_dependencies(
                    content, path, nodes
                )
                depends_on[path].update(skill_deps)

        # Invert: who depends ON each path
        depended_by: dict[str, set[str]] = {}
        for path, deps in depends_on.items():
            for dep in deps:
                depended_by.setdefault(dep, set()).add(path)

        return depended_by

    def _extract_references(
        self,
        content: str,
        source_path: str,
        nodes: dict[str, FolderTreeNode],
    ) -> set[str]:
        """Extract cross-file references from file content.

        Looks for path-like strings (e.g. ``agents/analyst/role.md``)
        and content keywords that map to other nodes.
        """
        import re

        refs: set[str] = set()

        # Pattern: backtick-wrapped paths  `agents/analyst/role.md`
        for match in re.finditer(r"`([^`]+/[^\s`]+)`", content):
            ref = match.group(1)
            # Find matching node
            for node_path in nodes:
                if node_path.endswith(ref) or ref in node_path:
                    if node_path != source_path:
                        refs.add(node_path)
                    break

        # Pattern: markdown links  [text](path)
        for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", content):
            link_path = match.group(2)
            if not link_path.startswith("http"):
                for node_path in nodes:
                    if node_path.endswith(link_path) or link_path in node_path:
                        if node_path != source_path:
                            refs.add(node_path)
                        break

        return refs

    def _extract_skill_md_dependencies(
        self,
        content: str,
        source_path: str,
        nodes: dict[str, FolderTreeNode],
    ) -> set[str]:
        """Extract dependencies from SKILL.md content.

        SKILL.md files have a structured format with a
        ``## Dependencies`` section listing paths.
        """
        refs: set[str] = set()
        in_deps = False

        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("## Dependencies"):
                in_deps = True
                continue
            if in_deps and stripped.startswith("## "):
                break
            if in_deps and stripped.startswith("- "):
                dep_ref = stripped[2:].strip().strip("`")
                for node_path in nodes:
                    if node_path.endswith(dep_ref) or dep_ref in node_path:
                        if node_path != source_path:
                            refs.add(node_path)
                        break

        return refs

    def _find_direct_dependents(
        self,
        full_path: str,
        nodes: dict[str, FolderTreeNode],
        dep_map: dict[str, set[str]],
    ) -> list[DependentNode]:
        """Find nodes that directly depend on the target path."""
        dependents = dep_map.get(full_path, set())
        result: list[DependentNode] = []

        for dep_path in sorted(dependents):
            node = nodes.get(dep_path)
            if node is not None:
                node_type_val = node.node_type
                nt = node_type_val.value if node_type_val else "unknown"
                reason = self._infer_reason(full_path, dep_path, nodes)
                result.append(DependentNode(
                    path=dep_path,
                    node_type=nt,
                    hop_distance=1,
                    reason=reason,
                ))

        return result

    def _find_transitive_dependents(
        self,
        full_path: str,
        nodes: dict[str, FolderTreeNode],
        dep_map: dict[str, set[str]],
    ) -> list[DependentNode]:
        """Find nodes that transitively depend on the target path.

        Uses BFS from direct dependents up to ``_max_hops`` depth.
        """
        direct_paths = {d.path for d in self._find_direct_dependents(
            full_path, nodes, dep_map
        )}
        visited: set[str] = set(direct_paths)
        visited.add(full_path)
        queue: list[tuple[str, int]] = [(p, 2) for p in direct_paths]
        result: list[DependentNode] = []

        while queue:
            current_path, distance = queue.pop(0)
            if distance > self._max_hops:
                continue

            for dep_path in dep_map.get(current_path, set()):
                if dep_path in visited:
                    continue
                visited.add(dep_path)
                node = nodes.get(dep_path)
                if node is not None:
                    node_type_val = node.node_type
                    nt = node_type_val.value if node_type_val else "unknown"
                    result.append(DependentNode(
                        path=dep_path,
                        node_type=nt,
                        hop_distance=distance,
                        reason=f"Transitive via {current_path}",
                    ))
                    queue.append((dep_path, distance + 1))

        return result

    def _infer_reason(
        self,
        target_path: str,
        dependent_path: str,
        nodes: dict[str, FolderTreeNode],
    ) -> str:
        """Infer why a dependent relies on the target."""
        # Parent-child structural dependency
        dep_parent = dependent_path.rsplit("/", 1)[0] if "/" in dependent_path else ""
        if target_path == dep_parent:
            return "Child directory/file"

        # Content reference
        dep_node = nodes.get(dependent_path)
        if dep_node is not None:
            content = getattr(dep_node, "content", "") or ""
            # Extract just the filename for a cleaner reason
            target_name = target_path.rsplit("/", 1)[-1] if "/" in target_path else target_path
            if target_name in content:
                return f"References {target_name}"

        # Sibling in same directory
        target_parent = target_path.rsplit("/", 1)[0] if "/" in target_path else ""
        dep_parent = dependent_path.rsplit("/", 1)[0] if "/" in dependent_path else ""
        if target_parent and target_parent == dep_parent:
            return "Sibling in same directory"

        return "Cross-reference"

    def _classify_severity(
        self,
        all_affected: list[DependentNode],
        nodes: dict[str, FolderTreeNode],
        target_path: str,
    ) -> ImpactSeverity:
        """Classify the impact severity based on affected node count and types."""
        count = len(all_affected)

        # Critical: config files or README always high-impact
        target_name = target_path.rsplit("/", 1)[-1] if "/" in target_path else target_path
        if target_name in ("domain_config.json", "README.md", "criteria.json"):
            return ImpactSeverity.CRITICAL

        # Check if target is a directory (directories affect more nodes)
        target_node = nodes.get(target_path)
        is_directory = (
            getattr(target_node, "node_type", None) == NodeType.DIRECTORY
            if target_node
            else False
        )

        if is_directory:
            count = int(count * 1.5)  # Directory changes have wider blast radius

        if count >= _SEVERITY_THRESHOLDS["HIGH"]:
            return ImpactSeverity.HIGH
        if count >= _SEVERITY_THRESHOLDS["MEDIUM"]:
            return ImpactSeverity.MEDIUM
        if count >= _SEVERITY_THRESHOLDS["LOW"]:
            return ImpactSeverity.LOW
        return ImpactSeverity.LOW

    def _generate_mitigations(
        self,
        severity: ImpactSeverity,
        direct: list[DependentNode],
        transitive: list[DependentNode],
        path: str,
    ) -> list[str]:
        """Generate human-readable mitigation suggestions."""
        mitigations: list[str] = []

        match severity:
            case ImpactSeverity.CRITICAL:
                mitigations.append(
                    f"CRITICAL: '{path}' is a core system file. "
                    "Consider creating a new version instead of modifying in-place."
                )
                mitigations.append(
                    "Run a simulation before applying this change to assess"
                    " downstream effects on all dependents."
                )
            case ImpactSeverity.HIGH:
                mitigations.append(
                    f"Changing '{path}' affects {len(direct)} direct and "
                    f"{len(transitive)} transitive dependents. "
                    "Review each dependent before proceeding."
                )
                mitigations.append(
                    "Consider deprecating the current path and creating a new one"
                    " with a migration plan for dependents."
                )
            case ImpactSeverity.MEDIUM:
                mitigations.append(
                    f"Review the {len(direct)} direct dependents of '{path}' "
                    "to ensure compatibility."
                )
            case ImpactSeverity.LOW:
                mitigations.append(
                    f"Change to '{path}' has minimal blast radius. "
                    "Standard review is sufficient."
                )

        if direct:
            file_deps = [d for d in direct if d.node_type == "file"]
            dir_deps = [d for d in direct if d.node_type == "directory"]
            if file_deps:
                mitigations.append(
                    f"Direct file dependents: "
                    f"{', '.join(d.path.rsplit('/', 1)[-1] for d in file_deps[:5])}"
                )
            if dir_deps:
                mitigations.append(
                    f"Direct directory dependents: "
                    f"{', '.join(d.path.rsplit('/', 1)[-1] for d in dir_deps[:5])}"
                )

        return mitigations
