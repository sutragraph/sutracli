enum ToolName {
  Database
  SearchKeyword
  SearchKeywordWithoutProjectName
  SemanticSearch
  ListFiles
  ListFilesWithoutProjectName
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

class ListFilesToolCallParamsWithoutProjectName {
  tool_name "list_files"
  parameters ListFilesParamsWithoutProjectName
}
 
type BaseToolCall = DatabaseToolCall | SearchKeywordToolCall | SearchKeywordToolCallWithoutProjectName | SemanticSearchToolCall | ListFilesToolCall | ListFilesToolCallParamsWithoutProjectName