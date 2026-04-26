"""InkosAI Plugin Marketplace -- Discovery, search, installation, rating, and permission flow.

The Marketplace enables users to browse, search, install, rate, and manage
plugins for their InkosAI domains. Every marketplace operation is logged to
the Tape for full auditability.

Architecture::

    MarketplaceService
    +------ publish_plugin()       -- Submit a new plugin to the marketplace
    +------ discover()             -- Browse plugins with category/tag filters
    +------ search()               -- Full-text search across plugin metadata
    +------ get_plugin()           -- Get detailed plugin info by ID
    +------ install()              -- Install a plugin with permission approval
    +------ uninstall()            -- Remove an installed plugin
    +------ rate()                 -- Rate an installed plugin (1-5 stars)
    +------ get_installation()     -- Get an installation record
    +------ list_installed()       -- List all installed plugins for a domain
    +------ approve_permissions()  -- Approve pending permission requests
    +------ reject_permissions()   -- Reject pending permission requests
    +------ get_pending_permissions() -- List pending permission requests

    PluginListing          -- A published plugin in the marketplace
    PluginInstallation    -- An installed plugin in a domain
    PluginRating          -- A user rating for a plugin
    PermissionRequest     -- A pending permission approval
"""

from packages.marketplace.service import (
    AlreadyRatedError,
    DuplicateInstallationError,
    DuplicateListingError,
    InstallationNotFoundError,
    InstallationStore,
    InsufficientPermissionLevelError,
    InvalidPermissionError,
    MarketplaceError,
    MarketplaceEventType,
    MarketplaceService,
    PermissionRequest,
    PermissionRequestNotFoundError,
    PermissionRequestStatus,
    PermissionRequestStore,
    PluginCategory,
    PluginInstallation,
    PluginInstallationStatus,
    PluginListing,
    PluginNotFoundError,
    PluginPermissionLevel,
    PluginRating,
    PluginSortOrder,
    PublishedPluginStore,
    RatingStore,
    RatingValidationError,
    SelfRatingError,
)

__all__ = [
    "AlreadyRatedError",
    "DuplicateInstallationError",
    "DuplicateListingError",
    "InstallationNotFoundError",
    "InstallationStore",
    "InsufficientPermissionLevelError",
    "InvalidPermissionError",
    "MarketplaceError",
    "MarketplaceEventType",
    "MarketplaceService",
    "PermissionRequest",
    "PermissionRequestNotFoundError",
    "PermissionRequestStatus",
    "PermissionRequestStore",
    "PluginCategory",
    "PluginInstallation",
    "PluginInstallationStatus",
    "PluginListing",
    "PluginNotFoundError",
    "PluginPermissionLevel",
    "PluginRating",
    "PluginSortOrder",
    "PublishedPluginStore",
    "RatingStore",
    "RatingValidationError",
    "SelfRatingError",
]
