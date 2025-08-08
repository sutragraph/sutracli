"""
Sutra Memory System - Roadmap Agent focused guidelines
Anti-hallucination rules with impact-aware planning emphasis
"""

SUTRA_MEMORY = """
# SUTRA MEMORY SYSTEM

## PURPOSE
Track roadmap construction across iterations. Prevent redundant operations and preserve context (discoveries, dependencies, connections) between steps.

## MANDATORY COMPONENT
**add_history**: REQUIRED in every response. Store ALL information needed for future iterations (tool, parameters, results, key findings).

## OPTIONAL COMPONENTS
- **task**: Manage pending/current/completed tasks (ONE current task only)
- **code**: Store code snippets with exact file paths and line numbers
- **files**: Track file changes (modified/deleted/added)

## CRITICAL RULES

### CODE STORAGE CONSTRAINTS
1. ONLY store code you have SEEN with exact file path and line numbers
2. NEVER store code based on assumptions or guesses
3. If you lack exact lines, add an investigation task instead

### TASK MANAGEMENT RULES
1. Only ONE current task at any time
2. Complete current task before switching
3. Task IDs must be unique and sequential
4. Include specific file paths and function names in task descriptions

### HISTORY REQUIREMENTS
1. Store ALL information relevant to the user request
2. Include tool names, parameters, and results (summarized)
3. Record file paths, function names, and line numbers when found
4. Note failures and null results to prevent repetition

## USAGE FORMAT

```xml
<sutra_memory>
  <task>
    <add id="1" to="pending">Analyze imports for src/services/user_service.py</add>
    <move from="pending" to="current">1</move>
    <move from="current" to="completed">1</move>
    <remove>1</remove>
  </task>

  <code>
    <add id="1">
      <file>src/services/user_service.py</file>
      <start_line>45</start_line>
      <end_line>67</end_line>
      <description>uploadAvatar implementation - current behavior</description>
    </add>
  </code>

  <files>
    <modified>src/api/user_api.py</modified>
  </files>

  <add_history>database GET_FILE_IMPORTS(file_id=456) → imports: models.user, storage.s3; search_keyword pattern "uploadAvatar(" found in src/controllers/profile.py:23.</add_history>
</sutra_memory>
```

## ANTI-HALLUCINATION EXAMPLES

### ✅ CORRECT - Specific and Verified
```xml
<add_history>semantic_search query "profile picture upload" → block_1234; database GET_CODE_BLOCK_BY_ID(1234) → src/services/user_service.py lines 45-67.</add_history>
```

### ❌ WRONG - Assumptions and Guesses
```xml
<add_history>Likely uses S3 for uploads somewhere in services.</add_history>
```

### ✅ CORRECT - Code Storage with Exact Details
```xml
<code>
  <add id="2">
    <file>src/controllers/profile.py</file>
    <start_line>20</start_line>
    <end_line>33</end_line>
    <description>updateProfile endpoint calling uploadAvatar</description>
  </add>
</code>
```

## WORKFLOW CONSTRAINTS

1. Start each iteration: Review sutra_memory state
2. Before tool calls: Check history to avoid repeats; plan the next step in <thinking>
3. After tool results: Store relevant findings in history and code
4. Code storage: Only store code examined with precise lines
5. Memory cleanup: Remove outdated tasks and code when no longer needed

## VALIDATION CHECKLIST

Before updating sutra_memory, verify:
- [ ] Have I seen the exact code I'm storing?
- [ ] Are file paths and line numbers accurate?
- [ ] Have I captured enough info for next steps?
- [ ] Is my task description specific with file paths?
- [ ] Have I avoided assumptions and guesses?

## FORBIDDEN ACTIONS

1. Never store code without exact line numbers
2. Never assume file contents or structure
3. Never have multiple current tasks
4. Never skip add_history in any response
5. Never respond without a tool call

This system ensures accurate, verifiable memory management without hallucination, tailored for roadmap planning.
"""