"""
Available tools for the Roadmap Agent
"""

from tools import ToolName

# Tools needed for roadmap generation
ROADMAP_TOOLS = [
    ToolName.SEMANTIC_SEARCH,
    ToolName.LIST_FILES,
    ToolName.DATABASE_SEARCH,
    ToolName.SEARCH_KEYWORD,
    ToolName.TERMINAL_COMMANDS,
]

# Tool list for the roadmap agent
TOOL_LIST = [tool.value for tool in ROADMAP_TOOLS]
