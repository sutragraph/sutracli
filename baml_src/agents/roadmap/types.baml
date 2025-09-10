class RoadmapCompletionToolCall {
  tool_name "attempt_completion"
  parameters RoadmapCompletionParams | BaseCompletionParams
}

type RoadmapToolCall = DatabaseToolCall | SearchKeywordToolCall | SemanticSearchToolCall | ListFilesToolCall | RoadmapCompletionToolCall

class RoadmapPromptParams {
  base_params BasePromptParams
}

class RoadmapAgentParams {
  context string
  prompt_params RoadmapPromptParams
}

class RoadmapResponse {
  thinking string?
  tool_call RoadmapToolCall?
  sutra_memory SutraMemoryParams
}
