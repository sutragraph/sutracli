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

class DatabaseParamsGetFileByPath {
  query_name "GET_FILE_BY_PATH" @description("Retrieve full file content.")
  file_path string @description("Full absolute path to the file.")
  start_line int? @description("1-indexed line number to start reading from.")
  end_line int? @description("1-indexed line number to stop reading at.")
  fetch_next_chunk bool?
}

class DatabaseParamsGetBlockDetails {
  query_name "GET_BLOCK_DETAILS" @description("Retrieve block content/connections by block ID.")
  block_id string @description("Unique identifier for the code block.")
  fetch_next_chunk bool?
}
