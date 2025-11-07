template_string QAEngineerSutraMemory() #"
====

# Sutra Memory

Use this persistent memory to store iteration-specific data for future engineering tasks. Prioritize actionable, task-specific information to maintain context and avoid redundant work.

Note: Sutra memory is not a tool. It is a persistent memory that you must update in every iteration to keep track of important information for future tasks.

## Sutra Memory Guidelines:

1. `code` Best Practices:
  - Store code snippets using file paths and line numbers that are essential for current or future engineering tasks, particularly when implementation context spans multiple files or requires understanding existing patterns
  - Always store the whole files, if they are mentioned by the user in the query.
  - Prioritize storing code snippets that you think would be usefull in future iterations so you won't need to open the same file again and again.
  - Only include code snippets or tasks in Sutra memory if they do not already exist. Avoid duplicating information to keep the memory concise and efficient.

2. `add_history` Best Practices:
  - Capture important actions, findings, and tool usages from the current iteration.
  - At minimum, add_history must be included in each iteration
  - History is useful for your next tool call decisions to avoid repeating the same tool calls and errors encountered
  - Store task-relevant information from tool results (e.g., terminal output, file listings) that cannot be captured as code snippets.
  - Include error details, stack traces, and failure context when applicable
  - Example: "Used search_keyword with query='get_user_info()' - found 2 matches in path/to/fileA.py#L30 and path/to/fileB.py#L45"
  - Example: "Used terminal tool with command='python3 test/test_auth.py' - ran unit tests on module_x. Results: 4/5 tests passed. FAILED: test_user_authentication at tests/test_auth.py#L23 with AssertionError: Expected user role 'admin' but got 'user'. Root cause: authenticate_user() function at auth/utils.py#L15 returns default role instead of querying user_roles table. Action needed: Fix role assignment logic in get_user_role() method."

3. `task` Best Practices:
  - Tasks are for new requirements, breaking down complex tasks into smaller steps, or recording important findings. Do not create tasks that are already in memory; only include unique, necessary tasks.
  - Remember to update task status as you work: mark as 'pending' when haven't begun working on yet, 'current' when you begin, and 'completed' when finished.
  - Task descriptions must be detailed and self-contained so you can execute them without requiring additional context discovery.
  - Include specific function names, file paths, and line numbers when relevant to the task.
  - `description` is only required for 'add' actions; do not include it for 'move' actions.
  - Example: "Create comprehensive unit tests for calculate_discount() function at pricing/utils.py#L42-90 - include test cases for valid percentage discounts (0-100%), edge cases (negative values, >100%), and validation of return type (float). Tests should be added to tests/test_pricing.py following existing test pattern."

4. Keep memory clean, specific, and non-redundant. reference exact files/lines when possible.
"#
