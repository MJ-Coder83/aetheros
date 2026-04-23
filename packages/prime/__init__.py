"""InkosAI Prime — The self-aware meta-agent package."""

from packages.prime.introspection import PrimeIntrospector, SystemSnapshot
from packages.prime.proposals import (
    ModificationType,
    Proposal,
    ProposalEngine,
    ProposalError,
    ProposalNotFoundError,
    ProposalStatus,
    ProposalStore,
    ProposalSummary,
    ProposalTransitionError,
    RiskLevel,
)
from packages.prime.skill_evolution import (
    EvolutionNotApprovedError,
    EvolutionProposalNotFoundError,
    EvolutionResult,
    EvolutionType,
    RollbackError,
    SkillAnalysis,
    SkillEvolutionEngine,
    SkillEvolutionError,
    SkillEvolutionProposal,
    SkillEvolutionStore,
)

__all__ = [
    "EvolutionNotApprovedError",
    "EvolutionProposalNotFoundError",
    "EvolutionResult",
    "EvolutionType",
    "ModificationType",
    "PrimeIntrospector",
    "Proposal",
    "ProposalEngine",
    "ProposalError",
    "ProposalNotFoundError",
    "ProposalStatus",
    "ProposalStore",
    "ProposalSummary",
    "ProposalTransitionError",
    "RiskLevel",
    "RollbackError",
    "SkillAnalysis",
    "SkillEvolutionEngine",
    "SkillEvolutionError",
    "SkillEvolutionProposal",
    "SkillEvolutionStore",
    "SystemSnapshot",
]
