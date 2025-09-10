"""
Configuration classes for post-requisites system.
"""

from enum import Enum


class AgentProvider(Enum):
    """Available external agent providers."""
    ROVODEV = "rovodev"
    GEMINI = "gemini"
