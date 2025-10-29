class QAEngineerCompletionToolCall {
  tool_name "attempt_completion"
  parameters QAEngineerCompletionParams
}

type QAEngineerToolCall = DatabaseToolCallSimple | SearchKeywordToolCallSimple | SemanticSearchToolCallSimple | ListFilesToolCallSimple | TermianlToolCall | QAEngineerCompletionToolCall

class QAEngineerPromptParams {
  context string
  system_info SystemInfoParams
}

class QAEngineerResponse {
  thinking string @description("Concise user-facing progress update for the UI (one sentence).")
  sutra_memory SutraMemoryParams @description("Persistent memory for code snippets, task updates, and history.")
  tool_call QAEngineerToolCall @description("Next tool to invoke with parameters.")
}
