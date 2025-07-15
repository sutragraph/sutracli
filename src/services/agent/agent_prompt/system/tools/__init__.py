from .semantic_search import SEMANTIC_SEARCH_TOOL
from .database_search import DATABASE_SEARCH_TOOL
from .search_keyword import SEARCH_KEYWORD_TOOL
from .list_files import LIST_FILES_TOOL
from .terminal_commands import TERMINAL_TOOL
from .apply_diff import APPLY_DIFF_TOOL
from .write_to_file import WRITE_TO_FILE_TOOL
from .completion import COMPLETION_TOOLS
from .tool_use import TOOL_USE_INFORMATION
from .web_scrap import WEB_SCRAP_TOOL
from .web_search import WEB_SEARCH_TOOL


# TODO: Uncomment when search and replace tool is implemented
# from .search_and_replace import SEARCH_AND_REPLACE_TOOL

from utils.system_utils import get_current_directory

CURRENT_DIR = get_current_directory()

# TODO: Add directory-scoped semantic search support.


def get_all_tools() -> str:
    return f"""
{TOOL_USE_INFORMATION}
# Tools

{SEMANTIC_SEARCH_TOOL} 
{DATABASE_SEARCH_TOOL}
{SEARCH_KEYWORD_TOOL.format(current_dir=CURRENT_DIR)}
{LIST_FILES_TOOL.format(current_dir=CURRENT_DIR)}
{TERMINAL_TOOL.format(current_dir=CURRENT_DIR)}
{APPLY_DIFF_TOOL.format(current_dir=CURRENT_DIR)}
{WRITE_TO_FILE_TOOL.format(current_dir=CURRENT_DIR)}
{WEB_SEARCH_TOOL}
{WEB_SCRAP_TOOL}
{COMPLETION_TOOLS}"""


__all__ = [
    "get_all_tools",
]
