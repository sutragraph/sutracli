"""
Tool Usage Examples for Cross-Indexing

This module provides comprehensive examples of how to use different tools
and how to include variable information from environment and config files.
"""

TOOL_USAGE_EXAMPLES = """====

TOOL USAGE EXAMPLES

This section provides comprehensive examples of how to use different tools effectively and how to include environment and configuration variable information in connection descriptions.

1. SEMANTIC SEARCH EXAMPLES

Use semantic_search for finding connection-related concepts:

Example 1: Finding API endpoints
- Query: "API endpoint implementation"
- Usage: When you found API framework packages in dependencies, search for API endpoint patterns
- Result: Finds route definitions, endpoint handlers, API middleware for user's own services

Example 2: Finding HTTP client calls
- Query: "HTTP client calls to services"
- Usage: When you found HTTP client packages in dependencies, search for HTTP client usage
- Result: Finds HTTP client calls to localhost, user domains, relative paths - excludes external APIs

Example 3: Finding WebSocket connections
- Query: "WebSocket connection setup"
- Usage: When you found WebSocket packages in dependencies, search for socket patterns
- Result: Finds WebSocket connections between user's own services, socket implementations

2. KEYWORD SEARCH EXAMPLES

Use search_keyword for specific patterns with regex and context:

Example 1: API endpoint patterns
- search_keyword("app\\.(get|post|put|delete|use)\\(|router\\.(get|post|put|delete|use)\\(", regex=true, after_lines=2)
- Purpose: Find Express route definitions with context
- Result: Captures route handlers with parameter and response context

Example 2: HTTP client patterns
- search_keyword("fetch\\(|http\\.get|HttpClient|requests\\.", regex=true, after_lines=2)
- Purpose: Find HTTP client calls with request details
- Result: Captures HTTP calls with URL, method, and data context

Example 3: WebSocket patterns
- search_keyword("WebSocket|socket\\.io|ws://|wss://|io\\(", regex=true, after_lines=2)
- Purpose: Find WebSocket connections with configuration
- Result: Captures socket connections with endpoint and auth context

Example 4: Message queue patterns
- search_keyword("publish|subscribe|queue|topic|amqp://", regex=true, after_lines=2)
- Purpose: Find message queue operations with queue details
- Result: Captures queue operations with queue names and message context

3. WRAPPER FUNCTION DISCOVERY EXAMPLES

Step-by-step approach for wrapper function analysis:

WHEN TO ANALYZE WRAPPER FUNCTIONS VS DIRECT CALLS:

PRIORITY RULE: Focus on CONNECTION IDENTIFIERS (endpoint names, queue names, socket event names), not data content.

CASE 1: DIRECT CALLS WITH LITERAL CONNECTION IDENTIFIERS (BEST - STORE IMMEDIATELY)
When connection identifiers are literal strings, store the call directly:
- `queue.consume("user-adding-queue", addUserHandler)` - STORE: queue name "user-adding-queue" is literal
- `socket.emit("user_status_update", userData)` - STORE: event name "user_status_update" is literal
- `app.get("/api/users", handler)` - STORE: endpoint "/api/users" is literal
- `makeApiCall("/admin/users", "POST", userData)` - STORE: endpoint "/admin/users" is literal

CASE 2: CALLS WITH VARIABLE CONNECTION IDENTIFIERS (ANALYZE WRAPPER FUNCTIONS)
When connection identifiers are variables, you must find wrapper function calls:
- `queue.consume(queueName, handler)` - ANALYZE: queueName is variable, find all wrapper calls
- `socket.emit(eventName, data)` - ANALYZE: eventName is variable, find all wrapper calls
- `app.get(routePath, handler)` - ANALYZE: routePath is variable, find all wrapper calls
- `makeApiCall(endpoint, method, data)` - ANALYZE: endpoint is variable, find all wrapper calls

Step 1: Identify if connection identifier is literal or variable
- LITERAL: "user-adding-queue", "/api/users", "user_status_update" - store immediately
- VARIABLE: queueName, endpoint, eventName - analyze wrapper functions

Step 2: For VARIABLE connection identifiers, find wrapper function calls
- search_keyword("makeApiCall\\(", regex=true, after_lines=2)
- Result: Find all places where wrapper function is called with actual connection identifiers
- Purpose: Get actual endpoints, queue names, event names used in real connections

Step 3: Store calls with actual connection identifiers
For each call site found:
- STORE: The function call with actual connection identifier like:
```
const result = await makeApiCall("/admin/users", "POST", requestData)
```
- FOCUS: Connection identifier "/admin/users" is the key information
- DESCRIBE: "API call for admin user management using endpoint '/admin/users' with POST method"
- Extract actual connection identifiers (real endpoints like "/admin/users", queue names like "user-notifications")
- Identify variable sources for connection identifiers when they use environment variables
- Purpose: Store actual connection identifiers, not generic variable-based calls

4. ENVIRONMENT VARIABLE INTEGRATION EXAMPLES

How to include environment and configuration variable information in descriptions and focus on actual function calls:

Priority: Store higher-level wrapper function calls, not base library calls

Critical rule: When both wrapper function calls and base library calls exist, always prioritize the wrapper function calls because they contain the actual endpoints and business logic. This applies to HTTP wrappers, socket wrappers, queue wrappers, and any service communication wrappers.

Example 1: Direct call with LITERAL connection identifier (BEST - STORE IMMEDIATELY)
- Code: `queue.consume("user-adding-queue", addUserHandler)`
- Description: "Queue consumer for user addition using queue name 'user-adding-queue'"
- Why store: Queue name "user-adding-queue" is literal string - no need to analyze wrapper functions

Example 2: Direct call with LITERAL connection identifier (BEST - STORE IMMEDIATELY)
- Code: `socket.emit("user_status_update", statusData)`
- Description: "Socket event emission for user status updates using event name 'user_status_update'"
- Why store: Event name "user_status_update" is literal string - store directly

Example 3: Direct call with LITERAL connection identifier (BEST - STORE IMMEDIATELY)
- Code: `app.get("/api/users", getUsersHandler)`
- Description: "API endpoint for user retrieval using endpoint '/api/users' with GET method"
- Why store: Endpoint "/api/users" is literal string - store directly

Example 4: Wrapper call with VARIABLE connection identifier (ANALYZE WRAPPER FUNCTIONS)
- Code: `queue.consume(queueName, handler)`
- Description: "Queue consumer with variable queue name - must find wrapper function calls"
- Why analyze: queueName is variable - need to find actual queue names used

Example 5: Wrapper call with VARIABLE connection identifier (ANALYZE WRAPPER FUNCTIONS)
- Code: `makeApiCall(endpoint, "POST", userData)`
- Description: "API call with variable endpoint - must find wrapper function calls"
- Why analyze: endpoint is variable - need to find actual endpoints used

Example 6: Found wrapper function call with LITERAL connection identifier (STORE THIS)
- Code: `makeApiCall("/admin/users", "POST", userData)`
- Description: "API call for admin user management using endpoint '/admin/users' with POST method"
- Why store: Found actual endpoint "/admin/users" through wrapper function analysis

Example 5: Base HTTP library call inside wrapper function (BAD - DO NOT STORE THIS)
- Code: return (await axios.get(url, mergedConfig)).data;
- Why not store: This is internal implementation of wrapper function, doesn't show actual endpoints

Example 6: Wrapper function definition (BAD - DO NOT STORE THIS)
- Code: function apiCallFunction(endpoint, method, data) { return axios[method.toLowerCase()](baseUrl + endpoint, data); }
- Why not store: This is generic wrapper definition, doesn't show actual endpoints being called

Example 7: Variable assignment (BAD - DO NOT STORE THIS)
- Code: const apiUrl = process.env.API_URL || 'http://localhost:3000'
- Why not store: This is just variable assignment, not an actual API call

5. ENVIRONMENT VARIABLE RESOLUTION WORKFLOW

Step 1: Find actual function calls (not definitions)
Step 2: Identify environment variables used in the calls
Step 3: Search for .env files, config files, or variable definitions and store into sutra memory
Step 4: Include both variable name and resolved value in description
Step 5: Store the actual call line with comprehensive description

6. VARIABLE RESOLUTION EXAMPLES

CRITICAL: FOCUS ON ACTUAL CALLS, NOT VARIABLE DEFINITIONS

WHY RESOLVE VARIABLES:
Variables in code often contain the actual connection endpoints and configuration. We need to resolve them because:
- Code might use `const API_URL = process.env.BASE_URL + '/api'` instead of hardcoded URLs
- Environment variables contain the real endpoints like `process.env.USER_SERVICE_URL = "http://localhost:3001"`
- Configuration files store actual queue names, service URLs, and connection details
- Without resolution, we only see variable names, not the actual connection information needed for matching

ENVIRONMENT VARIABLE SEARCH STRATEGY

When you find process.env.API_BASE_URL in code, search for:
- Variable definitions: `search_keyword("API_BASE_URL=")`
- Variable usage: `search_keyword("API_BASE_URL")`
- Use list_files to find .env files and config files

Common environment variable patterns to search for:
- `search_keyword("process\\.env\\.[A-Z_]+", regex=true)` - find all env var usage in code
- Use list_files to find environment files (.env, .env.local, etc.)
- Use list_files to find config files (config.js, config.json, config.yaml)

ACTUAL CALL EXAMPLES WITH RESOLVED VARIABLES

Example 1: Direct axios call (STORE THIS)
- Code: const response = await axios.get(`${process.env.API_BASE_URL}update/data`)
- Environment file (.env): API_BASE_URL=http://localhost:3001/
- Description: "HTTP GET call for initial data retrieval using environment variable API_BASE_URL"

Example 2: Direct fetch with path construction (STORE THIS)
- Code: const response = await fetch(path.join(process.env.SERVICE_URL, `/api/users/${userId}`))
- Environment file (.env): SERVICE_URL=http://localhost:3002
- Description: "HTTP GET call for user data using environment variable SERVICE_URL with dynamic userId parameter"

Example 3: Variable assignment (DO NOT STORE THIS)
- Code: const apiUrl = process.env.API_URL || 'http://localhost:3000'
- Why not store: This is just variable assignment, not an actual API call

Example 4: Actual call using resolved variable (STORE THIS)
- Code: const result = await fetch(apiUrl + '/data', { method: 'POST', body: payload })
- Environment: process.env.API_URL = "http://user-service:3000"
- Description: "HTTP POST call for data submission using environment variable API_URL"

7. COMPREHENSIVE DESCRIPTION TEMPLATE

TEMPLATE FOR ACTUAL FUNCTION CALLS (NOT WRAPPER DEFINITIONS)

Template for direct API calls:
"[HTTP method] call to [service_name] using environment variable [env_var] configured as [actual_value] for endpoint [endpoint_path] for [purpose]"

Template for wrapper function calls:
"[Connection type] using [wrapper_function] with endpoint [actual_endpoint], method [actual_method], environment variable [env_var] configured as [actual_value] for [purpose]"

GOOD EXAMPLES - PRIORITIZE WRAPPER FUNCTION CALLS WITH ACTUAL VALUES

Example 1: Complete socket wrapper function call with environment variable context (BEST)
- Code:
```
await emitToSocket('room_update', roomData, {
  namespace: process.env.SOCKET_NAMESPACE,
  room: `interview_${interviewId}`,
  broadcast: true,
  acknowledgment: true,
  timeout: 8000
})
```
- Environment: SOCKET_NAMESPACE=/interviews
- Result: "Socket event emission for room updates using event name 'room_update', roomData contains interview room information, environment variable SOCKET_NAMESPACE configured as '/interviews', broadcast to interview room, acknowledgment required with 8 second timeout"

Example 2: Complete queue consumer wrapper function call with multiple parameters (BEST)
- Code:
```
await consumeMessages('job_applications', processApplicationHandler, {
  queueUrl: process.env.JOB_QUEUE_URL,
  concurrency: 5,
  prefetch: 15,
  autoAck: false,
  retryAttempts: 3,
  deadLetterQueue: 'failed_applications'
})
```
- Environment: JOB_QUEUE_URL=amqp://localhost:5672/jobs
- Result: "Queue consumer setup for job applications using queue name 'job_applications', processApplicationHandler function processes messages, environment variable JOB_QUEUE_URL configured as 'amqp://localhost:5672/jobs', 5 concurrent workers, prefetch 15 messages, manual acknowledgment with 3 retry attempts and dead letter queue 'failed_applications'"

Example 3: Complete API wrapper function call (BEST)
- Code:
```
const result = await makeApiCall('/candidate/profile', candidateId, 'GET', {
  baseURL: process.env.CANDIDATE_API_URL,
  headers: { 'Authorization': `Bearer ${token}` },
  params: { includeSkills: true, includeHistory: true },
  timeout: 12000
})
```
- Environment: CANDIDATE_API_URL=http://localhost:3004
- Result: "API call for candidate profile retrieval using endpoint '/candidate/profile' with candidateId parameter, GET method, environment variable CANDIDATE_API_URL configured as 'http://localhost:3004', includes skills and history data, bearer token authorization, 12 second timeout"

Example 4: Complete direct axios call with environment variable context (ONLY IF NO WRAPPER EXISTS)
- Code:
```
const response = await axios.get(`${process.env.API_BASE_URL}/update/data`, {
  params: { companyId, format: 'json' },
  headers: { 'Authorization': `Bearer ${authToken}` },
  timeout: 5000
})
```
- Environment: API_BASE_URL=http://localhost:3001
- Result: "HTTP GET call for initial data retrieval using endpoint '/update/data' with environment variable API_BASE_URL configured as 'http://localhost:3001', companyId parameter, JSON format, bearer token authorization, 5 second timeout"

Example 5: Complete direct API call without environment variables (ONLY IF NO WRAPPER EXISTS)
- Code:
```
const response = await axios.post('/api/users', userData, {
  headers: { 'Content-Type': 'application/json' },
  validateStatus: (status) => status < 500
})
```
- Result: "HTTP POST call for user creation using endpoint '/api/users', userData contains user registration form, JSON content type, accepts status codes below 500"

BAD EXAMPLES - DO NOT STORE THESE

Bad Example 1: Base HTTP library calls inside wrapper functions
- Code: return (await axios.get(url, mergedConfig)).data;
- Code: return (await axios.post(url, data, mergedConfig)).data;
- Why bad: These are internal implementation details, not the actual API calls with endpoints

Bad Example 2: Wrapper function definition
- Code: function apiCallFunction(endpoint, method, data) { ... }
- Why bad: Generic definition, no actual endpoints being called

Bad Example 3: Variable assignment
- Code: const endpointUrl = `${process.env.SERVER}path`
- Why bad: Just variable construction, not an actual API call

Bad Example 4: Import/require statements
- Code: const axios = require('axios');
- Why bad: Library imports are not connection points

Bad Example 5: Overly detailed description
- Description: "HTTP GET wrapper function using apiCallFunction for service communication with endpoint /update/data"
- Why bad: Wrapper function name and endpoint are already visible in code snippet

8. TOOL USAGE WORKFLOW

WHY THIS SYSTEMATIC APPROACH:
Cross-indexing requires finding actual connection points between services, not just code patterns. This systematic approach ensures we:
- Discover all connection technologies used in the project
- Find actual endpoints and data being sent/received
- Match incoming and outgoing connections accurately
- Don't miss connections hidden in wrapper functions or configuration

Systematic approach for connection discovery:

Project Structure Analysis
- Purpose: Understand the codebase organization to know where connections might be located
- Use list_files to explore directory structure
- Identify key directories (src/, routes/, api/, services/)
- Look for configuration files (package.json, .env, config/)

Dependency Analysis
- Purpose: Identify what connection technologies are actually used in the project
- Use database tool to examine dependency files (package.json, requirements.txt, etc.)
- Identify connection-related packages (HTTP clients, API frameworks, WebSocket libraries)
- Create specific search tasks based on found dependencies
- Why: Prevents searching for technologies not used in the project

Pattern Discovery
- Purpose: Find actual connection code in the project
- Use semantic_search for broad concept discovery
- Use search_keyword with regex for specific pattern matching
- Always use after_lines parameter to capture context
- Why: Gets the actual connection implementations, not just imports

Wrapper Function Analysis
- Purpose: Extract real connection details from abstracted code
- Search for wrapper function definitions first
- Then search for all calls to wrapper functions
- Extract actual parameter values from call sites
- Why: Wrapper functions hide the real endpoints - we need the call sites to see actual usage

Variable Resolution
- Purpose: Get actual connection endpoints and configuration
- Search for variable definitions and assignments
- Look for environment variable usage patterns
- Check configuration files for variable values
- Why: Variables contain the real URLs, queue names, and connection details needed for matching

Description Creation
- Purpose: Store connection information in a way that enables matching
- Include all variable information with actual values
- Add environment variable context with configured values
- Provide business context and calling function information
- Use the comprehensive description template
- Why: Rich descriptions help match incoming/outgoing connections accurately

Connection Storage
- Purpose: Build a complete map of service-to-service connections
- Store each connection separately with complete context
- Include file path, line numbers, and comprehensive descriptions
- Focus on call sites where actual values are passed
- Maintain generic patterns while providing specific context
- Why: Each connection point needs individual analysis for proper cross-indexing

This systematic approach ensures comprehensive connection discovery with complete variable context and environment information.

9. CRITICAL XML FORMATTING FOR SUTRA MEMORY

When storing connection information in sutra memory, follow these XML formatting rules to prevent parsing errors:

XML Character Escaping
- Replace & with &amp;
- Replace < with &lt;
- Replace > with &gt;
- Replace " with &quot;
- Replace ' with &apos;

Safe Description Format
- Use simple, plain text descriptions
- Avoid quotes, ampersands, and angle brackets
- Keep descriptions concise and clear
- Use underscores instead of spaces in technical terms

Example Safe Descriptions
- GOOD: "HTTP client wrapper function for API calls"
- BAD: "HTTP client wrapper function for 'API' calls & data processing"
- GOOD: "Message queue publisher using environment variable USER_QUEUE"
- BAD: "Message queue publisher using environment variable 'USER_QUEUE' configured as "user_processing_queue""

Variable Information Format
- Use plain text without special characters
- Describe variables without using quotes or complex punctuation
- Focus on functionality rather than exact syntax

This prevents XML parsing failures that can cause cross-indexing iterations to fail.

"""
