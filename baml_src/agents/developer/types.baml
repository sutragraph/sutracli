class DeveloperCompletionToolCall {
  tool_name "attempt_completion"
  parameters DeveloperCompletionParams
}

type DeveloperToolCall = DatabaseToolCallSimple | SearchKeywordToolCallSimple | SemanticSearchToolCallSimple | ListFilesToolCallSimple | DeveloperCompletionToolCall | TermianlToolCall | EditFileToolCall | DiagnosticsToolCall

class DeveloperPromptParams {
  context string
  system_info SystemInfoParams
}


class DeveloperResponse {
  thinking string?
  sutra_memory SutraMemoryParams
  tool_call DeveloperToolCall?
}
