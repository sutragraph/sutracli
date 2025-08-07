"""
Cross-Indexing Core Services

Core functionality for cross-project connection analysis and management.
"""

from .cross_index_service import CrossIndexService
from .cross_index_system import CrossIndexSystem
from .connection_matching_service import ConnectionMatchingService
from .connection_matching_manager import ConnectionMatchingManager

__all__ = [
    "CrossIndexService",
    "CrossIndexSystem",
    "ConnectionMatchingService",
    "ConnectionMatchingManager"
]