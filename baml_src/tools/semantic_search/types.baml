class SemanticSearchParams {
  query string
  project_name string?
  fetch_next_chunk bool?
}

class SemanticSearchParamsWithoutProjectName {
  query string @description("Describe the concept in natural language.")
  fetch_next_chunk bool?
}
