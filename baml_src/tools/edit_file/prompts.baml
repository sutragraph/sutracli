template_string EditFileToolTemplate() #"
## edit_file

Use the edit_file tool to make changes to files.

Guidelines
- Ensure the file's encoding (e.g., UTF-8) matches the tool's expectations, as mismatched encodings can corrupt content or cause edit failures.

Modes Usage:
- `create`: Creates a new file with the specified content
- `edit`: Applies specific edits to an existing file, replacing `old_text` with `new_text` at optional `line_hint` locations
- `overwrite`: Replaces the entire file content with the provided `content`
"#
