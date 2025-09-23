template_string Rules_Phase2() #"
====

RULES

1. Focus EXCLUSIVELY on IMPORT STATEMENTS for data communication packages identified in previous analysis.

2. CRITICAL SCOPE: Only find import statements for packages that enable connections between different user repositories, projects, or folders.

3. TASK EXECUTION METHODOLOGY:
  - Execute ONLY the pending tasks from previous analysis - do not search for anything else
  - Use search_keyword tool with the exact patterns provided in tasks
  - Process all tasks systematically before creating implementation tasks
  - Handle different import syntaxes based on discovered packages
  - CRITICAL: After seeing tool results when marking a task as completed, if you found meaningful import information, create new implementation tasks for the next phase

4. IMPORT PATTERN REQUIREMENTS:
  - Find all import statements for packages discovered in previous analysis
  - Include different import syntaxes based on language (require, import, from...import)
  - Handle import aliases and destructured imports appropriately
  - Locate dynamic and conditional imports when present

5. SEARCH PATTERN GUIDELINES:
  - Use regex patterns provided in previous analysis tasks exactly as specified
  - Handle language-specific import syntaxes appropriately
  - Include proper escaping for special characters in regex patterns
  - Search for both exact matches and common pattern variations

6. FILE IDENTIFICATION AND TRACKING:
  - Identify all files that import connection packages with complete file paths
  - Note import patterns and variations found in each file
  - Track import context and usage patterns for implementation analysis
  - Store file information systematically for subsequent implementation analysis

7. IMPLEMENTATION TASK CREATION REQUIREMENTS:
  - Create implementation tasks ONLY after finding import statements from previous analysis tasks
  - For few files (3-5 files): Create individual database tool tasks for each file (1 task per file)
  - For many files (6+ files): Create combined search_keyword tasks with method usage patterns (1 task for all files)
  - CRITICAL: When completing a task, review tool results and create new implementation tasks if meaningful import information was found
  - CRITICAL: ALWAYS create built-in pattern tasks for subsequent analysis regardless of package findings
  - Add complete tool guidance with exact usage patterns to search for

8. TASK CREATION FORMAT EXAMPLES:
  For Example:
    - Few files (database tool - create separate task for each file):
      * Task 1: "Found axios imports in src/api/client.js. Use database tool to read this file and analyze axios.get(), axios.post(), axios.put() usage patterns."
      * Task 2: "Found axios imports in src/services/http.js. Use database tool to read this file and analyze axios.get(), axios.post(), axios.put() usage patterns."
      * Task 3: "Found axios imports in src/utils/request.js. Use database tool to read this file and analyze axios.get(), axios.post(), axios.put() usage patterns."
    - Many files (search_keyword - create combined task):
      * Task 1: "Found express imports in 8 files (src/app.js, src/routes/api.js, src/routes/users.js, src/middleware/auth.js, src/controllers/main.js, src/services/server.js, src/utils/router.js, src/config/routes.js). Use search_keyword with pattern 'app\.(get|post|put|delete)\(' to find express route definitions across all files."
    - Built-in patterns: "Create built-in pattern task: Use search_keyword with pattern 'fetch\(' to find native fetch API usage across all files."

9. BUILT-IN PATTERN TASK CREATION (ALWAYS REQUIRED):
  - ALWAYS create built-in pattern tasks
  - Include examples for multiple languages, not just one language
  - For Example:
    - JavaScript: Create task to search for fetch(), XMLHttpRequest, WebSocket patterns
    - Python: Create task to search for urllib, http.client, socket patterns
    - Java: Create task to search for HttpURLConnection, Socket patterns

10. EXCLUSION CRITERIA:
  - Skip development and testing imports that don't establish connections
  - Ignore utility imports without communication capabilities
  - Exclude database imports (infrastructure, not service communication)
  - Skip file system and storage imports (not data communication)

11. COMPLETION REQUIREMENT: When import discovery is complete, you MUST use the `attempt_completion` tool with a summary of discovered imports.

12. NO PACKAGES/DEPENDENCIES HANDLING:
  - If no tasks exist in sutra_memory, it means no packages/dependencies were found in previous analysis
  - Use attempt_completion as there are no task for the analysis
  - MUST create file exploration workflow:
    - Create list_files task to discover all files recursively
    - Do not create any other tasks except list_files and built-in pattern tasks

13. JSON FORMAT SPECIFICATION:
  - ALL responses MUST follow the exact JSON structure
  - Complete response structure:
    ```json
    {
      "thinking": "analysis and decision-making process",
      "sutra_memory": {
        "tasks": [
          {
            "action": "move|add|remove",
            "id": "task_id_string",
            "from_status": "pending|current|completed",
            "to_status": "pending|current|completed",
            "description": "task description"
          }
        ],
        "add_history": "Brief summary of current iteration actions and findings"
      }
      "tool_call": {
        "tool_name": "database|search_keyword|list_files|attempt_completion",
        "parameters": {
          /* tool-specific parameters */
        }
      },
    }
    ```
  - The `tool_call` field contains the tool to execute with proper parameters
  - The `sutra_memory` field MUST use nested structure as shown above
  - Task operations MUST include all required fields: `action`, `id`, `description`
  - For move operations: MUST include both `from_status` and `to_status`
  - For add operations: MUST include `to_status` (pending/current/completed)
  - The `add_history` field is MANDATORY in every sutra_memory response
  - Task IDs MUST be strings, not integers
  - All enum values MUST use lowercase aliases: "add", "move", "remove", "pending", "current", "completed"
"#
