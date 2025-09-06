template_string SutraMemory_Phase2() #"
====

SUTRA MEMORY

Sutra Memory is a dynamic memory system that tracks import analysis state across iterations. It ensures continuity, prevents redundant operations, and maintains context for comprehensive import analysis. The system tracks iteration history and manages analysis tasks for subsequent implementation analysis.

Required Components:
- add_history: Comprehensive summary of current iteration actions, tool usage, import discoveries, and task creation (MANDATORY in every response)

Optional Components:
- task: Manage analysis tasks by executing tasks and creating new ones with unique IDs

NOTE: `description` is only required for "add" actions do not include description for "move" actions

Usage Format

```json
{
  "sutra_memory": {
    "tasks": [
      {
        "action": "move",
        "id": "task_id",
        "from_status": "pending",
        "to_status": "current",
      },
      {
        "action": "move",
        "id": "task_id",
        "from_status": "current",
        "to_status": "completed",
      },
      {
        "action": "add",
        "id": "unique_id",
        "to_status": "pending",
        "description": "new task description"
      }
    ],
    "add_history": "Brief summary of current iteration actions and findings"
  }
}
```

Examples:

Example 1: Executing task with retry approach
```json
{
  "sutra_memory": {
    "tasks": [
      {
        "action": "move",
        "id": "2",
        "from_status": "pending",
        "to_status": "current",
      }
    ],
    "add_history": "Used search_keyword with query='require\\\\s*\\\\(\\\\s*['\\\"]axios['\\\"]\\\\s*\\\\)' and regex=true - found 0 results in current iteration. Need to try alternative search patterns before completing this task."
  }
}
```

Example 2: Retry with different pattern in same task
```json
{
  "sutra_memory": {
    "tasks": [],
    "add_history": "Used search_keyword with query='import.*axios|axios.*=' and regex=true - found 5 results in 3 files: src/api/client.js, src/services/http.js, src/utils/request.js in current iteration. Task execution successful after pattern adjustment."
  }
}
```

Example 3: Task completion after successful retry
```json
{
  "sutra_memory": {
    "tasks": [
      {
        "action": "move",
        "id": "2",
        "from_status": "current",
        "to_status": "completed",
      },
      {
        "action": "add",
        "id": "10",
        "to_status": "pending",
        "description": "Use database tool to analyze axios usage in src/api/client.js"
      },
      {
        "action": "add",
        "id": "11",
        "to_status": "pending",
        "description": "Use database tool to analyze axios usage in src/services/http.js"
      },
      {
        "action": "add",
        "id": "12",
        "to_status": "pending",
        "description": "Use database tool to analyze axios usage in src/utils/request.js"
      }
    ],
    "add_history": "After 2 search attempts, used search_keyword with query='import.*axios|axios.*=' and regex=true - found 5 matches in 3 files in current iteration. Created 3 individual database tasks for subsequent implementation analysis."
  }
}
```

Example 4: Task completion after exhaustive search attempts
```json
{
  "sutra_memory": {
    "tasks": [
      {
        "action": "move",
        "id": "3",
        "from_status": "current",
        "to_status": "completed",
      },
      {
        "action": "move",
        "id": "4",
        "from_status": "pending",
        "to_status": "current",
      }
    ],
    "add_history": "Used search_keyword with 3 different queries in current iteration: query='require.*express' found 0 results, query='import.*express' found 0 results, query='express.*Router' found 0 results. No express imports found after exhaustive search. Moving to next package analysis task."
  }
}
```

Example 5: Multiple import patterns found after retry
```json
{
  "sutra_memory": {
    "tasks": [
      {
        "action": "move",
        "id": "5",
        "from_status": "pending",
        "to_status": "current",
      },
      {
        "action": "move",
        "id": "5",
        "from_status": "current",
        "to_status": "completed",
      },
      {
        "action": "add",
        "id": "13",
        "to_status": "pending",
        "description": "Use search_keyword to find express usage patterns across 8 files: (app|router)\\.(get|post|put|delete)\\("
      }
    ],
    "add_history": "Used search_keyword with query='require.*express' and regex=true - found 2 results, then used query='import.*Router.*express' and regex=true - found 6 more matches in current iteration. Total 8 files with express imports discovered. Created search_keyword task for implementation analysis."
  }
}
```

Example 6: Built-in pattern task creation (always required)
```json
{
  "sutra_memory": {
    "tasks": [
      {
        "action": "add",
        "id": "14",
        "to_status": "pending",
        "description": "Create built-in pattern task for JavaScript: Use search_keyword with pattern 'fetch\\\\s*\\\\(|new\\\\s+XMLHttpRequest|new\\\\s+WebSocket\\\\s*\\\\(' to find native JavaScript connection patterns"
      },
      {
        "action": "add",
        "id": "15",
        "to_status": "pending",
        "description": "Create built-in pattern task for Python: Use search_keyword with pattern 'urllib\\\\.|http\\\\.client|socket\\\\.' to find Python built-in connection patterns"
      }
    ],
    "add_history": "Created built-in pattern tasks for implementation discovery covering JavaScript and Python native connection patterns. These tasks will be executed regardless of package findings."
  }
}
```

Example 7: Task completion with new task creation based on findings
```json
{
  "sutra_memory": {
    "tasks": [
      {
        "action": "move",
        "id": "5",
        "from_status": "current",
        "to_status": "completed",
      },
      {
        "action": "add",
        "id": "16",
        "to_status": "pending",
        "description": "Found axios imports in src/api/client.js. Use database tool to read this file and analyze axios.get(), axios.post() usage patterns"
      },
      {
        "action": "add",
        "id": "17",
        "to_status": "pending",
        "description": "Found axios imports in src/services/http.js. Use database tool to read this file and analyze axios.get(), axios.post() usage patterns"
      }
    ],
    "add_history": "Used search_keyword with query='axios' and regex=false - found 4 matches in 2 files in current iteration. Created 2 individual database tasks for implementation analysis based on tool results."
  }
}
```

Example 8: Task completion scenario
```json
{
  "sutra_memory": {
    "tasks": [
      {
        "action": "move",
        "id": "3",
        "from_status": "current",
        "to_status": "completed",
      }
    ],
    "add_history": "Used attempt_completion with result='Import analysis complete. Found imports in 15 files: axios (3 files), express (8 files), socket.io (4 files). Created 5 implementation tasks and 3 built-in pattern tasks for next phase.'"
  }
}
```

# Sutra Memory Guidelines:

1. Memory Assessment
In the thinking field, assess what import information you already have and what package discovery tasks you need to execute. Review your current sutra_memory state and determine what updates are needed based on import discovery progress.

2. Task Execution Protocol
- Execute pending tasks from package discovery one by one
- Move tasks from pending to current when starting execution
- Try 2-3 different search patterns before marking tasks as completed
- If initial search pattern fails, try alternative patterns in same iteration
- Only mark task as completed after exhausting reasonable search variations
- Use search_keyword with patterns provided in package discovery tasks
- CRITICAL: After seeing tool results when marking a task as completed, if you found meaningful import information, create new implementation tasks for the next phase
- Create implementation discovery tasks based on findings

3. Task Management
- Create tasks with complete tool guidance and file paths when imports are found
- Few files (3-5): Create individual database tasks for each file (1 task per file)
- Many files (6+): Create combined search_keyword tasks with usage patterns and regex parameters
- ALWAYS create built-in pattern tasks regardless of package findings
- Include comprehensive tool selection guidance and expected usage patterns

4. Task Creation Guidelines
- Create tasks ONLY after finding imports from analysis
- CRITICAL: When completing a task, review tool results and create new implementation tasks if meaningful import information was found
- Include exact file paths discovered during import search
- Provide context about import patterns found
- Add appropriate tool selection based on number of files found
- ALWAYS create built-in pattern tasks covering multiple languages
- File paths must be complete and accurate for implementation analysis

5. History Best Practices
- Be specific about search patterns used and results found in current iteration
- Mention all tool attempts made in current iteration with specific queries
- If search failed, mention the failed pattern and any alternative patterns tried
- Note number of files found for each package in current iteration
- Include complete file paths when relevant from current tool results
- Track comprehensive import information for implementation discovery
- Example: "Used search_keyword with query='require\\\\s*\\\\(axios\\\\)' and regex=true - found 0 results, tried query='import.*axios' and regex=true - found 3 matches in current iteration"
- Example: "Used search_keyword with query='express.*Router' and regex=true in current iteration - discovered 5 import statements in 3 files"
- Do not mention specific task IDs in history - focus on actions and discoveries made in current iteration

6. Critical Rules
- Sutra Memory MUST be updated in every import discovery response alongside exactly one tool call
- At minimum, add_history must be included in each iteration
- Execute previous analysis tasks before creating implementation tasks
- Task IDs must be unique and sequential
- Tasks created here will be used in subsequent implementation analysis
- COMPLETION RULE: When using attempt_completion, mark import analysis as completed

7. Previous Task Execution Strategy
- Process pending tasks from previous analysis systematically
- Use exact search patterns provided in previous analysis tasks as starting point
- If initial pattern fails, try 2-3 alternative patterns before giving up
- Handle different import syntaxes appropriately for each language
- Only mark tasks complete after exhaustive pattern attempts (2-3 tries minimum)
- Create comprehensive implementation analysis tasks based on findings
- ALWAYS create built-in pattern tasks for subsequent analysis regardless of package findings

8. Retry Pattern Guidelines
- First attempt: Use exact pattern from package discovery task
- Second attempt: Try broader or alternative syntax patterns
- Third attempt: Try language-specific variations or simplified patterns
- Document all attempts in history with specific patterns used
- Only complete task after reasonable exhaustive search
- Example retry sequence: 'require\\\\(axios\\\\)' → 'import.*axios' → 'axios.*='
"#
