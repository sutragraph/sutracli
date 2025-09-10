template_string Rules_Phase3() #"
====

RULES

1. Focus EXCLUSIVELY on ACTUAL USAGE of imported connection methods that establish data communication between different user repositories, projects, or folders.

2. CRITICAL SCOPE: Only find actual connection establishment code with real parameters that sends/receives data between services, not generic function definitions or configuration code.

3. TASK EXECUTION METHODOLOGY:
   - Execute pending tasks from previous import analysis one by one systematically
   - Use tool selection guidance provided in tasks (database vs search_keyword)
   - Process all previous import analysis tasks before creating additional tasks
   - Handle different connection types and languages appropriately
   - MANDATORY: When you find environment variables in connection code, IMMEDIATELY check sutra memory and create config file search tasks if needed

4. CONNECTION CODE REQUIREMENTS:
   - Find actual usage of imported methods with real parameters and endpoint values
   - Include environment variable values and their resolved configurations
   - Find connection establishment lines that show actual service communication
   - Focus on where connections are USED with real values, not where they are defined
   - CRITICAL: When you see process.env.VARIABLE_NAME or config variables in connection code, you MUST create tasks to find and analyze config files

5. TOOL SELECTION STRATEGY:
   - Few files (3-5 files with imports): Use database tool to read entire file content for comprehensive analysis
   - Many files (6+ files): Use search_keyword with targeted patterns based on actual imports
   - Wrapper functions: Always use search_keyword to find usage sites across entire codebase
   - Built-in patterns: Use search_keyword for language built-ins that don't require imports
   - Follow specific guidance provided in previous import analysis tasks

6. CONNECTION ANALYSIS PRIORITIES:
   - Find actual connection calls with real parameters and endpoint information
   - Include environment variable usage and resolved values when available
   - Find wrapper function calls with actual parameters, not wrapper function definitions
   - Focus on connection establishment that shows service-to-service communication

7. ACTUAL USAGE EXAMPLES (FIND THESE):
   For Example:
   - HTTP calls: `const response = await axios.get(`${process.env.API_BASE_URL}/users/${userId}`)` with real endpoints
   - Server routes: `@app.route('/api/users', methods=['POST'])` with actual endpoint paths
   - Wrapper calls: `apiClient.makeRequest('/admin/users', 'POST', userData)` with real parameters
   - Socket events: `socket.emit('user-message', { userId, message })` with actual event names

8. GENERIC DEFINITIONS (DON'T FOCUS ON THESE):
   For Example:
   - Function definitions: `function makeApiCall(url, method, data) { ... }` without actual usage
   - Client creation: `const apiClient = axios.create({ baseURL: config.baseURL })` without usage
   - Middleware setup: `app.use(express.json())` without endpoint definitions

9. BUILT-IN LANGUAGE PATTERNS (NO IMPORTS REQUIRED):
   For Example:
   - JavaScript: Native `fetch()` API, `XMLHttpRequest`, `WebSocket` constructor
   - Python: Built-in `urllib.request`, `http.client`, `socket` module
   - These patterns should be analyzed alongside imported package usage when relevant

10. WRAPPER FUNCTION ANALYSIS RULES - MANDATORY EXECUTION:
     - CRITICAL DETECTION: When you find ANY connection code with VARIABLE/PARAMETER names instead of actual values, you MUST search for wrapper function calls
     - TRIGGER PATTERNS: Look for these patterns that indicate wrapper functions:
       * HTTP: `axios.get(url, config)`, `fetch(endpoint)`, `requests.get(api_url)`
       * Queue: `channel.sendToQueue(queueName, message)`, `producer.send(topic, data)`, `publisher.publish(queue, msg)`
       * Socket: `socket.emit(eventName, data)`, `io.emit(event, payload)`, `ws.send(channel, message)`
       * Database: `db.query(tableName, conditions)`, `collection.find(query)`, `model.create(data)`

     - MANDATORY WORKFLOW FOR VARIABLE PARAMETERS:
       1. DETECT: Found connection code with variable parameters (not hardcoded values)
       2. READ FILE: Use database tool to read the complete file containing this code
       3. IDENTIFY: Find the wrapper function name that contains this connection code
       4. SEARCH USAGE: Create search_keyword task to find ALL calls to this wrapper function across the codebase
       5. COLLECT: Gather all wrapper function calls with actual parameter values

     - EXAMPLE WORKFLOW:
       * Found: `this.channel.sendToQueue(queueName, Buffer.from(message))` (variable queueName)
       * Action: Read complete file to find wrapper function name (e.g., `publishMessage`)
       * Search: Create task "Use search_keyword to find publishMessage usage: publishMessage\\("
       * Result: Find calls like `publishMessage('user-notifications', data)`, `publishMessage('email-queue', emailData)`

     - CRITICAL: DO NOT move to next task when you find variable parameters - you MUST search for actual usage sites
     - CREATE TASKS for ALL wrapper functions with variable parameters: "Use search_keyword to find [functionName] usage patterns: [functionName]\\("
     - NEVER accept variable names as final connection data - always search for the actual values passed to wrapper functions

11. TASK CREATION WITHIN IMPLEMENTATION DISCOVERY:
     - MANDATORY THINKING PROCESS: Before proceeding, ask these specific questions:
       1. "Did I find connection code with VARIABLE NAMES instead of actual values?" (queueName, endpoint, url, topic, eventName, etc.)
       2. "Are these variables being passed as parameters to a function?" (indicating wrapper function usage)
       3. "Do I need to search for where this wrapper function is called with real values?"
       4. "Have I already found the actual usage sites with hardcoded connection details?"

     - CREATE TASKS IMMEDIATELY when you find:
       * Connection code with variable parameters: `sendToQueue(queueName, message)` → Search for wrapper function calls
       * Environment variables in connection code: `process.env.API_URL` → Search for config files
       * Dynamic endpoints/topics/events: `axios.get(url)` → Search for wrapper function calls with actual URLs
       * Custom wrapper classes: `apiClient.makeRequest(endpoint)` → Search for all method calls

     - DON'T CREATE TASKS when you find:
       * Hardcoded connection details: `axios.get('https://api.example.com/users')` → This IS the actual connection
       * Direct usage with real values: `socket.emit('user-joined', data)` → This IS the actual usage
       * Configuration objects with fixed values: `{ baseURL: 'https://api.service.com' }` → This IS the actual config

     - TASK CREATION EXAMPLES:
       * Found: `channel.sendToQueue(queueName, Buffer.from(message))` → CREATE: "Use search_keyword to find wrapper function calls with actual queue names"
       * Found: `axios.get(process.env.API_BASE_URL + endpoint)` → CREATE: "Use list_files to find .env files and search for API_BASE_URL configuration"
       * Found: `socket.emit(eventName, eventData)` → CREATE: "Use search_keyword to find wrapper function calls with actual event names"

12. ENVIRONMENT VARIABLE AND CONFIG FILE ANALYSIS RULES - MANDATORY EXECUTION:
    - TRIGGER: When you see process.env.API_URL, process.env.DATABASE_URL, config.endpoint, or any environment/config variable in connection code
    - STEP 1: ALWAYS CHECK SUTRA MEMORY FIRST - review if .env, config files, or environment setup files are already tracked
    - STEP 2: If NOT in sutra memory → IMMEDIATELY CREATE TASK: "Use list_files to find config files (.env, config.*, docker-compose.yml, etc.) then use database tool to analyze them"
    - STEP 3: If already in sutra memory → Use existing tracked data, no new task needed
    - MANDATORY: You CANNOT skip environment variable resolution - it's required for complete connection analysis
    - EXAMPLES OF TRIGGERS: process.env.DISCOVERY_SERVER_URL, process.env.DATA_LAYER_URL, config.apiBaseUrl, process.env.API_BASE_URL

13. EXCLUSION CRITERIA:
    - Skip generic function definitions without actual usage or real parameters
    - Ignore configuration references that don't send/receive data between services
    - Exclude test code, mock implementations, and development debugging code
    - Skip infrastructure connections that don't represent service-to-service communication

14. ADAPTIVE ANALYSIS STRATEGY:
    - Analyze connection patterns based on what was actually found in import pattern discovery
    - Focus on technologies and packages that exist in the project
    - Don't search for patterns from packages that weren't found in previous phases
    - Prioritize actual usage over theoretical connection possibilities

15. JSON FORMAT SPECIFICATION:
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

16. COMPLETION REQUIREMENT: When implementation discovery is complete, you MUST use the `attempt_completion` tool with a summary of discovered connection implementations.
"#
