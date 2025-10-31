class SemanticSearchParamsWithoutProjectName {
  query string @description("Describe the concept in natural language.")
  fetch_next_chunk bool?
}

class SemanticSearchParamsWithProjectName {
  query string @description("Describe the concept in natural language.")
  project_name string? @description("Project to search in, by default searches across all the projects.")
  fetch_next_chunk bool?
}
