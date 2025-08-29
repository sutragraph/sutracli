
enum RoadmapToolName {
  Database
  SearchKeyword
  SemanticSearch
  ListFiles
  Completion
}

class RoadmapCompletionToolCall {
  tool_name "attempt_completion"
  parameters RoadmapCompletionParams
}

type RoadmapToolCall = BaseToolCall | RoadmapCompletionToolCall

class RoadmapAgentParams {
  context string
  project_context ProjectContext
}

class RoadmapResponse {
  thinking string?
  tool_call RoadmapToolCall?
  sutra_memory SutraMemoryParams
}
