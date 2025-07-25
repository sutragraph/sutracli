"""
Tool Integration for Cross-Index Analysis

Integrates existing agent tools with cross-indexing specific usage patterns.
"""

from services.agent.agent_prompt.system.tools.semantic_search import SEMANTIC_SEARCH_TOOL
from services.agent.agent_prompt.system.tools.search_keyword import SEARCH_KEYWORD_TOOL
from services.agent.agent_prompt.system.tools.database_search import DATABASE_SEARCH_TOOL
from services.agent.agent_prompt.system.tools.list_files import LIST_FILES_TOOL
from utils.system_utils import get_current_directory
from .attempt_completion import ATTEMPT_COMPLETION_TOOL


TOOLS_CROSS_INDEXING = f"""\n# Tools

{LIST_FILES_TOOL.format(current_dir=get_current_directory())}

{SEARCH_KEYWORD_TOOL.format(current_dir=get_current_directory())}

{SEMANTIC_SEARCH_TOOL}

{DATABASE_SEARCH_TOOL}

{ATTEMPT_COMPLETION_TOOL}
"""
