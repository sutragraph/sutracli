// Database Tool Parameter Types
// BAML only handles what agents need to CALL tools, not what tools RETURN

enum DatabaseQueryName {
  GET_FILE_BY_PATH @alias("GET_FILE_BY_PATH")
  GET_BLOCK_DETAILS @alias("GET_BLOCK_DETAILS")
}

class DatabaseParams {
  query_name DatabaseQueryName
  file_path string?
  start_line int?
  end_line int?
  block_id string?
  fetch_next_chunk bool?
}
