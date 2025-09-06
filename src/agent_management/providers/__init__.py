"""
External agent providers management.
Handles different CLI agents like rovodev, gemini, etc.
"""

from .manager import AgentProviderManager
from .config import AgentProviderConfig
from .rovodev import RovodevProvider
from .gemini import GeminiProvider

__all__ = [
    'AgentProviderManager',
    'AgentProviderConfig',
    'RovodevProvider',
    'GeminiProvider'
]