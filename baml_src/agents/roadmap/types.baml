
enum RoadmapToolName {
  Database
  SearchKeyword
  SemanticSearch
  ListFiles
  Completion
}

type RoadmapToolParameters = DatabaseParams | SearchKeywordParams | SemanticSearchParams | ListFilesParams | RoadmapCompletionParams

class RoadmapToolCall {
  tool_name RoadmapToolName
  parameters RoadmapToolParameters
}

class RoadmapResponse {
  thinking string?
  tool_call RoadmapToolCall?
  sutra_memory SutraMemoryParams
  completion RoadmapCompletionParams?
}
