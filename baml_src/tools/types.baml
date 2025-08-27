// Base Tool Types
// Comprehensive definitions for all available tools in the system

// All available tools in the system
enum ToolName {
  Database
  SearchKeyword
  SemanticSearch
  ListFiles
  Completion
  // Future tools can be added here
}


type ToolParameters = DatabaseParams | SearchKeywordParams | SemanticSearchParams | ListFilesParams | RoadmapCompletionParams

// Base Tool Call Structure
class BaseToolCall {
  tool_name ToolName
  parameters ToolParameters
}


