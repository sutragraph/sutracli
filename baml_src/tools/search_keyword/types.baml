class SearchKeywordParams {
  keyword string
  before_lines int?
  after_lines int?
  case_sensitive bool?
  regex bool?
  file_paths string?
  project_name string?
  fetch_next_chunk bool?
}

class SearchKeywordParamsWithoutProjectName{
  keyword string @description("The search pattern.")
  file_paths string? @description("Comma-separated file or directory paths to search in. Example: 'src/main.ts, tests/'. Defaults to entire codebase if not provided.")
  before_lines int? @description("Lines before match (default: 0)")
  after_lines int? @description("Lines after match (default: 5)")
  case_sensitive bool? @description("Case-sensitive search (default: false)")
  regex bool? @description("Treat keyword as regex pattern (default: false)")
  fetch_next_chunk bool?
}
