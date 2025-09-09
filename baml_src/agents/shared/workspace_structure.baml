template_string WorkspaceStructure(current_dir: string, structure: string, max_depth: int) #"
====

## WORKSPACE STRUCTURE

Current Workspace Directory: {{ current_dir }}

Structure:
{{ structure }}

This section provides a comprehensive overview of the project's directory structure, showing folders up to {{ max_depth }} levels deep. This gives key insights into the project organization and how developers structure their code. The WORKSPACE STRUCTURE represents the initial state of the project and remains static throughout your session.
"#
