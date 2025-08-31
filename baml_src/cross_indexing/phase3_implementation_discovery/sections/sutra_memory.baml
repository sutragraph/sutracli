template_string SutraMemory_Phase3() #"====

SUTRA MEMORY

Sutra Memory is a dynamic memory system that tracks implementation discovery state across iterations. It ensures continuity, prevents redundant operations, and maintains context for comprehensive implementation analysis. The system tracks iteration history and manages analysis tasks that can be created within implementation discovery.

Required Components:
- add_history: Comprehensive summary of current iteration actions, tool usage, and implementation discoveries (MANDATORY in every response)

Optional Components:
- task: Manage analysis tasks by executing tasks and creating additional tasks when needed

Usage Format

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
        "id": "unique_int_id",
        "to_status": "pending",
        "description": "additional task for further analysis"
      }
    ],
    "add_history": "Brief summary of current iteration actions and findings"
  }
}

Examples:

Example 1: Wrapper function analysis
{
  "sutra_memory": {
    "tasks": [
      {
        "action": "move",
        "id": "13",
        "from_status": "pending",
        "to_status": "current",
      },
      {
        "action": "move",
        "id": "3", 
        "from_status": "current",
        "to_status": "completed",
      }
    ],
    "add_history": "Used search_keyword to find apiClient wrapper function usage - discovered 18 calls across 6 files with real endpoints and parameters. All wrapper function calls with actual usage analyzed."
  }
}

Example 2: Wrapper function discovery with task creation
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
        "action": "add",
        "id": "21",
        "to_status": "current",
        "description": "Use search_keyword to find all apicall( wrapper function usage: apicall\\("
      }
    ],
    "add_history": "Used database tool to read src/utils/api.js - found wrapper function definition apicall(endpoint, method, data). Created task to search for all usage sites of this wrapper function across codebase."
  }
}

Example 3: Custom API client pattern discovery with task creation
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
        "action": "add",
        "id": "22",
        "to_status": "current",
        "description": "Use search_keyword to find all httpClient usage patterns: httpClient\\.(get|post|put|delete)\\("
      }
    ],
    "add_history": "Used database tool to read src/services/client.py - found custom httpClient class with methods. Created task to search for all httpClient method calls across project files."
  }
}

Example 4: Wrapper function analysis with dynamic parameters
{
  "sutra_memory": {
    "tasks": [
      {
        "action": "move",
        "id": "15",
        "from_status": "current",
        "to_status": "completed",
      },
      {
        "action": "add", 
        "id": "23",
        "to_status": "current",
        "description": "Use database tool to read src/utils/apiHelper.js completely to identify function name containing axios.get(url, config) wrapper calls"
      }
    ],
    "add_history": "Found wrapper function with dynamic url parameter in src/utils/apiHelper.js. Created task to read complete file and identify function name before searching for actual usage patterns with real endpoint values."
  }
}

Example 5: Wrapper function usage discovery
{
  "sutra_memory": {
    "tasks": [
      {
        "action": "move",
        "id": "23",
        "from_status": "current",
        "to_status": "completed",
      },
      {
        "action": "add",
        "id": "24", 
        "to_status": "current",
        "description": "Use search_keyword to find makeApiCall usage patterns: makeApiCall\\("
      }
    ],
    "add_history": "Used database tool to read src/utils/apiHelper.js - identified function name makeApiCall() containing axios wrapper calls with dynamic parameters. Created task to search for all makeApiCall usage sites across codebase to find real endpoint values."
  }
}

Example 6: Environment variable analysis with config file discovery
{
  "sutra_memory": {
    "tasks": [
      {
        "action": "move",
        "id": "25",
        "from_status": "current",
        "to_status": "completed",
      },
      {
        "action": "add",
        "id": "26",
        "to_status": "current", 
        "description": "Use database tool to read .env file to analyze DATABASE_URL and API_BASE_URL values"
      }
    ],
    "add_history": "Used list_files to find config files - discovered .env, config/database.yml, and docker-compose.yml. Found environment variables DATABASE_URL and API_BASE_URL used in connection code. Created task to analyze config file contents."
  }
}

Example 7: Task completion scenario
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
    "add_history": "Used attempt_completion - provided summary of discovered connection implementations across multiple languages"
  }
}

# Sutra Memory Guidelines:

1. Memory Assessment
In the `thinking` JSON field, assess what implementation information you already have and what import pattern discovery tasks you need to execute. Review your current sutra_memory state and determine what updates are needed based on implementation discovery progress.

2. Task Execution Protocol
- Execute pending tasks from import pattern discovery one by one
- Move tasks from pending to current, then to completed
- Use tool selection guidance provided in import pattern discovery tasks
- Process results after each tool call

3. Task Management
- Can create additional tasks for further analysis when needed
- Add tasks when discovering wrapper functions that need usage analysis with specific search patterns
- Create tasks for environment variable resolution with complete tool guidance
- Add tasks for complex connection patterns requiring deeper analysis with proper tool parameters

4. Task Creation Guidelines
- Create additional tasks ONLY when discovering new patterns requiring analysis
- Include specific search patterns for wrapper functions or complex patterns
- Provide context about discoveries that led to additional task creation
- Use descriptive task names with clear analysis objectives

5. History Best Practices
- Be specific about tools used and connection implementations found
- Mention processing and analysis results
- Note number of connections found and their types
- Include complete file paths and connection details when relevant
- Track comprehensive implementation information and analysis results

6. Critical Rules
- Sutra Memory MUST be updated in every implementation discovery response alongside exactly one tool call
- At minimum, add_history must be included in each iteration
- Execute import pattern discovery tasks before creating additional tasks
- Task IDs must be unique and sequential
- Tool results are automatically processed after each call
- COMPLETION RULE: When using attempt_completion, mark implementation discovery as completed
"#