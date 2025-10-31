class ListFilesParamsWithoutProjectName {
  path string @description("The absolute path to the directory whose contents (files and folders) should be listed.")
  recursive bool? @description("Whether to list files recursively. Use true for recursive listing, false or omit for top-level only.")
  fetch_next_chunk bool?
}

class ListFilesParamsWithProjectName{
  path string @description("The relative path to the directory whose contents (files and folders) should be listed.")
  project_name string @description("Name of the project the path belongs to.")
  recursive bool? @description("Whether to list files recursively. Use true for recursive listing, false or omit for top-level only.")
  fetch_next_chunk bool?
}
