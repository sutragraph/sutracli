// Search Keyword Tool Parameter Types
// BAML only handles what agents need to CALL tools, not what tools RETURN

class SearchKeywordParams {
  keyword string
  before_lines int?
  after_lines int?
  case_sensitive bool?
  regex bool?
  file_paths string?
  project_name string?
}

class SearchKeywordParamsWithoutProjectName{
  keyword string
  file_paths string
  before_lines int?
  after_lines int?
  case_sensitive bool?
  regex bool?
}