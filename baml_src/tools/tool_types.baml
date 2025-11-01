enum ToolName {
  Database
  DatabaseSimple
  SearchKeyword
  SearchKeywordSimple
  SearchKeywordWithoutProjectName
  SemanticSearch
  SemanticSearchSimple
  ListFilesWithProjectName
  ListFilesWithoutProjectName
  Terminal
  Completion
  EditFile
  Diagnostics
}

class DatabaseToolCall {
  tool_name "database"
  parameters DatabaseParams
}

class DatabaseToolCallSimple {
  tool_name "database"
  parameters DatabaseParamsGetFileByPath | DatabaseParamsGetBlockDetails
}

class SearchKeywordToolCallWithoutProjectName {
  tool_name "search_keyword"
  parameters SearchKeywordParamsWithoutProjectName
}

class SearchKeywordToolCallWithProjectName {
  tool_name "search_keyword"
  parameters SearchKeywordParamsWithoutProjectName
}

class SemanticSearchToolCallWithoutProjectName {
  tool_name "semantic_search"
  parameters SemanticSearchParamsWithoutProjectName
}

class SemanticSearchToolCallWithProjectName {
  tool_name "semantic_search"
  parameters SemanticSearchParamsWithProjectName
}

class ListFilesToolCallWithProjectName {
  tool_name "list_files"
  parameters ListFilesParamsWithProjectName
}

class ListFilesToolCallWithoutProjectName {
  tool_name "list_files"
  parameters ListFilesParamsWithoutProjectName
}

class EditFileToolCall {
  tool_name "edit_file"
  parameters EditFileParams
}

class DiagnosticsToolCall {
  tool_name "diagnostics"
  parameters DiagnosticsParams
}

class TermianlToolCall {
  tool_name "terminal"
  parameters TermianlParams
}

class CompletionToolCall {
  tool_name "attempt_completion"
  parameters BaseCompletionParams
}
