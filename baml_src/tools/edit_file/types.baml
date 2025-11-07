enum EditFileMode {
  CREATE @alias("create")
  EDIT @alias("edit")
  OVERWRITE @alias("overwrite")
}

class Edit {
  old_text string @description("The text to be replaced in the file")
  new_text string @description("The text to replace with")
  line_hint int? @description("A suggested line number for the edit")
}

class EditFileParams {
  path string @description("The file path to edit or create")
  mode EditFileMode
  content string? @description("The full content to write when using `create` or `overwrite` mode")
  edits Edit[]? @description("An array of edit operations for `edit` mode")
}
