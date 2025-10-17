template_string DeveloperSutraMemoryPrompt() #"
## SUTRA MEMORY

Use this persistent memory to store data critical for future iterations of development tasks. Prioritize actionable, task-specific information to maintain context and avoid redundant work.

### Format Requirements

Include add_history in every response to log any new, relevant data for the next iteration (e.g., code changes, bug details, task outcomes, blockers, configurations). Structure as a concise, freeform string capturing deltas only, avoiding repetition.

### Task Management (Optional)
Manage tasks with one current task at a time:

{ "action": "add", "id": "1", "to_status": "pending|current|completed", "description": "Implement login endpoint" }
{ "action": "move", "id": "1", "to_status": "pending|current|completed" }

### Code Storage (Optional)
Store code details: { "action": "add", "id": "code_1", "file": "path/file.py", "start_line": 10, "end_line": 15, "description": "Login function implementation" }.

### Guidelines

Store in sutra_memory:

- add_history: Iteration-specific data (e.g., "Added auth.py#L10-15 for login; bug in token validation", "Blocked by missing DB config").
- tasks: Task status and descriptions.
- code: File paths, line ranges, and descriptions for relevant code.

Use add_history for new findings, progress, or issues (e.g., code added, bugs found, blockers). Break tasks into specific subtasks. Clean obsolete tasks/code after completion. Prioritize exact references (file paths, line numbers) and avoid duplication.
"#
