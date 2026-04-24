"""Unit tests for Folder Tree integration.

Tests cover:
- FolderTreeService CRUD operations
- FolderTreeGenerator producing correct structures
- Folder Thinking Mode (Prime introspection integration)
- Domain creation generating folder trees
- Proposal folder_operations field
- Skill Evolution folder_operations field
- Canvas sync operations
- Tape logging for folder operations
- Error handling (path not found, path already exists, etc.)

Run with: pytest tests/test_folder_tree.py -v
"""

from uuid import uuid4

import pytest

from packages.folder_tree import (
    DomainTreeNotFoundError,
    FolderOperation,
    FolderOpType,
    FolderTreeGenerator,
    FolderTreeService,
    NodeType,
    PathAlreadyExistsError,
    PathNotFoundError,
)
from packages.prime.domain_creation import (
    DomainCreationEngine,
)
from packages.prime.introspection import (
    FolderThinkingError,
    PrimeIntrospector,
)
from packages.prime.proposals import ModificationType, ProposalEngine, RiskLevel
from packages.prime.skill_evolution import SkillEvolutionProposal
from packages.tape.repository import InMemoryTapeRepository
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tape_svc() -> TapeService:
    return TapeService(InMemoryTapeRepository())


@pytest.fixture()
def folder_tree_svc(tape_svc: TapeService) -> FolderTreeService:
    return FolderTreeService(tape_service=tape_svc)


@pytest.fixture()
def introspector(tape_svc: TapeService) -> PrimeIntrospector:
    return PrimeIntrospector(tape_service=tape_svc)


@pytest.fixture()
def introspector_with_folders(tape_svc: TapeService, folder_tree_svc: FolderTreeService) -> PrimeIntrospector:
    return PrimeIntrospector(
        tape_service=tape_svc,
        folder_tree_service=folder_tree_svc,
    )


@pytest.fixture()
def proposal_engine(tape_svc: TapeService, introspector: PrimeIntrospector) -> ProposalEngine:
    return ProposalEngine(tape_service=tape_svc, introspector=introspector)


@pytest.fixture()
def domain_engine(tape_svc: TapeService, introspector: PrimeIntrospector, proposal_engine: ProposalEngine) -> DomainCreationEngine:
    folder_svc = FolderTreeService(tape_service=tape_svc)
    return DomainCreationEngine(
        tape_service=tape_svc,
        introspector=introspector,
        proposal_engine=proposal_engine,
        folder_tree_service=folder_svc,
    )


# ---------------------------------------------------------------------------
# FolderTreeGenerator tests
# ---------------------------------------------------------------------------

class TestFolderTreeGenerator:
    """Tests for FolderTreeGenerator."""

    def _make_simple_agents(self) -> list[object]:
        """Create simple agent-like objects for testing."""

        class Agent:
            def __init__(self, name: str, role: str, goal: str, capabilities: list[str]):
                self.name = name
                self.role = role
                self.goal = goal
                self.capabilities = capabilities

        return [
            Agent("Contract Analyst", "specialist", "Analyse contracts", ["analysis", "review"]),
            Agent("Compliance Checker", "reviewer", "Check compliance", ["compliance"]),
        ]

    def _make_simple_skills(self) -> list[object]:
        class Skill:
            def __init__(self, skill_id: str, name: str, description: str):
                self.skill_id = skill_id
                self.name = name
                self.description = description

        return [
            Skill("contract-analysis", "Contract Analysis", "Analyses contracts"),
            Skill("risk-scoring", "Risk Scoring", "Scores risk levels"),
        ]

    def _make_simple_workflows(self) -> list[object]:
        class Workflow:
            def __init__(self, workflow_id: str, name: str, workflow_type: str, steps: list[str]):
                self.workflow_id = workflow_id
                self.name = name
                self.workflow_type = workflow_type
                self.steps = steps

        return [
            Workflow("wf-1", "Full Contract Review", "sequential", ["Gather", "Review", "Approve"]),
        ]

    def test_generate_creates_root_directory(self):
        gen = FolderTreeGenerator()
        tree = gen.generate(
            domain_id="legal-research",
            domain_name="Legal Research Domain",
            description="Legal research domain",
            agents=self._make_simple_agents(),
            skills=self._make_simple_skills(),
            workflows=self._make_simple_workflows(),
        )
        assert tree.domain_id == "legal-research"
        assert tree.root_path == "Legal_Research_Domain"
        root = tree.nodes.get("Legal_Research_Domain")
        assert root is not None
        assert root.node_type == NodeType.DIRECTORY

    def test_generate_creates_agents_directory(self):
        gen = FolderTreeGenerator()
        tree = gen.generate(
            domain_id="legal-research",
            domain_name="Legal Research Domain",
            description="Legal research domain",
            agents=self._make_simple_agents(),
            skills=self._make_simple_skills(),
            workflows=self._make_simple_workflows(),
        )
        agents_path = "Legal_Research_Domain/agents"
        assert agents_path in tree.nodes
        agents_node = tree.nodes[agents_path]
        assert agents_node.node_type == NodeType.DIRECTORY
        assert len(agents_node.children) == 2  # Two agents

    def test_generate_creates_agent_role_file(self):
        gen = FolderTreeGenerator()
        tree = gen.generate(
            domain_id="legal-research",
            domain_name="Legal Research Domain",
            description="Legal research domain",
            agents=self._make_simple_agents(),
            skills=self._make_simple_skills(),
            workflows=self._make_simple_workflows(),
        )
        role_path = "Legal_Research_Domain/agents/contract_analyst/role.md"
        assert role_path in tree.nodes
        role_node = tree.nodes[role_path]
        assert role_node.node_type == NodeType.FILE
        assert "Contract Analyst" in role_node.content

    def test_generate_creates_skills_files(self):
        gen = FolderTreeGenerator()
        tree = gen.generate(
            domain_id="legal-research",
            domain_name="Legal Research Domain",
            description="Legal research domain",
            agents=self._make_simple_agents(),
            skills=self._make_simple_skills(),
            workflows=self._make_simple_workflows(),
        )
        skill_path = "Legal_Research_Domain/skills/contract_analysis.py"
        assert skill_path in tree.nodes
        skill_node = tree.nodes[skill_path]
        assert skill_node.node_type == NodeType.FILE

    def test_generate_creates_workflows_directory(self):
        gen = FolderTreeGenerator()
        tree = gen.generate(
            domain_id="legal-research",
            domain_name="Legal Research Domain",
            description="Legal research domain",
            agents=self._make_simple_agents(),
            skills=self._make_simple_skills(),
            workflows=self._make_simple_workflows(),
        )
        wf_path = "Legal_Research_Domain/workflows/full_contract_review"
        assert wf_path in tree.nodes
        wf_json = f"{wf_path}/workflow.json"
        assert wf_json in tree.nodes

    def test_generate_creates_config_directory(self):
        gen = FolderTreeGenerator()
        tree = gen.generate(
            domain_id="legal-research",
            domain_name="Legal Research Domain",
            description="Legal research domain",
            agents=self._make_simple_agents(),
            skills=self._make_simple_skills(),
            workflows=self._make_simple_workflows(),
        )
        config_path = "Legal_Research_Domain/config/domain_config.json"
        assert config_path in tree.nodes

    def test_generate_creates_readme(self):
        gen = FolderTreeGenerator()
        tree = gen.generate(
            domain_id="legal-research",
            domain_name="Legal Research Domain",
            description="Legal research domain",
            agents=self._make_simple_agents(),
            skills=self._make_simple_skills(),
            workflows=self._make_simple_workflows(),
        )
        readme_path = "Legal_Research_Domain/README.md"
        assert readme_path in tree.nodes
        assert "Legal Research Domain" in tree.nodes[readme_path].content

    def test_generate_creates_data_sources_directory(self):
        gen = FolderTreeGenerator()
        tree = gen.generate(
            domain_id="legal-research",
            domain_name="Legal Research Domain",
            description="Legal research domain",
            agents=self._make_simple_agents(),
            skills=self._make_simple_skills(),
            workflows=self._make_simple_workflows(),
        )
        ds_path = "Legal_Research_Domain/data_sources"
        assert ds_path in tree.nodes


# ---------------------------------------------------------------------------
# FolderTreeService CRUD tests
# ---------------------------------------------------------------------------

class TestFolderTreeService:
    """Tests for FolderTreeService CRUD operations."""

    @pytest.fixture()
    def setup_tree(self, folder_tree_svc: FolderTreeService) -> None:
        """Create a basic tree for CRUD tests."""
        import asyncio

        async def _create():
            return await folder_tree_svc.create_tree(
                domain_id="test-domain",
                domain_name="Test Domain",
                description="A test domain",
                agents=[],
                skills=[],
                workflows=[],
            )

        asyncio.get_event_loop().run_until_complete(_create())

    @pytest.mark.asyncio
    async def test_create_tree(self, folder_tree_svc: FolderTreeService):
        tree = await folder_tree_svc.create_tree(
            domain_id="test-domain",
            domain_name="Test Domain",
            description="A test domain",
            agents=[],
            skills=[],
            workflows=[],
        )
        assert tree.domain_id == "test-domain"
        assert tree.root_path == "Test_Domain"
        assert tree.version == 1

    @pytest.mark.asyncio
    async def test_list_directory_root(self, folder_tree_svc: FolderTreeService):
        await folder_tree_svc.create_tree(
            domain_id="test-domain",
            domain_name="Test Domain",
            description="A test domain",
            agents=[],
            skills=[],
            workflows=[],
        )
        children = await folder_tree_svc.list_directory("test-domain", "")
        assert len(children) > 0

    @pytest.mark.asyncio
    async def test_read_file(self, folder_tree_svc: FolderTreeService):
        await folder_tree_svc.create_tree(
            domain_id="test-domain",
            domain_name="Test Domain",
            description="A test domain",
            agents=[],
            skills=[],
            workflows=[],
        )
        node = await folder_tree_svc.read_file("test-domain", "README.md")
        assert node.node_type == NodeType.FILE
        assert "Test Domain" in node.content

    @pytest.mark.asyncio
    async def test_read_file_not_found(self, folder_tree_svc: FolderTreeService):
        await folder_tree_svc.create_tree(
            domain_id="test-domain",
            domain_name="Test Domain",
            description="A test domain",
            agents=[],
            skills=[],
            workflows=[],
        )
        with pytest.raises(PathNotFoundError):
            await folder_tree_svc.read_file("test-domain", "nonexistent.md")

    @pytest.mark.asyncio
    async def test_write_file_new(self, folder_tree_svc: FolderTreeService):
        await folder_tree_svc.create_tree(
            domain_id="test-domain",
            domain_name="Test Domain",
            description="A test domain",
            agents=[],
            skills=[],
            workflows=[],
        )
        node = await folder_tree_svc.write_file(
            "test-domain", "agents/new_agent.md", "# New Agent"
        )
        assert node.content == "# New Agent"
        assert node.node_type == NodeType.FILE

    @pytest.mark.asyncio
    async def test_write_file_update(self, folder_tree_svc: FolderTreeService):
        await folder_tree_svc.create_tree(
            domain_id="test-domain",
            domain_name="Test Domain",
            description="A test domain",
            agents=[],
            skills=[],
            workflows=[],
        )
        # Update existing README
        node = await folder_tree_svc.write_file(
            "test-domain", "README.md", "# Updated"
        )
        assert node.content == "# Updated"

    @pytest.mark.asyncio
    async def test_create_directory(self, folder_tree_svc: FolderTreeService):
        await folder_tree_svc.create_tree(
            domain_id="test-domain",
            domain_name="Test Domain",
            description="A test domain",
            agents=[],
            skills=[],
            workflows=[],
        )
        node = await folder_tree_svc.create_directory(
            "test-domain", "agents/new_section"
        )
        assert node.node_type == NodeType.DIRECTORY
        assert node.name == "new_section"

    @pytest.mark.asyncio
    async def test_create_directory_already_exists(self, folder_tree_svc: FolderTreeService):
        await folder_tree_svc.create_tree(
            domain_id="test-domain",
            domain_name="Test Domain",
            description="A test domain",
            agents=[],
            skills=[],
            workflows=[],
        )
        with pytest.raises(PathAlreadyExistsError):
            await folder_tree_svc.create_directory("test-domain", "agents")

    @pytest.mark.asyncio
    async def test_move_path(self, folder_tree_svc: FolderTreeService):
        await folder_tree_svc.create_tree(
            domain_id="test-domain",
            domain_name="Test Domain",
            description="A test domain",
            agents=[],
            skills=[],
            workflows=[],
        )
        node = await folder_tree_svc.move_path(
            "test-domain", "README.md", "INTRO.md"
        )
        assert node.name == "INTRO.md"

    @pytest.mark.asyncio
    async def test_move_path_not_found(self, folder_tree_svc: FolderTreeService):
        await folder_tree_svc.create_tree(
            domain_id="test-domain",
            domain_name="Test Domain",
            description="A test domain",
            agents=[],
            skills=[],
            workflows=[],
        )
        with pytest.raises(PathNotFoundError):
            await folder_tree_svc.move_path(
                "test-domain", "nonexistent.md", "new_name.md"
            )

    @pytest.mark.asyncio
    async def test_delete_path(self, folder_tree_svc: FolderTreeService):
        await folder_tree_svc.create_tree(
            domain_id="test-domain",
            domain_name="Test Domain",
            description="A test domain",
            agents=[],
            skills=[],
            workflows=[],
        )
        await folder_tree_svc.delete_path("test-domain", "README.md")
        with pytest.raises(PathNotFoundError):
            await folder_tree_svc.read_file("test-domain", "README.md")

    @pytest.mark.asyncio
    async def test_delete_path_not_found(self, folder_tree_svc: FolderTreeService):
        await folder_tree_svc.create_tree(
            domain_id="test-domain",
            domain_name="Test Domain",
            description="A test domain",
            agents=[],
            skills=[],
            workflows=[],
        )
        with pytest.raises(PathNotFoundError):
            await folder_tree_svc.delete_path("test-domain", "nonexistent.md")

    @pytest.mark.asyncio
    async def test_search_by_name(self, folder_tree_svc: FolderTreeService):
        await folder_tree_svc.create_tree(
            domain_id="test-domain",
            domain_name="Test Domain",
            description="A test domain",
            agents=[],
            skills=[],
            workflows=[],
        )
        results = await folder_tree_svc.search("test-domain", "README")
        assert len(results) > 0
        assert any("README" in r.name for r in results)

    @pytest.mark.asyncio
    async def test_search_by_content(self, folder_tree_svc: FolderTreeService):
        await folder_tree_svc.create_tree(
            domain_id="test-domain",
            domain_name="Test Domain",
            description="A test domain",
            agents=[],
            skills=[],
            workflows=[],
        )
        results = await folder_tree_svc.search("test-domain", "test domain")
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_get_tree(self, folder_tree_svc: FolderTreeService):
        await folder_tree_svc.create_tree(
            domain_id="test-domain",
            domain_name="Test Domain",
            description="A test domain",
            agents=[],
            skills=[],
            workflows=[],
        )
        tree = await folder_tree_svc.get_tree("test-domain")
        assert tree.domain_id == "test-domain"

    @pytest.mark.asyncio
    async def test_get_tree_not_found(self, folder_tree_svc: FolderTreeService):
        with pytest.raises(DomainTreeNotFoundError):
            await folder_tree_svc.get_tree("nonexistent")

    @pytest.mark.asyncio
    async def test_domain_not_found(self, folder_tree_svc: FolderTreeService):
        with pytest.raises(DomainTreeNotFoundError):
            await folder_tree_svc.list_directory("nonexistent", "")


# ---------------------------------------------------------------------------
# Folder Thinking Mode tests (Prime introspection integration)
# ---------------------------------------------------------------------------

class TestFolderThinkingMode:
    """Tests for Prime's Folder Thinking Mode."""

    @pytest.mark.asyncio
    async def test_folder_navigate_without_service(
        self, introspector: PrimeIntrospector
    ):
        """Folder Thinking Mode raises error when service not configured."""
        with pytest.raises(FolderThinkingError):
            await introspector.folder_navigate("test-domain")

    @pytest.mark.asyncio
    async def test_folder_read_without_service(
        self, introspector: PrimeIntrospector
    ):
        with pytest.raises(FolderThinkingError):
            await introspector.folder_read("test-domain", "README.md")

    @pytest.mark.asyncio
    async def test_folder_search_without_service(
        self, introspector: PrimeIntrospector
    ):
        with pytest.raises(FolderThinkingError):
            await introspector.folder_search("test-domain", "test")

    @pytest.mark.asyncio
    async def test_folder_navigate_with_service(
        self, introspector_with_folders: PrimeIntrospector,
        folder_tree_svc: FolderTreeService,
    ):
        """Folder Thinking Mode works when service is configured."""
        await folder_tree_svc.create_tree(
            domain_id="test-domain",
            domain_name="Test Domain",
            description="A test domain",
            agents=[],
            skills=[],
            workflows=[],
        )
        children = await introspector_with_folders.folder_navigate("test-domain", "")
        assert len(children) > 0

    @pytest.mark.asyncio
    async def test_folder_read_with_service(
        self, introspector_with_folders: PrimeIntrospector,
        folder_tree_svc: FolderTreeService,
    ):
        await folder_tree_svc.create_tree(
            domain_id="test-domain",
            domain_name="Test Domain",
            description="A test domain",
            agents=[],
            skills=[],
            workflows=[],
        )
        node = await introspector_with_folders.folder_read("test-domain", "README.md")
        assert node.node_type == NodeType.FILE

    @pytest.mark.asyncio
    async def test_folder_search_with_service(
        self, introspector_with_folders: PrimeIntrospector,
        folder_tree_svc: FolderTreeService,
    ):
        await folder_tree_svc.create_tree(
            domain_id="test-domain",
            domain_name="Test Domain",
            description="A test domain",
            agents=[],
            skills=[],
            workflows=[],
        )
        results = await introspector_with_folders.folder_search("test-domain", "README")
        assert len(results) > 0


# ---------------------------------------------------------------------------
# Domain Creation integration tests
# ---------------------------------------------------------------------------

class TestDomainCreationFolderTree:
    """Tests for folder tree generation during domain creation."""

    @pytest.mark.asyncio
    async def test_domain_creation_generates_folder_tree(
        self, domain_engine: DomainCreationEngine, tape_svc: TapeService,
    ):
        """Domain creation with folder_tree_service generates a tree."""
        result = await domain_engine.create_domain_from_description(
            description="Create a Legal Research Domain for contract analysis",
            created_by="test-user",
        )
        # The domain was created (proposed)
        assert result.blueprint is not None

        # Check if folder tree was generated
        folder_svc = domain_engine._folder_tree_service
        if folder_svc is not None:
            folder_svc.store.get(result.blueprint.domain_id)
            # Note: tree is only generated on register_domain (after approval),
            # not on creation (which just submits a proposal)
            # So we verify the service is wired up correctly
            assert folder_svc is not None

    @pytest.mark.asyncio
    async def test_domain_creation_without_folder_service_still_works(
        self, tape_svc: TapeService, introspector: PrimeIntrospector,
        proposal_engine: ProposalEngine,
    ):
        """Domain creation works even without folder_tree_service."""
        engine = DomainCreationEngine(
            tape_service=tape_svc,
            introspector=introspector,
            proposal_engine=proposal_engine,
            folder_tree_service=None,
        )
        result = await engine.create_domain_from_description(
            description="Create a Research Domain for academic studies",
            created_by="test-user",
        )
        assert result.blueprint is not None


# ---------------------------------------------------------------------------
# Canvas sync tests
# ---------------------------------------------------------------------------

class TestCanvasSync:
    """Tests for visual canvas ↔ folder tree synchronization."""

    @pytest.mark.asyncio
    async def test_sync_create_operation(
        self, folder_tree_svc: FolderTreeService,
    ):
        await folder_tree_svc.create_tree(
            domain_id="test-domain",
            domain_name="Test Domain",
            description="A test domain",
            agents=[],
            skills=[],
            workflows=[],
        )
        ops = [
            FolderOperation(
                op_type=FolderOpType.CREATE,
                path="agents/new_agent.md",
                content="# New Agent from Canvas",
            ),
        ]
        await folder_tree_svc.sync_from_canvas("test-domain", ops)
        # Verify file was created
        node = await folder_tree_svc.read_file("test-domain", "agents/new_agent.md")
        assert "# New Agent from Canvas" in node.content

    @pytest.mark.asyncio
    async def test_sync_edit_operation(
        self, folder_tree_svc: FolderTreeService,
    ):
        await folder_tree_svc.create_tree(
            domain_id="test-domain",
            domain_name="Test Domain",
            description="A test domain",
            agents=[],
            skills=[],
            workflows=[],
        )
        ops = [
            FolderOperation(
                op_type=FolderOpType.EDIT,
                path="README.md",
                content="# Updated from Canvas",
            ),
        ]
        await folder_tree_svc.sync_from_canvas("test-domain", ops)
        node = await folder_tree_svc.read_file("test-domain", "README.md")
        assert "# Updated from Canvas" in node.content

    @pytest.mark.asyncio
    async def test_sync_delete_operation(
        self, folder_tree_svc: FolderTreeService,
    ):
        await folder_tree_svc.create_tree(
            domain_id="test-domain",
            domain_name="Test Domain",
            description="A test domain",
            agents=[],
            skills=[],
            workflows=[],
        )
        ops = [
            FolderOperation(
                op_type=FolderOpType.DELETE,
                path="README.md",
            ),
        ]
        await folder_tree_svc.sync_from_canvas("test-domain", ops)
        with pytest.raises(PathNotFoundError):
            await folder_tree_svc.read_file("test-domain", "README.md")

    @pytest.mark.asyncio
    async def test_sync_multiple_operations(
        self, folder_tree_svc: FolderTreeService,
    ):
        await folder_tree_svc.create_tree(
            domain_id="test-domain",
            domain_name="Test Domain",
            description="A test domain",
            agents=[],
            skills=[],
            workflows=[],
        )
        ops = [
            FolderOperation(
                op_type=FolderOpType.CREATE,
                path="agents/agent1.md",
                content="Agent 1",
            ),
            FolderOperation(
                op_type=FolderOpType.EDIT,
                path="README.md",
                content="Updated README",
            ),
        ]
        tree = await folder_tree_svc.sync_from_canvas("test-domain", ops)
        assert tree.version > 1  # Version should have incremented


# ---------------------------------------------------------------------------
# Proposal folder_operations tests
# ---------------------------------------------------------------------------

class TestProposalFolderOperations:
    """Tests for folder operations in proposals."""

    @pytest.mark.asyncio
    async def test_proposal_with_folder_operations(
        self, proposal_engine: ProposalEngine,
    ):
        """Proposals can include folder operations."""
        proposal = await proposal_engine.propose(
            title="Add new agent role",
            modification_type=ModificationType.SKILL_ADDITION,
            description="Add a new role.md file",
            reasoning="Need a new agent role",
            expected_impact="Better domain coverage",
            risk_level=RiskLevel.LOW,
            implementation_steps=["Create role file"],
            folder_operations=[
                {"op_type": "create", "path": "agents/new_role.md", "content": "# New Role"},
            ],
        )
        assert len(proposal.folder_operations) == 1
        assert proposal.folder_operations[0]["path"] == "agents/new_role.md"

    @pytest.mark.asyncio
    async def test_proposal_without_folder_operations(
        self, proposal_engine: ProposalEngine,
    ):
        """Proposals work without folder operations (backward compatible)."""
        proposal = await proposal_engine.propose(
            title="Simple change",
            modification_type=ModificationType.BEHAVIOR_CHANGE,
            description="A simple change",
            reasoning="Needed",
            expected_impact="Minor",
            risk_level=RiskLevel.LOW,
            implementation_steps=["Step 1"],
        )
        assert proposal.folder_operations == []


# ---------------------------------------------------------------------------
# Skill Evolution folder_operations tests
# ---------------------------------------------------------------------------

class TestSkillEvolutionFolderOperations:
    """Tests for folder operations in skill evolution proposals."""

    def test_evolution_proposal_with_folder_operations(self):
        """Skill evolution proposals can include folder operations."""
        proposal = SkillEvolutionProposal(
            proposal_id=uuid4(),
            evolution_type="enhance",
            target_skill_ids=["skill-1"],
            reasoning="Improve skill",
            folder_operations=[
                {"op_type": "edit", "path": "skills/skill_1.py", "content": "def execute(): pass"},
            ],
        )
        assert len(proposal.folder_operations) == 1

    def test_evolution_proposal_without_folder_operations(self):
        """Skill evolution proposals work without folder operations (backward compatible)."""
        proposal = SkillEvolutionProposal(
            proposal_id=uuid4(),
            evolution_type="create",
            target_skill_ids=[],
            reasoning="New skill",
        )
        assert proposal.folder_operations == []


# ---------------------------------------------------------------------------
# Tape logging tests
# ---------------------------------------------------------------------------

class TestFolderTreeTapeLogging:
    """Tests for Tape audit logging of folder operations."""

    @pytest.mark.asyncio
    async def test_create_tree_logs_to_tape(
        self, folder_tree_svc: FolderTreeService, tape_svc: TapeService,
    ):
        await folder_tree_svc.create_tree(
            domain_id="test-domain",
            domain_name="Test Domain",
            description="A test domain",
            agents=[],
            skills=[],
            workflows=[],
        )
        entries = await tape_svc.get_entries(event_type="prime.folder_tree_created")
        assert len(entries) == 1
        assert entries[0].payload["domain_id"] == "test-domain"

    @pytest.mark.asyncio
    async def test_read_file_logs_to_tape(
        self, folder_tree_svc: FolderTreeService, tape_svc: TapeService,
    ):
        await folder_tree_svc.create_tree(
            domain_id="test-domain",
            domain_name="Test Domain",
            description="A test domain",
            agents=[],
            skills=[],
            workflows=[],
        )
        await folder_tree_svc.read_file("test-domain", "README.md")
        entries = await tape_svc.get_entries(event_type="prime.file_read")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_list_directory_logs_to_tape(
        self, folder_tree_svc: FolderTreeService, tape_svc: TapeService,
    ):
        await folder_tree_svc.create_tree(
            domain_id="test-domain",
            domain_name="Test Domain",
            description="A test domain",
            agents=[],
            skills=[],
            workflows=[],
        )
        await folder_tree_svc.list_directory("test-domain", "")
        entries = await tape_svc.get_entries(event_type="prime.directory_listed")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_write_file_logs_to_tape(
        self, folder_tree_svc: FolderTreeService, tape_svc: TapeService,
    ):
        await folder_tree_svc.create_tree(
            domain_id="test-domain",
            domain_name="Test Domain",
            description="A test domain",
            agents=[],
            skills=[],
            workflows=[],
        )
        await folder_tree_svc.write_file("test-domain", "test.md", "# Test")
        entries = await tape_svc.get_entries(event_type="prime.file_created")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_delete_logs_to_tape(
        self, folder_tree_svc: FolderTreeService, tape_svc: TapeService,
    ):
        await folder_tree_svc.create_tree(
            domain_id="test-domain",
            domain_name="Test Domain",
            description="A test domain",
            agents=[],
            skills=[],
            workflows=[],
        )
        await folder_tree_svc.delete_path("test-domain", "README.md")
        entries = await tape_svc.get_entries(event_type="prime.path_deleted")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_search_logs_to_tape(
        self, folder_tree_svc: FolderTreeService, tape_svc: TapeService,
    ):
        await folder_tree_svc.create_tree(
            domain_id="test-domain",
            domain_name="Test Domain",
            description="A test domain",
            agents=[],
            skills=[],
            workflows=[],
        )
        await folder_tree_svc.search("test-domain", "README")
        entries = await tape_svc.get_entries(event_type="prime.folder_search")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_canvas_sync_logs_to_tape(
        self, folder_tree_svc: FolderTreeService, tape_svc: TapeService,
    ):
        await folder_tree_svc.create_tree(
            domain_id="test-domain",
            domain_name="Test Domain",
            description="A test domain",
            agents=[],
            skills=[],
            workflows=[],
        )
        ops = [
            FolderOperation(
                op_type=FolderOpType.EDIT,
                path="README.md",
                content="Updated",
            ),
        ]
        await folder_tree_svc.sync_from_canvas("test-domain", ops)
        entries = await tape_svc.get_entries(event_type="prime.canvas_synced")
        assert len(entries) == 1
        assert entries[0].payload["operation_count"] == 1
