// Semantic Search Tool Parameter Types
// BAML only handles what agents need to CALL tools, not what tools RETURN

class SemanticSearchParams {
  query string
  project_name string?
  fetch_next_chunk bool?
}
