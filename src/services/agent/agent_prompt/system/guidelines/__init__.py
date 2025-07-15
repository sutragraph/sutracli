from .sutra_memory import SUTRA_MEMORY
from .tool_guidelines import TOOL_GUIDELINES
from .capabilities import CAPABILITIES_GUIDELINES
from .rules import RULES
from .system_info import SYSTEM_INFO
from .objective import OBJECTIVE

from utils.system_utils import (
    get_current_directory,
    get_home_directory,
    get_default_shell,
    get_operating_system,
)

CURRENT_DIR = get_current_directory()
HOME_DIR = get_home_directory()
DEFAULT_SHELL = get_default_shell()
OS_NAME = get_operating_system()


def get_all_guidelines() -> str:
    return f"""
{TOOL_GUIDELINES}
{SUTRA_MEMORY}
{CAPABILITIES_GUIDELINES.format(current_dir=CURRENT_DIR)}
{RULES.format(current_dir=CURRENT_DIR)}
{SYSTEM_INFO.format(
    current_dir=CURRENT_DIR,
    home_directory=HOME_DIR, 
    shell=DEFAULT_SHELL, 
    os_name=OS_NAME)
}
{OBJECTIVE}"""


__all__ = [
    "get_all_guidelines",
]
