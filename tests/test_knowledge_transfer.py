"""Tests for Cross-Domain Knowledge Transfer engine."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import pytest

from packages.prime.knowledge_transfer import (
    AdaptationType,
    CompatibilityAssessor,
    CompatibilityLevel,
    DomainNotFoundError,
    IncompatibleKnowledgeError,
    KnowledgeExtractor,
    KnowledgeItem,
    KnowledgePackage,
    KnowledgeTransferEngine,
    KnowledgeTransferError,
    KnowledgeType,
    TransferNotFoundError,
    TransferRecord,
    TransferResult,
    TransferStatus,
    TransferStore,
    TransferTransitionError,
    TransferValidationError,
    _validate_transfer_transition,
)
from packages.tape.repository import InMemoryTapeRepository
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_tape_service() -> TapeService:
    repo = InMemoryTapeRepository()
    return TapeService(repo)


def _make_engine(
    tape_service: TapeService | None = None,
) -> KnowledgeTransferEngine:
    return KnowledgeTransferEngine(
        tape_service=tape_service or _make_tape_service(),
    )


LEGAL_METADATA: dict[str, object] = {
    "name": "Legal Research",
    "agents": [
        {"role": "researcher", "name": "Legal Researcher", "skills": ["case_law"]},
        {"role": "analyst", "name": "Legal Analyst", "skills": ["contract_review"]},
    ],
    "skills": [
        {"name": "Case Law Search", "description": "Search case law databases"},
        {"name": "Contract Review", "description": "Review and analyse contracts"},
        {"name": "Legal Research", "description": "General legal research skill"},
    ],
    "workflows": [
        {"name": "Document Review", "description": "Systematic document review workflow"},
    ],
    "config": {"max_results": 50, "language": "en"},
    "patterns": [
        {"name": "Precedent Analysis", "description": "Pattern for analysing legal precedents"},
    ],
    "best_practices": [
        {"name": "Source Verification", "description": "Always verify legal sources"},
    ],
}

FINANCE_METADATA: dict[str, object] = {
    "name": "Finance Operations",
    "agents": [
        {"role": "analyst", "name": "Financial Analyst", "skills": ["risk_assessment"]},
    ],
    "skills": [
        {"name": "Risk Assessment", "description": "Assess financial risk"},
    ],
    "workflows": [
        {"name": "Compliance Check", "description": "Regulatory compliance workflow"},
    ],
    "config": {"max_results": 100, "currency": "USD"},
}

RESEARCH_METADATA: dict[str, object] = {
    "name": "Research Lab",
    "skills": [
        {"name": "Data Analysis", "description": "Statistical data analysis"},
        {"name": "Literature Review", "description": "Systematic literature review"},
    ],
    "workflows": [
        {"name": "Peer Review", "description": "Academic peer review workflow"},
    ],
    "config": {"field": "science"},
}


# ===========================================================================
# KnowledgeExtractor tests
# ===========================================================================


class TestKnowledgeExtractor:
    """Test KnowledgeExtractor extraction logic."""

    def test_extract_skills(self) -> None:
        ext = KnowledgeExtractor()
        items = ext.extract_from_domain(
            domain_id="legal",
            domain_metadata=LEGAL_METADATA,
            knowledge_types=[KnowledgeType.SKILL],
        )
        assert len(items) == 3
        assert all(i.knowledge_type == KnowledgeType.SKILL for i in items)
        names = {i.name for i in items}
        assert "Case Law Search" in names
        assert "Contract Review" in names

    def test_extract_agent_roles(self) -> None:
        ext = KnowledgeExtractor()
        items = ext.extract_from_domain(
            domain_id="legal",
            domain_metadata=LEGAL_METADATA,
            knowledge_types=[KnowledgeType.AGENT_ROLE],
        )
        # 2 unique roles: researcher, analyst
        assert len(items) == 2
        assert all(i.knowledge_type == KnowledgeType.AGENT_ROLE for i in items)

    def test_extract_agent_roles_dedup(self) -> None:
        """Duplicate roles should be deduplicated."""
        metadata: dict[str, object] = {
            "agents": [
                {"role": "analyst", "name": "A1"},
                {"role": "analyst", "name": "A2"},
            ],
        }
        ext = KnowledgeExtractor()
        items = ext.extract_from_domain(
            domain_id="test",
            domain_metadata=metadata,
            knowledge_types=[KnowledgeType.AGENT_ROLE],
        )
        assert len(items) == 1

    def test_extract_workflows(self) -> None:
        ext = KnowledgeExtractor()
        items = ext.extract_from_domain(
            domain_id="legal",
            domain_metadata=LEGAL_METADATA,
            knowledge_types=[KnowledgeType.WORKFLOW],
        )
        assert len(items) == 1
        assert items[0].name == "Document Review"

    def test_extract_config(self) -> None:
        ext = KnowledgeExtractor()
        items = ext.extract_from_domain(
            domain_id="legal",
            domain_metadata=LEGAL_METADATA,
            knowledge_types=[KnowledgeType.CONFIG],
        )
        assert len(items) == 1
        assert items[0].knowledge_type == KnowledgeType.CONFIG

    def test_extract_patterns(self) -> None:
        ext = KnowledgeExtractor()
        items = ext.extract_from_domain(
            domain_id="legal",
            domain_metadata=LEGAL_METADATA,
            knowledge_types=[KnowledgeType.PATTERN],
        )
        assert len(items) == 1
        assert items[0].name == "Precedent Analysis"

    def test_extract_best_practices(self) -> None:
        ext = KnowledgeExtractor()
        items = ext.extract_from_domain(
            domain_id="legal",
            domain_metadata=LEGAL_METADATA,
            knowledge_types=[KnowledgeType.BEST_PRACTICE],
        )
        assert len(items) == 1
        assert items[0].name == "Source Verification"

    def test_extract_all_types_by_default(self) -> None:
        ext = KnowledgeExtractor()
        items = ext.extract_from_domain(
            domain_id="legal",
            domain_metadata=LEGAL_METADATA,
        )
        # 3 skills + 2 roles + 1 workflow + 1 config + 1 pattern + 1 best_practice = 9
        assert len(items) == 9

    def test_extract_empty_domain(self) -> None:
        ext = KnowledgeExtractor()
        items = ext.extract_from_domain(
            domain_id="empty",
            domain_metadata={},
        )
        # Only config with empty dict
        assert len(items) == 1

    def test_extract_with_non_list_agents(self) -> None:
        metadata: dict[str, object] = {"agents": "not a list"}
        ext = KnowledgeExtractor()
        items = ext.extract_from_domain(
            domain_id="test",
            domain_metadata=metadata,
            knowledge_types=[KnowledgeType.AGENT_ROLE],
        )
        assert len(items) == 0

    def test_extract_skill_with_dict_entries(self) -> None:
        metadata: dict[str, object] = {
            "skills": [{"name": "S1"}, "not_a_dict", {"name": "S2"}],
        }
        ext = KnowledgeExtractor()
        items = ext.extract_from_domain(
            domain_id="test",
            domain_metadata=metadata,
            knowledge_types=[KnowledgeType.SKILL],
        )
        # Only dict entries count
        assert len(items) == 2


# ===========================================================================
# CompatibilityAssessor tests
# ===========================================================================


class TestCompatibilityAssessor:
    """Test compatibility assessment logic."""

    def test_high_compatibility_skill(self) -> None:
        assessor = CompatibilityAssessor()
        item = KnowledgeItem(
            name="Unique Skill",
            knowledge_type=KnowledgeType.SKILL,
            source_domain_id="source",
            success_rate=0.9,
        )
        assessed = assessor.assess_item(item, FINANCE_METADATA)
        # Skill type bonus + base = high
        assert assessed.compatibility_score > 0.5
        assert assessed.compatibility_level in (
            CompatibilityLevel.HIGH,
            CompatibilityLevel.MEDIUM,
        )

    def test_duplicate_item_low_compatibility(self) -> None:
        assessor = CompatibilityAssessor()
        item = KnowledgeItem(
            name="Risk Assessment",  # Already exists in finance
            knowledge_type=KnowledgeType.SKILL,
            source_domain_id="source",
        )
        assessed = assessor.assess_item(item, FINANCE_METADATA)
        # Duplicate penalty should reduce score
        assert assessed.compatibility_score < 0.5

    def test_incompatible_item(self) -> None:
        assessor = CompatibilityAssessor()
        item = KnowledgeItem(
            name="Duplicate Skill",
            knowledge_type=KnowledgeType.CONFIG,
            source_domain_id="source",
            success_rate=0.1,
        )
        assessed = assessor.assess_item(item, FINANCE_METADATA)
        # Config type + low success rate = low
        assert assessed.compatibility_score < 0.5

    def test_score_to_level_mapping(self) -> None:
        assert CompatibilityAssessor._score_to_level(0.8) == CompatibilityLevel.HIGH
        assert CompatibilityAssessor._score_to_level(0.5) == CompatibilityLevel.MEDIUM
        assert CompatibilityAssessor._score_to_level(0.3) == CompatibilityLevel.LOW
        assert CompatibilityAssessor._score_to_level(0.1) == CompatibilityLevel.INCOMPATIBLE

    def test_adaptation_type_high_score(self) -> None:
        assert CompatibilityAssessor._determine_adaptation(
            KnowledgeItem(name="x", knowledge_type=KnowledgeType.SKILL, source_domain_id="s"),
            {}, 0.85,
        ) == AdaptationType.NONE

    def test_adaptation_type_medium_score(self) -> None:
        assert CompatibilityAssessor._determine_adaptation(
            KnowledgeItem(name="x", knowledge_type=KnowledgeType.SKILL, source_domain_id="s"),
            {}, 0.65,
        ) == AdaptationType.RENAME

    def test_adaptation_type_low_score(self) -> None:
        assert CompatibilityAssessor._determine_adaptation(
            KnowledgeItem(name="x", knowledge_type=KnowledgeType.SKILL, source_domain_id="s"),
            {}, 0.35,
        ) == AdaptationType.RESTRUCTURE

    def test_adaptation_type_very_low_score(self) -> None:
        assert CompatibilityAssessor._determine_adaptation(
            KnowledgeItem(name="x", knowledge_type=KnowledgeType.SKILL, source_domain_id="s"),
            {}, 0.15,
        ) == AdaptationType.CUSTOM

    def test_assess_package(self) -> None:
        assessor = CompatibilityAssessor()
        items = [
            KnowledgeItem(name="S1", knowledge_type=KnowledgeType.SKILL, source_domain_id="s"),
            KnowledgeItem(name="S2", knowledge_type=KnowledgeType.BEST_PRACTICE, source_domain_id="s"),
        ]
        package = KnowledgePackage(
            name="Test Package",
            source_domain_id="s",
            target_domain_id="t",
            items=items,
        )
        assessed = assessor.assess_package(package, FINANCE_METADATA)
        assert assessed.overall_compatibility > 0.0
        assert len(assessed.items) == 2

    def test_assess_package_empty_items(self) -> None:
        assessor = CompatibilityAssessor()
        package = KnowledgePackage(
            name="Empty Package",
            source_domain_id="s",
            target_domain_id="t",
            items=[],
        )
        assessed = assessor.assess_package(package, {})
        assert assessed.overall_compatibility == 0.0

    def test_assess_package_complexity_high(self) -> None:
        assessor = CompatibilityAssessor()
        items = [
            KnowledgeItem(
                name="Low Score Item",
                knowledge_type=KnowledgeType.CONFIG,
                source_domain_id="s",
                success_rate=0.1,
            ),
        ]
        package = KnowledgePackage(
            name="Pkg",
            source_domain_id="s",
            target_domain_id="t",
            items=items,
        )
        assessed = assessor.assess_package(package, FINANCE_METADATA)
        # Should be high complexity since restructure/custom needed
        assert assessed.adaptation_complexity in ("high", "medium")

    def test_adaptation_notes_generation(self) -> None:
        notes = CompatibilityAssessor._generate_adaptation_notes(
            KnowledgeItem(name="x", knowledge_type=KnowledgeType.SKILL, source_domain_id="s"),
            AdaptationType.NONE,
            {"name": "Finance Ops"},
        )
        assert "Finance Ops" in notes

    def test_adaptation_notes_non_string_name(self) -> None:
        notes = CompatibilityAssessor._generate_adaptation_notes(
            KnowledgeItem(name="x", knowledge_type=KnowledgeType.SKILL, source_domain_id="s"),
            AdaptationType.RENAME,
            {"name": 42},
        )
        assert "target domain" in notes


# ===========================================================================
# TransferStore tests
# ===========================================================================


class TestTransferStore:
    """Test in-memory transfer store operations."""

    def test_add_and_get_transfer(self) -> None:
        store = TransferStore()
        record = TransferRecord(
            source_domain_id="s",
            target_domain_id="t",
        )
        store.add_transfer(record)
        assert store.get_transfer(record.id) is not None

    def test_get_nonexistent_transfer(self) -> None:
        store = TransferStore()
        from uuid import uuid4
        assert store.get_transfer(uuid4()) is None

    def test_update_transfer(self) -> None:
        store = TransferStore()
        record = TransferRecord(
            source_domain_id="s",
            target_domain_id="t",
            status=TransferStatus.DRAFT,
        )
        store.add_transfer(record)
        updated = record.model_copy(update={"status": TransferStatus.PROPOSED})
        store.update_transfer(updated)
        fetched = store.get_transfer(record.id)
        assert fetched is not None
        assert fetched.status == TransferStatus.PROPOSED

    def test_update_nonexistent_transfer_raises(self) -> None:
        store = TransferStore()
        record = TransferRecord(source_domain_id="s", target_domain_id="t")
        with pytest.raises(TransferNotFoundError):
            store.update_transfer(record)

    def test_list_transfers(self) -> None:
        store = TransferStore()
        store.add_transfer(TransferRecord(source_domain_id="s1", target_domain_id="t1"))
        store.add_transfer(TransferRecord(source_domain_id="s2", target_domain_id="t2"))
        assert len(store.list_transfers()) == 2

    def test_list_transfers_by_status(self) -> None:
        store = TransferStore()
        store.add_transfer(
            TransferRecord(source_domain_id="s1", target_domain_id="t1", status=TransferStatus.COMPLETED)
        )
        store.add_transfer(
            TransferRecord(source_domain_id="s2", target_domain_id="t2", status=TransferStatus.DRAFT)
        )
        assert len(store.list_transfers_by_status(TransferStatus.COMPLETED)) == 1

    def test_add_and_get_package(self) -> None:
        store = TransferStore()
        pkg = KnowledgePackage(name="Pkg", source_domain_id="s", target_domain_id="t")
        store.add_package(pkg)
        assert store.get_package(pkg.id) is not None

    def test_list_packages(self) -> None:
        store = TransferStore()
        store.add_package(KnowledgePackage(name="P1", source_domain_id="s", target_domain_id="t"))
        store.add_package(KnowledgePackage(name="P2", source_domain_id="s", target_domain_id="t"))
        assert len(store.list_packages()) == 2

    def test_add_and_get_knowledge_item(self) -> None:
        store = TransferStore()
        item = KnowledgeItem(name="S1", knowledge_type=KnowledgeType.SKILL, source_domain_id="s")
        store.add_knowledge_item(item)
        assert store.get_knowledge_item(item.id) is not None

    def test_list_knowledge_items_filtered(self) -> None:
        store = TransferStore()
        store.add_knowledge_item(
            KnowledgeItem(name="S1", knowledge_type=KnowledgeType.SKILL, source_domain_id="legal")
        )
        store.add_knowledge_item(
            KnowledgeItem(name="S2", knowledge_type=KnowledgeType.PATTERN, source_domain_id="finance")
        )
        legal = store.list_knowledge_items(source_domain_id="legal")
        assert len(legal) == 1
        skills = store.list_knowledge_items(knowledge_type=KnowledgeType.SKILL)
        assert len(skills) == 1


# ===========================================================================
# State transition validation tests
# ===========================================================================


class TestTransferTransitions:
    """Test transfer state machine transitions."""

    def test_draft_to_proposed(self) -> None:
        _validate_transfer_transition(TransferStatus.DRAFT, TransferStatus.PROPOSED)

    def test_draft_to_rejected(self) -> None:
        _validate_transfer_transition(TransferStatus.DRAFT, TransferStatus.REJECTED)

    def test_proposed_to_approved(self) -> None:
        _validate_transfer_transition(TransferStatus.PROPOSED, TransferStatus.APPROVED)

    def test_proposed_to_rejected(self) -> None:
        _validate_transfer_transition(TransferStatus.PROPOSED, TransferStatus.REJECTED)

    def test_approved_to_transferring(self) -> None:
        _validate_transfer_transition(TransferStatus.APPROVED, TransferStatus.TRANSFERRING)

    def test_transferring_to_completed(self) -> None:
        _validate_transfer_transition(TransferStatus.TRANSFERRING, TransferStatus.COMPLETED)

    def test_transferring_to_failed(self) -> None:
        _validate_transfer_transition(TransferStatus.TRANSFERRING, TransferStatus.FAILED)

    def test_failed_to_rolled_back(self) -> None:
        _validate_transfer_transition(TransferStatus.FAILED, TransferStatus.ROLLED_BACK)

    def test_failed_to_draft(self) -> None:
        _validate_transfer_transition(TransferStatus.FAILED, TransferStatus.DRAFT)

    def test_rolled_back_to_draft(self) -> None:
        _validate_transfer_transition(TransferStatus.ROLLED_BACK, TransferStatus.DRAFT)

    def test_invalid_transition_raises(self) -> None:
        with pytest.raises(TransferTransitionError):
            _validate_transfer_transition(TransferStatus.DRAFT, TransferStatus.COMPLETED)

    def test_completed_to_rolled_back(self) -> None:
        _validate_transfer_transition(TransferStatus.COMPLETED, TransferStatus.ROLLED_BACK)

    def test_completed_to_other_raises(self) -> None:
        with pytest.raises(TransferTransitionError):
            _validate_transfer_transition(TransferStatus.COMPLETED, TransferStatus.DRAFT)

    def test_rejected_to_anything_raises(self) -> None:
        with pytest.raises(TransferTransitionError):
            _validate_transfer_transition(TransferStatus.REJECTED, TransferStatus.PROPOSED)

    def test_transferring_to_draft_raises(self) -> None:
        with pytest.raises(TransferTransitionError):
            _validate_transfer_transition(TransferStatus.TRANSFERRING, TransferStatus.DRAFT)


# ===========================================================================
# KnowledgeTransferEngine integration tests
# ===========================================================================


class TestKnowledgeTransferEngineExtract:
    """Test knowledge extraction through the engine."""

    @pytest.mark.asyncio
    async def test_extract_knowledge(self) -> None:
        engine = _make_engine()
        items = await engine.extract_knowledge(
            domain_id="legal",
            domain_metadata=LEGAL_METADATA,
            knowledge_types=[KnowledgeType.SKILL],
        )
        assert len(items) == 3
        assert all(i.knowledge_type == KnowledgeType.SKILL for i in items)

    @pytest.mark.asyncio
    async def test_extract_logs_to_tape(self) -> None:
        tape = _make_tape_service()
        engine = _make_engine(tape)
        await engine.extract_knowledge(
            domain_id="legal",
            domain_metadata=LEGAL_METADATA,
        )
        entries = await tape.get_entries()
        assert any(e.event_type == "knowledge.extracted" for e in entries)


class TestKnowledgeTransferEngineAssess:
    """Test compatibility assessment through the engine."""

    @pytest.mark.asyncio
    async def test_assess_compatibility(self) -> None:
        engine = _make_engine()
        items = [
            KnowledgeItem(name="S1", knowledge_type=KnowledgeType.SKILL, source_domain_id="s"),
        ]
        assessed = await engine.assess_compatibility(items, FINANCE_METADATA)
        assert len(assessed) == 1
        assert assessed[0].compatibility_score > 0.0

    @pytest.mark.asyncio
    async def test_assess_logs_to_tape(self) -> None:
        tape = _make_tape_service()
        engine = _make_engine(tape)
        items = [
            KnowledgeItem(name="S1", knowledge_type=KnowledgeType.SKILL, source_domain_id="s"),
        ]
        await engine.assess_compatibility(items, {})
        entries = await tape.get_entries()
        assert any(e.event_type == "knowledge.assessed" for e in entries)


class TestKnowledgeTransferEnginePackage:
    """Test knowledge package creation."""

    @pytest.mark.asyncio
    async def test_create_package(self) -> None:
        engine = _make_engine()
        package = await engine.create_package(
            name="Legal to Finance",
            source_domain_id="legal",
            target_domain_id="finance",
            source_metadata=LEGAL_METADATA,
            target_metadata=FINANCE_METADATA,
            knowledge_types=[KnowledgeType.SKILL],
        )
        assert package.source_domain_id == "legal"
        assert package.target_domain_id == "finance"
        assert len(package.items) > 0
        assert package.overall_compatibility > 0.0

    @pytest.mark.asyncio
    async def test_create_package_filters_incompatible(self) -> None:
        engine = _make_engine()
        # Create an item that will be incompatible (duplicate name in target)
        package = await engine.create_package(
            name="Test",
            source_domain_id="finance",
            target_domain_id="finance",
            source_metadata=FINANCE_METADATA,
            target_metadata=FINANCE_METADATA,
        )
        # Items with duplicate names should have been filtered or have low scores
        for item in package.items:
            assert item.compatibility_level != CompatibilityLevel.INCOMPATIBLE

    @pytest.mark.asyncio
    async def test_create_package_logs_to_tape(self) -> None:
        tape = _make_tape_service()
        engine = _make_engine(tape)
        await engine.create_package(
            name="Pkg",
            source_domain_id="legal",
            target_domain_id="finance",
            source_metadata=LEGAL_METADATA,
            target_metadata=FINANCE_METADATA,
        )
        entries = await tape.get_entries()
        assert any(e.event_type == "knowledge.package_created" for e in entries)


class TestKnowledgeTransferEngineTransfer:
    """Test full knowledge transfer execution."""

    @pytest.mark.asyncio
    async def test_transfer_knowledge_success(self) -> None:
        engine = _make_engine()
        record = await engine.transfer_knowledge(
            source_domain_id="legal",
            target_domain_id="finance",
            source_metadata=LEGAL_METADATA,
            target_metadata=FINANCE_METADATA,
            knowledge_types=[KnowledgeType.SKILL, KnowledgeType.PATTERN],
        )
        assert record.status == TransferStatus.COMPLETED
        assert record.result is not None
        assert record.result.items_transferred > 0

    @pytest.mark.asyncio
    async def test_transfer_records_result_details(self) -> None:
        engine = _make_engine()
        record = await engine.transfer_knowledge(
            source_domain_id="legal",
            target_domain_id="finance",
            source_metadata=LEGAL_METADATA,
            target_metadata=FINANCE_METADATA,
        )
        assert record.result is not None
        r = record.result
        assert r.source_domain_id == "legal"
        assert r.target_domain_id == "finance"
        assert r.items_transferred + r.items_skipped == r.total_items
        assert r.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_transfer_logs_to_tape(self) -> None:
        tape = _make_tape_service()
        engine = _make_engine(tape)
        await engine.transfer_knowledge(
            source_domain_id="legal",
            target_domain_id="finance",
            source_metadata=LEGAL_METADATA,
            target_metadata=FINANCE_METADATA,
        )
        entries = await tape.get_entries()
        assert any(e.event_type == "knowledge.transfer_completed" for e in entries)

    @pytest.mark.asyncio
    async def test_transfer_item_transferred_tape_events(self) -> None:
        tape = _make_tape_service()
        engine = _make_engine(tape)
        await engine.transfer_knowledge(
            source_domain_id="legal",
            target_domain_id="finance",
            source_metadata=LEGAL_METADATA,
            target_metadata=FINANCE_METADATA,
            knowledge_types=[KnowledgeType.SKILL],
        )
        entries = await tape.get_entries()
        item_events = [e for e in entries if e.event_type == "knowledge.item_transferred"]
        assert len(item_events) > 0

    @pytest.mark.asyncio
    async def test_transfer_stores_record(self) -> None:
        engine = _make_engine()
        record = await engine.transfer_knowledge(
            source_domain_id="legal",
            target_domain_id="finance",
            source_metadata=LEGAL_METADATA,
            target_metadata=FINANCE_METADATA,
        )
        # Should be retrievable
        fetched = await engine.get_transfer(record.id)
        assert fetched.id == record.id

    @pytest.mark.asyncio
    async def test_transfer_with_empty_source(self) -> None:
        engine = _make_engine()
        record = await engine.transfer_knowledge(
            source_domain_id="empty",
            target_domain_id="finance",
            source_metadata={},
            target_metadata=FINANCE_METADATA,
        )
        assert record.status == TransferStatus.COMPLETED
        assert record.result is not None
        assert record.result.items_transferred <= 1  # may include config item

    @pytest.mark.asyncio
    async def test_transfer_adapted_items_counted(self) -> None:
        engine = _make_engine()
        record = await engine.transfer_knowledge(
            source_domain_id="legal",
            target_domain_id="finance",
            source_metadata=LEGAL_METADATA,
            target_metadata=FINANCE_METADATA,
        )
        assert record.result is not None
        # Some items should need adaptation
        assert record.result.items_transferred >= record.result.items_adapted


class TestKnowledgeTransferEngineRollback:
    """Test transfer rollback."""

    @pytest.mark.asyncio
    async def test_rollback_completed_transfer(self) -> None:
        engine = _make_engine()
        record = await engine.transfer_knowledge(
            source_domain_id="legal",
            target_domain_id="finance",
            source_metadata=LEGAL_METADATA,
            target_metadata=FINANCE_METADATA,
        )
        assert record.status == TransferStatus.COMPLETED
        rolled_back = await engine.rollback_transfer(record.id)
        assert rolled_back.status == TransferStatus.ROLLED_BACK

    @pytest.mark.asyncio
    async def test_rollback_failed_transfer(self) -> None:
        engine = _make_engine()
        record = await engine.transfer_knowledge(
            source_domain_id="legal",
            target_domain_id="finance",
            source_metadata=LEGAL_METADATA,
            target_metadata=FINANCE_METADATA,
        )
        # Manually set to failed for testing
        store_record = engine._store.get_transfer(record.id)
        assert store_record is not None
        store_record = store_record.model_copy(update={"status": TransferStatus.FAILED})
        engine._store.update_transfer(store_record)

        rolled_back = await engine.rollback_transfer(record.id)
        assert rolled_back.status == TransferStatus.ROLLED_BACK

    @pytest.mark.asyncio
    async def test_rollback_nonexistent_raises(self) -> None:
        engine = _make_engine()
        with pytest.raises(TransferNotFoundError):
            await engine.rollback_transfer(UUID(int=0))

    @pytest.mark.asyncio
    async def test_rollback_draft_raises(self) -> None:
        engine = _make_engine()
        record = TransferRecord(
            source_domain_id="s",
            target_domain_id="t",
            status=TransferStatus.DRAFT,
        )
        engine._store.add_transfer(record)
        with pytest.raises(TransferTransitionError):
            await engine.rollback_transfer(record.id)

    @pytest.mark.asyncio
    async def test_rollback_logs_to_tape(self) -> None:
        tape = _make_tape_service()
        engine = _make_engine(tape)
        record = await engine.transfer_knowledge(
            source_domain_id="legal",
            target_domain_id="finance",
            source_metadata=LEGAL_METADATA,
            target_metadata=FINANCE_METADATA,
        )
        await engine.rollback_transfer(record.id)
        entries = await tape.get_entries()
        assert any(e.event_type == "knowledge.transfer_rolled_back" for e in entries)


class TestKnowledgeTransferEngineQueries:
    """Test query methods."""

    @pytest.mark.asyncio
    async def test_get_transfer(self) -> None:
        engine = _make_engine()
        record = await engine.transfer_knowledge(
            source_domain_id="legal",
            target_domain_id="finance",
            source_metadata=LEGAL_METADATA,
            target_metadata=FINANCE_METADATA,
        )
        fetched = await engine.get_transfer(record.id)
        assert fetched.id == record.id

    @pytest.mark.asyncio
    async def test_get_transfer_not_found(self) -> None:
        engine = _make_engine()
        with pytest.raises(TransferNotFoundError):
            await engine.get_transfer(UUID(int=0))

    @pytest.mark.asyncio
    async def test_list_transfers(self) -> None:
        engine = _make_engine()
        await engine.transfer_knowledge(
            source_domain_id="legal",
            target_domain_id="finance",
            source_metadata=LEGAL_METADATA,
            target_metadata=FINANCE_METADATA,
        )
        transfers = await engine.list_transfers()
        assert len(transfers) >= 1

    @pytest.mark.asyncio
    async def test_list_transfers_by_status(self) -> None:
        engine = _make_engine()
        await engine.transfer_knowledge(
            source_domain_id="legal",
            target_domain_id="finance",
            source_metadata=LEGAL_METADATA,
            target_metadata=FINANCE_METADATA,
        )
        completed = await engine.list_transfers(status=TransferStatus.COMPLETED)
        assert len(completed) >= 1

    @pytest.mark.asyncio
    async def test_get_package(self) -> None:
        engine = _make_engine()
        pkg = await engine.create_package(
            name="Test",
            source_domain_id="legal",
            target_domain_id="finance",
            source_metadata=LEGAL_METADATA,
            target_metadata=FINANCE_METADATA,
        )
        fetched = await engine.get_package(pkg.id)
        assert fetched.id == pkg.id

    @pytest.mark.asyncio
    async def test_get_package_not_found(self) -> None:
        engine = _make_engine()
        with pytest.raises(KnowledgeTransferError):
            await engine.get_package(UUID(int=0))

    @pytest.mark.asyncio
    async def test_list_packages(self) -> None:
        engine = _make_engine()
        await engine.create_package(
            name="P1",
            source_domain_id="legal",
            target_domain_id="finance",
            source_metadata=LEGAL_METADATA,
            target_metadata=FINANCE_METADATA,
        )
        packages = await engine.list_packages()
        assert len(packages) >= 1

    @pytest.mark.asyncio
    async def test_list_knowledge_items(self) -> None:
        engine = _make_engine()
        await engine.extract_knowledge(
            domain_id="legal",
            domain_metadata=LEGAL_METADATA,
        )
        items = await engine.list_knowledge_items()
        assert len(items) > 0

    @pytest.mark.asyncio
    async def test_list_knowledge_items_filtered(self) -> None:
        engine = _make_engine()
        await engine.extract_knowledge(
            domain_id="legal",
            domain_metadata=LEGAL_METADATA,
        )
        skills = await engine.list_knowledge_items(knowledge_type=KnowledgeType.SKILL)
        assert all(i.knowledge_type == KnowledgeType.SKILL for i in skills)


class TestKnowledgeTransferEngineRecommendations:
    """Test transfer recommendations."""

    @pytest.mark.asyncio
    async def test_recommend_transfers(self) -> None:
        engine = _make_engine()
        all_metadata: dict[str, dict[str, object]] = {
            "legal": LEGAL_METADATA,
            "finance": FINANCE_METADATA,
            "research": RESEARCH_METADATA,
        }
        recommendations = await engine.recommend_transfers(
            domain_id="finance",
            all_domain_metadata=all_metadata,
        )
        assert len(recommendations) >= 1
        # Each recommendation should have source_domain_id and compatible_items
        for rec in recommendations:
            assert "source_domain_id" in rec
            assert "compatible_items" in rec

    @pytest.mark.asyncio
    async def test_recommend_transfers_sorted_by_compatibility(self) -> None:
        engine = _make_engine()
        all_metadata: dict[str, dict[str, object]] = {
            "legal": LEGAL_METADATA,
            "research": RESEARCH_METADATA,
        }
        recommendations = await engine.recommend_transfers(
            domain_id="finance",
            all_domain_metadata=all_metadata,
        )
        if len(recommendations) > 1:
            scores = [
                float(str(r.get("average_compatibility", "0")))
                for r in recommendations
            ]
            assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_recommend_transfers_excludes_self(self) -> None:
        engine = _make_engine()
        all_metadata: dict[str, dict[str, object]] = {
            "finance": FINANCE_METADATA,
        }
        recommendations = await engine.recommend_transfers(
            domain_id="finance",
            all_domain_metadata=all_metadata,
        )
        # Should not recommend from self
        assert len(recommendations) == 0

    @pytest.mark.asyncio
    async def test_recommend_transfers_empty_target(self) -> None:
        engine = _make_engine()
        all_metadata: dict[str, dict[str, object]] = {
            "legal": LEGAL_METADATA,
        }
        recommendations = await engine.recommend_transfers(
            domain_id="nonexistent",
            all_domain_metadata=all_metadata,
        )
        # Target domain not in metadata
        assert len(recommendations) == 0

    @pytest.mark.asyncio
    async def test_recommend_transfers_logs_to_tape(self) -> None:
        tape = _make_tape_service()
        engine = _make_engine(tape)
        all_metadata: dict[str, dict[str, object]] = {
            "legal": LEGAL_METADATA,
            "finance": FINANCE_METADATA,
        }
        await engine.recommend_transfers(
            domain_id="finance",
            all_domain_metadata=all_metadata,
        )
        entries = await tape.get_entries()
        assert any(e.event_type == "knowledge.recommendations_generated" for e in entries)


# ===========================================================================
# KnowledgeItem model tests
# ===========================================================================


class TestKnowledgeItemModel:
    """Test KnowledgeItem Pydantic model."""

    def test_default_fields(self) -> None:
        item = KnowledgeItem(
            name="Test Skill",
            knowledge_type=KnowledgeType.SKILL,
            source_domain_id="legal",
        )
        assert item.version == "1.0.0"
        assert item.compatibility_score == 0.0
        assert item.transfer_count == 0
        assert item.success_rate == 0.0
        assert isinstance(item.id, UUID)
        assert isinstance(item.created_at, datetime)

    def test_custom_fields(self) -> None:
        item = KnowledgeItem(
            name="Test",
            knowledge_type=KnowledgeType.PATTERN,
            source_domain_id="legal",
            compatibility_score=0.85,
            compatibility_level=CompatibilityLevel.HIGH,
            adaptation_needed=AdaptationType.NONE,
            description="A test pattern",
            version="2.0.0",
            transfer_count=5,
            success_rate=0.9,
        )
        assert item.compatibility_score == 0.85
        assert item.transfer_count == 5

    def test_compatibility_score_bounds(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            KnowledgeItem(
                name="Bad",
                knowledge_type=KnowledgeType.SKILL,
                source_domain_id="s",
                compatibility_score=1.5,
            )
        with pytest.raises(ValidationError):
            KnowledgeItem(
                name="Bad",
                knowledge_type=KnowledgeType.SKILL,
                source_domain_id="s",
                compatibility_score=-0.1,
            )


class TestKnowledgePackageModel:
    """Test KnowledgePackage model."""

    def test_default_fields(self) -> None:
        pkg = KnowledgePackage(
            name="Test",
            source_domain_id="s",
            target_domain_id="t",
        )
        assert pkg.overall_compatibility == 0.0
        assert pkg.adaptation_complexity == "low"
        assert len(pkg.items) == 0


class TestTransferRecordModel:
    """Test TransferRecord model."""

    def test_default_fields(self) -> None:
        record = TransferRecord(
            source_domain_id="s",
            target_domain_id="t",
        )
        assert record.status == TransferStatus.DRAFT
        assert record.created_by == "prime"
        assert record.result is None
        assert record.proposal_id is None
        assert record.completed_at is None

    def test_custom_fields(self) -> None:
        record = TransferRecord(
            source_domain_id="s",
            target_domain_id="t",
            status=TransferStatus.COMPLETED,
            created_by="user",
            knowledge_types=[KnowledgeType.SKILL, KnowledgeType.PATTERN],
        )
        assert record.status == TransferStatus.COMPLETED
        assert record.created_by == "user"
        assert len(record.knowledge_types) == 2


class TestTransferResultModel:
    """Test TransferResult model."""

    def test_result_fields(self) -> None:
        result = TransferResult(
            transfer_id=UUID(int=1),
            status=TransferStatus.COMPLETED,
            source_domain_id="s",
            target_domain_id="t",
            items_transferred=5,
            items_adapted=2,
            items_skipped=1,
            total_items=6,
            compatibility_score=0.75,
        )
        assert result.items_transferred == 5
        assert result.duration_seconds == 0.0
        assert len(result.errors) == 0


# ===========================================================================
# Enum tests
# ===========================================================================


class TestEnums:
    """Test StrEnum values."""

    def test_knowledge_type_values(self) -> None:
        assert KnowledgeType.SKILL.value == "skill"
        assert KnowledgeType.PATTERN.value == "pattern"
        assert KnowledgeType.BEST_PRACTICE.value == "best_practice"
        assert KnowledgeType.CONFIG.value == "config"
        assert KnowledgeType.WORKFLOW.value == "workflow"
        assert KnowledgeType.AGENT_ROLE.value == "agent_role"

    def test_transfer_status_values(self) -> None:
        assert TransferStatus.DRAFT.value == "draft"
        assert TransferStatus.COMPLETED.value == "completed"
        assert TransferStatus.ROLLED_BACK.value == "rolled_back"

    def test_compatibility_level_values(self) -> None:
        assert CompatibilityLevel.HIGH.value == "high"
        assert CompatibilityLevel.INCOMPATIBLE.value == "incompatible"

    def test_adaptation_type_values(self) -> None:
        assert AdaptationType.NONE.value == "none"
        assert AdaptationType.RESTRUCTURE.value == "restructure"
        assert AdaptationType.CUSTOM.value == "custom"


# ===========================================================================
# Exception hierarchy tests
# ===========================================================================


class TestExceptions:
    """Test exception hierarchy."""

    def test_base_exception(self) -> None:
        with pytest.raises(KnowledgeTransferError):
            raise KnowledgeTransferError("test")

    def test_domain_not_found(self) -> None:
        with pytest.raises(KnowledgeTransferError):
            raise DomainNotFoundError("test")

    def test_transfer_not_found(self) -> None:
        with pytest.raises(KnowledgeTransferError):
            raise TransferNotFoundError("test")

    def test_transition_error(self) -> None:
        with pytest.raises(KnowledgeTransferError):
            raise TransferTransitionError("test")

    def test_incompatible_knowledge(self) -> None:
        with pytest.raises(KnowledgeTransferError):
            raise IncompatibleKnowledgeError("test")

    def test_validation_error(self) -> None:
        with pytest.raises(KnowledgeTransferError):
            raise TransferValidationError("test")
