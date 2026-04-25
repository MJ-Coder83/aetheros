"""InkosAI Folder Tree -- Canonical filesystem representation for Domains and Canvases.

Every Domain and Canvas has a dual representation:
  - **Folder Tree** (source of truth) -- stored on disk / in AetherGit
  - **Visual Graph** (user-facing) -- synchronized in real time with the folder tree

The folder-tree is the stable backbone. It makes Prime's reasoning deterministic,
portable, auditable, and easy for coding agents to work with, while the visual
Canvas provides the delightful user experience.

Architecture::

    FolderTreeService
    +------ create_tree()         -- Generate a folder tree from a DomainBlueprint
    +------ read_file()           -- Read a file at a given path
    +------ list_directory()      -- List contents of a directory
    +------ write_file()          -- Write content to a file path
    +------ create_directory()    -- Create a new directory
    +------ move_path()           -- Move/rename a file or directory
    +------ delete_path()         -- Delete a file or directory
    +------ search()              -- Search files by name, content, or semantic query
    +------ get_tree()            -- Get the full tree structure for a domain
    +------ diff_trees()          -- Compare two versions of a tree
    +------ sync_from_canvas()    -- Synchronize visual canvas changes into the tree

    FolderTreeNode             -- A single node (file or directory) in the tree
    FolderTree                 -- The complete tree for a domain
    FolderOperation            -- A single file/folder operation (create/edit/move/delete)
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from enum import StrEnum
from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class NodeType(StrEnum):
    """Type of a folder tree node."""
    FILE = "file"
    DIRECTORY = "directory"


class FolderOpType(StrEnum):
    """Types of folder operations."""
    CREATE = "create"
    EDIT = "edit"
    MOVE = "move"
    DELETE = "delete"


class FolderViewMode(StrEnum):
    """Canvas view mode -- visual or folder."""
    VISUAL = "visual"
    FOLDER = "folder"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class FolderTreeNode(BaseModel):
    """A single node in the folder tree -- either a file or a directory."""
    path: str                          # e.g. "/agents/contract_analyst/role.md"
    name: str                          # e.g. "role.md"
    node_type: NodeType                # file or directory
    content: str = ""                  # File content (empty for directories)
    children: list[str] = []           # Child paths (for directories)
    metadata: dict[str, object] = {}   # Arbitrary metadata (e.g. last_modified, size)


class FolderTree(BaseModel):
    """Complete folder tree for a domain -- the canonical source of truth."""
    domain_id: str
    root_path: str                     # e.g. "Legal_Research_Domain/"
    nodes: dict[str, FolderTreeNode] = Field(default_factory=dict)
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class FolderOperation(BaseModel):
    """A single folder operation -- used in proposals, skill evolution, and Tape logging."""
    id: UUID = Field(default_factory=uuid4)
    op_type: FolderOpType
    path: str                          # Target path
    content: str = ""                  # New content (for create/edit)
    old_path: str = ""                 # Previous path (for move)
    description: str = ""              # Human-readable description


class FolderDiff(BaseModel):
    """Diff between two versions of a folder tree."""
    domain_id: str
    source_version: int
    target_version: int
    operations: list[FolderOperation] = []
    summary: str = ""


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class FolderTreeError(Exception):
    """Base exception for folder tree operations."""


class PathNotFoundError(FolderTreeError):
    """Raised when a requested path does not exist in the tree."""


class PathAlreadyExistsError(FolderTreeError):
    """Raised when trying to create a path that already exists."""


class InvalidPathError(FolderTreeError):
    """Raised when a path is malformed or outside the domain root."""


class DomainTreeNotFoundError(FolderTreeError):
    """Raised when a domain has no folder tree."""


# ---------------------------------------------------------------------------
# Folder tree store (in-memory; will be Postgres-backed later)
# ---------------------------------------------------------------------------

class FolderTreeStore:
    """In-memory store for domain folder trees."""

    def __init__(self) -> None:
        self._trees: dict[str, FolderTree] = {}

    def add(self, tree: FolderTree) -> None:
        self._trees[tree.domain_id] = tree

    def get(self, domain_id: str) -> FolderTree | None:
        return self._trees.get(domain_id)

    def update(self, tree: FolderTree) -> None:
        self._trees[tree.domain_id] = tree

    def remove(self, domain_id: str) -> FolderTree | None:
        return self._trees.pop(domain_id, None)

    def list_domains(self) -> list[str]:
        return list(self._trees.keys())


# ---------------------------------------------------------------------------
# FolderTreeGenerator -- generates folder trees from DomainBlueprints
# ---------------------------------------------------------------------------

class FolderTreeGenerator:
    """Generates a clean folder-tree structure from a DomainBlueprint.

    The generated tree follows the canonical layout:
        Domain_Name/
        +------ agents/
        |   +------ <agent_slug>/
        |       +------ role.md
        |       +------ goals.md
        |       +------ tools/
        |       +------ examples/
        +------ skills/
        |   +------ <skill_slug>.py
        +------ workflows/
        |   +------ <workflow_slug>/
        |       +------ workflow.json
        |       +------ example_inputs/
        +------ templates/
        |   +------ <template>.md
        +------ config/
        |   +------ domain_config.json
        +------ data_sources/
        +------ README.md
    """

    def generate(
        self,
        domain_id: str,
        domain_name: str,
        description: str,
        agents: Sequence[object],
        skills: Sequence[object],
        workflows: Sequence[object],
        config: object | None = None,
    ) -> FolderTree:
        """Generate a folder tree from domain blueprint data.

        Args:
            domain_id: The domain's slug ID.
            domain_name: Human-readable domain name.
            description: Domain description.
            agents: List of agent blueprints (with name, role, goal, capabilities attrs).
            skills: List of skill blueprints (with skill_id, name, description attrs).
            workflows: List of workflow blueprints (with workflow_id, name, steps attrs).
            config: Optional domain config object.

        Returns:
            A FolderTree representing the canonical folder structure.
        """
        root = domain_name.replace(" ", "_")
        nodes: dict[str, FolderTreeNode] = {}

        def _add_dir(path: str, name: str) -> None:
            nodes[path] = FolderTreeNode(
                path=path, name=name, node_type=NodeType.DIRECTORY,
            )

        def _add_file(path: str, name: str, content: str = "") -> None:
            nodes[path] = FolderTreeNode(
                path=path, name=name, node_type=NodeType.FILE, content=content,
            )

        def _slug(name: str) -> str:
            return name.lower().replace(" ", "_").replace("-", "_")

        # Root
        _add_dir(root, root)

        # agents/
        agents_path = f"{root}/agents"
        _add_dir(agents_path, "agents")
        nodes[root].children.append(agents_path)

        for agent in agents:
            agent_name = _slug(getattr(agent, "name", "unnamed_agent"))
            agent_path = f"{agents_path}/{agent_name}"
            _add_dir(agent_path, agent_name)
            nodes[agents_path].children.append(agent_path)

            # role.md
            role_path = f"{agent_path}/role.md"
            role_content = f"# {getattr(agent, 'name', 'Unnamed')}\n\n"
            role_content += f"**Role**: {getattr(agent, 'role', 'specialist')}\n\n"
            role_content += f"**Goal**: {getattr(agent, 'goal', 'No goal defined')}\n"
            _add_file(role_path, "role.md", role_content)
            nodes[agent_path].children.append(role_path)

            # goals.md
            goals_path = f"{agent_path}/goals.md"
            goals_content = f"# Goals\n\n- {getattr(agent, 'goal', 'No goals defined')}\n"
            _add_file(goals_path, "goals.md", goals_content)
            nodes[agent_path].children.append(goals_path)

            # tools/
            tools_path = f"{agent_path}/tools"
            _add_dir(tools_path, "tools")
            nodes[agent_path].children.append(tools_path)

            for cap in getattr(agent, "capabilities", []):
                tool_path = f"{tools_path}/{_slug(str(cap))}.md"
                _add_file(tool_path, f"{_slug(str(cap))}.md", f"# {cap}\n\nTool definition for {cap}.\n")
                nodes[tools_path].children.append(tool_path)

            # examples/
            examples_path = f"{agent_path}/examples"
            _add_dir(examples_path, "examples")
            nodes[agent_path].children.append(examples_path)

        # skills/
        skills_path = f"{root}/skills"
        _add_dir(skills_path, "skills")
        nodes[root].children.append(skills_path)

        for skill in skills:
            skill_name = _slug(getattr(skill, "name", "unnamed_skill"))
            skill_file = f"{skills_path}/{skill_name}.py"
            skill_content = f'"""{getattr(skill, "name", "Unnamed Skill")} -- {getattr(skill, "description", "")}"""\n\n'
            skill_content += "def execute(*args, **kwargs):\n    pass\n"
            _add_file(skill_file, f"{skill_name}.py", skill_content)
            nodes[skills_path].children.append(skill_file)

        # workflows/
        workflows_path = f"{root}/workflows"
        _add_dir(workflows_path, "workflows")
        nodes[root].children.append(workflows_path)

        for workflow in workflows:
            wf_name = _slug(getattr(workflow, "name", "unnamed_workflow"))
            wf_path = f"{workflows_path}/{wf_name}"
            _add_dir(wf_path, wf_name)
            nodes[workflows_path].children.append(wf_path)

            # workflow.json
            wf_json_path = f"{wf_path}/workflow.json"
            import json
            wf_data = {
                "name": getattr(workflow, "name", wf_name),
                "type": str(getattr(workflow, "workflow_type", "sequential")),
                "steps": getattr(workflow, "steps", []),
            }
            _add_file(wf_json_path, "workflow.json", json.dumps(wf_data, indent=2))
            nodes[wf_path].children.append(wf_json_path)

            # example_inputs/
            examples_wf_path = f"{wf_path}/example_inputs"
            _add_dir(examples_wf_path, "example_inputs")
            nodes[wf_path].children.append(examples_wf_path)

        # templates/
        templates_path = f"{root}/templates"
        _add_dir(templates_path, "templates")
        nodes[root].children.append(templates_path)

        # config/
        config_path = f"{root}/config"
        _add_dir(config_path, "config")
        nodes[root].children.append(config_path)

        config_file = f"{config_path}/domain_config.json"
        import json
        config_data = {}
        if config is not None:
            config_data = {
                "max_agents": getattr(config, "max_agents", 10),
                "max_concurrent_tasks": getattr(config, "max_concurrent_tasks", 5),
                "requires_human_approval": getattr(config, "requires_human_approval", True),
                "priority_level": getattr(config, "priority_level", "normal"),
            }
        _add_file(config_file, "domain_config.json", json.dumps(config_data, indent=2))
        nodes[config_path].children.append(config_file)

        # data_sources/
        data_sources_path = f"{root}/data_sources"
        _add_dir(data_sources_path, "data_sources")
        nodes[root].children.append(data_sources_path)

        # README.md
        readme_path = f"{root}/README.md"
        readme_content = f"# {domain_name}\n\n{description}\n\n"
        readme_content += "## Structure\n\n"
        readme_content += "- `agents/` -- Domain agents and their configurations\n"
        readme_content += "- `skills/` -- Domain skills and capabilities\n"
        readme_content += "- `workflows/` -- Workflow definitions and examples\n"
        readme_content += "- `templates/` -- Reusable prompt templates\n"
        readme_content += "- `config/` -- Domain configuration\n"
        readme_content += "- `data_sources/` -- Data source connections\n"
        _add_file(readme_path, "README.md", readme_content)
        nodes[root].children.append(readme_path)

        return FolderTree(
            domain_id=domain_id,
            root_path=root,
            nodes=nodes,
        )


# ---------------------------------------------------------------------------
# FolderTreeService -- the main public API
# ---------------------------------------------------------------------------

class FolderTreeService:
    """Manages folder-tree representations for domains.

    Every domain has a dual representation:
      - **Folder Tree** (source of truth) -- stored here and in AetherGit
      - **Visual Graph** (user-facing) -- synchronized in real time

    The folder tree is the primary source of truth for AetherGit commits,
    Prime's "Folder Thinking Mode", and all file/folder-based operations.

    All operations are logged to the Tape for full auditability.
    """

    def __init__(
        self,
        tape_service: TapeService,
        store: FolderTreeStore | None = None,
        generator: FolderTreeGenerator | None = None,
    ) -> None:
        self._tape = tape_service
        self._store = store or FolderTreeStore()
        self._generator = generator or FolderTreeGenerator()

    # ------------------------------------------------------------------
    # create_tree
    # ------------------------------------------------------------------

    async def create_tree(
        self,
        domain_id: str,
        domain_name: str,
        description: str,
        agents: Sequence[object],
        skills: Sequence[object],
        workflows: Sequence[object],
        config: object | None = None,
    ) -> FolderTree:
        """Generate and store a folder tree for a domain.

        This is called automatically during domain creation to produce
        the canonical folder-tree structure alongside the blueprint.

        Args:
            domain_id: The domain's slug ID.
            domain_name: Human-readable domain name.
            description: Domain description.
            agents: List of agent blueprints.
            skills: List of skill blueprints.
            workflows: List of workflow blueprints.
            config: Optional domain configuration.

        Returns:
            The generated FolderTree.
        """
        tree = self._generator.generate(
            domain_id=domain_id,
            domain_name=domain_name,
            description=description,
            agents=agents,
            skills=skills,
            workflows=workflows,
            config=config,
        )
        self._store.add(tree)

        await self._tape.log_event(
            event_type="prime.folder_tree_created",
            payload={
                "domain_id": domain_id,
                "domain_name": domain_name,
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
            },
            agent_id="folder-tree-service",
        )

        return tree

    # ------------------------------------------------------------------
    # read_file
    # ------------------------------------------------------------------

    async def read_file(self, domain_id: str, path: str) -> FolderTreeNode:
        """Read a file from the domain's folder tree.

        Args:
            domain_id: The domain to read from.
            path: Relative path within the domain (e.g. "agents/analyst/role.md").

        Returns:
            The FolderTreeNode for the file.

        Raises:
            DomainTreeNotFoundError: if the domain has no tree.
            PathNotFoundError: if the path does not exist.
        """
        tree = self._get_tree(domain_id)
        full_path = f"{tree.root_path}/{path}"
        node = tree.nodes.get(full_path)
        if node is None:
            raise PathNotFoundError(
                f"Path '{path}' not found in domain '{domain_id}'"
            )
        if node.node_type == NodeType.DIRECTORY:
            raise FolderTreeError(
                f"Path '{path}' is a directory, not a file"
            )

        await self._tape.log_event(
            event_type="prime.file_read",
            payload={
                "domain_id": domain_id,
                "path": path,
            },
            agent_id="folder-tree-service",
        )

        return node

    # ------------------------------------------------------------------
    # list_directory
    # ------------------------------------------------------------------

    async def list_directory(
        self, domain_id: str, path: str = "",
    ) -> list[FolderTreeNode]:
        """List contents of a directory in the domain's folder tree.

        Args:
            domain_id: The domain to list in.
            path: Relative directory path (empty string for root).

        Returns:
            List of child FolderTreeNodes in the directory.

        Raises:
            DomainTreeNotFoundError: if the domain has no tree.
            PathNotFoundError: if the directory does not exist.
        """
        tree = self._get_tree(domain_id)
        if path == "":
            dir_node = tree.nodes.get(tree.root_path)
        else:
            full_path = f"{tree.root_path}/{path}"
            dir_node = tree.nodes.get(full_path)

        if dir_node is None:
            raise PathNotFoundError(
                f"Directory '{path}' not found in domain '{domain_id}'"
            )
        if dir_node.node_type != NodeType.DIRECTORY:
            raise FolderTreeError(
                f"Path '{path}' is a file, not a directory"
            )

        children = [
            tree.nodes[child_path]
            for child_path in dir_node.children
            if child_path in tree.nodes
        ]

        await self._tape.log_event(
            event_type="prime.directory_listed",
            payload={
                "domain_id": domain_id,
                "path": path or "/",
                "child_count": len(children),
            },
            agent_id="folder-tree-service",
        )

        return children

    # ------------------------------------------------------------------
    # write_file
    # ------------------------------------------------------------------

    async def write_file(
        self, domain_id: str, path: str, content: str,
    ) -> FolderTreeNode:
        """Write content to a file in the domain's folder tree.

        Creates the file if it doesn't exist; updates it if it does.

        Args:
            domain_id: The domain to write to.
            path: Relative file path.
            content: New file content.

        Returns:
            The updated or created FolderTreeNode.
        """
        tree = self._get_tree(domain_id)
        full_path = f"{tree.root_path}/{path}"
        name = path.rsplit("/", 1)[-1] if "/" in path else path

        is_new = full_path not in tree.nodes
        node = FolderTreeNode(
            path=full_path,
            name=name,
            node_type=NodeType.FILE,
            content=content,
        )
        tree.nodes[full_path] = node
        tree.updated_at = datetime.now(UTC)
        tree.version += 1

        # Add to parent directory's children if new
        if is_new:
            parent_path = full_path.rsplit("/", 1)[0] if "/" in full_path else tree.root_path
            parent = tree.nodes.get(parent_path)
            if parent and parent.node_type == NodeType.DIRECTORY and full_path not in parent.children:
                parent.children.append(full_path)

        self._store.update(tree)

        await self._tape.log_event(
            event_type="prime.file_modified" if not is_new else "prime.file_created",
            payload={
                "domain_id": domain_id,
                "path": path,
                "is_new": is_new,
                "content_length": len(content),
                "tree_version": tree.version,
            },
            agent_id="folder-tree-service",
        )

        return node

    # ------------------------------------------------------------------
    # create_directory
    # ------------------------------------------------------------------

    async def create_directory(
        self, domain_id: str, path: str,
    ) -> FolderTreeNode:
        """Create a new directory in the domain's folder tree.

        Args:
            domain_id: The domain to create in.
            path: Relative directory path.

        Returns:
            The created FolderTreeNode.

        Raises:
            PathAlreadyExistsError: if the path already exists.
        """
        tree = self._get_tree(domain_id)
        full_path = f"{tree.root_path}/{path}"
        name = path.rsplit("/", 1)[-1] if "/" in path else path

        if full_path in tree.nodes:
            raise PathAlreadyExistsError(
                f"Path '{path}' already exists in domain '{domain_id}'"
            )

        node = FolderTreeNode(
            path=full_path,
            name=name,
            node_type=NodeType.DIRECTORY,
        )
        tree.nodes[full_path] = node
        tree.updated_at = datetime.now(UTC)
        tree.version += 1

        # Add to parent directory's children
        parent_path = full_path.rsplit("/", 1)[0] if "/" in full_path else tree.root_path
        parent = tree.nodes.get(parent_path)
        if parent and parent.node_type == NodeType.DIRECTORY and full_path not in parent.children:
            parent.children.append(full_path)

        self._store.update(tree)

        await self._tape.log_event(
            event_type="prime.folder_created",
            payload={
                "domain_id": domain_id,
                "path": path,
                "tree_version": tree.version,
            },
            agent_id="folder-tree-service",
        )

        return node

    # ------------------------------------------------------------------
    # move_path
    # ------------------------------------------------------------------

    async def move_path(
        self, domain_id: str, old_path: str, new_path: str,
    ) -> FolderTreeNode:
        """Move/rename a file or directory.

        Args:
            domain_id: The domain to operate on.
            old_path: Current relative path.
            new_path: New relative path.

        Raises:
            PathNotFoundError: if the old path doesn't exist.
            PathAlreadyExistsError: if the new path already exists.
        """
        tree = self._get_tree(domain_id)
        full_old = f"{tree.root_path}/{old_path}"
        full_new = f"{tree.root_path}/{new_path}"

        if full_old not in tree.nodes:
            raise PathNotFoundError(
                f"Path '{old_path}' not found in domain '{domain_id}'"
            )
        if full_new in tree.nodes:
            raise PathAlreadyExistsError(
                f"Path '{new_path}' already exists in domain '{domain_id}'"
            )

        node = tree.nodes.pop(full_old)
        new_name = new_path.rsplit("/", 1)[-1] if "/" in new_path else new_path
        node.path = full_new
        node.name = new_name
        tree.nodes[full_new] = node
        tree.updated_at = datetime.now(UTC)
        tree.version += 1

        # Update parent's children list
        old_parent = full_old.rsplit("/", 1)[0] if "/" in full_old else tree.root_path
        parent = tree.nodes.get(old_parent)
        if parent and full_old in parent.children:
            parent.children.remove(full_old)
            parent.children.append(full_new)

        self._store.update(tree)

        await self._tape.log_event(
            event_type="prime.path_moved",
            payload={
                "domain_id": domain_id,
                "old_path": old_path,
                "new_path": new_path,
                "tree_version": tree.version,
            },
            agent_id="folder-tree-service",
        )

        return node

    # ------------------------------------------------------------------
    # delete_path
    # ------------------------------------------------------------------

    async def delete_path(self, domain_id: str, path: str) -> None:
        """Delete a file or directory from the domain's folder tree.

        Args:
            domain_id: The domain to delete from.
            path: Relative path to delete.

        Raises:
            PathNotFoundError: if the path doesn't exist.
        """
        tree = self._get_tree(domain_id)
        full_path = f"{tree.root_path}/{path}"

        if full_path not in tree.nodes:
            raise PathNotFoundError(
                f"Path '{path}' not found in domain '{domain_id}'"
            )

        node = tree.nodes[full_path]
        # Recursively delete children for directories
        if node.node_type == NodeType.DIRECTORY:
            child_paths = list(node.children)
            for child_path in child_paths:
                child = tree.nodes.get(child_path)
                if child and child.node_type == NodeType.DIRECTORY:
                    # Recurse (simple BFS for nested dirs)
                    queue = list(child.children)
                    while queue:
                        cp = queue.pop(0)
                        cn = tree.nodes.get(cp)
                        if cn and cn.node_type == NodeType.DIRECTORY:
                            queue.extend(cn.children)
                        tree.nodes.pop(cp, None)
                tree.nodes.pop(child_path, None)

        del tree.nodes[full_path]

        # Remove from parent's children
        parent_path = full_path.rsplit("/", 1)[0] if "/" in full_path else tree.root_path
        parent = tree.nodes.get(parent_path)
        if parent and full_path in parent.children:
            parent.children.remove(full_path)

        tree.updated_at = datetime.now(UTC)
        tree.version += 1
        self._store.update(tree)

        await self._tape.log_event(
            event_type="prime.path_deleted",
            payload={
                "domain_id": domain_id,
                "path": path,
                "was_directory": node.node_type == NodeType.DIRECTORY,
                "tree_version": tree.version,
            },
            agent_id="folder-tree-service",
        )

    # ------------------------------------------------------------------
    # search
    # ------------------------------------------------------------------

    async def search(
        self,
        domain_id: str,
        query: str,
        search_content: bool = True,
        max_results: int = 20,
    ) -> list[FolderTreeNode]:
        """Search files by name and optionally by content.

        Args:
            domain_id: The domain to search in.
            query: Search query (case-insensitive substring match).
            search_content: Also search file contents.
            max_results: Maximum number of results.

        Returns:
            List of matching FolderTreeNodes.
        """
        tree = self._get_tree(domain_id)
        q = query.lower()
        results: list[FolderTreeNode] = []

        for node in tree.nodes.values():
            if node.node_type != NodeType.FILE:
                continue
            if q in node.name.lower() or (search_content and q in node.content.lower()):
                results.append(node)
            if len(results) >= max_results:
                break

        await self._tape.log_event(
            event_type="prime.folder_search",
            payload={
                "domain_id": domain_id,
                "query": query,
                "result_count": len(results),
            },
            agent_id="folder-tree-service",
        )

        return results

    # ------------------------------------------------------------------
    # get_tree
    # ------------------------------------------------------------------

    async def get_tree(self, domain_id: str) -> FolderTree:
        """Get the full folder tree for a domain.

        Raises:
            DomainTreeNotFoundError: if the domain has no tree.
        """
        tree = self._store.get(domain_id)
        if tree is None:
            raise DomainTreeNotFoundError(
                f"No folder tree found for domain '{domain_id}'"
            )
        return tree

    # ------------------------------------------------------------------
    # diff_trees
    # ------------------------------------------------------------------

    async def diff_trees(
        self,
        domain_id: str,
        source_version: int,
        target_version: int,
    ) -> FolderDiff:
        """Compare two versions of a domain's tree.

        Note: Version history is not yet stored -- this returns an empty
        diff for now. Full version-diff support will come with AetherGit
        integration.
        """
        tree = self._get_tree(domain_id)
        return FolderDiff(
            domain_id=domain_id,
            source_version=source_version,
            target_version=target_version,
            summary=f"Tree at version {tree.version} (versioned diff requires AetherGit integration)",
        )

    # ------------------------------------------------------------------
    # sync_from_canvas
    # ------------------------------------------------------------------

    async def sync_from_canvas(
        self,
        domain_id: str,
        operations: list[FolderOperation],
    ) -> FolderTree:
        """Synchronize visual canvas changes into the folder tree.

        Applies a batch of folder operations (from canvas interactions)
        to the domain's folder tree.

        Args:
            domain_id: The domain to sync.
            operations: List of folder operations to apply.

        Returns:
            The updated FolderTree.
        """
        tree = self._get_tree(domain_id)

        for op in operations:
            full_path = f"{tree.root_path}/{op.path}"
            match op.op_type:
                case FolderOpType.CREATE:
                    name = op.path.rsplit("/", 1)[-1] if "/" in op.path else op.path
                    tree.nodes[full_path] = FolderTreeNode(
                        path=full_path,
                        name=name,
                        node_type=NodeType.FILE,
                        content=op.content,
                    )
                    parent_path = full_path.rsplit("/", 1)[0] if "/" in full_path else tree.root_path
                    parent = tree.nodes.get(parent_path)
                    if parent and full_path not in parent.children:
                        parent.children.append(full_path)

                case FolderOpType.EDIT:
                    if full_path in tree.nodes:
                        tree.nodes[full_path].content = op.content

                case FolderOpType.MOVE:
                    if op.old_path:
                        full_old = f"{tree.root_path}/{op.old_path}"
                        if full_old in tree.nodes:
                            node = tree.nodes.pop(full_old)
                            node.path = full_path
                            node.name = op.path.rsplit("/", 1)[-1] if "/" in op.path else op.path
                            tree.nodes[full_path] = node

                case FolderOpType.DELETE:
                    tree.nodes.pop(full_path, None)
                    parent_path = full_path.rsplit("/", 1)[0] if "/" in full_path else tree.root_path
                    parent = tree.nodes.get(parent_path)
                    if parent and full_path in parent.children:
                        parent.children.remove(full_path)

        tree.updated_at = datetime.now(UTC)
        tree.version += 1
        self._store.update(tree)

        await self._tape.log_event(
            event_type="prime.canvas_synced",
            payload={
                "domain_id": domain_id,
                "operation_count": len(operations),
                "operation_types": [op.op_type.value for op in operations],
                "tree_version": tree.version,
            },
            agent_id="folder-tree-service",
        )

        return tree

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_tree(self, domain_id: str) -> FolderTree:
        """Retrieve a tree or raise DomainTreeNotFoundError."""
        tree = self._store.get(domain_id)
        if tree is None:
            raise DomainTreeNotFoundError(
                f"No folder tree found for domain '{domain_id}'"
            )
        return tree

    # ------------------------------------------------------------------
    # Store accessors (for testing)
    # ------------------------------------------------------------------

    @property
    def store(self) -> FolderTreeStore:
        """Access the underlying store (for testing)."""
        return self._store

    # ------------------------------------------------------------------
    # GitNexus-inspired enhancements (lazy-loaded submodules)
    # ------------------------------------------------------------------

    async def assess_impact(
        self,
        domain_id: str,
        path: str,
    ) -> object:
        """Predict the impact of changing a path in a domain's folder tree.

        Delegates to ``ImpactAnalyzer.assess_impact()``.

        Parameters
        ----------
        domain_id:
            The domain to analyse.
        path:
            Relative path within the domain.

        Returns
        -------
        ImpactReport
            Full impact analysis with dependents, severity, and mitigations.
        """
        from packages.folder_tree.impact import ImpactAnalyzer

        analyzer = ImpactAnalyzer(
            folder_tree_service=self,
            tape_service=self._tape,
        )
        return await analyzer.assess_impact(domain_id, path)

    async def build_dependency_graph(
        self,
        domain_id: str,
        include_semantic: bool = True,
    ) -> object:
        """Build a dependency graph for a domain's folder tree.

        Delegates to ``DependencyGraphBuilder.build_graph()``.

        Parameters
        ----------
        domain_id:
            The domain to build the graph for.
        include_semantic:
            Whether to include keyword-inferred semantic edges.

        Returns
        -------
        DependencyGraph
            Complete dependency graph ready for rendering.
        """
        from packages.folder_tree.dependency_graph import DependencyGraphBuilder

        builder = DependencyGraphBuilder(
            folder_tree_service=self,
            tape_service=self._tape,
        )
        return await builder.build_graph(domain_id, include_semantic=include_semantic)

    async def generate_skill_mds(
        self,
        domain_id: str,
    ) -> dict[str, str]:
        """Generate SKILL.md files for all agents and skills in a domain.

        Delegates to ``SkillMdGenerator.generate_for_domain()``.

        Parameters
        ----------
        domain_id:
            The domain to generate SKILL.md files for.

        Returns
        -------
        dict[str, str]
            Mapping of relative path to SKILL.md content.
        """
        from packages.folder_tree.skill_md import SkillMdGenerator

        generator = SkillMdGenerator(
            folder_tree_service=self,
            tape_service=self._tape,
        )
        return await generator.generate_for_domain(domain_id)
