template_string SutraMemory_Phase2() #"
====

SUTRA MEMORY

Sutra Memory is a dynamic memory system that tracks import analysis state across iterations. It ensures continuity, prevents redundant operations, and maintains context for comprehensive import analysis. The system tracks iteration history and manages analysis tasks for subsequent implementation analysis.

Required Components:
- add_history: Comprehensive summary of current iteration actions, tool usage, import discoveries, and task creation (MANDATORY in every response)

Optional Components:
- task: Manage analysis tasks by executing tasks and creating new ones with unique IDs

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

Example 1: Executing previous analysis task
```json
{
  "sutra_memory": {
    "tasks": [
      {
        "action": "move",
        "id": "2",
        "from_status": "pending",
        "to_status": "current",
      },
      {
        "action": "move",
        "id": "3",
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
    "add_history": "Used search_keyword with pattern 'require\\('axios'\\)|import.*from.*'axios'' - found axios imports in 3 files: src/api/client.js, src/services/http.js, src/utils/request.js. Created 3 individual database tasks for subsequent implementation analysis."
  }
}
```

Example 2: Multiple import patterns found
```json
{
  "sutra_memory": {
    "tasks": [
      {
        "action": "move",
        "id": "3",
        "from_status": "pending",
        "to_status": "current",
      },
      {
        "action": "move",
        "id": "3",
        "from_status": "current",
        "to_status": "completed",
      },
      {
        "action": "add",
        "id": "11",
        "to_status": "pending",
        "description": "Use search_keyword to find express usage patterns across 8 files: app\\.(get|post|put|delete)\\(|router\\."
      }
    ],
    "add_history": "Used search_keyword to find express imports - discovered in 8 files including routes and middleware files. Created search_keyword task for subsequent implementation analysis due to many files found."
  }
}
```

Example 3: Built-in pattern task creation (always required)
```json
{
  "sutra_memory": {
    "tasks": [
      {
        "action": "add",
        "id": "12",
        "to_status": "pending",
        "description": "Create built-in pattern task for JavaScript: Use search_keyword with pattern 'fetch\\(|XMLHttpRequest|new WebSocket\\(' to find native JavaScript connection patterns"
      },
      {
        "action": "add",
        "id": "13",
        "to_status": "pending",
        "description": "Create built-in pattern task for Python: Use search_keyword with pattern 'urllib\\.|http\\.client|socket\\.' to find Python built-in connection patterns"
      }
    ],
    "add_history": "implementation discovery covering JavaScript and Python native connection patterns. These tasks will be executed regardless of package findings."
  }
}
```

Example 4: Task completion with new task creation based on findings
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
        "id": "14",
        "to_status": "pending",
        "description": "Found axios imports in src/api/client.js. Use database tool to read this file and analyze axios.get(), axios.post() usage patterns"
      },
      {
        "action": "add",
        "id": "15",
        "to_status": "pending",
        "description": "Found axios imports in src/services/http.js. Use database tool to read this file and analyze axios.get(), axios.post() usage patterns"
      }
    ],
    "add_history": "Used search_keyword to find axios imports - found meaningful results in 2 files. Created 2 individual database tasks for implementation analysis based on tool results."
  }
}
```

Example 5: Task completion scenario
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
    "add_history": "Used attempt_completion - provided summary of discovered imports"
  }
}
```

# Sutra Memory Guidelines:

1. Memory Assessment
In the thinking field, assess what import information you already have and what package discovery tasks you need to execute. Review your current sutra_memory state and determine what updates are needed based on import discovery progress.

2. Task Execution Protocol
- Execute pending tasks from package discovery one by one
- Move tasks from pending to current, then to completed
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
- Be specific about search patterns used and results found
- Mention key import discoveries and file locations
- Note number of files found for each package
- Include complete file paths when relevant
- Track comprehensive import information for implementation discovery

6. Critical Rules
- Sutra Memory MUST be updated in every import discovery response alongside exactly one tool call
- At minimum, add_history must be included in each iteration
- Execute previous analysis tasks before creating implementation tasks
- Task IDs must be unique and sequential
- Tasks created here will be used in subsequent implementation analysis
- COMPLETION RULE: When using attempt_completion, mark import analysis as completed

7. Previous Task Execution Strategy
- Process pending tasks from previous analysis systematically
- Use exact search patterns provided in previous analysis tasks
- Handle different import syntaxes appropriately for each language
- Create comprehensive implementation analysis tasks based on findings
- ALWAYS create built-in pattern tasks for subsequent analysis regardless of package findings
"#
