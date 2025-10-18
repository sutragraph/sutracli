class QAEngineerCompletionToolCall {
  tool_name "attempt_completion"
  parameters QAEngineerCompletionParams
}

type QAEngineerToolCall = DatabaseToolCall | SearchKeywordToolCall | SemanticSearchToolCall | ListFilesToolCall | TermianlToolCall | QAEngineerCompletionToolCall

class QAEngineerPromptParams {
  base_params BasePromptParams
}

class QAEngineerAgentParams {
  context string
  prompt_params QAEngineerPromptParams
}

class QAEngineerResponse {
  thinking string? @description("The agent's internal thought process")
  tool_call QAEngineerToolCall? @description("The tool call to be made by the QA Engineer agent")
  sutra_memory SutraMemoryParams @description("Sutra memory updates to be made")
}
