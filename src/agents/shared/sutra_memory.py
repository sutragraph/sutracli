"""
Sutra Memory System - Precise Guidelines for Agent Memory Management
Anti-hallucination focused version with clear constraints and validation rules
"""

SUTRA_MEMORY = """
# SUTRA MEMORY SYSTEM

## PURPOSE
Track implementation state across iterations. Prevents redundant operations and maintains context for multi-step tasks.

## MANDATORY COMPONENT
**add_history**: REQUIRED in every response. Store ALL information needed for future iterations.

## OPTIONAL COMPONENTS
- **task**: Manage current/pending/completed tasks (ONE current task only)
- **code**: Store code snippets with exact file paths and line numbers
- **files**: Track file changes (modified/deleted/added)

## CRITICAL RULES

### CODE STORAGE CONSTRAINTS
1. **ONLY store code you have SEEN with exact line numbers**
2. **NEVER store code based on assumptions or guesses**
3. **If you don't know exact content/lines, add investigation task instead**

### TASK MANAGEMENT RULES
1. **Only ONE current task at any time**
2. **Complete current task before moving another to current**
3. **Task IDs must be unique and sequential**
4. **Include specific file paths and function names in task descriptions**

### FILE OPERATION RULES
1. **NEVER mark tasks completed after file operations (write_to_file, apply_diff)**
2. **WAIT for user confirmation before completing file operation tasks**
3. **Keep task as "current" until user confirms success**

### HISTORY REQUIREMENTS
1. **Store ALL information related to user query**
2. **Include exact tool names, parameters, and results**
3. **Record file paths, function names, line numbers when found**
4. **Note failures and null results to prevent repetition**

## USAGE FORMAT

```xml
<sutra_memory>
<task>
<add id="1" to="pending">Specific task with file path: src/auth/validator.py line 15</add>
<move from="pending" to="current">1</move>
<move from="current" to="completed">1</move>
<remove>1</remove>
</task>

<code>
<add id="1">
<file>src/models/user.py</file>
<start_line>23</start_line>
<end_line>45</end_line>
<description>User class constructor - needed for role system implementation</description>
</add>
<remove>1</remove>
</code>

<files>
<modified>src/auth/validator.py</modified>
<added>src/models/permissions.py</added>
<deleted>old/legacy_file.py</deleted>
</files>

<add_history>Tool used: semantic_search query "user auth". Found: validateUser() in src/auth/validator.py lines 15-28, takes (username, password). Called from: src/controllers/auth.js line 23, src/middleware/verify.py line 45. Need to check parameter compatibility for role system.</add_history>
</sutra_memory>
```

## ANTI-HALLUCINATION EXAMPLES

### ✅ CORRECT - Specific and Verified
```xml
<add_history>Used list_files on src/auth/ - found 3 files: validator.py, middleware.py, tokens.py. Used view on src/auth/validator.py lines 1-50 - found validateUser(username, password) function at line 15. Function returns boolean, uses bcrypt for password hashing.</add_history>
```

### ❌ WRONG - Assumptions and Guesses
```xml
<add_history>Found authentication system, probably has user validation and password checking functions somewhere in the auth directory.</add_history>
```

### ✅ CORRECT - Code Storage with Exact Details
```xml
<code>
<add id="1">
<file>src/auth/validator.py</file>
<start_line>15</start_line>
<end_line>28</end_line>
<description>validateUser function - returns boolean, uses bcrypt</description>
</add>
</code>
```

### ❌ WRONG - Code Storage Without Verification
```xml
<code>
<add id="1">
<file>src/auth/validator.py</file>
<start_line>unknown</start_line>
<end_line>unknown</end_line>
<description>User validation function that probably exists</description>
</add>
</code>
```

## WORKFLOW CONSTRAINTS

1. **Start each iteration**: Review existing sutra_memory state
2. **Before tool calls**: Check history to avoid redundant operations
3. **After tool results**: Store ALL relevant findings in history
4. **Task completion**: Only mark completed AFTER user confirms file operations
5. **Code storage**: Only store code you've actually examined
6. **Memory cleanup**: Remove outdated tasks and code when no longer needed

## VALIDATION CHECKLIST

Before updating sutra_memory, verify:
- [ ] Have I seen the exact code I'm storing?
- [ ] Are file paths and line numbers accurate?
- [ ] Have I stored all information needed for future iterations?
- [ ] Am I waiting for user confirmation on file operations?
- [ ] Is my task description specific with file paths?
- [ ] Have I avoided assumptions and guesses?

## FORBIDDEN ACTIONS

1. **Never store code without exact line numbers**
2. **Never assume file contents or structure**
3. **Never complete file operation tasks immediately**
4. **Never use vague task descriptions**
5. **Never skip add_history in any response**
6. **Never have multiple current tasks**
7. **Never respond with only sutra_memory (must include tool call)**

This system ensures accurate, verifiable memory management without hallucination.
"""