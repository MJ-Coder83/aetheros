"""Unit tests for DomainBlueprint & DomainFolderTreeGenerator.

Tests cover:
- DomainBlueprint model defaults, fields, and serialisation
- EvaluationCriteria model defaults and custom metrics
- DomainFolderTreeGenerator.generate() — folder-tree structure
- Folder-tree node content (role.md, goals.md, workflow.json, etc.)
- EvaluationCriteria derivation from DomainConfig priority levels
- Tape logging from DomainFolderTreeGenerator
- Re-exports via packages.domain.__init__

Run with: pytest tests/test_domain_blueprint.py -v
"""

import json

import pytest

from packages.domain import (
    AgentBlueprint,
    AgentRole,
    CreationMode,
    DomainBlueprint,
    DomainConfig,
    DomainFolderTreeGenerator,
    DomainStatus,
    EvaluationCriteria,
    SkillBlueprint,
    WorkflowBlueprint,
    WorkflowType,
)
from packages.domain.domain_blueprint import _slug
from packages.folder_tree import FolderTree, NodeType
from packages.tape.repository import InMemoryTapeRepository
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tape_svc() -> TapeService:
    return TapeService(InMemoryTapeRepository())


@pytest.fixture()
def generator(tape_svc: TapeService) -> DomainFolderTreeGenerator:
    return DomainFolderTreeGenerator(tape_service=tape_svc)


@pytest.fixture()
def minimal_blueprint() -> DomainBlueprint:
    """A minimal valid blueprint with one agent, one skill, one workflow."""
    return DomainBlueprint(
        domain_name="Test Domain",
        domain_id="test-domain",
        description="A test domain for unit tests",
        agents=[
            AgentBlueprint(
                agent_id="a1",
                name="Test Agent",
                role=AgentRole.ANALYST,
                goal="Analyse test data",
                capabilities=["analysis"],
            ),
        ],
        skills=[
            SkillBlueprint(
                skill_id="s1",
                name="Data Analysis",
                description="Core data analysis skill",
            ),
        ],
        workflows=[
            WorkflowBlueprint(
                workflow_id="w1",
                name="Main Pipeline",
                workflow_type=WorkflowType.SEQUENTIAL,
                description="Main processing pipeline",
                steps=["Gather", "Analyse", "Report"],
            ),
        ],
    )


@pytest.fixture()
def legal_blueprint() -> DomainBlueprint:
    """A fuller legal-domain blueprint with multiple agents, skills, and workflows."""
    return DomainBlueprint(
        domain_name="Legal Research Domain",
        domain_id="legal-research",
        description="Legal research and compliance domain",
        agents=[
            AgentBlueprint(
                agent_id="a-coordinator",
                name="Legal Operations Lead",
                role=AgentRole.COORDINATOR,
                goal="Manages legal workflows",
                backstory="Experienced legal operations manager",
                capabilities=["coordination"],
                tools=["contract_analysis"],
            ),
            AgentBlueprint(
                agent_id="a-analyst",
                name="Contract Analyst",
                role=AgentRole.SPECIALIST,
                goal="Analyse contract terms and identify risks",
                capabilities=["analysis", "review"],
            ),
            AgentBlueprint(
                agent_id="a-reviewer",
                name="Compliance Checker",
                role=AgentRole.REVIEWER,
                goal="Verify compliance with regulations",
                capabilities=["compliance"],
            ),
        ],
        skills=[
            SkillBlueprint(
                skill_id="s-contract",
                name="Contract Analysis",
                description="Analyses legal contracts",
            ),
            SkillBlueprint(
                skill_id="s-compliance",
                name="Compliance Checking",
                description="Checks regulatory compliance",
                is_reused=True,
                source_domain="global",
            ),
            SkillBlueprint(
                skill_id="s-risk",
                name="Risk Assessment",
                description="Evaluates legal risks",
            ),
        ],
        workflows=[
            WorkflowBlueprint(
                workflow_id="w-review",
                name="Contract Review Cycle",
                workflow_type=WorkflowType.REVIEW,
                description="Draft → Review → Flag → Revise → Approve",
                agent_ids=["a-coordinator", "a-analyst", "a-reviewer"],
                steps=["Draft", "Review", "Flag", "Revise", "Approve"],
            ),
            WorkflowBlueprint(
                workflow_id="w-audit",
                name="Compliance Audit",
                workflow_type=WorkflowType.SEQUENTIAL,
                description="Scope → Check → Report → Remediate",
                agent_ids=["a-coordinator", "a-reviewer"],
                steps=["Scope", "Check", "Report", "Remediate"],
            ),
        ],
        config=DomainConfig(
            max_agents=10,
            max_concurrent_tasks=5,
            requires_human_approval=True,
            priority_level="high",
        ),
    )


# ===========================================================================
# EvaluationCriteria tests
# ===========================================================================


class TestEvaluationCriteria:
    """Tests for the EvaluationCriteria model."""

    def test_default_values(self) -> None:
        c = EvaluationCriteria()
        assert c.accuracy_threshold == 0.85
        assert c.response_time_sla_seconds == 30.0
        assert c.human_approval_rate == 0.90
        assert c.uptime_target == 99.5
        assert c.custom_metrics == {}

    def test_custom_values(self) -> None:
        c = EvaluationCriteria(
            accuracy_threshold=0.99,
            response_time_sla_seconds=5.0,
            human_approval_rate=1.0,
            uptime_target=99.999,
            custom_metrics={"error_rate": 0.01},
        )
        assert c.accuracy_threshold == 0.99
        assert c.custom_metrics["error_rate"] == 0.01

    def test_serialises_to_dict(self) -> None:
        c = EvaluationCriteria(custom_metrics={"foo": "bar"})
        d = c.model_dump()
        assert "accuracy_threshold" in d
        assert d["custom_metrics"] == {"foo": "bar"}


# ===========================================================================
# DomainBlueprint model tests
# ===========================================================================


class TestDomainBlueprintModel:
    """Tests for the DomainBlueprint model (re-exported from domain package)."""

    def test_defaults(self) -> None:
        bp = DomainBlueprint(domain_name="Test", domain_id="test")
        assert bp.agents == []
        assert bp.skills == []
        assert bp.workflows == []
        assert bp.status == DomainStatus.DRAFT
        assert bp.creation_mode == CreationMode.HUMAN_GUIDED
        assert bp.created_by == "prime"
        assert bp.validation_errors == []

    def test_id_is_uuid(self) -> None:
        from uuid import UUID
        bp = DomainBlueprint(domain_name="Test", domain_id="test")
        assert isinstance(bp.id, UUID)

    def test_agent_blueprint_defaults(self) -> None:
        a = AgentBlueprint(agent_id="a1", name="Agent")
        assert a.role == AgentRole.SPECIALIST
        assert a.goal == ""
        assert a.capabilities == []
        assert a.tools == []

    def test_skill_blueprint_defaults(self) -> None:
        s = SkillBlueprint(skill_id="s1", name="Skill")
        assert s.is_reused is False
        assert s.version == "0.1.0"
        assert s.source_domain is None

    def test_workflow_blueprint_defaults(self) -> None:
        w = WorkflowBlueprint(workflow_id="w1", name="Workflow")
        assert w.workflow_type == WorkflowType.SEQUENTIAL
        assert w.agent_ids == []
        assert w.steps == []

    def test_domain_config_defaults(self) -> None:
        cfg = DomainConfig()
        assert cfg.max_agents == 10
        assert cfg.max_concurrent_tasks == 5
        assert cfg.requires_human_approval is True
        assert cfg.data_retention_days == 90
        assert cfg.priority_level == "normal"

    def test_blueprint_with_full_data(self, legal_blueprint: DomainBlueprint) -> None:
        assert legal_blueprint.domain_name == "Legal Research Domain"
        assert len(legal_blueprint.agents) == 3
        assert len(legal_blueprint.skills) == 3
        assert len(legal_blueprint.workflows) == 2

    def test_agent_role_enum_values(self) -> None:
        assert AgentRole.COORDINATOR.value == "coordinator"
        assert AgentRole.ANALYST.value == "analyst"
        assert AgentRole.SPECIALIST.value == "specialist"
        assert AgentRole.REVIEWER.value == "reviewer"

    def test_workflow_type_enum_values(self) -> None:
        assert WorkflowType.SEQUENTIAL.value == "sequential"
        assert WorkflowType.REVIEW.value == "review"
        assert WorkflowType.PARALLEL.value == "parallel"

    def test_domain_status_enum_values(self) -> None:
        assert DomainStatus.DRAFT.value == "draft"
        assert DomainStatus.PROPOSED.value == "proposed"
        assert DomainStatus.ACTIVE.value == "active"


# ===========================================================================
# _slug helper tests
# ===========================================================================


class TestSlugHelper:
    """Tests for the internal _slug() helper."""

    def test_lowercase(self) -> None:
        assert _slug("Contract Analyst") == "contract_analyst"

    def test_spaces_to_underscores(self) -> None:
        assert _slug("Legal Research") == "legal_research"

    def test_hyphens_to_underscores(self) -> None:
        assert _slug("risk-scoring") == "risk_scoring"

    def test_already_slug(self) -> None:
        assert _slug("data_analysis") == "data_analysis"

    def test_mixed(self) -> None:
        assert _slug("Full Contract Review") == "full_contract_review"


# ===========================================================================
# DomainFolderTreeGenerator tests — structure
# ===========================================================================


class TestDomainFolderTreeGeneratorStructure:
    """Tests for the folder-tree structure produced by DomainFolderTreeGenerator."""

    @pytest.mark.asyncio
    async def test_returns_folder_tree(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        assert isinstance(tree, FolderTree)

    @pytest.mark.asyncio
    async def test_domain_id_set_correctly(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        assert tree.domain_id == minimal_blueprint.domain_id

    @pytest.mark.asyncio
    async def test_root_path_uses_domain_name(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        assert tree.root_path == "Test_Domain"

    @pytest.mark.asyncio
    async def test_root_directory_exists(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        root = tree.nodes.get("Test_Domain")
        assert root is not None
        assert root.node_type == NodeType.DIRECTORY

    @pytest.mark.asyncio
    async def test_agents_directory_created(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        agents_node = tree.nodes.get("Test_Domain/agents")
        assert agents_node is not None
        assert agents_node.node_type == NodeType.DIRECTORY

    @pytest.mark.asyncio
    async def test_agent_subdirectory_created(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        agent_dir = tree.nodes.get("Test_Domain/agents/test_agent")
        assert agent_dir is not None
        assert agent_dir.node_type == NodeType.DIRECTORY

    @pytest.mark.asyncio
    async def test_agent_role_md_created(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        role_node = tree.nodes.get("Test_Domain/agents/test_agent/role.md")
        assert role_node is not None
        assert role_node.node_type == NodeType.FILE

    @pytest.mark.asyncio
    async def test_agent_role_md_content(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        role_node = tree.nodes["Test_Domain/agents/test_agent/role.md"]
        assert "Test Agent" in role_node.content
        assert "Analyse test data" in role_node.content

    @pytest.mark.asyncio
    async def test_agent_goals_md_created(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        goals_node = tree.nodes.get("Test_Domain/agents/test_agent/goals.md")
        assert goals_node is not None
        assert goals_node.node_type == NodeType.FILE

    @pytest.mark.asyncio
    async def test_agent_tools_directory_created(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        tools_dir = tree.nodes.get("Test_Domain/agents/test_agent/tools")
        assert tools_dir is not None
        assert tools_dir.node_type == NodeType.DIRECTORY

    @pytest.mark.asyncio
    async def test_agent_capabilities_create_tool_stubs(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        """Capabilities (not explicit tools) should create tool stubs."""
        tree = await generator.generate(minimal_blueprint)
        # The agent has capability "analysis" and no explicit tools
        cap_file = tree.nodes.get("Test_Domain/agents/test_agent/tools/analysis.md")
        assert cap_file is not None
        assert cap_file.node_type == NodeType.FILE

    @pytest.mark.asyncio
    async def test_agent_explicit_tools_create_stubs(
        self, generator: DomainFolderTreeGenerator, legal_blueprint: DomainBlueprint
    ) -> None:
        """Explicit tools list should create stubs, not capabilities."""
        tree = await generator.generate(legal_blueprint)
        # Legal Operations Lead has tools=["contract_analysis"]
        tool_file = tree.nodes.get(
            "Legal_Research_Domain/agents/legal_operations_lead/tools/contract_analysis.md"
        )
        assert tool_file is not None

    @pytest.mark.asyncio
    async def test_agent_examples_directory_created(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        examples_dir = tree.nodes.get("Test_Domain/agents/test_agent/examples")
        assert examples_dir is not None
        assert examples_dir.node_type == NodeType.DIRECTORY

    @pytest.mark.asyncio
    async def test_skills_directory_created(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        skills_dir = tree.nodes.get("Test_Domain/skills")
        assert skills_dir is not None
        assert skills_dir.node_type == NodeType.DIRECTORY

    @pytest.mark.asyncio
    async def test_skill_python_file_created(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        skill_file = tree.nodes.get("Test_Domain/skills/data_analysis.py")
        assert skill_file is not None
        assert skill_file.node_type == NodeType.FILE

    @pytest.mark.asyncio
    async def test_skill_file_content(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        skill_file = tree.nodes["Test_Domain/skills/data_analysis.py"]
        assert "Data Analysis" in skill_file.content
        assert "def execute" in skill_file.content

    @pytest.mark.asyncio
    async def test_reused_skill_noted_in_content(
        self, generator: DomainFolderTreeGenerator, legal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(legal_blueprint)
        compliance_file = tree.nodes.get(
            "Legal_Research_Domain/skills/compliance_checking.py"
        )
        assert compliance_file is not None
        assert "(reused)" in compliance_file.content

    @pytest.mark.asyncio
    async def test_workflows_directory_created(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        wf_dir = tree.nodes.get("Test_Domain/workflows")
        assert wf_dir is not None
        assert wf_dir.node_type == NodeType.DIRECTORY

    @pytest.mark.asyncio
    async def test_workflow_subdirectory_created(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        wf_sub = tree.nodes.get("Test_Domain/workflows/main_pipeline")
        assert wf_sub is not None
        assert wf_sub.node_type == NodeType.DIRECTORY

    @pytest.mark.asyncio
    async def test_workflow_json_created(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        wf_json = tree.nodes.get("Test_Domain/workflows/main_pipeline/workflow.json")
        assert wf_json is not None
        assert wf_json.node_type == NodeType.FILE

    @pytest.mark.asyncio
    async def test_workflow_json_content(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        wf_json_node = tree.nodes["Test_Domain/workflows/main_pipeline/workflow.json"]
        data = json.loads(wf_json_node.content)
        assert data["name"] == "Main Pipeline"
        assert data["type"] == "sequential"
        assert data["steps"] == ["Gather", "Analyse", "Report"]

    @pytest.mark.asyncio
    async def test_workflow_json_includes_agent_ids(
        self, generator: DomainFolderTreeGenerator, legal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(legal_blueprint)
        wf_json_node = tree.nodes[
            "Legal_Research_Domain/workflows/contract_review_cycle/workflow.json"
        ]
        data = json.loads(wf_json_node.content)
        assert "a-coordinator" in data["agent_ids"]

    @pytest.mark.asyncio
    async def test_workflow_example_inputs_directory(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        ex_dir = tree.nodes.get(
            "Test_Domain/workflows/main_pipeline/example_inputs"
        )
        assert ex_dir is not None
        assert ex_dir.node_type == NodeType.DIRECTORY

    @pytest.mark.asyncio
    async def test_templates_directory_created(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        tmpl_dir = tree.nodes.get("Test_Domain/templates")
        assert tmpl_dir is not None
        assert tmpl_dir.node_type == NodeType.DIRECTORY

    @pytest.mark.asyncio
    async def test_config_directory_created(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        cfg_dir = tree.nodes.get("Test_Domain/config")
        assert cfg_dir is not None
        assert cfg_dir.node_type == NodeType.DIRECTORY

    @pytest.mark.asyncio
    async def test_domain_config_json_created(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        cfg_file = tree.nodes.get("Test_Domain/config/domain_config.json")
        assert cfg_file is not None
        assert cfg_file.node_type == NodeType.FILE

    @pytest.mark.asyncio
    async def test_domain_config_json_content(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        cfg_node = tree.nodes["Test_Domain/config/domain_config.json"]
        data = json.loads(cfg_node.content)
        assert data["domain_id"] == "test-domain"
        assert data["domain_name"] == "Test Domain"
        assert "max_agents" in data
        assert "priority_level" in data

    @pytest.mark.asyncio
    async def test_data_sources_directory_created(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        ds_dir = tree.nodes.get("Test_Domain/data_sources")
        assert ds_dir is not None
        assert ds_dir.node_type == NodeType.DIRECTORY

    @pytest.mark.asyncio
    async def test_evaluation_directory_created(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        eval_dir = tree.nodes.get("Test_Domain/evaluation")
        assert eval_dir is not None
        assert eval_dir.node_type == NodeType.DIRECTORY

    @pytest.mark.asyncio
    async def test_evaluation_criteria_json_created(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        criteria_file = tree.nodes.get("Test_Domain/evaluation/criteria.json")
        assert criteria_file is not None
        assert criteria_file.node_type == NodeType.FILE

    @pytest.mark.asyncio
    async def test_evaluation_criteria_json_content(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        criteria_node = tree.nodes["Test_Domain/evaluation/criteria.json"]
        data = json.loads(criteria_node.content)
        assert "accuracy_threshold" in data
        assert "response_time_sla_seconds" in data
        assert "uptime_target" in data

    @pytest.mark.asyncio
    async def test_readme_md_created(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        readme = tree.nodes.get("Test_Domain/README.md")
        assert readme is not None
        assert readme.node_type == NodeType.FILE

    @pytest.mark.asyncio
    async def test_readme_md_content(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        readme = tree.nodes["Test_Domain/README.md"]
        assert "Test Domain" in readme.content
        assert "A test domain for unit tests" in readme.content
        assert "agents/" in readme.content


# ===========================================================================
# DomainFolderTreeGenerator — multi-agent/skill/workflow tests
# ===========================================================================


class TestDomainFolderTreeGeneratorMulti:
    """Tests with multiple agents, skills, and workflows."""

    @pytest.mark.asyncio
    async def test_multiple_agents_all_have_directories(
        self, generator: DomainFolderTreeGenerator, legal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(legal_blueprint)
        expected_slugs = [
            "legal_operations_lead",
            "contract_analyst",
            "compliance_checker",
        ]
        for slug in expected_slugs:
            path = f"Legal_Research_Domain/agents/{slug}"
            assert path in tree.nodes, f"Missing directory for agent slug: {slug}"

    @pytest.mark.asyncio
    async def test_multiple_skills_all_have_files(
        self, generator: DomainFolderTreeGenerator, legal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(legal_blueprint)
        expected_files = [
            "Legal_Research_Domain/skills/contract_analysis.py",
            "Legal_Research_Domain/skills/compliance_checking.py",
            "Legal_Research_Domain/skills/risk_assessment.py",
        ]
        for f in expected_files:
            assert f in tree.nodes, f"Missing skill file: {f}"

    @pytest.mark.asyncio
    async def test_multiple_workflows_all_have_subdirs(
        self, generator: DomainFolderTreeGenerator, legal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(legal_blueprint)
        expected = [
            "Legal_Research_Domain/workflows/contract_review_cycle",
            "Legal_Research_Domain/workflows/compliance_audit",
        ]
        for path in expected:
            assert path in tree.nodes, f"Missing workflow directory: {path}"

    @pytest.mark.asyncio
    async def test_node_count_reasonable(
        self, generator: DomainFolderTreeGenerator, legal_blueprint: DomainBlueprint
    ) -> None:
        """A legal blueprint with 3 agents, 3 skills, 2 workflows should produce
        a non-trivial tree (at minimum root + standard dirs + per-agent dirs)."""
        tree = await generator.generate(legal_blueprint)
        # Should have at least 25 nodes (rough lower bound)
        assert len(tree.nodes) >= 25

    @pytest.mark.asyncio
    async def test_readme_lists_all_agents(
        self, generator: DomainFolderTreeGenerator, legal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(legal_blueprint)
        readme = tree.nodes["Legal_Research_Domain/README.md"]
        for agent in legal_blueprint.agents:
            assert agent.name in readme.content

    @pytest.mark.asyncio
    async def test_readme_lists_all_skills(
        self, generator: DomainFolderTreeGenerator, legal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(legal_blueprint)
        readme = tree.nodes["Legal_Research_Domain/README.md"]
        for skill in legal_blueprint.skills:
            assert skill.name in readme.content

    @pytest.mark.asyncio
    async def test_readme_lists_all_workflows(
        self, generator: DomainFolderTreeGenerator, legal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(legal_blueprint)
        readme = tree.nodes["Legal_Research_Domain/README.md"]
        for workflow in legal_blueprint.workflows:
            assert workflow.name in readme.content


# ===========================================================================
# DomainFolderTreeGenerator — EvaluationCriteria derivation
# ===========================================================================


class TestEvaluationCriteriaDerivation:
    """Tests that criteria are correctly derived from DomainConfig."""

    @pytest.mark.asyncio
    async def test_default_criteria_for_normal_priority(
        self,
        generator: DomainFolderTreeGenerator,
        minimal_blueprint: DomainBlueprint,
    ) -> None:
        # minimal_blueprint has priority_level="normal" (default)
        tree = await generator.generate(minimal_blueprint)
        criteria_node = tree.nodes["Test_Domain/evaluation/criteria.json"]
        data = json.loads(criteria_node.content)
        assert data["accuracy_threshold"] == 0.85
        assert data["uptime_target"] == 99.5

    @pytest.mark.asyncio
    async def test_stricter_criteria_for_high_priority(
        self,
        generator: DomainFolderTreeGenerator,
        legal_blueprint: DomainBlueprint,
    ) -> None:
        # legal_blueprint has priority_level="high"
        tree = await generator.generate(legal_blueprint)
        criteria_node = tree.nodes["Legal_Research_Domain/evaluation/criteria.json"]
        data = json.loads(criteria_node.content)
        assert data["accuracy_threshold"] >= 0.90
        assert data["uptime_target"] >= 99.9

    @pytest.mark.asyncio
    async def test_strictest_criteria_for_critical_priority(
        self, generator: DomainFolderTreeGenerator
    ) -> None:
        blueprint = DomainBlueprint(
            domain_name="Critical Domain",
            domain_id="critical-domain",
            description="A critical priority domain",
            agents=[
                AgentBlueprint(agent_id="a1", name="Monitor", role=AgentRole.MONITOR, goal="Watch everything"),
            ],
            skills=[SkillBlueprint(skill_id="s1", name="Monitoring", description="System monitoring")],
            workflows=[WorkflowBlueprint(workflow_id="w1", name="Alert Pipeline", steps=["Detect", "Alert"])],
            config=DomainConfig(priority_level="critical"),
        )
        tree = await generator.generate(blueprint)
        criteria_node = tree.nodes["Critical_Domain/evaluation/criteria.json"]
        data = json.loads(criteria_node.content)
        assert data["accuracy_threshold"] >= 0.95
        assert data["uptime_target"] >= 99.99

    @pytest.mark.asyncio
    async def test_custom_criteria_override(
        self,
        generator: DomainFolderTreeGenerator,
        minimal_blueprint: DomainBlueprint,
    ) -> None:
        custom = EvaluationCriteria(
            accuracy_threshold=0.999,
            custom_metrics={"latency_p99_ms": 100},
        )
        tree = await generator.generate(minimal_blueprint, evaluation_criteria=custom)
        criteria_node = tree.nodes["Test_Domain/evaluation/criteria.json"]
        data = json.loads(criteria_node.content)
        assert data["accuracy_threshold"] == 0.999
        assert data["custom_metrics"]["latency_p99_ms"] == 100


# ===========================================================================
# DomainFolderTreeGenerator — Tape logging tests
# ===========================================================================


class TestDomainFolderTreeGeneratorTapeLogging:
    """Tests for Tape audit logging."""

    @pytest.mark.asyncio
    async def test_generate_logs_event(
        self,
        generator: DomainFolderTreeGenerator,
        minimal_blueprint: DomainBlueprint,
        tape_svc: TapeService,
    ) -> None:
        await generator.generate(minimal_blueprint)
        entries = await tape_svc.get_entries(
            event_type="domain.folder_tree_generated"
        )
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_log_event_payload(
        self,
        generator: DomainFolderTreeGenerator,
        minimal_blueprint: DomainBlueprint,
        tape_svc: TapeService,
    ) -> None:
        await generator.generate(minimal_blueprint)
        entries = await tape_svc.get_entries(
            event_type="domain.folder_tree_generated"
        )
        payload = entries[0].payload
        assert payload["domain_id"] == "test-domain"
        assert payload["domain_name"] == "Test Domain"
        assert payload["agent_count"] == 1
        assert payload["skill_count"] == 1
        assert payload["workflow_count"] == 1

    @pytest.mark.asyncio
    async def test_log_counts_correct(
        self,
        generator: DomainFolderTreeGenerator,
        legal_blueprint: DomainBlueprint,
        tape_svc: TapeService,
    ) -> None:
        tree = await generator.generate(legal_blueprint)
        entries = await tape_svc.get_entries(
            event_type="domain.folder_tree_generated"
        )
        payload = entries[0].payload
        assert payload["node_count"] == len(tree.nodes)
        file_count = sum(
            1 for n in tree.nodes.values() if n.node_type == NodeType.FILE
        )
        assert payload["file_count"] == file_count

    @pytest.mark.asyncio
    async def test_multiple_generate_calls_log_multiple_events(
        self,
        generator: DomainFolderTreeGenerator,
        minimal_blueprint: DomainBlueprint,
        legal_blueprint: DomainBlueprint,
        tape_svc: TapeService,
    ) -> None:
        await generator.generate(minimal_blueprint)
        await generator.generate(legal_blueprint)
        entries = await tape_svc.get_entries(
            event_type="domain.folder_tree_generated"
        )
        assert len(entries) == 2

    @pytest.mark.asyncio
    async def test_log_agent_id_is_correct(
        self,
        generator: DomainFolderTreeGenerator,
        minimal_blueprint: DomainBlueprint,
        tape_svc: TapeService,
    ) -> None:
        await generator.generate(minimal_blueprint)
        entries = await tape_svc.get_entries(
            event_type="domain.folder_tree_generated"
        )
        assert entries[0].agent_id == "domain-folder-tree-generator"


# ===========================================================================
# DomainFolderTreeGenerator — edge cases
# ===========================================================================


class TestDomainFolderTreeGeneratorEdgeCases:
    """Edge case tests."""

    @pytest.mark.asyncio
    async def test_empty_blueprint_generates_minimal_tree(
        self, generator: DomainFolderTreeGenerator
    ) -> None:
        blueprint = DomainBlueprint(
            domain_name="Empty Domain",
            domain_id="empty-domain",
            description="A domain with no agents, skills, or workflows",
        )
        tree = await generator.generate(blueprint)
        # Root + standard dirs + README
        assert "Empty_Domain" in tree.nodes
        assert "Empty_Domain/agents" in tree.nodes
        assert "Empty_Domain/skills" in tree.nodes
        assert "Empty_Domain/workflows" in tree.nodes
        assert "Empty_Domain/templates" in tree.nodes
        assert "Empty_Domain/config" in tree.nodes
        assert "Empty_Domain/data_sources" in tree.nodes
        assert "Empty_Domain/evaluation" in tree.nodes
        assert "Empty_Domain/README.md" in tree.nodes

    @pytest.mark.asyncio
    async def test_domain_name_with_spaces_forms_valid_path(
        self, generator: DomainFolderTreeGenerator
    ) -> None:
        blueprint = DomainBlueprint(
            domain_name="My Complex Domain Name",
            domain_id="my-complex",
            description="Complex name",
        )
        tree = await generator.generate(blueprint)
        assert tree.root_path == "My_Complex_Domain_Name"
        assert "My_Complex_Domain_Name" in tree.nodes

    @pytest.mark.asyncio
    async def test_agent_with_backstory_included_in_role_md(
        self, generator: DomainFolderTreeGenerator
    ) -> None:
        blueprint = DomainBlueprint(
            domain_name="Backstory Domain",
            domain_id="backstory-domain",
            description="A domain",
            agents=[
                AgentBlueprint(
                    agent_id="a1",
                    name="Deep Agent",
                    role=AgentRole.RESEARCHER,
                    goal="Research deeply",
                    backstory="Once a great scholar, now a digital agent.",
                ),
            ],
            skills=[SkillBlueprint(skill_id="s1", name="Research", description="Research skill")],
            workflows=[WorkflowBlueprint(workflow_id="w1", name="Research Flow", steps=["Explore"])],
        )
        tree = await generator.generate(blueprint)
        role_node = tree.nodes["Backstory_Domain/agents/deep_agent/role.md"]
        assert "Once a great scholar" in role_node.content

    @pytest.mark.asyncio
    async def test_each_agent_has_separate_directory(
        self, generator: DomainFolderTreeGenerator
    ) -> None:
        blueprint = DomainBlueprint(
            domain_name="Multi Agent Domain",
            domain_id="multi-agent",
            description="Multi-agent test",
            agents=[
                AgentBlueprint(agent_id=f"a{i}", name=f"Agent {i}", role=AgentRole.EXECUTOR, goal=f"Goal {i}")
                for i in range(5)
            ],
            skills=[SkillBlueprint(skill_id="s1", name="Core Skill", description="A skill")],
            workflows=[WorkflowBlueprint(workflow_id="w1", name="Pipe", steps=["A"])],
        )
        tree = await generator.generate(blueprint)
        for i in range(5):
            path = f"Multi_Agent_Domain/agents/agent_{i}"
            assert path in tree.nodes, f"Missing directory: {path}"

    @pytest.mark.asyncio
    async def test_parent_directory_children_references_correct(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        agents_dir = tree.nodes["Test_Domain/agents"]
        # agents/ should list the test_agent sub-directory
        assert "Test_Domain/agents/test_agent" in agents_dir.children

    @pytest.mark.asyncio
    async def test_root_children_contains_all_top_level_dirs(
        self, generator: DomainFolderTreeGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        tree = await generator.generate(minimal_blueprint)
        root = tree.nodes["Test_Domain"]
        expected_children = {
            "Test_Domain/agents",
            "Test_Domain/skills",
            "Test_Domain/workflows",
            "Test_Domain/templates",
            "Test_Domain/config",
            "Test_Domain/data_sources",
            "Test_Domain/evaluation",
            "Test_Domain/README.md",
        }
        assert expected_children.issubset(set(root.children))


# ===========================================================================
# Package-level import tests
# ===========================================================================


class TestPackageImports:
    """Verify that all expected symbols are importable from packages.domain."""

    def test_import_domain_blueprint(self) -> None:
        from packages.domain import DomainBlueprint  # noqa: F401 (import check)

    def test_import_agent_blueprint(self) -> None:
        from packages.domain import AgentBlueprint  # noqa: F401

    def test_import_skill_blueprint(self) -> None:
        from packages.domain import SkillBlueprint  # noqa: F401

    def test_import_workflow_blueprint(self) -> None:
        from packages.domain import WorkflowBlueprint  # noqa: F401

    def test_import_domain_config(self) -> None:
        from packages.domain import DomainConfig  # noqa: F401

    def test_import_evaluation_criteria(self) -> None:
        from packages.domain import EvaluationCriteria  # noqa: F401

    def test_import_domain_folder_tree_generator(self) -> None:
        from packages.domain import DomainFolderTreeGenerator  # noqa: F401

    def test_import_starter_canvas_generator(self) -> None:
        from packages.domain import StarterCanvasGenerator  # noqa: F401

    def test_import_canvas_layout(self) -> None:
        from packages.domain import CanvasLayout  # noqa: F401
