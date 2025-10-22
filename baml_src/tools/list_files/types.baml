class ListFilesParams {
  path string?
  project_name string?
  recursive bool?
  fetch_next_chunk bool?
}

class ListFilesParamsWithoutProjectName {
  path string @description("The absolute path to the directory whose contents (files and folders) should be listed.")
  recursive bool? @description("Whether to list files recursively. Use true for recursive listing, false or omit for top-level only.")
  fetch_next_chunk bool?
}
