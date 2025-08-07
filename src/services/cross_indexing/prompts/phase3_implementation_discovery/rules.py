"""
Implementation Discovery Rules

Core rules and constraints for effective implementation discovery.
"""

IMPLEMENTATION_DISCOVERY_RULES = """====

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

10. WRAPPER FUNCTION ANALYSIS RULES:
    - CRITICAL: When you find wrapper functions with dynamic parameters (like url, endpoint, method variables), you MUST analyze the complete file first to find the function name
    - MANDATORY WORKFLOW: Found wrapper function → Read entire file with database tool → Identify function name → Create search_keyword task to find all calls with actual values
    - EXAMPLE: If you see `axios.get(url, config)` inside a function, you must find what that function is called (e.g., `apiCallFunction`) then search for `apiCallFunction\\(` to find real usage
    - DO NOT move to next task when wrapper functions have dynamic parameters - you must find actual usage sites with real endpoint values
    - CREATE TASKS for wrapper functions with dynamic parameters: "Use search_keyword to find [functionName] usage patterns: [functionName]\\("
    - Use generic function names in examples like `apiCallFunction()`, `makeRequest()`, `sendData()` - avoid specific domain references

11. TASK CREATION WITHIN IMPLEMENTATION DISCOVERY:
    - ALWAYS THINK BEFORE CREATING TASKS: Ask yourself "Do I need to search further for actual usage?"
    - Can create additional tasks for further searching within current analysis when discovering new patterns
    - CREATE TASKS for wrapper functions with dynamic parameters to find all usage sites with real values
    - DON'T CREATE TASKS when you already found actual usage sites with real endpoint/parameter values
    - DON'T CREATE TASKS for wrapper functions with hardcoded endpoints (the connection info is already visible)
    - Create tasks for environment variable resolution with complete tool guidance
    - Add tasks for complex connection patterns requiring deeper analysis with proper tool parameters

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

15. COMPLETION REQUIREMENT: When implementation discovery is complete, you MUST use the `attempt_completion` tool with a summary of discovered connection implementations.
"""
