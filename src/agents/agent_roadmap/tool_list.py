"""
Available tools for the Roadmap Agent
"""

from tools import ToolName


TOOL_LIST_ENUM = [
    ToolName.COMPLETION,
    ToolName.SEMANTIC_SEARCH,
    ToolName.LIST_FILES,
    ToolName.DATABASE_SEARCH,
    ToolName.SEARCH_KEYWORD,
]


TOOL_LIST = [tool.value for tool in TOOL_LIST_ENUM]
