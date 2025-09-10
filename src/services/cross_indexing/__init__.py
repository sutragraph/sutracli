"""
Cross-Indexing Service Package

This package provides comprehensive cross-project connection analysis and management.
It includes core services, memory management, prompts, and utilities for analyzing
inter-service connections and dependencies.
"""

from .core.cross_index_service import CrossIndexService
from .core.cross_index_system import CrossIndexSystem
from .core.cross_index_phase import CrossIndexing

__all__ = [
    "CrossIndexService",
    "CrossIndexSystem",
    "CrossIndexing",
]
