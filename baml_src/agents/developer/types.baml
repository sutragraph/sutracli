class DeveloperCompletionToolCall {
  tool_name "attempt_completion"
  parameters DeveloperCompletionParams
}

type DeveloperToolCall = DatabaseToolCallSimple | SearchKeywordToolCallWithoutProjectName | SemanticSearchToolCallWithoutProjectName | ListFilesToolCallWithoutProjectName | DeveloperCompletionToolCall | TermianlToolCall | EditFileToolCall | DiagnosticsToolCall

class DeveloperPromptParams {
  context string
  system_info SystemInfoParams
}

class DeveloperResponse {
  thinking string @description("Concise user-facing progress update for the UI (one sentence).")
  sutra_memory SutraMemoryParams @description("Persistent memory for code snippets, task updates, and history.")
  tool_call DeveloperToolCall? @description("Next tool to invoke with parameters.")
}
