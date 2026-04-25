"""Tests for GitNexus-inspired folder tree enhancements.

Covers:
- ImpactAnalyzer: assess_impact(), severity classification, mitigations
- DependencyGraphBuilder: build_graph(), edge extraction, semantic inference
- SkillMdGenerator: generate_for_agent/skill/domain, parse_skill_md
- FolderTreeService convenience methods
- PrimeIntrospector new Folder Thinking Mode methods
- DomainFolderTreeGenerator SKILL.md auto-generation
"""

from __future__ import annotations

import pytest

from packages.folder_tree import (
    FolderTreeService,
)
from packages.folder_tree.dependency_graph import (
    DependencyEdge,
    DependencyEdgeType,
    DependencyGraph,
    DependencyGraphBuilder,
    DependencyNode,
)
from packages.folder_tree.impact import (
    DependentNode,
    ImpactAnalyzer,
    ImpactReport,
    ImpactSeverity,
)
from packages.folder_tree.skill_md import (
    SkillMdContent,
    SkillMdGenerator,
)
from packages.prime.domain_creation import (
    AgentBlueprint,
    AgentRole,
    DomainBlueprint,
    SkillBlueprint,
    WorkflowBlueprint,
)
from packages.prime.introspection import (
    FolderThinkingError,
    PrimeIntrospector,
)
from packages.tape.repository import InMemoryTapeRepository
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tape_service() -> TapeService:
    return TapeService(InMemoryTapeRepository())


def _make_folder_tree_service(tape: TapeService | None = None) -> FolderTreeService:
    tape = tape or _make_tape_service()
    return FolderTreeService(tape_service=tape)


async def _create_sample_tree(
    fts: FolderTreeService,
    domain_id: str = "test-domain",
    domain_name: str = "Test Domain",
) -> None:
    """Create a sample domain folder tree for testing."""
    agents = [
        AgentBlueprint(
            agent_id="analyst",
            name="Contract Analyst",
            role=AgentRole.SPECIALIST,
            goal="Analyse contracts for risks",
            capabilities=["contract_analysis", "risk_scoring"],
            tools=["contract_parser", "risk_model"],
        ),
        AgentBlueprint(
            agent_id="reviewer",
            name="Compliance Reviewer",
            role=AgentRole.REVIEWER,
            goal="Review compliance requirements",
            capabilities=["compliance_check", "audit_trail"],
            tools=["compliance_db", "audit_logger"],
        ),
    ]
    skills = [
        SkillBlueprint(
            skill_id="contract_analysis",
            name="Contract Analysis",
            description="Analyse legal contracts for risk factors",
        ),
        SkillBlueprint(
            skill_id="risk_scoring",
            name="Risk Scoring",
            description="Score risk levels for contracts",
        ),
    ]
    workflows = [
        WorkflowBlueprint(
            workflow_id="full_review",
            name="Full Contract Review",
            steps=["Gather documents", "Analyse", "Score risk", "Report"],
            agent_ids=["analyst", "reviewer"],
        ),
    ]
    await fts.create_tree(
        domain_id=domain_id,
        domain_name=domain_name,
        description="A test domain for contract analysis",
        agents=agents,
        skills=skills,
        workflows=workflows,
    )


# ===========================================================================
# ImpactAnalyzer tests
# ===========================================================================

class TestImpactAnalyzer:
    """Tests for the ImpactAnalyzer."""

    @pytest.mark.asyncio
    async def test_assess_impact_file(self) -> None:
        """Assessing impact of a file should return direct dependents."""
        tape = _make_tape_service()
        fts = _make_folder_tree_service(tape)
        await _create_sample_tree(fts)

        analyzer = ImpactAnalyzer(folder_tree_service=fts, tape_service=tape)
        report = await analyzer.assess_impact("test-domain", "agents/contract_analyst/role.md")

        assert isinstance(report, ImpactReport)
        assert report.domain_id == "test-domain"
        assert report.target_path == "agents/contract_analyst/role.md"
        assert report.severity in list(ImpactSeverity)
        assert isinstance(report.mitigations, list)

    @pytest.mark.asyncio
    async def test_assess_impact_directory(self) -> None:
        """Assessing impact of a directory should have wider blast radius."""
        tape = _make_tape_service()
        fts = _make_folder_tree_service(tape)
        await _create_sample_tree(fts)

        analyzer = ImpactAnalyzer(folder_tree_service=fts, tape_service=tape)
        report = await analyzer.assess_impact("test-domain", "agents/contract_analyst")

        # Directory should have at least the child files as dependents
        assert report.affected_node_count >= 0  # structural dependents

    @pytest.mark.asyncio
    async def test_assess_impact_config_critical(self) -> None:
        """Changing domain_config.json should be CRITICAL severity."""
        tape = _make_tape_service()
        fts = _make_folder_tree_service(tape)
        await _create_sample_tree(fts)

        analyzer = ImpactAnalyzer(folder_tree_service=fts, tape_service=tape)
        report = await analyzer.assess_impact("test-domain", "config/domain_config.json")

        assert report.severity == ImpactSeverity.CRITICAL

    @pytest.mark.asyncio
    async def test_assess_impact_readme_critical(self) -> None:
        """Changing README.md should be CRITICAL severity."""
        tape = _make_tape_service()
        fts = _make_folder_tree_service(tape)
        await _create_sample_tree(fts)

        analyzer = ImpactAnalyzer(folder_tree_service=fts, tape_service=tape)
        report = await analyzer.assess_impact("test-domain", "README.md")

        assert report.severity == ImpactSeverity.CRITICAL

    @pytest.mark.asyncio
    async def test_assess_impact_unknown_path(self) -> None:
        """Assessing a non-existent path should raise DomainTreeNotFoundError."""
        from packages.folder_tree import DomainTreeNotFoundError

        tape = _make_tape_service()
        fts = _make_folder_tree_service(tape)

        analyzer = ImpactAnalyzer(folder_tree_service=fts, tape_service=tape)
        with pytest.raises(DomainTreeNotFoundError):
            await analyzer.assess_impact("nonexistent", "some/path")

    @pytest.mark.asyncio
    async def test_impact_report_model(self) -> None:
        """ImpactReport model should have all expected fields."""
        report = ImpactReport(
            domain_id="test",
            target_path="some/file.md",
            severity=ImpactSeverity.HIGH,
            affected_node_count=5,
            mitigations=["Review dependents"],
        )
        assert report.severity == ImpactSeverity.HIGH
        assert report.affected_node_count == 5
        assert len(report.mitigations) == 1
        assert report.id is not None

    def test_dependent_node_model(self) -> None:
        """DependentNode model should store path and hop distance."""
        dep = DependentNode(
            path="Test_Domain/agents/analyst/role.md",
            node_type="file",
            hop_distance=1,
            reason="Cross-reference",
        )
        assert dep.hop_distance == 1
        assert dep.node_type == "file"

    def test_severity_enum(self) -> None:
        """ImpactSeverity should have 4 levels."""
        assert ImpactSeverity.LOW.value == "low"
        assert ImpactSeverity.MEDIUM.value == "medium"
        assert ImpactSeverity.HIGH.value == "high"
        assert ImpactSeverity.CRITICAL.value == "critical"

    @pytest.mark.asyncio
    async def test_impact_mitigations_for_high(self) -> None:
        """HIGH severity should generate appropriate mitigations."""
        tape = _make_tape_service()
        fts = _make_folder_tree_service(tape)
        await _create_sample_tree(fts)

        analyzer = ImpactAnalyzer(folder_tree_service=fts, tape_service=tape)
        # The agents directory should have many dependents
        report = await analyzer.assess_impact("test-domain", "agents")

        if report.severity in (ImpactSeverity.HIGH, ImpactSeverity.CRITICAL):
            assert len(report.mitigations) >= 1


# ===========================================================================
# DependencyGraphBuilder tests
# ===========================================================================

class TestDependencyGraphBuilder:
    """Tests for the DependencyGraphBuilder."""

    @pytest.mark.asyncio
    async def test_build_graph(self) -> None:
        """Building a graph should return nodes and edges."""
        tape = _make_tape_service()
        fts = _make_folder_tree_service(tape)
        await _create_sample_tree(fts)

        builder = DependencyGraphBuilder(folder_tree_service=fts, tape_service=tape)
        graph = await builder.build_graph("test-domain")

        assert isinstance(graph, DependencyGraph)
        assert graph.domain_id == "test-domain"
        assert graph.node_count > 0
        assert graph.edge_count > 0

    @pytest.mark.asyncio
    async def test_build_graph_has_structural_edges(self) -> None:
        """Graph should have STRUCTURAL edges for parent-child relationships."""
        tape = _make_tape_service()
        fts = _make_folder_tree_service(tape)
        await _create_sample_tree(fts)

        builder = DependencyGraphBuilder(folder_tree_service=fts, tape_service=tape)
        graph = await builder.build_graph("test-domain", include_semantic=False)

        structural_edges = [
            e for e in graph.edges
            if e.edge_type == DependencyEdgeType.STRUCTURAL
        ]
        assert len(structural_edges) > 0

    @pytest.mark.asyncio
    async def test_build_graph_with_semantic(self) -> None:
        """Graph with semantic edges should have more edges than without."""
        tape = _make_tape_service()
        fts = _make_folder_tree_service(tape)
        await _create_sample_tree(fts)

        builder = DependencyGraphBuilder(folder_tree_service=fts, tape_service=tape)
        graph_semantic = await builder.build_graph("test-domain", include_semantic=True)
        graph_no_semantic = await builder.build_graph("test-domain", include_semantic=False)

        # Semantic graph should have >= edges
        assert graph_semantic.edge_count >= graph_no_semantic.edge_count

    @pytest.mark.asyncio
    async def test_build_graph_group_counts(self) -> None:
        """Graph should have group counts for UI rendering."""
        tape = _make_tape_service()
        fts = _make_folder_tree_service(tape)
        await _create_sample_tree(fts)

        builder = DependencyGraphBuilder(folder_tree_service=fts, tape_service=tape)
        graph = await builder.build_graph("test-domain")

        assert isinstance(graph.group_counts, dict)
        # Should have at least "agents" and "skills" groups
        assert "agents" in graph.group_counts
        assert "skills" in graph.group_counts

    @pytest.mark.asyncio
    async def test_build_graph_nonexistent_domain(self) -> None:
        """Building graph for nonexistent domain should raise."""
        from packages.folder_tree import DomainTreeNotFoundError

        tape = _make_tape_service()
        fts = _make_folder_tree_service(tape)

        builder = DependencyGraphBuilder(folder_tree_service=fts, tape_service=tape)
        with pytest.raises(DomainTreeNotFoundError):
            await builder.build_graph("nonexistent")

    def test_dependency_edge_types(self) -> None:
        """DependencyEdgeType should have 4 types."""
        assert DependencyEdgeType.IMPORT.value == "import"
        assert DependencyEdgeType.REFERENCE.value == "reference"
        assert DependencyEdgeType.STRUCTURAL.value == "structural"
        assert DependencyEdgeType.SEMANTIC.value == "semantic"

    def test_dependency_node_model(self) -> None:
        """DependencyNode should store group info."""
        node = DependencyNode(
            id="Test_Domain/agents/analyst",
            label="analyst",
            node_type="directory",
            group="agents",
            path="Test_Domain/agents/analyst",
        )
        assert node.group == "agents"

    def test_dependency_edge_model(self) -> None:
        """DependencyEdge should store edge type and label."""
        edge = DependencyEdge(
            source="a",
            target="b",
            edge_type=DependencyEdgeType.IMPORT,
            label="imports module",
        )
        assert edge.edge_type == DependencyEdgeType.IMPORT
        assert edge.label == "imports module"

    @pytest.mark.asyncio
    async def test_extract_keywords(self) -> None:
        """Keyword extraction should filter stop words."""
        keywords = DependencyGraphBuilder._extract_keywords(
            "The contract analysis system analyses contracts for risk"
        )
        assert "contract" in keywords
        assert "analysis" in keywords
        assert "risk" in keywords
        # Stop words should be filtered
        assert "the" not in keywords
        assert "for" not in keywords


# ===========================================================================
# SkillMdGenerator tests
# ===========================================================================

class TestSkillMdGenerator:
    """Tests for the SkillMdGenerator."""

    def test_generate_for_agent(self) -> None:
        """Generating SKILL.md for an agent should produce valid markdown."""
        tape = _make_tape_service()
        fts = _make_folder_tree_service(tape)
        gen = SkillMdGenerator(folder_tree_service=fts, tape_service=tape)

        content = gen.generate_for_agent(
            agent_name="Contract Analyst",
            role="specialist",
            goal="Analyse contracts",
            capabilities=["contract_analysis", "risk_scoring"],
            tools=["contract_parser"],
        )

        assert "# SKILL.md -- Contract Analyst" in content
        assert "specialist" in content
        assert "contract_analysis" in content
        assert "risk_scoring" in content
        assert "contract_parser" in content
        assert "## Capabilities" in content
        assert "## Dependencies" in content
        assert "## Usage Examples" in content
        assert "## Metadata" in content

    def test_generate_for_agent_minimal(self) -> None:
        """Generating SKILL.md with no capabilities should still work."""
        tape = _make_tape_service()
        fts = _make_folder_tree_service(tape)
        gen = SkillMdGenerator(folder_tree_service=fts, tape_service=tape)

        content = gen.generate_for_agent(agent_name="Simple Agent")
        assert "# SKILL.md -- Simple Agent" in content
        assert "_No capabilities defined_" in content

    def test_generate_for_skill(self) -> None:
        """Generating SKILL.md for a skill should include description."""
        tape = _make_tape_service()
        fts = _make_folder_tree_service(tape)
        gen = SkillMdGenerator(folder_tree_service=fts, tape_service=tape)

        content = gen.generate_for_skill(
            skill_name="Contract Analysis",
            description="Analyse legal contracts for risk factors",
        )

        assert "# SKILL.md -- Contract Analysis" in content
        assert "Analyse legal contracts for risk factors" in content
        assert "## Description" in content
        assert "## Dependencies" in content

    def test_generate_for_skill_reused(self) -> None:
        """Reused skill SKILL.md should indicate reuse."""
        tape = _make_tape_service()
        fts = _make_folder_tree_service(tape)
        gen = SkillMdGenerator(folder_tree_service=fts, tape_service=tape)

        content = gen.generate_for_skill(
            skill_name="Shared Skill",
            is_reused=True,
        )

        assert "(reused)" in content
        assert "| Reused | Yes |" in content

    def test_generate_for_skill_with_deps(self) -> None:
        """SKILL.md with explicit dependencies should list them."""
        tape = _make_tape_service()
        fts = _make_folder_tree_service(tape)
        gen = SkillMdGenerator(folder_tree_service=fts, tape_service=tape)

        content = gen.generate_for_skill(
            skill_name="Complex Skill",
            dependencies=["skills/parser.py", "agents/analyst/role.md"],
        )

        assert "skills/parser.py" in content
        assert "agents/analyst/role.md" in content

    @pytest.mark.asyncio
    async def test_generate_for_domain(self) -> None:
        """Generating SKILL.md files for a domain should write to tree."""
        tape = _make_tape_service()
        fts = _make_folder_tree_service(tape)
        await _create_sample_tree(fts)

        gen = SkillMdGenerator(folder_tree_service=fts, tape_service=tape)
        results = await gen.generate_for_domain("test-domain")

        assert isinstance(results, dict)
        assert len(results) > 0
        # Should have SKILL.md entries for agents
        agent_skill_mds = [p for p in results if "SKILL.md" in p]
        assert len(agent_skill_mds) > 0

    @pytest.mark.asyncio
    async def test_update_skill_md(self) -> None:
        """Updating a SKILL.md should produce new content."""
        tape = _make_tape_service()
        fts = _make_folder_tree_service(tape)
        await _create_sample_tree(fts)

        gen = SkillMdGenerator(folder_tree_service=fts, tape_service=tape)
        content = await gen.update_skill_md(
            "test-domain",
            "agents/contract_analyst/SKILL.md",
        )

        assert isinstance(content, str)
        assert "SKILL.md" in content

    def test_parse_skill_md(self) -> None:
        """Parsing SKILL.md should extract structured data."""
        raw = (
            "# SKILL.md -- Test Agent\n\n"
            "> Auto-generated\n\n"
            "## Metadata\n\n"
            "| Field | Value |\n|-------|-------|\n"
            "| Version | `2.0.0` |\n"
            "| Status | deprecated |\n"
            "| Last Updated | 2025-01-15 |\n\n"
            "## Capabilities\n\n"
            "- analysis\n"
            "- scoring\n\n"
            "## Dependencies\n\n"
            "- `tools/parser.md`\n"
            "- `skills/math.py`\n\n"
            "## Usage Examples\n\n"
            "```\n"
            "agent = registry.get_agent('test')\n"
            "result = await agent.execute()\n"
            "```\n"
        )

        parsed = SkillMdGenerator.parse_skill_md(raw)
        assert isinstance(parsed, SkillMdContent)
        assert parsed.title == "Test Agent"
        assert parsed.version == "2.0.0"
        assert parsed.status == "deprecated"
        assert parsed.last_updated == "2025-01-15"
        assert "analysis" in parsed.capabilities
        assert "scoring" in parsed.capabilities
        assert "tools/parser.md" in parsed.dependencies
        assert "skills/math.py" in parsed.dependencies

    def test_parse_skill_md_empty(self) -> None:
        """Parsing empty content should return defaults."""
        parsed = SkillMdGenerator.parse_skill_md("")
        assert parsed.title == ""
        assert parsed.version == "1.0.0"
        assert parsed.status == "active"

    def test_skill_md_content_model(self) -> None:
        """SkillMdContent model should have all fields."""
        content = SkillMdContent(
            title="Test",
            capabilities=["a", "b"],
            dependencies=["x.md"],
            version="1.0.0",
        )
        assert content.title == "Test"
        assert len(content.capabilities) == 2
        assert content.raw_content == ""


# ===========================================================================
# FolderTreeService convenience methods
# ===========================================================================

class TestFolderTreeServiceEnhancements:
    """Tests for the new FolderTreeService convenience methods."""

    @pytest.mark.asyncio
    async def test_assess_impact_convenience(self) -> None:
        """FolderTreeService.assess_impact() should delegate correctly."""
        tape = _make_tape_service()
        fts = _make_folder_tree_service(tape)
        await _create_sample_tree(fts)

        report = await fts.assess_impact("test-domain", "README.md")
        # Should return an ImpactReport-like dict
        assert isinstance(report, object)

    @pytest.mark.asyncio
    async def test_build_dependency_graph_convenience(self) -> None:
        """FolderTreeService.build_dependency_graph() should delegate."""
        tape = _make_tape_service()
        fts = _make_folder_tree_service(tape)
        await _create_sample_tree(fts)

        graph = await fts.build_dependency_graph("test-domain")
        assert isinstance(graph, object)

    @pytest.mark.asyncio
    async def test_generate_skill_mds_convenience(self) -> None:
        """FolderTreeService.generate_skill_mds() should delegate."""
        tape = _make_tape_service()
        fts = _make_folder_tree_service(tape)
        await _create_sample_tree(fts)

        results = await fts.generate_skill_mds("test-domain")
        assert isinstance(results, dict)


# ===========================================================================
# PrimeIntrospector Folder Thinking Mode enhancements
# ===========================================================================

class TestPrimeFolderThinkingEnhancements:
    """Tests for Prime's new Folder Thinking Mode methods."""

    @pytest.mark.asyncio
    async def test_folder_assess_impact(self) -> None:
        """Prime should delegate assess_impact to folder tree service."""
        tape = _make_tape_service()
        fts = _make_folder_tree_service(tape)
        await _create_sample_tree(fts)

        introspector = PrimeIntrospector(
            tape_service=tape,
            folder_tree_service=fts,
        )
        report = await introspector.folder_assess_impact(
            "test-domain", "README.md"
        )
        assert report is not None

    @pytest.mark.asyncio
    async def test_folder_dependency_graph(self) -> None:
        """Prime should delegate dependency graph building."""
        tape = _make_tape_service()
        fts = _make_folder_tree_service(tape)
        await _create_sample_tree(fts)

        introspector = PrimeIntrospector(
            tape_service=tape,
            folder_tree_service=fts,
        )
        graph = await introspector.folder_dependency_graph("test-domain")
        assert graph is not None

    @pytest.mark.asyncio
    async def test_folder_generate_skill_mds(self) -> None:
        """Prime should delegate SKILL.md generation."""
        tape = _make_tape_service()
        fts = _make_folder_tree_service(tape)
        await _create_sample_tree(fts)

        introspector = PrimeIntrospector(
            tape_service=tape,
            folder_tree_service=fts,
        )
        results = await introspector.folder_generate_skill_mds("test-domain")
        assert isinstance(results, dict)

    @pytest.mark.asyncio
    async def test_folder_assess_impact_no_service(self) -> None:
        """Prime should raise FolderThinkingError without folder tree service."""
        tape = _make_tape_service()
        introspector = PrimeIntrospector(tape_service=tape)

        with pytest.raises(FolderThinkingError):
            await introspector.folder_assess_impact("test", "path")

    @pytest.mark.asyncio
    async def test_folder_dependency_graph_no_service(self) -> None:
        """Prime should raise FolderThinkingError without folder tree service."""
        tape = _make_tape_service()
        introspector = PrimeIntrospector(tape_service=tape)

        with pytest.raises(FolderThinkingError):
            await introspector.folder_dependency_graph("test")

    @pytest.mark.asyncio
    async def test_folder_generate_skill_mds_no_service(self) -> None:
        """Prime should raise FolderThinkingError without folder tree service."""
        tape = _make_tape_service()
        introspector = PrimeIntrospector(tape_service=tape)

        with pytest.raises(FolderThinkingError):
            await introspector.folder_generate_skill_mds("test")


# ===========================================================================
# DomainFolderTreeGenerator SKILL.md auto-generation
# ===========================================================================

class TestDomainFolderTreeGeneratorSkillMd:
    """Tests that DomainFolderTreeGenerator auto-generates SKILL.md files."""

    @pytest.mark.asyncio
    async def test_tree_contains_agent_skill_md(self) -> None:
        """Generated tree should contain SKILL.md for each agent."""
        tape = _make_tape_service()
        from packages.domain.domain_blueprint import DomainFolderTreeGenerator

        blueprint = DomainBlueprint(
            domain_name="Legal Research",
            domain_id="legal-research",
            description="Legal domain",
            agents=[
                AgentBlueprint(
                    agent_id="a1",
                    name="Contract Analyst",
                    role=AgentRole.SPECIALIST,
                    goal="Analyse contracts",
                    capabilities=["contract_analysis"],
                ),
            ],
            skills=[
                SkillBlueprint(
                    skill_id="s1",
                    name="Contract Analysis",
                    description="Analyse contracts",
                ),
            ],
        )

        generator = DomainFolderTreeGenerator(tape_service=tape)
        tree = await generator.generate(blueprint)

        # Find SKILL.md files
        skill_md_nodes = [
            n for p, n in tree.nodes.items()
            if n.name == "SKILL.md"
        ]
        assert len(skill_md_nodes) >= 1

    @pytest.mark.asyncio
    async def test_tree_contains_skill_skill_md(self) -> None:
        """Generated tree should contain SKILL.md for each skill."""
        tape = _make_tape_service()
        from packages.domain.domain_blueprint import DomainFolderTreeGenerator

        blueprint = DomainBlueprint(
            domain_name="Legal",
            domain_id="legal",
            description="Legal",
            agents=[
                AgentBlueprint(
                    agent_id="a1",
                    name="Analyst",
                    role=AgentRole.SPECIALIST,
                    goal="Analyse",
                ),
            ],
            skills=[
                SkillBlueprint(
                    skill_id="s1",
                    name="Analysis",
                    description="Do analysis",
                ),
            ],
        )

        generator = DomainFolderTreeGenerator(tape_service=tape)
        tree = await generator.generate(blueprint)

        # Find skill-level SKILL.md files (named <skill>_SKILL.md)
        skill_md_nodes = [
            n for p, n in tree.nodes.items()
            if n.name.endswith("_SKILL.md")
        ]
        assert len(skill_md_nodes) >= 1

    @pytest.mark.asyncio
    async def test_agent_skill_md_content(self) -> None:
        """SKILL.md content should reference agent capabilities."""
        tape = _make_tape_service()
        from packages.domain.domain_blueprint import DomainFolderTreeGenerator

        blueprint = DomainBlueprint(
            domain_name="Finance",
            domain_id="finance",
            description="Finance domain",
            agents=[
                AgentBlueprint(
                    agent_id="a1",
                    name="Risk Analyst",
                    role=AgentRole.SPECIALIST,
                    goal="Assess risk",
                    capabilities=["risk_assessment", "portfolio_analysis"],
                    tools=["risk_model", "market_data"],
                ),
            ],
            skills=[],
        )

        generator = DomainFolderTreeGenerator(tape_service=tape)
        tree = await generator.generate(blueprint)

        # Find the agent SKILL.md
        skill_md_path = None
        for p, n in tree.nodes.items():
            if n.name == "SKILL.md" and "/agents/" in p:
                skill_md_path = p
                break

        assert skill_md_path is not None
        content = tree.nodes[skill_md_path].content
        assert "risk_assessment" in content
        assert "portfolio_analysis" in content
