template_string Rules_Phase3() #"
====

RULES

1. Focus EXCLUSIVELY on ACTUAL DATA COMMUNICATION CODE that sends/receives data between different services.

2. CRITICAL SCOPE: Find code that actively transmits or receives data (sends messages, makes API calls, publishes to queues, consumes from queues, receives responses) with real parameters.

3. TASK EXECUTION METHODOLOGY:
  - Execute pending tasks from previous import analysis one by one systematically
  - Use tool selection guidance provided in tasks (database vs search_keyword)
  - Process all previous import analysis tasks before creating additional tasks
  - Handle different connection types and languages appropriately
  - MANDATORY: When you find environment variables in connection code, IMMEDIATELY check sutra memory and create config file search tasks if needed

4. LIST_FILES TASK HANDLING:
  - If you see task like: "No packages/dependencies found in previous analysis. Use list_files tool to list all files recursively in current directory to identify files that might contain connection code."
  - Execute list_files tool to discover all files in the project
  - After getting results, create individual database tool tasks for each file that might contain connection code
  - Create separate database task for each identified potential connection file

5. DATA COMMUNICATION CODE REQUIREMENTS:
  - Find actual data transmission and reception code: API calls, queue sends/consumes, event emits/listens with real parameters
  - Include environment variable values and their resolved configurations
  - Find code that actively sends/receives data between services with real values

6. TOOL SELECTION STRATEGY:
  - Few files (3-5 files with imports): Use database tool to read entire file content for comprehensive analysis
  - Many files (6+ files): Use search_keyword with targeted patterns based on actual imports
  - Wrapper functions: Always use search_keyword to find usage sites across entire codebase
  - Built-in patterns: Use search_keyword for language built-ins that don't require imports

7. DATA COMMUNICATION ANALYSIS PRIORITIES:
  - Find actual data transmission and reception calls with real parameters and endpoint information
  - Include environment variable usage and resolved values when available
  - Find wrapper function calls with actual parameters, not wrapper function definitions
  - Focus on active data communication that shows service-to-service data transfer

8. ACTUAL DATA COMMUNICATION EXAMPLES (FIND THESE):
  - HTTP calls: `const response = await axios.get(\`${process.env.API_BASE_URL}/users/${userId}\`)` with real endpoints
  - Queue operations: `channel.basic_publish(exchange='', routing_key='notifications', body=json.dumps(data))` and `channel.basic_consume(queue='events', on_message_callback=callback)` with real queue names
  - Queue operations: `ch.Publish("", "order-processing", false, false, amqp.Publishing{Body: messageBody})` and `msgs, err := ch.Consume("events", "", true, false, false, false, nil)` with real queue names

9. CONNECTION SETUP CODE (DON'T FOCUS ON THESE):
  - Connection establishment: `const connection = amqp.connect(process.env.URL)` without data transmission
  - Client creation: `session = requests.Session()` without actual requests
  - Connection establishment: `ConnectionFactory factory = new ConnectionFactory(); Connection connection = factory.newConnection()` without data transmission
  - Connection establishment: `conn, err := amqp.Dial(rabbitURL)` without data transmission

10. CRITICAL: CONNECTION ESTABLISHMENT TRIGGERS FURTHER ANALYSIS
  When you find connection establishment code (like `const connection = amqp.connect(url)`), this is NOT the final result:
  - MANDATORY: Read the entire file containing connection establishment using database tool
  - SEARCH FOR: Actual usage of that connection object for data transmission and reception
  - FIND: Queue operations, channel methods, data sends/receives using the established connection
  - EXAMPLE: Found `const connection = amqp.connect(url)` → Must find `connection.createChannel()`, `channel.sendToQueue()`, `channel.consume()`, etc.

11. BUILT-IN LANGUAGE PATTERNS (NO IMPORTS REQUIRED):
  - For Example:
    - JavaScript: Native `fetch()` API, `XMLHttpRequest`, `WebSocket` constructor
    - Python: Built-in `urllib.request`, `http.client`, `socket` module
    - Java: Built-in `java.net.HttpURLConnection`, `java.net.Socket`
  - These patterns should be analyzed alongside imported package usage when relevant

12. WRAPPER FUNCTION ANALYSIS RULES - MANDATORY EXECUTION:
  - CRITICAL DETECTION: When you find ANY connection code with VARIABLE/PARAMETER names instead of actual values, you MUST search for wrapper function calls
  - TRIGGER PATTERNS Examples: Look for these type of patterns that indicate wrapper functions:
    * JavaScript: `axios.get(url, config)`, `socket.emit(eventName, data)`, `channel.sendToQueue(queueName, message)`
    * Python: `requests.get(api_url)`, `channel.basic_publish(routing_key=queue_name, body=data)`, `socket.send(message)`
    * Java: `restTemplate.getForObject(endpoint, ResponseClass.class)`, `rabbitTemplate.convertAndSend(queueName, message)`
    * Go: `http.Get(apiUrl)`, `ch.Publish("", queueName, false, false, amqp.Publishing{Body: data})`

  - MANDATORY WORKFLOW FOR VARIABLE PARAMETERS:
    1. DETECT: Found connection code with variable parameters (not hardcoded values)
    2. READ FILE: Use database tool to read the complete file containing this code
    3. IDENTIFY: Find the wrapper function name that contains this connection code
    4. SEARCH USAGE: Create search_keyword task to find ALL calls to this wrapper function across the codebase
    5. COLLECT: Gather all wrapper function calls with actual parameter values

  - EXAMPLE WORKFLOW:
    * Found: `this.channel.sendToQueue(queueName, Buffer.from(message))` (variable queueName)
    * Action: Read complete file to find wrapper function name (e.g., `publishMessage`)
    * Search: Create task "Use search_keyword to find publishMessage usage: publishMessage\("
    * Result: Find calls like `publishMessage('user-notifications', data)`, `publishMessage('email-queue', emailData)`

  - CRITICAL: DO NOT move to next task when you find variable parameters - you MUST search for actual usage sites
  - CREATE TASKS for ALL wrapper functions with variable parameters: "Use search_keyword to find [functionName] usage patterns: [functionName]\("
  - NEVER accept variable names as final connection data - always search for the actual values passed to wrapper functions

13. TASK CREATION WITHIN IMPLEMENTATION DISCOVERY:
  - MANDATORY THINKING PROCESS Examples: Before proceeding, ask these specific questions:
    1. "Did I find connection code with VARIABLE NAMES instead of actual values?" (queueName, endpoint, url, topic, eventName, etc.)
    2. "Are these variables being passed as parameters to a function?" (indicating wrapper function usage)
    3. "Do I need to search for where this wrapper function is called with real values?"
    4. "Have I already found the actual usage sites with hardcoded connection details?"

  - CREATE TASKS IMMEDIATELY when you find (Examples):
    * Connection code with variable parameters: `sendToQueue(queueName, message)` → Search for wrapper function calls
    * Coonection with environment variables in connection code: `process.env.API_URL` → Search for config files
    * Dynamic endpoints/topics/events: `axios.get(url)` → Search for wrapper function calls with actual URLs
    * Custom wrapper classes: `apiClient.makeRequest(endpoint)` → Search for all method calls
    * Wrapper fuctions with variable parameters: sendToUserQueue(eventName, data) → search for this eventName value (e.g., First search in same file using search keyword if it is variable and not in sutra memory, then create task to search in entire codebase)

  - DON'T CREATE TASKS when you find (Examples):
    * Hardcoded connection details: `axios.get('https://api.example.com/users')` → This IS the actual connection
    * Direct usage with real values: `socket.emit('user-joined', data)` → This IS the actual usage
    * Configuration objects with fixed values: `{ baseURL: 'https://api.service.com' }` → This IS the actual config

  - TASK CREATION EXAMPLES:
    * Found: `channel.sendToQueue(queueName, Buffer.from(message))` → CREATE: "Use search_keyword to find wrapper function calls with actual queue names"
    * Found: `axios.get(process.env.API_BASE_URL + endpoint)` → CREATE: "Use list_files to find .env files and search for API_BASE_URL configuration"
    * Found: `socket.emit(eventName, eventData)` → CREATE: "Use search_keyword to find wrapper function calls with actual event names"

14. ENVIRONMENT VARIABLE AND CONFIG FILE ANALYSIS RULES - MANDATORY EXECUTION:
  - TRIGGER: When you see process.env.API_URL, process.env.DATABASE_URL, config.endpoint, or any environment/config variable in connection code
  - STEP 1: ALWAYS CHECK SUTRA MEMORY FIRST - review if .env, config files, or environment setup files are already tracked
  - STEP 2: If NOT in sutra memory → IMMEDIATELY CREATE TASK: "Use list_files to find config files (.env, config.*, docker-compose.yml, etc.) then use database tool to analyze them"
  - STEP 3: If already in sutra memory → Use existing tracked data, no new task needed
  - MANDATORY: You CANNOT skip environment variable resolution - it's required for complete connection analysis
  - EXAMPLES OF TRIGGERS: process.env.SERVER_URL, process.env.SERVICE_URL, config.apiBaseUrl, process.env.API_BASE_URL

15. WRAPPER FUNCTION / ENDPOINT WITH VARIABLE PARAMETERS EXAMPLES:
  - Variable Search Strategy (use `thinking` field to think through steps):
    * If variable not in sutra memory → First search within current file using search_keyword
    * If not found in current file → Create task to search entire codebase for variable usage
    * If found variable is environment variable → Check sutra memory for existing tracking
    * If environment variable not tracked → Create task to find environment files (.env, config files, etc.)
  - WebSocket: sendToSocket(eventName, data) → wrapper function with variable eventName → search for actual event names
  - HTTP: makeApiCall(url, method, data) → wrapper function with variable url → search for actual URLs
  - Queue: publishMessage(queueName, message) → wrapper function with variable queueName → search for actual queue names

16. EXCLUSION CRITERIA:
  - Skip generic function definitions without actual usage or real parameters
  - Ignore configuration references that don't send/receive data between services
  - Exclude test code, mock implementations, and development debugging code
  - Skip infrastructure connections that don't represent service-to-service communication

17. ADAPTIVE ANALYSIS STRATEGY:
  - Analyze connection patterns based on what was actually found in import pattern discovery
  - Focus on technologies and packages that exist in the project
  - Don't search for patterns from packages that weren't found in previous phases
  - Prioritize actual usage over theoretical connection possibilities

18. JSON FORMAT SPECIFICATION:
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
  - The `thinking` field MUST contain detailed reasoning and step-by-step analysis including:
    * What type of connection code was found and its characteristics
    * Which specific rules and cases apply to the current situation
    * Why certain tasks were created or not created (with rule references)
    * What to search for next and the reasoning behind the search strategy
    * Whether additional information is needed for complete connection analysis
    * Assessment of whether wrapper functions or environment variables require further investigation
    * Evaluation of whether the found connection code represents actual usage or just definitions
  - The `tool_call` field contains the tool to execute with proper parameters
  - The `sutra_memory` field MUST use nested structure as shown above
  - Task operations MUST include all required fields: `action`, `id`, `description`
  - For move operations: MUST include both `from_status` and `to_status`
  - For add operations: MUST include `to_status` (pending/current/completed)
  - The `add_history` field is MANDATORY in every sutra_memory response
  - Task IDs MUST be strings, not integers
  - All enum values MUST use lowercase aliases: "add", "move", "remove", "pending", "current", "completed"

19. COMPLETION REQUIREMENT: When implementation discovery is complete, you MUST use the `attempt_completion` tool with a summary of discovered connection implementations.
"#
