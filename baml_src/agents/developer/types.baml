class DeveloperCompletionToolCall {
  tool_name "attempt_completion"
  parameters DeveloperCompletionParams
}

type DeveloperToolCall = DatabaseToolCall | SearchKeywordToolCall | SemanticSearchToolCall | ListFilesToolCall | DeveloperCompletionToolCall

class DeveloperPromptParams {
  base_params BasePromptParams
}

class DeveloperAgentParams {
  context string
  prompt_params DeveloperPromptParams
}

class DeveloperResponse {
  thinking string?
  tool_call DeveloperToolCall?
  sutra_memory SutraMemoryParams
}
