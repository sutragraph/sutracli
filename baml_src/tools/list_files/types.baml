// List Files Tool Parameter Types
// BAML only handles what agents need to CALL tools, not what tools RETURN

class ListFilesParams {
  path string?
  project_name string?
  recursive string?
}

class ListFilesParamsWithoutProjectName {
  path string
  recursive string?
}
