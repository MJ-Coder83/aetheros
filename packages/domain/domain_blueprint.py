"""Domain Blueprint & Folder-Tree Generator — One-Click Domain Creation (Agent 1).

This module provides the canonical ``DomainBlueprint`` model and the
``DomainFolderTreeGenerator`` that converts a blueprint into a clean,
fully-populated ``FolderTree``.

It is the *source-of-truth definition* for what a domain blueprint contains.
The model is re-exported from ``packages.prime.domain_creation`` for backward
compatibility, but all new code should import directly from this module.

Architecture::

    DomainBlueprint              — complete spec for a new domain
    ├── AgentBlueprint           — per-agent spec (role, goal, capabilities)
    ├── SkillBlueprint           — per-skill spec (id, name, description)
    ├── WorkflowBlueprint        — per-workflow spec (steps, agent refs)
    ├── DomainConfig             — domain-level configuration
    └── EvaluationCriteria       — success / quality metrics

    DomainFolderTreeGenerator    — blueprint → FolderTree
    └── generate(blueprint)      — returns a fully-populated FolderTree

Canonical folder-tree layout::

    Domain_Name/
    ├── agents/
    │   └── <agent_slug>/
    │       ├── role.md
    │       ├── goals.md
    │       ├── tools/
    │       │   └── <tool_slug>.md
    │       └── examples/
    ├── skills/
    │   └── <skill_slug>.py
    ├── workflows/
    │   └── <workflow_slug>/
    │       ├── workflow.json
    │       └── example_inputs/
    ├── templates/
    ├── config/
    │   └── domain_config.json
    ├── data_sources/
    ├── evaluation/
    │   └── criteria.json
    └── README.md

Usage::

    from packages.domain.domain_blueprint import (
        DomainBlueprint,
        AgentBlueprint,
        SkillBlueprint,
        WorkflowBlueprint,
        DomainConfig,
        EvaluationCriteria,
        DomainFolderTreeGenerator,
    )
    from packages.tape.service import TapeService
    from packages.tape.repository import InMemoryTapeRepository

    blueprint = DomainBlueprint(
        domain_name="Legal Research",
        domain_id="legal-research",
        description="Legal research and compliance domain",
        agents=[AgentBlueprint(agent_id="a1", name="Contract Analyst", role=AgentRole.SPECIALIST, goal="Analyse contracts")],
        skills=[SkillBlueprint(skill_id="s1", name="Contract Analysis", description="Analyse legal contracts")],
        workflows=[WorkflowBlueprint(workflow_id="w1", name="Review Pipeline", steps=["Gather", "Review", "Approve"])],
    )

    tape_svc = TapeService(InMemoryTapeRepository())
    generator = DomainFolderTreeGenerator(tape_service=tape_svc)
    folder_tree = await generator.generate(blueprint)

    # folder_tree.nodes  — dict[str, FolderTreeNode]
    # folder_tree.root_path — e.g. "Legal_Research/"
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from packages.folder_tree import (
    FolderTree,
    FolderTreeNode,
    NodeType,
)
from packages.tape.service import TapeService

# Re-export the existing blueprint models from prime.domain_creation so that
# this module is the single canonical import point.  Other modules can still
# import from prime.domain_creation for backward compatibility.
from packages.prime.domain_creation import (
    AgentBlueprint,
    AgentRole,
    CreationMode,
    DomainBlueprint,
    DomainConfig,
    DomainCreationError,
    DomainStatus,
    SkillBlueprint,
    WorkflowBlueprint,
    WorkflowType,
)

__all__ = [
    # Re-exported from prime.domain_creation
    "AgentBlueprint",
    "AgentRole",
    "CreationMode",
    "DomainBlueprint",
    "DomainConfig",
    "DomainCreationError",
    "DomainStatus",
    "SkillBlueprint",
    "WorkflowBlueprint",
    "WorkflowType",
    # New in this module
    "EvaluationCriteria",
    "DomainFolderTreeGenerator",
]


# ---------------------------------------------------------------------------
# EvaluationCriteria — success metrics for a domain
# ---------------------------------------------------------------------------


class EvaluationCriteria(BaseModel):
    """Success and quality metrics for a domain.

    These criteria are written to ``evaluation/criteria.json`` in the
    folder tree and used by Prime to assess domain health.

    Attributes
    ----------
    accuracy_threshold:
        Minimum acceptable task accuracy (0.0–1.0, default 0.85).
    response_time_sla_seconds:
        Maximum acceptable response time in seconds (default 30).
    human_approval_rate:
        Minimum required human approval rate for proposals (0.0–1.0).
    uptime_target:
        Target system uptime percentage (0.0–100.0, default 99.5).
    custom_metrics:
        Any domain-specific key/value metric thresholds.
    """

    accuracy_threshold: float = 0.85
    response_time_sla_seconds: float = 30.0
    human_approval_rate: float = 0.90
    uptime_target: float = 99.5
    custom_metrics: dict[str, object] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# DomainFolderTreeGenerator
# ---------------------------------------------------------------------------


def _slug(name: str) -> str:
    """Convert a human-readable name into a filesystem-safe slug."""
    return name.lower().replace(" ", "_").replace("-", "_")


class DomainFolderTreeGenerator:
    """Generate a clean folder-tree structure from a ``DomainBlueprint``.

    This generator is the authoritative implementation for turning a
    ``DomainBlueprint`` into a ``FolderTree``.  It delegates all low-level
    tree construction to the ``packages.folder_tree`` service (via
    ``FolderTreeService.create_tree``), but can also produce a ``FolderTree``
    *directly* (without a running service) for testing and offline use.

    All generation events are logged to the Tape under the
    ``domain.folder_tree_generated`` event type.

    Parameters
    ----------
    tape_service:
        Shared Tape service for audit logging.

    Usage::

        generator = DomainFolderTreeGenerator(tape_service=tape_svc)
        folder_tree = await generator.generate(blueprint)
    """

    def __init__(self, tape_service: TapeService) -> None:
        self._tape = tape_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate(
        self,
        blueprint: DomainBlueprint,
        evaluation_criteria: EvaluationCriteria | None = None,
    ) -> FolderTree:
        """Generate a ``FolderTree`` from a ``DomainBlueprint``.

        Parameters
        ----------
        blueprint:
            The domain blueprint to materialise as a folder tree.
        evaluation_criteria:
            Optional evaluation criteria.  If ``None``, sensible defaults
            are derived from the blueprint's ``DomainConfig``.

        Returns
        -------
        FolderTree
            A fully-populated ``FolderTree`` ready to be persisted.
        """
        criteria = evaluation_criteria or self._derive_criteria(blueprint)
        tree = self._build_tree(blueprint, criteria)

        await self._tape.log_event(
            event_type="domain.folder_tree_generated",
            payload={
                "blueprint_id": str(blueprint.id),
                "domain_id": blueprint.domain_id,
                "domain_name": blueprint.domain_name,
                "root_path": tree.root_path,
                "node_count": len(tree.nodes),
                "file_count": sum(
                    1 for n in tree.nodes.values()
                    if n.node_type == NodeType.FILE
                ),
                "directory_count": sum(
                    1 for n in tree.nodes.values()
                    if n.node_type == NodeType.DIRECTORY
                ),
                "agent_count": len(blueprint.agents),
                "skill_count": len(blueprint.skills),
                "workflow_count": len(blueprint.workflows),
            },
            agent_id="domain-folder-tree-generator",
        )

        return tree

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _derive_criteria(self, blueprint: DomainBlueprint) -> EvaluationCriteria:
        """Derive evaluation criteria from the blueprint config."""
        config = blueprint.config
        # High-priority domains get stricter SLAs
        if config.priority_level == "critical":
            return EvaluationCriteria(
                accuracy_threshold=0.95,
                response_time_sla_seconds=10.0,
                human_approval_rate=0.99,
                uptime_target=99.99,
            )
        if config.priority_level == "high":
            return EvaluationCriteria(
                accuracy_threshold=0.90,
                response_time_sla_seconds=20.0,
                human_approval_rate=0.95,
                uptime_target=99.9,
            )
        # Normal / low
        return EvaluationCriteria()

    def _build_tree(
        self,
        blueprint: DomainBlueprint,
        criteria: EvaluationCriteria,
    ) -> FolderTree:
        """Construct the FolderTree from blueprint data.

        This method does *not* call the FolderTreeService — it builds the
        FolderTree model directly, which makes it usable offline and in tests
        without an async context.
        """
        root = blueprint.domain_name.replace(" ", "_")
        nodes: dict[str, FolderTreeNode] = {}

        def _add_dir(path: str, name: str) -> None:
            nodes[path] = FolderTreeNode(
                path=path,
                name=name,
                node_type=NodeType.DIRECTORY,
            )

        def _add_file(path: str, name: str, content: str = "") -> None:
            nodes[path] = FolderTreeNode(
                path=path,
                name=name,
                node_type=NodeType.FILE,
                content=content,
            )

        # ---- Root ----
        _add_dir(root, root)

        # ---- agents/ ----
        agents_path = f"{root}/agents"
        _add_dir(agents_path, "agents")
        nodes[root].children.append(agents_path)

        for agent in blueprint.agents:
            agent_slug = _slug(agent.name)
            agent_path = f"{agents_path}/{agent_slug}"
            _add_dir(agent_path, agent_slug)
            nodes[agents_path].children.append(agent_path)

            # role.md
            role_path = f"{agent_path}/role.md"
            role_content = (
                f"# {agent.name}\n\n"
                f"**Role**: {agent.role}\n\n"
                f"**Goal**: {agent.goal}\n"
            )
            if agent.backstory:
                role_content += f"\n## Backstory\n\n{agent.backstory}\n"
            _add_file(role_path, "role.md", role_content)
            nodes[agent_path].children.append(role_path)

            # goals.md
            goals_path = f"{agent_path}/goals.md"
            goals_content = f"# Goals\n\n- {agent.goal or 'No goals defined'}\n"
            _add_file(goals_path, "goals.md", goals_content)
            nodes[agent_path].children.append(goals_path)

            # tools/
            tools_path = f"{agent_path}/tools"
            _add_dir(tools_path, "tools")
            nodes[agent_path].children.append(tools_path)

            for tool in agent.tools:
                tool_slug = _slug(str(tool))
                tool_path = f"{tools_path}/{tool_slug}.md"
                _add_file(
                    tool_path,
                    f"{tool_slug}.md",
                    f"# {tool}\n\nTool definition for {tool}.\n",
                )
                nodes[tools_path].children.append(tool_path)

            # Also add capability stubs if no explicit tools listed
            if not agent.tools:
                for cap in agent.capabilities:
                    cap_slug = _slug(str(cap))
                    cap_path = f"{tools_path}/{cap_slug}.md"
                    _add_file(
                        cap_path,
                        f"{cap_slug}.md",
                        f"# {cap}\n\nCapability stub for {cap}.\n",
                    )
                    nodes[tools_path].children.append(cap_path)

            # examples/
            examples_path = f"{agent_path}/examples"
            _add_dir(examples_path, "examples")
            nodes[agent_path].children.append(examples_path)

        # ---- skills/ ----
        skills_path = f"{root}/skills"
        _add_dir(skills_path, "skills")
        nodes[root].children.append(skills_path)

        for skill in blueprint.skills:
            skill_slug = _slug(skill.name)
            skill_file = f"{skills_path}/{skill_slug}.py"
            reused_note = " (reused)" if skill.is_reused else ""
            skill_content = (
                f'"""{skill.name}{reused_note} — {skill.description}"""\n\n'
                f"def execute(*args, **kwargs):\n"
                f"    \"\"\"Execute the {skill.name} skill.\"\"\"\n"
                f"    pass\n"
            )
            _add_file(skill_file, f"{skill_slug}.py", skill_content)
            nodes[skills_path].children.append(skill_file)

        # ---- workflows/ ----
        workflows_path = f"{root}/workflows"
        _add_dir(workflows_path, "workflows")
        nodes[root].children.append(workflows_path)

        for workflow in blueprint.workflows:
            wf_slug = _slug(workflow.name)
            wf_path = f"{workflows_path}/{wf_slug}"
            _add_dir(wf_path, wf_slug)
            nodes[workflows_path].children.append(wf_path)

            # workflow.json
            wf_json_path = f"{wf_path}/workflow.json"
            wf_data = {
                "id": workflow.workflow_id,
                "name": workflow.name,
                "type": str(workflow.workflow_type),
                "description": workflow.description,
                "agent_ids": workflow.agent_ids,
                "steps": workflow.steps,
            }
            _add_file(
                wf_json_path,
                "workflow.json",
                json.dumps(wf_data, indent=2),
            )
            nodes[wf_path].children.append(wf_json_path)

            # example_inputs/
            examples_wf_path = f"{wf_path}/example_inputs"
            _add_dir(examples_wf_path, "example_inputs")
            nodes[wf_path].children.append(examples_wf_path)

        # ---- templates/ ----
        templates_path = f"{root}/templates"
        _add_dir(templates_path, "templates")
        nodes[root].children.append(templates_path)

        # ---- config/ ----
        config_path = f"{root}/config"
        _add_dir(config_path, "config")
        nodes[root].children.append(config_path)

        config_file = f"{config_path}/domain_config.json"
        config_data = {
            "domain_id": blueprint.domain_id,
            "domain_name": blueprint.domain_name,
            "max_agents": blueprint.config.max_agents,
            "max_concurrent_tasks": blueprint.config.max_concurrent_tasks,
            "requires_human_approval": blueprint.config.requires_human_approval,
            "data_retention_days": blueprint.config.data_retention_days,
            "priority_level": blueprint.config.priority_level,
            "custom_settings": blueprint.config.custom_settings,
        }
        _add_file(
            config_file,
            "domain_config.json",
            json.dumps(config_data, indent=2),
        )
        nodes[config_path].children.append(config_file)

        # ---- data_sources/ ----
        data_sources_path = f"{root}/data_sources"
        _add_dir(data_sources_path, "data_sources")
        nodes[root].children.append(data_sources_path)

        # ---- evaluation/ ----
        evaluation_path = f"{root}/evaluation"
        _add_dir(evaluation_path, "evaluation")
        nodes[root].children.append(evaluation_path)

        criteria_file = f"{evaluation_path}/criteria.json"
        criteria_data = {
            "accuracy_threshold": criteria.accuracy_threshold,
            "response_time_sla_seconds": criteria.response_time_sla_seconds,
            "human_approval_rate": criteria.human_approval_rate,
            "uptime_target": criteria.uptime_target,
            "custom_metrics": criteria.custom_metrics,
        }
        _add_file(
            criteria_file,
            "criteria.json",
            json.dumps(criteria_data, indent=2),
        )
        nodes[evaluation_path].children.append(criteria_file)

        # ---- README.md ----
        readme_path = f"{root}/README.md"
        agent_list = "\n".join(
            f"- **{a.name}** ({a.role}) — {a.goal}" for a in blueprint.agents
        )
        skill_list = "\n".join(
            f"- **{s.name}** — {s.description}" for s in blueprint.skills
        )
        workflow_list = "\n".join(
            f"- **{w.name}** ({w.workflow_type})" for w in blueprint.workflows
        )
        readme_content = (
            f"# {blueprint.domain_name}\n\n"
            f"{blueprint.description}\n\n"
            f"## Agents\n\n{agent_list or '_No agents defined_'}\n\n"
            f"## Skills\n\n{skill_list or '_No skills defined_'}\n\n"
            f"## Workflows\n\n{workflow_list or '_No workflows defined_'}\n\n"
            f"## Structure\n\n"
            f"- `agents/` — Domain agents and their configurations\n"
            f"- `skills/` — Domain skills and capabilities\n"
            f"- `workflows/` — Workflow definitions and examples\n"
            f"- `templates/` — Reusable prompt templates\n"
            f"- `config/` — Domain configuration\n"
            f"- `data_sources/` — Data source connections\n"
            f"- `evaluation/` — Success criteria and quality metrics\n"
        )
        _add_file(readme_path, "README.md", readme_content)
        nodes[root].children.append(readme_path)

        return FolderTree(
            domain_id=blueprint.domain_id,
            root_path=root,
            nodes=nodes,
        )
