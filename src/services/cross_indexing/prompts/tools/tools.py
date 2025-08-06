"""
Tool Integration for Cross-Index Analysis

Integrates existing agent tools with cross-indexing specific usage patterns.
"""

from tools.tool_semantic_search.prompt import SEMANTIC_SEARCH_TOOL
from tools.tool_search_keyword.prompt import SEARCH_KEYWORD_TOOL
from tools.tool_database_search.prompt import DATABASE_SEARCH_TOOL
from tools.tool_list_files.prompt import LIST_FILES_TOOL
from utils.system_utils import get_current_directory
from .attempt_completion import ATTEMPT_COMPLETION_TOOL


TOOLS_CROSS_INDEXING = f"""\n# Tools

{LIST_FILES_TOOL.format(current_dir=get_current_directory())}

{SEARCH_KEYWORD_TOOL.format(current_dir=get_current_directory())}

{DATABASE_SEARCH_TOOL}

{ATTEMPT_COMPLETION_TOOL}
"""
