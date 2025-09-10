"""
Agent Management System for SutraKit.
Handles prerequisites, post-requisites, and external agent providers.
"""

from .prerequisites.agent_config import get_agent_registry
from .providers.manager import AgentProviderManager

__all__ = ["get_agent_registry", "PostRequisitesManager", "AgentProviderManager"]
