"""
System prompt components package
"""

from .sutra_base import BASE_IDENTITY
from .tools import get_all_tools
from .guidelines import get_all_guidelines
from .workspace_structure import WORKSPACE_STRUCTURE

from utils.system_utils import get_current_directory, get_workspace_structure
from utils.performance_monitor import performance_timer

CURRENT_DIR = get_current_directory()

# Cache for system prompt to avoid regeneration
_system_prompt_cache = None
_cache_timestamp = None
_cache_validity_seconds = 300  # 5 minutes


@performance_timer("get_base_system_prompt")
def get_base_system_prompt() -> str:
    """Get the base system prompt for the agent with caching."""
    global _system_prompt_cache, _cache_timestamp
    
    import time
    current_time = time.time()
    
    # Check if cache is valid
    if (_system_prompt_cache is not None and 
        _cache_timestamp is not None and 
        current_time - _cache_timestamp < _cache_validity_seconds):
        return _system_prompt_cache
    
    # Generate fresh system prompt
    complete_prompt = f"""{BASE_IDENTITY}
{get_all_tools()}
{get_all_guidelines()}
{WORKSPACE_STRUCTURE.format(
    current_dir=CURRENT_DIR,
    workspace_structure=get_workspace_structure())}

===="""
    
    # Cache the result
    _system_prompt_cache = complete_prompt
    _cache_timestamp = current_time
    
    return complete_prompt


def invalidate_system_prompt_cache():
    """Invalidate the system prompt cache to force regeneration."""
    global _system_prompt_cache, _cache_timestamp
    _system_prompt_cache = None
    _cache_timestamp = None


__all__ = [
    "get_base_system_prompt",
]
