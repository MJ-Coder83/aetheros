"""Shared FastAPI dependencies for the InkosAI API."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from packages.aethergit.advanced import AdvancedAetherGit
from packages.auth import AuthService
from packages.canvas.canvas_v5 import CanvasV5Engine
from packages.canvas.core import CanvasService
from packages.domain.creation import OneClickDomainCreationEngine
from packages.folder_tree import FolderTreeService
from packages.marketplace.service import MarketplaceService
from packages.plugin.core import PluginSDK
from packages.prime.debate import DebateArena
from packages.prime.domain_creation import DomainCreationEngine
from packages.prime.explainability import ExplainabilityEngine
from packages.prime.introspection import PrimeIntrospector
from packages.prime.knowledge_transfer import KnowledgeTransferEngine
from packages.prime.llm_planning import LLMPlanner
from packages.prime.planning import PlanningEngine
from packages.prime.profile import (
    IntelligenceProfileEngine,
    ProfileStorage,
)
from packages.prime.proposals import ProposalEngine
from packages.tape.nlq import SemanticTapeQueryEngine
from packages.tape.repository import TapeRepository
from packages.tape.service import TapeService
from services.api.database import async_session, get_db

# ---------------------------------------------------------------------------
# Tape service (singleton backed by PostgreSQL)
# ---------------------------------------------------------------------------

_tape_service_singleton: TapeService | None = None


def get_tape_service() -> TapeService:
    """Return the singleton TapeService backed by PostgreSQL."""
    global _tape_service_singleton
    if _tape_service_singleton is None:
        repo = TapeRepository(async_session)
        _tape_service_singleton = TapeService(repo)
    return _tape_service_singleton


TapeServiceDep = Annotated[TapeService, Depends(get_tape_service)]

# ---------------------------------------------------------------------------
# Stateful service singletons (backed by in-memory stores for now)
# All use the shared TapeService singleton for audit logging.
# ---------------------------------------------------------------------------

_introspector_singleton: PrimeIntrospector | None = None
_proposal_engine_singleton: ProposalEngine | None = None


def get_introspector() -> PrimeIntrospector:
    """Return the singleton PrimeIntrospector."""
    global _introspector_singleton
    if _introspector_singleton is None:
        _introspector_singleton = PrimeIntrospector(tape_service=get_tape_service())
    return _introspector_singleton


def get_proposal_engine() -> ProposalEngine:
    """Return the singleton ProposalEngine."""
    global _proposal_engine_singleton
    if _proposal_engine_singleton is None:
        _proposal_engine_singleton = ProposalEngine(
            tape_service=get_tape_service(),
            introspector=get_introspector(),
            profile_engine=get_intelligence_profile_service(),
        )
    return _proposal_engine_singleton


def get_aethergit_service() -> AdvancedAetherGit:
    """Return the singleton AdvancedAetherGit."""
    # Note: CommitStore is currently in-memory. Persistent backing can be
    # swapped in by passing a PersistentCommitStore(session) here.
    return AdvancedAetherGit(tape_service=get_tape_service())


def get_debate_service() -> DebateArena:
    """Return the singleton DebateArena."""
    return DebateArena(
        tape_service=get_tape_service(),
        profile_engine=get_intelligence_profile_service(),
    )


def get_explainability_service() -> ExplainabilityEngine:
    """Return the singleton ExplainabilityEngine."""
    return ExplainabilityEngine(
        tape_service=get_tape_service(),
        profile_engine=get_intelligence_profile_service(),
    )


def get_domain_creation_service() -> DomainCreationEngine:
    """Return the singleton DomainCreationEngine."""
    return DomainCreationEngine(
        tape_service=get_tape_service(),
        introspector=get_introspector(),
        proposal_engine=get_proposal_engine(),
        folder_tree_service=get_folder_tree_service(),
        profile_engine=get_intelligence_profile_service(),
    )


def get_one_click_domain_creation_service() -> OneClickDomainCreationEngine:
    """Return the singleton OneClickDomainCreationEngine."""
    return OneClickDomainCreationEngine(
        tape_service=get_tape_service(),
        introspector=get_introspector(),
        proposal_engine=get_proposal_engine(),
        profile_engine=get_intelligence_profile_service(),
    )


def get_planning_service() -> PlanningEngine:
    """Return the singleton PlanningEngine."""
    return PlanningEngine(
        tape_service=get_tape_service(),
        introspector=get_introspector(),
        proposal_engine=get_proposal_engine(),
        profile_engine=get_intelligence_profile_service(),
    )


def get_knowledge_transfer_service() -> KnowledgeTransferEngine:
    """Return the singleton KnowledgeTransferEngine."""
    return KnowledgeTransferEngine(
        tape_service=get_tape_service(),
        profile_engine=get_intelligence_profile_service(),
    )


_profile_storage_singleton: ProfileStorage | None = None

def get_profile_storage() -> ProfileStorage:
    """Return the singleton ProfileStorage."""
    global _profile_storage_singleton
    if _profile_storage_singleton is None:
        _profile_storage_singleton = ProfileStorage(tape_service=get_tape_service())
    return _profile_storage_singleton

ProfileStorageDep = Annotated[ProfileStorage, Depends(get_profile_storage)]


def get_intelligence_profile_service() -> IntelligenceProfileEngine:
    """Return the singleton IntelligenceProfileEngine."""
    return IntelligenceProfileEngine(
        tape_service=get_tape_service(),
        store=get_profile_storage(),
    )


def get_llm_planner_service() -> LLMPlanner:
    """Return the singleton LLMPlanner."""
    return LLMPlanner(tape_service=get_tape_service())


def get_auth_service() -> AuthService:
    """Return the singleton AuthService."""
    return AuthService(tape_service=get_tape_service())


def get_nlq_service() -> SemanticTapeQueryEngine:
    """Return the singleton SemanticTapeQueryEngine."""
    return SemanticTapeQueryEngine(tape_service=get_tape_service())


_marketplace_service_singleton: MarketplaceService | None = None


def get_marketplace_service() -> MarketplaceService:
    """Return the singleton MarketplaceService."""
    global _marketplace_service_singleton
    if _marketplace_service_singleton is None:
        _marketplace_service_singleton = MarketplaceService(tape_service=get_tape_service())
    return _marketplace_service_singleton


MarketplaceServiceDep = Annotated[MarketplaceService, Depends(get_marketplace_service)]

_plugin_sdk_singleton: PluginSDK | None = None


def get_plugin_sdk() -> PluginSDK:
    """Return the singleton PluginSDK."""
    global _plugin_sdk_singleton
    if _plugin_sdk_singleton is None:
        from packages.plugin.models import PluginVersion

        _plugin_sdk_singleton = PluginSDK(
            tape_service=get_tape_service(),
            platform_version=PluginVersion(major=0, minor=1, patch=0),
        )
    return _plugin_sdk_singleton


PluginSDKDep = Annotated[PluginSDK, Depends(get_plugin_sdk)]


def get_introspector_for_analysis() -> PrimeIntrospector:
    """Return the singleton PrimeIntrospector for historical analysis."""
    return get_introspector()


_folder_tree_service_singleton: FolderTreeService | None = None


def get_folder_tree_service() -> FolderTreeService:
    """Return the singleton FolderTreeService (in-memory store)."""
    global _folder_tree_service_singleton
    if _folder_tree_service_singleton is None:
        _folder_tree_service_singleton = FolderTreeService(tape_service=get_tape_service())
    return _folder_tree_service_singleton


def get_canvas_service() -> CanvasService:
    """Return the singleton CanvasService."""
    # CanvasService uses in-memory store by default
    # Pass folder_tree_service=get_folder_tree_service() for two-way sync
    return CanvasService(
        tape_service=get_tape_service(),
        folder_tree_service=get_folder_tree_service(),
    )

# Type aliases for FastAPI Depends
# Canvas V5 singleton
_canvas_v5_singleton: CanvasV5Engine | None = None


def get_canvas_v5_service() -> CanvasV5Engine:
    """Return the singleton CanvasV5Engine."""
    global _canvas_v5_singleton
    if _canvas_v5_singleton is None:
        _canvas_v5_singleton = CanvasV5Engine(
            tape_service=get_tape_service(),
            canvas_service=get_canvas_service(),
            proposal_engine=None,
        )
    return _canvas_v5_singleton


CanvasServiceDep = Annotated[CanvasService, Depends(get_canvas_service)]
CanvasV5ServiceDep = Annotated[CanvasV5Engine, Depends(get_canvas_v5_service)]
AetherGitServiceDep = Annotated[AdvancedAetherGit, Depends(get_aethergit_service)]
DebateServiceDep = Annotated[DebateArena, Depends(get_debate_service)]
ExplainabilityServiceDep = Annotated[ExplainabilityEngine, Depends(get_explainability_service)]
DomainCreationServiceDep = Annotated[DomainCreationEngine, Depends(get_domain_creation_service)]
OneClickDomainCreationServiceDep = Annotated[
    OneClickDomainCreationEngine, Depends(get_one_click_domain_creation_service),
]
PlanningServiceDep = Annotated[PlanningEngine, Depends(get_planning_service)]
KnowledgeTransferServiceDep = Annotated[KnowledgeTransferEngine, Depends(get_knowledge_transfer_service)]
IntelligenceProfileServiceDep = Annotated[IntelligenceProfileEngine, Depends(get_intelligence_profile_service)]
LLMPlannerServiceDep = Annotated[LLMPlanner, Depends(get_llm_planner_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
NLQServiceDep = Annotated[SemanticTapeQueryEngine, Depends(get_nlq_service)]
IntrospectorForAnalysisDep = Annotated[PrimeIntrospector, Depends(get_introspector_for_analysis)]
FolderTreeServiceDep = Annotated[FolderTreeService, Depends(get_folder_tree_service)]
DbSessionDep = Annotated[AsyncSession, Depends(get_db)]
