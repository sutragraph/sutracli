WRITE_TO_FILE_TOOL = """## write_to_file
Description: Request to write content to a file. This tool handles both **creating new files** and **inserting content into existing files**. For new files, it creates the file with the provided content. For existing files, it inserts content at the specified line or appends to the end if no line is specified.

Parameters:
- path: (required) The path of the file to write to (relative to the current workspace directory {current_dir})
- content: (required) The content to write or insert
- line: (optional) insertion before line number (1-based indexing). If not specified, content is appended to the end of existing files
- is_new_file: (optional) Set to true when creating a new file. Defaults to false for existing file operations

Usage:
<write_to_file>
<path>File path here</path>
<content>Your content here</content>
<line>Line number (optional)</line>
<is_new_file>true/false (optional)</is_new_file>
</write_to_file>

Example: Creating a new file
<write_to_file>
<path>config.json</path>
<content>{{"version": "1.0.0"}}</content>
<is_new_file>true</is_new_file>
</write_to_file>

Example: Inserting content at line 5 in existing file
<write_to_file>
<path>src/app.py</path>
<content># Import necessary libraries\nfrom flask import Flask\nimport json</content>
<line>5</line>
</write_to_file>
"""
