template_string Rules_Phase1() #"
====

RULES

1. Focus EXCLUSIVELY on DATA COMMUNICATION packages that enable connections between different user repositories, projects, or folders.

2. CRITICAL SCOPE: Only identify packages that can be used for sending/receiving data to/from other user services/repositories.

3. PACKAGE DISCOVERY METHODOLOGY:
   - Start with list_files tool to explore project structure
   - Look for package configuration files in the project (examples: package.json for Node.js, requirements.txt for Python)
   - Use database tool to read package files completely
   - IMMEDIATELY create tasks for import pattern discovery after finding packages in EACH file using <task> tags in Sutra Memory
   - THEN continue searching for additional package files if needed
   - CRITICAL: Create tasks immediately after analyzing each package file, do not wait to analyze all files first

4. TASK CREATION REQUIREMENTS:
   - Create tasks ONLY after analyzing package files
   - Never create task lists just by seeing file listings
   - Include ALL discovered packages from the current file being analyzed
   - Provide specific search patterns for each package
   - Use regex patterns with proper escaping for special characters

5. PACKAGE CLASSIFICATION RULES:
   - HTTP Client Libraries: Packages that enable making HTTP requests to other services
   - HTTP Server Frameworks: Packages that create HTTP servers to receive requests from other services
   - WebSocket Libraries: Packages that enable real-time bidirectional communication
   - Message Queue Libraries: Packages that enable asynchronous message passing between services
   - Media Streaming Libraries: Packages that handle media streaming protocols like WebRTC
   - Other Communication Libraries: Any other packages related to communication but not covered above
   
6. EXCLUSION CRITERIA:
   - Database connection libraries for data persistence (not communication)
   - File system and local storage libraries
   - Development tools and testing frameworks
   - Files Like package-lock.json, yarn.lock, Pipfile.lock, etc. that are not package configuration files
   
7. TASK CREATION FORMAT RULES:
   - Include complete tool selection guidance (search_keyword with specific patterns)
   - Provide exact search patterns with proper regex escaping
   - Add comprehensive context about package purpose and expected import variations
   - Include examples of expected import statements for the package
   - Specify tool parameters (regex=true, after_lines, etc.) when applicable

8. ADAPTIVE STRATEGY RULES:
   - Never search for non-existent packages
   - Create comprehensive task list based on actual findings

9. MANDATORY EXCLUSIONS - NEVER include these:
    - Database persistence libraries (e.g., ORMs, database drivers for data storage)
    - Local file system and storage libraries
    - NON-EXISTENT PACKAGES: Never search for patterns from packages that don't exist in the project

10. FILE PATH RULE: All file paths must be relative to the project root directory. When storing package findings in Sutra Memory, always use relative paths for consistency.

11. COMPLETION RULE: You MUST use `attempt_completion` tool with a brief 3-4 line summary when package discovery is complete. Do NOT provide detailed package data - only a summary of what types of packages were found and analyzed.

12. MEMORY UPDATE RULE: You MUST include Sutra Memory updates in EVERY response using `<sutra_memory></sutra_memory>` format. This system tracks your analysis progress and creates tasks for subsequent import analysis.

13. TOOL SELECTION RULE: You MUST select exactly ONE tool in each iteration. Every response must contain exactly one tool call.

14. IMMEDIATE TASK CREATION RULE: When you find connection packages in a package file, you MUST create tasks for those packages in the SAME iteration before searching for additional files. This ensures package information is preserved across iterations. The workflow should be: analyze file → create tasks for found packages → then search for more files.

14. COMPLETION RULE: When package discovery is complete, you MUST use the `attempt_completion` tool to signal completion after creating tasks list from package analysis.

15. UNKOWN FILE PATHS: When not sure about file paths, use list_files tool to explore project structure and find package configuration files. Do NOT assume file paths without verification.

16. VERIFIED FILE EXISTENCE RULE: Create tasks ONLY for package files that are explicitly present in the list_files tool results. Do NOT create tasks for files that are not found in the actual file listing. For example:
   - If package.json is found in list_files results, then create a task mentioning "package.json file open using database tool"
   - If pom.xml is NOT found in list_files results, then do NOT create any task for Maven packages
   - Always verify file existence in the list_files output before creating any task
   - Task creation must be based on actual file presence, not assumptions about what package files might exist

17. JSON FORMAT SPECIFICATION:
    - ALL responses MUST follow the exact JSON structure
    - Complete response structure:
    ```json
    {
      "thinking": "analysis and decision-making process",
      "tool_call": {
        "tool_name": "database|search_keyword|list_files|attempt_completion",
        "parameters": {
          /* tool-specific parameters */
        }
      },
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
    }
    ```
    - The `thinking` field is a JSON string field (not XML tags), used for analysis and decision-making process
    - The `tool_call` field contains the tool to execute with proper parameters
    - The `sutra_memory` field MUST use nested structure as shown above
    - Task operations MUST include all required fields: `action`, `id`, `description`
    - For move operations: MUST include both `from_status` and `to_status`
    - For add operations: MUST include `to_status` (pending/current/completed)
    - The `add_history` field is MANDATORY in every sutra_memory response
    - Task IDs MUST be strings, not integers
    - All enum values MUST use lowercase aliases: "add", "move", "remove", "pending", "current", "completed"
"#