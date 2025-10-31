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
    ListFilesParamsWithoutProjectName,
    ListFilesParamsWithProjectName,
    QAEngineerCompletionParams,
    RoadmapCompletionParams,
    RoadmapSutraMemoryParams,
    SearchKeywordParamsWithoutProjectName,
    SearchKeywordParamsWithProjectName,
    SemanticSearchParamsWithoutProjectName,
    SemanticSearchParamsWithProjectName,
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
    SearchKeywordParamsWithProjectName,
    SearchKeywordParamsWithoutProjectName,
    SemanticSearchParamsWithProjectName,
    SemanticSearchParamsWithoutProjectName,
    ListFilesParamsWithProjectName,
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
