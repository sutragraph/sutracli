// Database Tool Parameter Types
// BAML only handles what agents need to CALL tools, not what tools RETURN

class DatabaseParams {
  query_name string
  file_path string?
  start_line int?
  end_line int?
  block_id string?
  fetch_next_chunk bool?
}
