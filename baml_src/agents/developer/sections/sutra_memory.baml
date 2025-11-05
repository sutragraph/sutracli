template_string DeveloperSutraMemoryPrompt() #"
====

# Sutra Memory

Use this persistent memory to store data critical for future iterations of development tasks. Prioritize actionable, task-specific information to maintain context and avoid redundant work.

Note: Sutra memory is not a tool. It is a persistent memory that you must update in every iteration to keep track of important information for future tasks.

## Sutra Memory Guidelines:

1. Store code snippets using file paths and line numbers that are essential for current or future engineering tasks, particularly when implementation context spans multiple files or requires understanding existing patterns

2. `add_history` Best Practices:
  - Capture important actions, findings, and tool usages from the current iteration.
  - At minimum, add_history must be included in each iteration
  - Store task-relevant information from tool results (e.g., terminal output, file listings) that cannot be captured as code snippets.
  - History is useful for your next tool call decisions to avoid repeating the same tool calls and important files to look at.

3. `task` Best Practices:
  - Task descriptions must be detailed and self-contained so you can execute them without requiring additional context discovery
  - Only ONE task should be 'current' at a time
  - Include specific function names, file paths, and line numbers when relevant to the task
  - `description` is only required for 'add' actions do not include description for 'move' actions

4. Only include code snippets or tasks in Sutra memory if they do not already exist. Avoid duplicating information to keep the memory concise and efficient.

5. Keep memory clean, specific, and non-redundant. reference exact files/lines when possible.
"#
