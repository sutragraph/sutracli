"""
Tools module - Contains all agent tools with their actions and prompts.
"""

from typing import Union

from baml_client.types import (
    Agent,
    BaseCompletionParams,
    DatabaseParams,
    DatabaseParamsGetBlockDetails,
    DatabaseParamsGetFileByPath,
    DeveloperCompletionParams,
    DiagnosticsParams,
    EditFileParams,
    ListFilesParams,
    ListFilesParamsWithoutProjectName,
    QAEngineerCompletionParams,
    RoadmapCompletionParams,
    RoadmapSutraMemoryParams,
    SearchKeywordParams,
    SearchKeywordParamsWithoutProjectName,
    SemanticSearchParams,
    SemanticSearchParamsWithoutProjectName,
    SutraMemoryParams,
    TermianlParams,
    ToolName,
)

from .tool_action import get_tool_action
from .tool_executor import execute_tool

# Union type for all tool parameters
AllToolParams = Union[
    DatabaseParams,
    DatabaseParamsGetFileByPath,
    DatabaseParamsGetBlockDetails,
    SearchKeywordParams,
    SearchKeywordParamsWithoutProjectName,
    SemanticSearchParams,
    SemanticSearchParamsWithoutProjectName,
    ListFilesParams,
    ListFilesParamsWithoutProjectName,
    TermianlParams,
    DiagnosticsParams,
    EditFileParams,
    BaseCompletionParams,
    RoadmapCompletionParams,
    DeveloperCompletionParams,
    QAEngineerCompletionParams,
]

AllSutraMemoryParams = Union[
    SutraMemoryParams,
    RoadmapSutraMemoryParams,
]

__all__ = [
    "Agent",
    "ToolName",
    "AllToolParams",
    "AllSutraMemoryParams",
    "get_tool_action",
    "execute_tool",
]
