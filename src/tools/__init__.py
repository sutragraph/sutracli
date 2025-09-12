"""
Tools module - Contains all agent tools with their actions and prompts.
"""

from typing import Union

from baml_client.types import (
    Agent,
    BaseCompletionParams,
    DatabaseParams,
    ListFilesParams,
    RoadmapCompletionParams,
    SearchKeywordParams,
    SemanticSearchParams,
    ToolName,
)

from .tool_action import get_tool_action
from .tool_executor import execute_tool

# Union type for all tool parameters
AllToolParams = Union[
    DatabaseParams,
    SearchKeywordParams,
    SemanticSearchParams,
    ListFilesParams,
    RoadmapCompletionParams,
    BaseCompletionParams,
]


__all__ = ["Agent", "ToolName", "AllToolParams", "get_tool_action", "execute_tool"]
