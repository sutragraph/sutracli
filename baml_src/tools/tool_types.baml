enum ToolName {
  Database
  SearchKeyword
  SemanticSearch
  ListFiles
}

class DatabaseToolCall {
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

class SemanticSearchToolCall {
  tool_name "semantic_search"
  parameters SemanticSearchParams
}

class ListFilesToolCall {
  tool_name "list_files"
  parameters ListFilesParams
}
 
type BaseToolCall = DatabaseToolCall | SearchKeywordToolCall | SearchKeywordToolCallWithoutProjectName | SemanticSearchToolCall | ListFilesToolCall