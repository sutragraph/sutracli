enum ToolName {
  Database
  SearchKeyword
  SemanticSearch
  ListFiles
}

class DatabaseToolCall {
  tool_name "Database"
  parameters DatabaseParams
}

class SearchKeywordToolCall {
  tool_name "SearchKeyword"
  parameters SearchKeywordParams
}

class SemanticSearchToolCall {
  tool_name "SemanticSearch"
  parameters SemanticSearchParams
}

class ListFilesToolCall {
  tool_name "ListFiles"
  parameters ListFilesParams
}
 
type BaseToolCall = DatabaseToolCall | SearchKeywordToolCall | SemanticSearchToolCall | ListFilesToolCall