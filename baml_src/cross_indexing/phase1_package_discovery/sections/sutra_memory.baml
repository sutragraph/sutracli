template_string SutraMemory_Phase1() #"
====

SUTRA MEMORY

Sutra Memory is a dynamic memory system that tracks package discovery state across iterations. It ensures continuity, prevents redundant operations, and maintains context for comprehensive package analysis. The system tracks iteration history and manages analysis tasks for import pattern discovery.

Required Components:
  - add_history: Comprehensive summary of current iteration actions, tool usage, package discoveries, and task creation (MANDATORY in every response)

Optional Components:
  - task: Manage analysis tasks by adding new ones with unique IDs

NOTE: `description` is only required for "add" actions do not include description for "move" actions

Usage Format

```json
{
  "sutra_memory": {
    "tasks": [
      {
        "action": "add",
        "id": "unique_id",
        "to_status": "pending",
        "description": "specific task description"
      },
      {
        "action": "move",
        "id": "task_id",
        "from_status": "current",
        "to_status": "completed",
      },
      {
        "action": "move",
        "id": "task_id",
        "from_status": "pending",
        "to_status": "current",
      }
    ],
    "add_history": "Brief summary of current iteration actions and findings"
  }
}
```

Examples:

Example 1: Starting package discovery
```json
{
  "sutra_memory": {
    "add_history": "Used list_files with path='.' and max_depth=2 - found 15 files including package.json and requirements.txt in current iteration"
  }
}
```

Example 2: Package file analysis
```json
{
  "sutra_memory": {
    "tasks": [
      {
        "action": "add",
        "id": "2",
        "to_status": "pending",
        "description": "Use search_keyword tool with pattern 'require.*axios|import.*axios' and regex=true, case_sensitive=false to find axios import statements. Look for HTTP client library imports enabling requests to other services."
      }
    ],
    "add_history": "Used database query GET_FILE_BY_PATH with file_path='package.json' - found axios, express, socket.io connection packages in dependencies section. Discovered 3 communication packages for import analysis."
  }
}
```

Example 3: Multiple package files analysis
```json
{
  "sutra_memory": {
    "tasks": [
      {
        "action": "add",
        "id": "3",
        "to_status": "pending",
        "description": "Use search_keyword tool with pattern 'import.*pika|from.*pika' and regex=true, case_sensitive=false to find pika import statements in Python files"
      }
    ],
    "add_history": "Used database query GET_FILE_BY_PATH with file_path='requirements.txt' - found pika, flask, celery communication packages. Combined with previous package.json analysis, total 6 connection packages discovered across JavaScript and Python."
  }
}
```

Example 4: Task completion scenario with project summary (only mark as completed when it is fully executed)
```json
{
  "sutra_memory": {
    "tasks": [
      {
        "action": "move",
        "id": "1",
        "from_status": "current",
        "to_status": "completed",
      }
    ],
    "add_history": "Used attempt_completion with comprehensive connection summary. Project: OrderService v2.3.1 (Node.js microservice). Found 5 connection packages: express (HTTP server), axios (HTTP client), amqplib (message queue), jsonwebtoken + passport (auth)."
  }
}
```

# Sutra Memory Guidelines:

1. Memory Assessment
In the thinking field, assess what package information you already have and what package files you need to analyze. Review your current sutra_memory state and determine what updates are needed based on package discovery progress.

2. First Iteration Protocol
  - Start with list_files tool to explore project structure and identify package files
  - Use database tool to examine package files and identify connection packages
  - CRITICAL: Never create task lists without first analyzing package files
  - Use tools systematically based on discovered packages

3. Task Management
  - Create tasks with complete tool guidance: tool name, search patterns, regex parameters
  - Include specific search patterns with proper escaping and context
  - Provide comprehensive descriptions with expected import variations and tool parameters

4. Task Creation Guidelines
  - Create tasks ONLY after package analysis is complete
  - Include exact search patterns for import discovery
  - Provide context about package purpose
  - Use descriptive task names with clear objectives

5. History Best Practices
  - Be specific about tools used and package files analyzed in current iteration
  - Mention key package discoveries and findings from current tool calls
  - Note any failures or missing package files encountered in this iteration
  - Include complete package names and file paths discovered
  - Track comprehensive package information for import discovery
  - Write only what you did/found in the current iteration with specific tool and query details
  - Include project analysis details: project type, language detection, technology stack identification
  - Collect project metadata: project name (from package files), version info, main technologies used
  - Example: "Used list_files with path='.' and max_depth=2 - found 15 files including package.json in current iteration. Identified Node.js project structure."
  - Example: "Used database query GET_FILE_BY_PATH with file_path='package.json' - found axios, express connection packages in dependencies section. Project: OrderService (v2.3.1), Node.js microservice with HTTP communication."
  - Do not mention specific task IDs in history - focus on actions and discoveries made

6. Critical Rules
  - Sutra Memory MUST be updated in every package discovery response alongside exactly one tool call
  - At minimum, add_history must be included in each iteration
  - Task IDs must be unique and sequential
  - Tasks created here will be used in import pattern discovery
  - Never create tasks without analyzing package file
  - COMPLETION RULE: When using attempt_completion, mark package discovery as completed

Remember: Package discovery creates the foundation for import pattern discovery. Create comprehensive, actionable tasks based on actual package findings.
"#
