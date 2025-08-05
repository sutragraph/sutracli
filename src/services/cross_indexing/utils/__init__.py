"""
Cross-Index Utilities

Utilities for processing and storing cross-index analysis results.
"""

from .connection_processor import ConnectionProcessor
from .connection_utils import infer_technology_type

__all__ = ["ConnectionProcessor", "infer_technology_type"]
