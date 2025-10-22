enum ToolName {
  Database
  DatabaseSimple
  SearchKeyword
  SearchKeywordSimple
  SearchKeywordWithoutProjectName
  SemanticSearch
  SemanticSearchSimple
  SemanticSearchWithoutProjectName
  ListFiles
  ListFilesSimple
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
  parameters DatabaseParams
}

class SearchKeywordToolCall {
  tool_name "search_keyword"
  parameters SearchKeywordParams
}

class SearchKeywordToolCallWithoutProjectName {
  tool_name "search_keyword"
  parameters SearchKeywordParamsWithoutProjectName
}

class SearchKeywordToolCallSimple {
  tool_name "search_keyword"
  parameters SearchKeywordParamsWithoutProjectName
}

class SemanticSearchToolCall {
  tool_name "semantic_search"
  parameters SemanticSearchParams
}

class SemanticSearchToolCallWithoutProjectName {
  tool_name "semantic_search"
  parameters SemanticSearchParamsWithoutProjectName
}

class SemanticSearchToolCallSimple {
  tool_name "semantic_search"
  parameters SemanticSearchParamsWithoutProjectName
}

class ListFilesToolCall {
  tool_name "list_files"
  parameters ListFilesParams
}

class ListFilesToolCallWithoutProjectName {
  tool_name "list_files"
  parameters ListFilesParamsWithoutProjectName
}

class ListFilesToolCallSimple {
  tool_name "list_files"
  parameters ListFilesParamsWithoutProjectName
}

class TermianlToolCall {
  tool_name "terminal"
  parameters TermianlParams
}

class CompletionToolCall {
  tool_name "attempt_completion"
  parameters BaseCompletionParams
}
