"""GitNexus-inspired automatic SKILL.md generation for InkosAI.

Every agent and skill in a domain's folder tree gets an auto-generated
``SKILL.md`` file that describes:

- **Capabilities** — what the agent/skill can do
- **Dependencies** — other agents, skills, and resources it relies on
- **Usage examples** — how to invoke or interact with it
- **Metadata** — version, status, last updated, etc.

Prime automatically creates and maintains these files during domain
creation and whenever the folder tree changes.  The SKILL.md files are
used by:

- **Prime** — for reasoning about agent/skill capabilities
- **Impact Analyzer** — for dependency-aware change prediction
- **Dependency Graph Builder** — for reference edge extraction
- **Simulation Engine** — for capability-aware scenario modelling

Architecture::

    SkillMdGenerator
    ├── generate_for_agent()   — AgentBlueprint → SKILL.md content
    ├── generate_for_skill()   — SkillBlueprint → SKILL.md content
    ├── generate_for_domain()  — Generate all SKILL.md files for a domain
    ├── update_skill_md()      — Re-generate a single SKILL.md after changes
    └── parse_skill_md()       — Parse an existing SKILL.md back into a model

    SkillMdContent — Parsed representation of a SKILL.md file
"""

from __future__ import annotations

import contextlib
import re
from datetime import UTC, datetime

from pydantic import BaseModel

from packages.folder_tree import (
    FolderTreeNode,
    FolderTreeService,
    NodeType,
)
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class SkillMdContent(BaseModel):
    """Parsed representation of a SKILL.md file.

    Used to round-trip SKILL.md content and for structured access
    to the metadata within.
    """

    title: str = ""
    capabilities: list[str] = []
    dependencies: list[str] = []
    usage_examples: list[str] = []
    version: str = "1.0.0"
    status: str = "active"
    last_updated: str = ""
    raw_content: str = ""


class _RoleMdResult(BaseModel):
    """Internal helper for _parse_role_md return type."""

    role: str = "specialist"
    goal: str = ""
    capabilities: list[str] = []
    tools: list[str] = []


# ---------------------------------------------------------------------------
# SkillMdGenerator
# ---------------------------------------------------------------------------

class SkillMdGenerator:
    """Automatically generate and maintain SKILL.md files.

    Produces structured SKILL.md files for every agent and skill in a
    domain's folder tree.  These files serve as the machine-readable
    capability manifests that Prime and other engines use for reasoning.

    Parameters
    ----------
    folder_tree_service:
        The folder tree service to read/write domain trees.
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
    # Public API — single entity generation
    # ------------------------------------------------------------------

    def generate_for_agent(
        self,
        agent_name: str,
        role: str = "specialist",
        goal: str = "",
        capabilities: list[str] | None = None,
        tools: list[str] | None = None,
        backstory: str = "",
        version: str = "1.0.0",
        status: str = "active",
    ) -> str:
        """Generate SKILL.md content for an agent.

        Parameters
        ----------
        agent_name:
            Human-readable agent name.
        role:
            Agent role (e.g. ``"coordinator"``, ``"specialist"``).
        goal:
            The agent's primary objective.
        capabilities:
            List of capability names.
        tools:
            List of tool names the agent uses.
        backstory:
            Optional agent backstory / context.
        version:
            Skill manifest version.
        status:
            Current status (``"active"``, ``"deprecated"``, etc.).

        Returns
        -------
        str
            The complete SKILL.md markdown content.
        """
        caps = capabilities or []
        tool_list = tools or []
        now = datetime.now(UTC).strftime("%Y-%m-%d")

        lines: list[str] = []
        lines.append(f"# SKILL.md -- {agent_name}")
        lines.append("")
        lines.append(f"> Auto-generated capability manifest for **{agent_name}**")
        lines.append("")
        lines.append("## Metadata")
        lines.append("")
        lines.append("| Field | Value |")
        lines.append("|-------|-------|")
        lines.append(f"| Version | `{version}` |")
        lines.append(f"| Status | {status} |")
        lines.append(f"| Role | {role} |")
        lines.append(f"| Last Updated | {now} |")
        lines.append("")

        lines.append("## Capabilities")
        lines.append("")
        if caps:
            for cap in caps:
                lines.append(f"- {cap}")
        else:
            lines.append("- _No capabilities defined_")
        lines.append("")

        lines.append("## Dependencies")
        lines.append("")
        if tool_list:
            for tool in tool_list:
                slug = tool.lower().replace(" ", "_").replace("-", "_")
                lines.append(f"- `tools/{slug}.md`")
        else:
            lines.append("- _No dependencies_")
        lines.append("")

        lines.append("## Usage Examples")
        lines.append("")
        lines.append("```")
        lines.append(f"# Invoke {agent_name}")
        lines.append(f'agent = registry.get_agent("{agent_name.lower().replace(" ", "_")}")')
        lines.append('result = await agent.execute(task="...", context={})')
        lines.append("```")
        lines.append("")

        if backstory:
            lines.append("## Backstory")
            lines.append("")
            lines.append(backstory)
            lines.append("")

        return "\n".join(lines)

    def generate_for_skill(
        self,
        skill_name: str,
        description: str = "",
        dependencies: list[str] | None = None,
        version: str = "1.0.0",
        status: str = "active",
        is_reused: bool = False,
    ) -> str:
        """Generate SKILL.md content for a skill.

        Parameters
        ----------
        skill_name:
            Human-readable skill name.
        description:
            What the skill does.
        dependencies:
            List of file paths the skill depends on.
        version:
            Skill manifest version.
        status:
            Current status.
        is_reused:
            Whether the skill is reused from another domain.

        Returns
        -------
        str
            The complete SKILL.md markdown content.
        """
        deps = dependencies or []
        now = datetime.now(UTC).strftime("%Y-%m-%d")
        slug = skill_name.lower().replace(" ", "_").replace("-", "_")

        lines: list[str] = []
        lines.append(f"# SKILL.md -- {skill_name}")
        lines.append("")
        reused_tag = " (reused)" if is_reused else ""
        lines.append(
            f"> Auto-generated capability manifest for **{skill_name}**{reused_tag}"
        )
        lines.append("")

        lines.append("## Metadata")
        lines.append("")
        lines.append("| Field | Value |")
        lines.append("|-------|-------|")
        lines.append(f"| Version | `{version}` |")
        lines.append(f"| Status | {status} |")
        lines.append(f"| Reused | {'Yes' if is_reused else 'No'} |")
        lines.append(f"| Last Updated | {now} |")
        lines.append("")

        if description:
            lines.append("## Description")
            lines.append("")
            lines.append(description)
            lines.append("")

        lines.append("## Dependencies")
        lines.append("")
        if deps:
            for dep in deps:
                lines.append(f"- `{dep}`")
        else:
            lines.append("- _No dependencies_")
        lines.append("")

        lines.append("## Usage Examples")
        lines.append("")
        lines.append("```python")
        lines.append(f"# Execute {skill_name}")
        lines.append(f"from packages.skills import {slug}")
        lines.append(f"result = await {slug}.execute(*args, **kwargs)")
        lines.append("```")
        lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Public API — domain-wide generation
    # ------------------------------------------------------------------

    async def generate_for_domain(
        self,
        domain_id: str,
    ) -> dict[str, str]:
        """Generate SKILL.md files for all agents and skills in a domain.

        Writes the generated SKILL.md files into the domain's folder tree
        and returns a mapping of path -> content.

        Parameters
        ----------
        domain_id:
            The domain to generate SKILL.md files for.

        Returns
        -------
        dict[str, str]
            Mapping of relative path to SKILL.md content.
        """
        tree = await self._fts.get_tree(domain_id)
        results: dict[str, str] = {}

        items = list(tree.nodes.items())
        for path, node_obj in items:
            node = node_obj
            name = node.name
            content = node.content

            # Generate SKILL.md for agent directories
            if (
                node.node_type == NodeType.DIRECTORY
                and "/agents/" in path
                and path.count("/") == 2  # domain/agents/agent_name
            ):
                skill_md_path = f"{path}/SKILL.md"
                relative = skill_md_path.removeprefix(
                    tree.root_path + "/"
                ) if skill_md_path.startswith(tree.root_path + "/") else skill_md_path

                # Parse agent info from existing files
                role_md = self._find_sibling_content(
                    path, "role.md", tree.nodes
                )
                agent_name = name.replace("_", " ").title()
                role = "specialist"
                goal = ""
                capabilities: list[str] = []
                tools: list[str] = []

                if role_md:
                    parsed = self._parse_role_md(role_md)
                    role = parsed.role or role
                    goal = parsed.goal or goal
                    capabilities = parsed.capabilities
                    tools = parsed.tools

                skill_md = self.generate_for_agent(
                    agent_name=agent_name,
                    role=role,
                    goal=goal,
                    capabilities=capabilities,
                    tools=tools,
                )
                results[relative] = skill_md

                # Write into the folder tree
                with contextlib.suppress(Exception):
                    await self._fts.write_file(
                        domain_id, relative, skill_md
                    )

            # Generate SKILL.md for skill Python files
            if (
                node.node_type == NodeType.FILE
                and "/skills/" in path
                and name.endswith(".py")
                and name != "SKILL.md"
            ):
                # The SKILL.md goes alongside the .py file
                skill_md_name = name.replace(".py", "_SKILL.md")
                skill_dir_path = path.rsplit("/", 1)[0] if "/" in path else ""
                # Actually place it in the skills/ directory
                skill_md_path = f"{skill_dir_path}/{skill_md_name}"
                relative = skill_md_path.removeprefix(
                    tree.root_path + "/"
                ) if skill_md_path.startswith(tree.root_path + "/") else skill_md_path

                skill_name = name.replace(".py", "").replace("_", " ").title()
                description = self._extract_docstring(content)

                skill_md = self.generate_for_skill(
                    skill_name=skill_name,
                    description=description,
                )
                results[relative] = skill_md

                with contextlib.suppress(Exception):
                    await self._fts.write_file(
                        domain_id, relative, skill_md
                    )

        await self._tape.log_event(
            event_type="prime.skill_md_generated",
            payload={
                "domain_id": domain_id,
                "file_count": len(results),
                "paths": list(results.keys()),
            },
            agent_id="skill-md-generator",
        )

        return results

    # ------------------------------------------------------------------
    # Public API — update / parse
    # ------------------------------------------------------------------

    async def update_skill_md(
        self,
        domain_id: str,
        path: str,
    ) -> str:
        """Re-generate a single SKILL.md file after changes.

        Parameters
        ----------
        domain_id:
            The domain containing the SKILL.md.
        path:
            Relative path to the SKILL.md file.

        Returns
        -------
        str
            The updated SKILL.md content.
        """
        tree = await self._fts.get_tree(domain_id)

        if "/agents/" in path:
            # Extract agent directory from path
            parts = path.split("/")
            # Find the agent directory index
            agent_idx = None
            for i, part in enumerate(parts):
                if part == "agents" and i + 1 < len(parts):
                    agent_idx = i + 1
                    break

            if agent_idx is not None:
                agent_dir = "/".join(parts[: agent_idx + 1])
                full_dir = f"{tree.root_path}/{agent_dir}"

                role_md = self._find_sibling_content(
                    full_dir, "role.md", tree.nodes
                )
                agent_name = parts[agent_idx].replace("_", " ").title()
                role = "specialist"
                goal = ""
                capabilities: list[str] = []
                tools: list[str] = []

                if role_md:
                    parsed = self._parse_role_md(role_md)
                    role = parsed.role or role
                    goal = parsed.goal or goal
                    capabilities = parsed.capabilities
                    tools = parsed.tools

                content = self.generate_for_agent(
                    agent_name=agent_name,
                    role=role,
                    goal=goal,
                    capabilities=capabilities,
                    tools=tools,
                )
            else:
                content = self.generate_for_agent(
                    agent_name="Unknown Agent",
                )

        elif "/skills/" in path:
            # Parse skill name from path
            parts = path.split("/")
            skill_name = parts[-1].replace("_SKILL.md", "").replace(
                "_", " "
            ).title()
            content = self.generate_for_skill(
                skill_name=skill_name,
            )
        else:
            content = self.generate_for_agent(
                agent_name="Unknown",
            )

        await self._fts.write_file(domain_id, path, content)

        await self._tape.log_event(
            event_type="prime.skill_md_updated",
            payload={
                "domain_id": domain_id,
                "path": path,
            },
            agent_id="skill-md-generator",
        )

        return content

    @staticmethod
    def parse_skill_md(content: str) -> SkillMdContent:
        """Parse an existing SKILL.md file back into a structured model.

        Parameters
        ----------
        content:
            The raw SKILL.md markdown content.

        Returns
        -------
        SkillMdContent
            Parsed representation.
        """
        result = SkillMdContent(raw_content=content)

        # Extract title
        title_match = re.search(r"^# SKILL.md -- (.+)$", content, re.MULTILINE)
        if title_match:
            result.title = title_match.group(1).strip()

        # Extract capabilities
        in_caps = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("## Capabilities"):
                in_caps = True
                continue
            if in_caps and stripped.startswith("## "):
                break
            if in_caps and stripped.startswith("- ") and not stripped.startswith(
                "- _No"
            ):
                result.capabilities.append(stripped[2:])

        # Extract dependencies
        in_deps = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("## Dependencies"):
                in_deps = True
                continue
            if in_deps and stripped.startswith("## "):
                break
            if in_deps and stripped.startswith("- ") and not stripped.startswith(
                "- _No"
            ):
                # Remove backtick wrapping
                dep = stripped[2:].strip().strip("`")
                result.dependencies.append(dep)

        # Extract usage examples
        in_usage = False
        in_code_block = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("## Usage Examples"):
                in_usage = True
                continue
            if in_usage and stripped.startswith("## "):
                break
            if in_usage and stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_usage and in_code_block and stripped:
                result.usage_examples.append(stripped)

        # Extract metadata
        version_match = re.search(r"\| Version \| `(.+?)` \|", content)
        if version_match:
            result.version = version_match.group(1)

        status_match = re.search(r"\| Status \| (.+?) \|", content)
        if status_match:
            result.status = status_match.group(1).strip()

        updated_match = re.search(r"\| Last Updated \| (.+?) \|", content)
        if updated_match:
            result.last_updated = updated_match.group(1).strip()

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_sibling_content(
        dir_path: str,
        sibling_name: str,
        nodes: dict[str, FolderTreeNode],
    ) -> str:
        """Find and return the content of a sibling file in the same directory."""
        sibling_path = f"{dir_path}/{sibling_name}"
        node = nodes.get(sibling_path)
        if node is not None:
            return str(node.content)
        return ""

    @staticmethod
    def _parse_role_md(content: str) -> _RoleMdResult:
        """Parse a role.md file to extract agent metadata."""
        result = _RoleMdResult()

        # Extract role
        role_match = re.search(r"\*\*Role\*\*:\s*(.+)", content)
        if role_match:
            result.role = role_match.group(1).strip()

        # Extract goal
        goal_match = re.search(r"\*\*Goal\*\*:\s*(.+)", content)
        if goal_match:
            result.goal = goal_match.group(1).strip()

        # Extract capabilities from tool stubs
        # (The role.md itself doesn't usually list capabilities,
        # but we can extract them from the Tools section)
        in_tools = False
        caps: list[str] = []
        for line in content.splitlines():
            stripped = line.strip()
            if "Tool definition" in stripped or "Capability stub" in stripped:
                # Extract from heading
                cap_match = re.search(r"# (.+?)\n", stripped)
                if cap_match:
                    caps.append(cap_match.group(1).strip())
            if stripped.startswith("## Tools") or stripped.startswith("## Capabilities"):
                in_tools = True
                continue
            if in_tools and stripped.startswith("- "):
                caps.append(stripped[2:])

        if caps:
            result.capabilities = caps
            result.tools = caps  # tools and caps overlap in role.md

        return result

    @staticmethod
    def _extract_docstring(content: str) -> str:
        """Extract the module docstring from a Python file."""
        match = re.search(r'"""(.+?)"""', content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""



