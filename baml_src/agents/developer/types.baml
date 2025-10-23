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
  tool_call DeveloperToolCall?
  sutra_memory SutraMemoryParams
}
