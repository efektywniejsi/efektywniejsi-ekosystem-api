"""Application-wide constants.

This module centralizes magic numbers and configuration constants
that are used across multiple modules. For environment-specific
configuration, see config.py.
"""

# =============================================================================
# File Size Limits
# =============================================================================

# Avatar upload (2 MB)
AVATAR_MAX_SIZE_BYTES: int = 2 * 1024 * 1024

# Course/bundle thumbnail upload (5 MB)
THUMBNAIL_MAX_SIZE_BYTES: int = 5 * 1024 * 1024

# Sales page image upload (5 MB)
SALES_PAGE_IMAGE_MAX_SIZE_BYTES: int = 5 * 1024 * 1024

# =============================================================================
# Pagination Defaults
# =============================================================================

# Default page size for list endpoints
DEFAULT_PAGE_SIZE: int = 20

# Default page size for conversation messages
CONVERSATION_MESSAGES_PAGE_SIZE: int = 50

# Default page size for user search
USER_SEARCH_LIMIT: int = 10

# Maximum page size to prevent abuse
MAX_PAGE_SIZE: int = 100

# Default limit for rankings/top lists
DEFAULT_RANKINGS_LIMIT: int = 10

# Default limit for statistics lists
DEFAULT_STATS_LIST_LIMIT: int = 50

# =============================================================================
# Content Limits
# =============================================================================

# Notification message preview length
MESSAGE_PREVIEW_MAX_LENGTH: int = 200

# Error message max length (for truncation)
ERROR_MESSAGE_MAX_LENGTH: int = 500

# Tag limits for community threads
MAX_TAGS_PER_THREAD: int = 5
MAX_TAG_LENGTH: int = 30

# =============================================================================
# Allowed MIME Types
# =============================================================================

# Thumbnail images
THUMBNAIL_ALLOWED_MIME_TYPES: tuple[str, ...] = (
    "image/png",
    "image/jpeg",
    "image/webp",
)

# Avatar images
AVATAR_ALLOWED_MIME_TYPES: tuple[str, ...] = (
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
)

# =============================================================================
# Frontend URL Paths
# =============================================================================
# Note: These are paths relative to FRONTEND_URL from config.py

# Checkout/payment flow paths
CHECKOUT_SUCCESS_PATH: str = "/zamowienie/sukces"
CHECKOUT_CANCEL_PATH: str = "/zamowienie/anulowano"

# Email verification paths
EMAIL_VERIFICATION_PATH: str = "/verify-email"
PASSWORD_RESET_PATH: str = "/reset-password"

# =============================================================================
# Caching
# =============================================================================

# Default cache TTL in seconds
DEFAULT_CACHE_TTL_SECONDS: int = 300  # 5 minutes

# Unread count cache TTL
UNREAD_COUNT_CACHE_TTL_SECONDS: int = 60  # 1 minute
