"""GitNexus-inspired folder tree enhancement API routes.

Provides endpoints for:

- **Impact analysis** -- predict what breaks if a path is changed
- **Dependency graph** -- build an interactive dependency graph for a domain
- **SKILL.md generation** -- auto-generate capability manifests for agents/skills
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from packages.folder_tree import FolderTreeService
from services.api.dependencies import TapeServiceDep

router = APIRouter(prefix="/folder-tree", tags=["folder-tree"])


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------

def _get_folder_tree_service(tape_service: TapeServiceDep) -> FolderTreeService:
    """Create a FolderTreeService with the shared TapeService."""
    return FolderTreeService(tape_service=tape_service)


FolderTreeServiceDep = Annotated[
    FolderTreeService,
    Depends(_get_folder_tree_service),
]


# ---------------------------------------------------------------------------
# Impact analysis
# ---------------------------------------------------------------------------

@router.post("/impact/{domain_id}")
async def assess_impact(
    fts: FolderTreeServiceDep,
    domain_id: str,
    path: str = Query(..., description="Relative path within the domain"),
) -> dict[str, object]:
    """Assess the impact of changing a path in a domain's folder tree.

    Returns direct and transitive dependents, impact severity, and
    mitigation suggestions.
    """
    from packages.folder_tree.impact import ImpactAnalyzer

    analyzer = ImpactAnalyzer(
        folder_tree_service=fts,
        tape_service=fts._tape,
    )
    report = await analyzer.assess_impact(domain_id, path)
    return report.model_dump()


# ---------------------------------------------------------------------------
# Dependency graph
# ---------------------------------------------------------------------------

@router.get("/dependency-graph/{domain_id}")
async def build_dependency_graph(
    fts: FolderTreeServiceDep,
    domain_id: str,
    include_semantic: bool = Query(True, description="Include keyword-inferred edges"),
) -> dict[str, object]:
    """Build a dependency graph for a domain's folder tree.

    Returns nodes, edges, and group counts suitable for Sigma.js
    interactive rendering.
    """
    from packages.folder_tree.dependency_graph import DependencyGraphBuilder

    builder = DependencyGraphBuilder(
        folder_tree_service=fts,
        tape_service=fts._tape,
    )
    graph = await builder.build_graph(domain_id, include_semantic=include_semantic)
    return graph.model_dump()


# ---------------------------------------------------------------------------
# SKILL.md generation
# ---------------------------------------------------------------------------

@router.post("/skill-md/{domain_id}")
async def generate_skill_mds(
    fts: FolderTreeServiceDep,
    domain_id: str,
) -> dict[str, object]:
    """Auto-generate SKILL.md files for all agents and skills in a domain.

    Returns a mapping of relative path to SKILL.md content.
    """
    from packages.folder_tree.skill_md import SkillMdGenerator

    generator = SkillMdGenerator(
        folder_tree_service=fts,
        tape_service=fts._tape,
    )
    results = await generator.generate_for_domain(domain_id)
    return {"domain_id": domain_id, "files": results, "count": len(results)}


# ---------------------------------------------------------------------------
# Single SKILL.md update
# ---------------------------------------------------------------------------

@router.put("/skill-md/{domain_id}/{path:path}")
async def update_skill_md(
    fts: FolderTreeServiceDep,
    domain_id: str,
    path: str,
) -> dict[str, object]:
    """Re-generate a single SKILL.md file after changes."""
    from packages.folder_tree.skill_md import SkillMdGenerator

    generator = SkillMdGenerator(
        folder_tree_service=fts,
        tape_service=fts._tape,
    )
    content = await generator.update_skill_md(domain_id, path)
    return {"domain_id": domain_id, "path": path, "content": content}


# ---------------------------------------------------------------------------
# Parse SKILL.md
# ---------------------------------------------------------------------------

@router.post("/skill-md/parse")
async def parse_skill_md(
    content: str = Query(..., description="Raw SKILL.md content to parse"),
) -> dict[str, object]:
    """Parse an existing SKILL.md file into a structured model."""
    from packages.folder_tree.skill_md import SkillMdGenerator

    result = SkillMdGenerator.parse_skill_md(content)
    return result.model_dump()
