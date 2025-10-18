template_string QAEngineerSutraMemoryPrompt() #"
====

# Sutra Memory

Use this persistent memory to store critical, iteration-specific data for future engineering tasks. Prioritize actionable, task-specific information to maintain context and avoid redundant work.

Required Component:
  - add_history: Comprehensive summary of current iteration actions, tool usage, and implementation discoveries

Optional Components:
  - task: Manage analysis tasks by executing tasks and creating additional tasks when needed
  - code: Store code details which is important for future tasks

## Sutra Memory Guidelines:

1. Store critical code snippets using file paths and line numbers that are essential for current or future engineering tasks, particularly when implementation context spans multiple files or requires understanding existing patterns

2. `add_history` Best Practices:
  - Capture important actions, findings, and tool usages from the current iteration.
  - At minimum, add_history must be included in each iteration
  - History is useful for your next tool call decisions to avoid repeating the same tool calls
  - Example: "Used search_keyword with query='get_user_info()' - found 2 matches in path/to/fileA.py#L30 and path/to/fileB.py#L45"

3. `description` is only required for "add" actions do not include description for "move" actions

4. Keep memory clean, specific, and non-redundant. reference exact files/lines when possible.
"#
