"""
System prompt components package
"""

from .sutra_base import BASE_IDENTITY
from .tools import get_all_tools
from .guidelines import get_all_guidelines
from .workspace_structure import WORKSPACE_STRUCTURE

from src.utils.system_utils import get_current_directory, get_workspace_structure

CURRENT_DIR = get_current_directory()


def get_base_system_prompt() -> str:
    complete_prompt = f"""{BASE_IDENTITY}
{get_all_tools()}
{get_all_guidelines()}
{WORKSPACE_STRUCTURE.format(
    current_dir=CURRENT_DIR,
    workspace_structure=get_workspace_structure())}

===="""

    return complete_prompt


__all__ = [
    "get_base_system_prompt",
]
