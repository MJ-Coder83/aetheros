"""Backward-compatible re-export shim for intelligence_profile.

All profile functionality has been consolidated into ``packages.prime.profile``.
This module re-exports the public API so existing imports continue to work.

Migrate to::

    from packages.prime.profile import IntelligenceProfileEngine, InteractionType, ...

This shim will be removed in a future version.
"""

# Re-export everything that was previously in this module
from packages.prime.profile import (
    DomainExpertise,
    ExpertiseAssessor,
    ExpertiseLevel,
    IntelligenceProfile,
    IntelligenceProfileEngine,
    InteractionSummary,
    InteractionType,
    PreferenceCategory,
    PreferenceInferrer,
    ProfileError,
    ProfileNotFoundError,
    ProfileSnapshot,
    ProfileStatus,
    SnapshotNotFoundError,
    SnapshotStore,
    UserPreference,
)

# Backward-compatible alias: old code imported ProfileStore from this module.
# The old ProfileStore was an in-memory store for IntelligenceProfile objects.
# It has been replaced by ProfileStorage + InMemoryProfileStore in profile.py.
from packages.prime.profile import InMemoryProfileStore as ProfileStore

__all__ = [
    "DomainExpertise",
    "ExpertiseAssessor",
    "ExpertiseLevel",
    "IntelligenceProfile",
    "IntelligenceProfileEngine",
    "InteractionSummary",
    "InteractionType",
    "PreferenceCategory",
    "PreferenceInferrer",
    "ProfileError",
    "ProfileNotFoundError",
    "ProfileSnapshot",
    "ProfileStatus",
    "ProfileStore",
    "SnapshotNotFoundError",
    "SnapshotStore",
    "UserPreference",
]
