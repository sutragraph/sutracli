template_string SutraMemory_Phase1() #"
====

SUTRA MEMORY

Sutra Memory is a dynamic memory system that tracks package discovery state across iterations. It ensures continuity, prevents redundant operations, and maintains context for comprehensive package analysis. The system tracks iteration history and manages analysis tasks for import pattern discovery.

Required Components:
- add_history: Comprehensive summary of current iteration actions, tool usage, package discoveries, and task creation (MANDATORY in every response)

Optional Components:
- task: Manage analysis tasks by adding new ones with unique IDs

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
    "add_history": "Used list_files to explore project structure. Found Server/pom.xml and Frontend/package.json files in current project"
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
        "description": "Use search_keyword tool with pattern 'require\\('axios'\\)|import.*from.*'axios'|import.*axios|axios' and regex=true to find axios import statements. Look for HTTP client library imports enabling requests to other services."
      }
    ],
    "add_history": "Found package.json file and it contains axios package which is an HTTP client library."
  }
}
```

Example 3: Task completion scenario (only mark as completed when it is fully executed)
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
    "add_history": "Used attempt_completion - provided summary of discovered packages and created tasks for subsequent import analysis"
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
- Be specific about tools used and package files analyzed
- Mention key package discoveries and findings
- Note any failures or missing package files
- Include complete package names and file paths
- Track comprehensive package information for import discovery
- Write only what you did/found in the current iteration
- Do not mention specific task and IDs in history - focus on actions and discoveries made

6. Critical Rules
- Sutra Memory MUST be updated in every package discovery response alongside exactly one tool call
- At minimum, add_history must be included in each iteration
- Task IDs must be unique and sequential
- Tasks created here will be used in import pattern discovery
- Never create tasks without analyzing package file
- COMPLETION RULE: When using attempt_completion, mark package discovery as completed

Remember: Package discovery creates the foundation for import pattern discovery. Create comprehensive, actionable tasks based on actual package findings.
"#
