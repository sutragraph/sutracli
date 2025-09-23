template_string ConnectionSplittingPrompt() #"
You will receive connection data of cross-indexing analysis. Your task is to split this data into incoming and outgoing connections and return them in the required JSON format. Additionally, include a comprehensive top-level "summary" that thoroughly describes the project's purpose, functionality, and architecture based on the collected connections.

====

# CRITICAL RULE - ONE CONNECTION PER SNIPPET

MANDATORY: Each snippet entry must represent EXACTLY ONE connection. You are FORBIDDEN from grouping multiple connections together.

EXAMPLES OF FORBIDDEN GROUPING: (Avoid! Do Not use!)
  - "Incoming HTTP connection points for various endpoints"
  - "Outgoing HTTP connection points for several endpoints"
  - "Various incoming HTTP connection points"
  - "Multiple incoming HTTP connection points"
  - "Several outgoing HTTP connection points"
  - "Message handlers for incoming events including eventA, eventB, eventC"
  - "API endpoints including endpointX, endpointY, endpointZ"
  - "Multiple operations for data processing"
  - "Connection handlers including X, Y, Z"
  - "40+ REST API endpoints including /get-speech-token, /get-custom-token, /check-room"
  - "REST API endpoints for incoming connections - includes 45+ admin, internal, super-admin"
  - "Comprehensive incoming HTTP connection points"
  - Any description mentioning "multiple", "including", "various" , "several", numbers like "40+", "45+"
  - "Never combine multiple connections into one snippet even if they are similar"

**You are ABSOLUTELY FORBIDDEN from creating ANY description that mentions more than ONE connection, endpoint, route, or operation. Each JSON entry must describe EXACTLY ONE connection with EXACTLY ONE endpoint/route/operation.**

====

# OBJECTIVE

Process the collected connection data and categorize each connection as either incoming or outgoing, then return structured JSON with complete connection details. Each connection must be a separate entry with its own specific line numbers and description.

====

# TECHNOLOGY TYPE CLASSIFICATION

## MANDATORY TECHNOLOGY TYPES
You MUST classify each connection using ONLY one of these exact technology type names:

1. HTTP/HTTPS - HTTP/HTTPS REST API calls and endpoints
  - Any HTTP/HTTPS client library or REST API framework should use this type
  - Examples: axios, fetch, requests, superagent, got, node-fetch, Express routes, Flask routes, FastAPI endpoints

2. WebSockets - WebSocket connections for real-time bidirectional communication
  - Any WebSocket library or real-time bidirectional connection should use this type
  - Examples: socket.io, ws, websocket-client, Socket.IO-client, webrtc

3. gRPC - Google RPC framework for high-performance RPC
  - Any gRPC implementation or protobuf-based RPC should use this type
  - Examples: @grpc/grpc-js, grpcio, grpc-web

4. GraphQL - Query language for APIs
  - Any GraphQL client or server implementation should use this type
  - Examples: apollo-client, graphql-request, urql, relay

5. MessageQueue - Message queuing systems
  - Any message queue, job queue, or task queue system should use this type
  - Examples: amqplib (RabbitMQ), kafkajs (Kafka), bull (Redis queues), sqs (AWS SQS), pub/sub

6. Unknown - Use ONLY when technology type cannot be identified from code
  - IMPORTANT: This is a last resort. Only use when absolutely no other type fits.
  - Do NOT use for unclear code - make your best assessment based on context.

## CONNECTION CLASSIFICATION
### INCOMING CONNECTIONS
Connections where OTHER services connect TO this service:
Examples:
  - API endpoints and route handlers (Express routes, Flask routes, etc.)
  - WebSocket server endpoints that accept connections
  - Message queue consumers that receive messages

### OUTGOING CONNECTIONS
Connections where THIS service connects TO other services
Examples:
  - HTTP client calls (axios, fetch, requests, etc.)
  - WebSocket client connections to other services
  - Message queue producers that send messages

====

# PROCESSING RULES

1. STRICT ONE-TO-ONE MAPPING: Analyze each connection individually - never group multiple connections

2. INDIVIDUAL ENTRIES ONLY: Create separate entries - If you find code with multiple operations, create separate entries for each

3. PRECISE LINE NUMBERS: Extract individual details - Each entry gets its own specific line numbers (single line "23-23" or very small ranges "23-25" for one logical connection only)

4. SINGLE CONNECTION FOCUS: Focus on data transmission - Only code that sends or receives data (exclude setup and configuration)

5. Include only actual data transmission operations:
  - Message publishing/producing (publish, send, sendToQueue, produce)
  - Message consuming/processing (consume, process, subscribe, on('message'))
  - HTTP requests (axios.get, axios.post, fetch, request calls)
  - HTTP route handlers (app.get, router.post, endpoint definitions)
  - WebSocket data transmission (socket.emit, ws.send)
  - WebSocket event handlers (socket.on, ws.on('message'))

6. EXCLUDE SETUP CODE: Do not include connection setup, configuration, or infrastructure setup:
  - Connection creation (amqp.connect, axios.create, new Server, io.connect)
  - Event listeners for connection state (on('connect'), on('disconnect'), on('error'))
  - Channel/queue/exchange setup (createChannel, assertQueue, assertExchange, bindQueue)
  - Configuration objects and initialization code

7. COMPLETE PARAMETER DETAILS: Include complete parameter details:
  - Exact endpoints, event names, queue names, method names
  - Protocols, methods, parameters
  - Environment variables and their resolved values in descriptions using format ENV_VAR=actual_value
  - Variable names resolved to their actual values from same file definitions
  - File paths and line numbers

8. CORRECT DIRECTION: Classify direction correctly based on data flow

9. NO DUPLICATES: No duplicates - each data transmission operation must be unique

10. NO REPEATED CONTENT: CRITICAL: IGNORE REPEATING CONTENT - If you see the same file code with the same lines appearing multiple times in the input, include it only ONCE in your response. Same lines from same files are allowed only one time in splitting.

11. ENVIRONMENT RESOLUTION: ENVIRONMENT FILE CODE RESOLUTION - If environment file code is provided as a code block, look for env var/config values and include them in connection descriptions for better context

12. VARIABLE RESOLUTION: CRITICAL - If any endpoint is having variable value, look for same file path code snippet which has defined value of that variable and resolve in template by mentioning that actual value in description of the code snippet. If that variable's assigned value is also an env variable, then look for env file if it is in code snippets. Final target of phase 4 is to have static value of any variable used in endpoint from which it can be used to send or receive values using that identifier or name.

13. FORBIDDEN LANGUAGE: Never use words like "multiple", "including", "various", "several", "comprehensive", numbers with "+" (like "40+", "45+"), "operations for", "endpoints for"

====

# ENVIRONMENT FILE CODE RESOLUTION

When environment file code blocks are provided in the input (e.g., .env files, config files), use them to resolve environment variables in connection descriptions:

1. IDENTIFY ENV FILES: Look for code blocks that contain environment variable definitions (KEY=value format)
2. RESOLVE VARIABLES: When connection code uses environment variables (process.env.VAR_NAME, os.environ['VAR_NAME'], etc.), find the corresponding value from env file code blocks
3. ENHANCE DESCRIPTIONS: Include resolved values in connection descriptions using format: ENV_VAR=actual_value
4. PROVIDE CONTEXT: This gives better context for later users understanding the actual connection endpoints, queue names, etc.

## EXAMPLE OF ENV RESOLUTION:
If you find connection code:
```
./src/queue/consumer.js:
  20 |     queue.consume(process.env.USER_ADD_QUEUE, handler)
```

And env file code block contains:
```
./.env:
  5 |     USER_ADD_QUEUE="user-add"
  6 |     NOTIFICATION_QUEUE="notifications"
```

Then description should be:
```
"Message queue consumer for USER_ADD_QUEUE=user-add queue"
```

### EXAMPLE OF VARIABLE RESOLUTION IN SAME FILE:
If you find connection code:
```
./src/consumer/DataProcessor/index.js:
  36 | await consumePacketsWithRetries(channel, queueName, dataHandler);
```

And same file code block contains variable definition:
```
./src/consumer/DataProcessor/index.js:
  20 | const queueName = process.env.DATA_PROCESSING_QUEUE;
```

And env file code block contains:
```
./.env:
  15 | DATA_PROCESSING_QUEUE="data-processing"
```

Then description should be:
```
"Message queue consumer using queueName variable resolved to DATA_PROCESSING_QUEUE=data-processing queue"
```

## VARIABLE RESOLUTION WORKFLOW

### STEP-BY-STEP VARIABLE RESOLUTION PROCESS:
1. IDENTIFY VARIABLES IN CONNECTION CODE: Look for connection operations using variables instead of hardcoded values
  - Examples: `queueName`, `endpoint`, `apiUrl`, `eventName`, `topicName`
  - Pattern: `sendToQueue(queueName, message)`, `axios.get(url)`, `socket.emit(eventName, data)`

2. SEARCH SAME FILE FOR VARIABLE DEFINITION: Before creating additional tasks, check if variable is defined in the same file code snippets
  - Look for patterns like: `const queueName = ...`, `let endpoint = ...`, `var apiUrl = ...`
  - Check assignment statements: `queueName = process.env.QUEUE_NAME` or `queueName = "hardcoded-value"`

3. RESOLVE VARIABLE VALUE:
  - If hardcoded value found: Use that value directly in description
  - If environment variable found: Check if env variable already exists in sutra memory
    - If in memory: Use the stored value
    - If not in memory: Look for env file code blocks in current input
    - If env file available: Resolve and use the value
    - If env file not available: Note the unresolved env variable

4. CONNECTION DESCRIPTION: Include resolved values in format:
  - For hardcoded: `"using variableName resolved to actual-hardcoded-value"`
  - For env vars: `"using variableName resolved to ENV_VAR=actual-env-value"`
  - For unresolved: `"using variableName variable (unresolved)"`

### VARIABLE RESOLUTION EXAMPLES:
Case 1: Variable with Hardcoded Value
Connection Code:
```javascript
// Line 36: await publishMessage(queueName, messageData)
// Line 15: const queueName = "user-notifications"
```
Description: `"Message publishing using queueName variable resolved to user-notifications queue"`

Case 2: Variable with Environment Variable
Connection Code:
```python
# Line 42: producer.send(topic_name, event_data)
# Line 18: topic_name = os.environ.get('USER_EVENT_TOPIC')
```
With env file: `USER_EVENT_TOPIC=user-events`
Description: `"Message publishing using topic_name variable resolved to USER_EVENT_TOPIC=user-events topic"`

Case 3: Variable with Dynamic Construction
Connection Code:
```javascript
// Line 28: axios.get(`${baseUrl}/api/users`)
// Line 12: const baseUrl = process.env.API_BASE_URL || 'http://localhost:3000'
```
With env file: `API_BASE_URL=https://api.production.com`
Description: `"HTTP GET request using baseUrl variable resolved to API_BASE_URL=https://api.production.com/api/users endpoint"`

### EXAMPLE OF VARIABLE WITH HARDCODED VALUE:
If you find connection code:
```
./src/services/api.py:
  45 | response = requests.get(f"{base_url}/users", headers=headers)
```

And same file code block contains variable definition:
```
./src/services/api.py:
  12 | base_url = "https://api.production.com"
```

Then description should be:
```
"HTTP GET request using base_url variable resolved to https://api.production.com/users endpoint"
```

### EXAMPLE OF INCOMPLETE CODE SNIPPET HANDLING
CRITICAL SCENARIO: When search_keyword finds incomplete connection code that appears truncated, you must intelligently expand the line range to capture the complete connection context.

Example 1: Incomplete HTTP Client Call (Java Spring)
Search Result (Lines 15-17):
```java
15 |   ResponseEntity<String> response = restTemplate.exchange(
16 |     UriComponentsBuilder.fromHttpUrl(
17 |       configService.getBaseUrl()
```

PROBLEM: Missing complete endpoint path, HTTP method, and request configuration
SOLUTION: Extend to lines 15-22 to capture complete connection:
```java
15 |   ResponseEntity<String> response = restTemplate.exchange(
16 |     UriComponentsBuilder.fromHttpUrl(
17 |       configService.getBaseUrl()
18 |     ).path("/api/user/profile/{userId}")
19 |     .buildAndExpand(userId).toUri(),
20 |     HttpMethod.GET,
21 |     httpEntity,
22 |     String.class);
```

Example 2: Incomplete Message Queue Producer (Java RabbitMQ)
Search Result (Lines 42-44):
```java
42 |   rabbitTemplate.convertAndSend(
43 |     exchangeConfig.getUserExchange(),
44 |     routingKeyBuilder.buildKey(
```

PROBLEM: Missing routing key completion and message payload
SOLUTION: Extend to lines 42-47 to capture complete message publishing:
```java
42 |   rabbitTemplate.convertAndSend(
43 |     exchangeConfig.getUserExchange(),
44 |     routingKeyBuilder.buildKey(
45 |       "user.profile.updated", userId
46 |     ),
47 |     userUpdateMessage);
```

EXTRACTION STRATEGY FOR INCOMPLETE SNIPPETS:
  - For HTTP calls: Extend until you capture method, complete URL/endpoint
  - For message queues: Extend until you capture exchange/queue name, routing key, and message payload structure
  - For WebSocket: Extend until you capture event type, recipient identification, and message content
  - General rule: Add 3-8 additional lines based on code complexity and nesting level

INTELLIGENT LINE EXTENSION GUIDELINES:
  - Simple method calls: +2-3 lines
  - Complex builder patterns: +4-6 lines
  - Nested configuration objects: +5-8 lines
  - Multi-parameter method calls: +3-5 lines
  - Always prefer capturing complete context over partial information

EXTRACT ALL connections found - no selective sampling allowed.

====

# GENERIC ANALYSIS INSTRUCTIONS

## FOR CONDITIONAL/SWITCH STATEMENTS:
If you find code with multiple branches handling different operations:
```
switch/if (condition) {
  case/condition A: { /* handler code */ }
  case/condition B: { /* handler code */ }
  case/condition C: { /* handler code */ }
}
```

You MUST create separate entries:
- One for operation A handler
- One for operation B handler
- One for operation C handler

## FOR MULTIPLE OPERATION DEFINITIONS:
If you find code defining multiple operations:
```
operation1(params);
operation2(params);
operation3(params);
```

You MUST create separate entries:
- One for operation1
- One for operation2
- One for operation3

## FOR ROUTER/HANDLER REGISTRATIONS:
If you find code registering multiple handlers:
```
register('/pathA', handlerA);
register('/pathB', handlerB);
register('/pathC', handlerC);
```

You MUST create separate entries for each registration.

====

# PROJECT SUMMARY GUIDELINES

Produce a concise, README-like project summary that an agent can rely on with high confidence without scanning other files. The summary MUST:

1. Technology inventory (explicit names)
  - Name concrete libraries/frameworks detected for each connection type, e.g., axios/requests/node-fetch (HTTP client), Express/FastAPI/Flask (HTTP server), amqplib/pika (RabbitMQ), kafkajs (Kafka), socket.io/ws (WebSockets), grpcio/@grpc/grpc-js (gRPC), apollo-client/server or graphql-request (GraphQL).
  - Prefer exact package names as they appear in code or dependency files.
  - Only assert technologies present in the provided input. Do not speculate.

2. API surface overview (no endpoint listing)
  - Do NOT list individual endpoints, routes, or event names.
  - Describe endpoint/event categories and capabilities instead, e.g., "User management CRUD endpoints", "Order lifecycle operations", "Admin/reporting endpoints".

3. Messaging/streaming overview
  - Identify queues/topics/streams by technology and purpose at a category level, e.g., "RabbitMQ queues for order processing and notifications". Avoid listing every queue; focus on roles/patterns.

4. Architecture and data flow
  - Summarize how components interact (HTTP in/out, MQ producers/consumers, WebSocket emits/handlers, gRPC, GraphQL) and where this project sits relative to others when discernible.

5. Wrappers and abstractions (when evident)
  - Identify helper/wrapper functions used to perform connections instead of direct library calls (e.g., makeApiCall, publishMessage, sendEvent).
  - Name the exact function(s) and describe their argument shape from code, e.g., makeApiCall(path, method, dataOrParams[, config]).
  - Note when wrappers encapsulate auth headers, base URLs, interceptors/retries, or service targeting (e.g., routes calls to order service).

6. Style
  - Plain text, compact, skimmable. Short paragraphs and clear noun phrases. No endpoint lists.

7. Auth/security (when evident)
  - State observed authentication methods (tokens, API keys, OAuth, cookies, headers) and where they apply.
  - When visible, specify exact header names and placement, e.g., Authorization: Bearer <token> on outbound HTTP/HTTPS requests.

8. High-certainty language
  - Use definitive language only for facts evidenced in code/snippets/configs here. Avoid guesses. If something cannot be confirmed, omit it instead of hedging.

9. Operational notes (when evident)
  - Include tracing/logging/metrics libraries, and error-handling/retry patterns that affect connections.

Example style: "This service exposes user and order workflows over HTTP using Express and the axios client, publishes order events to RabbitMQ via amqplib for asynchronous processing, and pushes live updates via Socket.IO. Configuration uses ENV vars such as API_BASE_URL and ORDER_QUEUE. Outbound HTTP requests include an Authorization: Bearer <token> header."

====

# OUTPUT FORMAT

## CHAIN OF THOUGHTS PROCESS

You MUST use a chain of thoughts approach embedded within JSON comments. While JSON does not traditionally support comments, we accept JSON with comments for this analysis process. Use // comments within the JSON structure to show your thinking process.

## UNIQUE KEYS REQUIREMENT

CRITICAL: All keys in the JSON must be unique. For the same technology type, group all file paths under one technology key. For the same file path within a technology type, group all connections under one file path key.

## CHAIN OF THOUGHTS STRUCTURE

Your JSON output must include the following thinking process using // comments:

1. Before incoming_connections: Think about unique technology types found for incoming connections
2. Before outgoing_connections: Think about unique technology types found for outgoing connections
3. Before each technology type: List all unique file paths and connection counts for that technology
4. Before each file path: Analyze code type similarity with provided examples and apply appropriate splitting rules

## FILE PATH THINKING PROCESS

Before writing file path fields, include // comments that address:

1. Pattern Grouping: If multiple files contain similar code patterns, group them together with one comment mentioning the total count and pattern type
2. Code Type Analysis: What type of code pattern does this represent?
3. Example Similarity: Do any rules or examples have similar code snippet patterns?
4. Splitting Guidelines: If yes, which forbidden/corrected examples apply to this code?
5. Variable Detection: Does this code use dynamic, global, or environment variables?
6. Variable Resolution: If variables are found, what are their resolved values?

Pattern Grouping Strategy: When you find similar code patterns across multiple files, use one thinking comment like:
  - `// Found 3 files with Express route handlers pattern - all use app.get()/app.post() with hardcoded endpoints, no variable resolution needed`
  - `// Found 5 files with axios HTTP client calls - all use environment variables, BASE_URL resolved to https://api.example.com`
  - `// Found 2 files with WebSocket emit operations - all use hardcoded event names, no variable resolution needed`

Then proceed directly to write the file path entries, creating separate JSON entries for EVERY SINGLE connection found.

## ENVIRONMENT AND VARIABLE RESOLUTION THINKING

Within the file path comments, think about:
  - Environment variables: Look for process.env.VAR_NAME, os.environ['VAR_NAME'], etc.
  - Global variables: Look for variables defined outside the current scope
  - Dynamic variables: Look for variables constructed at runtime
  - Resolution sources: Check same file definitions, environment file blocks
  - Resolution format: Use ENV_VAR=actual_value or variableName=resolved_value

Therefore the output is:

```json
{
  // Found incoming technology types [HTTP/HTTPS, WebSockets] - HTTP/HTTPS for route handlers and API endpoints, WebSockets for real-time event handling
  "incoming_connections": {
    // Found unique file paths [src/routes/users.js: 2 connections, src/api/handlers.js: 1 connection, src/queue/consumer.js: 1 connection]
    "HTTP/HTTPS": {
      // Found 2 files with similar HTTP endpoint patterns - both use Express routing with hardcoded endpoints, no variable resolution needed
      "src/routes/users.js": [
        {
          "snippet_lines": "23-23",
          "description": "GET /api/users endpoint for user retrieval"
        },
        {
          "snippet_lines": "27-27",
          "description": "POST /api/users endpoint for user creation"
        }
      ],
      "src/api/handlers.js": [
        {
          "snippet_lines": "45-45",
          "description": "GET /admin/settings endpoint using BASE_URL=api.example.com"
        }
      ],
      // Found 1 file with message consuming pattern - uses consume method with hardcoded queue name, no variable resolution needed
      "src/queue/consumer.js": [
        {
          "snippet_lines": "20-20",
          "description": "Message queue consumer for USER_ADD_QUEUE=user-add queue"
        }
      ]
    },
    // Found unique file paths [src/socket/server.js: 1 connection]
    "WebSockets": {
      // Found 1 file with WebSocket event handler pattern - uses socket.on() with hardcoded event names
      "src/socket/server.js": [
        {
          "snippet_lines": "30-30",
          "description": "WebSocket event handler for user_login event"
        }
      ]
    }
  },
  // Found outgoing technology types [HTTP/HTTPS, MessageQueue] - HTTP/HTTPS for API calls to external services, MessageQueue for publishing messages
  "outgoing_connections": {
    // Found unique file paths [src/services/api.js: 2 connections]
    "HTTP/HTTPS": {
      // Found 1 file with wrapper function pattern - uses makeApiCall wrapper with environment variables, BASE_URL=https://api.example.com
      "src/services/api.js": [
        {
          "snippet_lines": "37-37",
          "description": "HTTP POST call using makeApiCall wrapper to /api/users endpoint"
        },
        {
          "snippet_lines": "54-54",
          "description": "HTTP GET call using makeApiCall wrapper to /api/orders endpoint"
        }
      ]
    },
    // Found unique file paths [src/queue/producer.js: 1 connection]
    "MessageQueue": {
      // Found 1 file with message publishing pattern - uses publishMessage wrapper with variable resolution from same file
      "src/queue/producer.js": [
        {
          "snippet_lines": "25-25",
          "description": "Message publishing using QUEUE_NAME=user-notifications"
        }
      ]
    }
  },
  "summary": "Comprehensive description of the project including its core purpose, main functionality, architectural patterns, key services it provides, data processing workflows, integration points with external systems, and overall business domain based on observed connections and code patterns"
}
```

Where `<technology_type>` MUST be one of: HTTP/HTTPS, WebSockets, gRPC, GraphQL, MessageQueue, or Unknown.

Summary constraints:
  - Do NOT list individual endpoints, routes, or event names. Describe capability categories only (e.g., user CRUD, order lifecycle, admin/reporting).
  - Explicitly name confirmed libraries/clients/servers detected (e.g., axios for HTTP client, Express/FastAPI/Flask for HTTP server, amqplib/pika for RabbitMQ, kafkajs, socket.io, grpcio/@grpc/grpc-js, apollo-client/server, graphql-request). Include versions if visible.
  - Include environment/config highlights relevant to connections using ENV_VAR=resolved_value when available.
  - Only assert what is evidenced by the provided code/config; avoid speculation.
  - When wrappers/abstractions are used for connections, name them and briefly describe their argument shape and responsibilities (e.g., auth header injection, base URL resolution, retries, service targeting), as evidenced by code.

====

# MANDATORY SNIPPET SEPARATION RULES

RULE 1: ONE OPERATION PER SNIPPET
For any code handling multiple operations:
  - Each operation gets its own snippet entry
  - Use specific line numbers for each operation block
  - Description must mention the specific operation

RULE 2: ONE ENDPOINT/EVENT/METHOD PER SNIPPET
For any code defining multiple endpoints/events/methods:
  - Each definition gets its own snippet entry
  - Use specific line numbers for each definition
  - Description must include the specific endpoint/event/method details

RULE 3: PRECISE LINE NUMBERS
  - Use exact line numbers for each individual connection
  - For single-line connections: "23-23"
  - For multi-line connections: "23-25" (only if they're truly one logical connection spanning multiple lines)
  - Never use large ranges that span multiple different connections
  - FORBIDDEN EXAMPLES: "364-600", "104-474", "100-500", "50-120" - these indicate multiple connections being grouped
  - CORRECT EXAMPLES: "23-23", "45-45", "67-69", "102-107"
  - REQUIRED: Each connection gets its own precise line number or very small range (maximum 3-10 lines for one connection)

**CRITICAL LINE RANGE RULE**: Any range larger than ~7-10 lines (e.g., "504-574" = 70 lines) indicates you are grouping multiple connections, which is STRICTLY FORBIDDEN. Break it down into individual connections with single line numbers or tiny ranges.

====

# EXAMPLES OF CORRECT SEPARATION
EXAMPLE 1: HTTP API CALLS WITH LITERAL ENDPOINTS
When you receive connection data with HTTP API calls:

Input Connection Data:
```
./src/api/client.js:
  15 |     axios.post(`${process.env.BASE_URL}/admin/users`, userData)

  23 |     axios.get(`${process.env.BASE_URL}/api/v1/orders`, paramsv1)
  24 |     axios.get(`${process.env.BASE_URL}/api/v2/orders`, paramsv2)

  31 |     makeApiCall(`${process.env.BASE_URL}/admin/users`, 'POST', userData)

  45 |     makeApiCall(`${process.env.BASE_URL}/api/orders`, 'GET', params)
```

Environment Variables (if provided):
```
BASE_URL=https://api.example.com
```

CORRECT Splitting:

```json
{
  // Found outgoing technology types [HTTP/HTTPS] - HTTP client calls using axios and makeApiCall wrapper for external API communication
  "outgoing_connections": {
    // Found unique file paths [src/api/client.js: 5 connections]
    "HTTP/HTTPS": {
      // src/api/client.js contains HTTP API calls with literal endpoints - matches EXAMPLE 1 pattern. Code uses direct axios calls and makeApiCall wrapper. Environment variables detected: BASE_URL resolved to https://api.example.com from provided env file. All outgoing connections since service makes calls to external endpoints.
      "src/api/client.js": [
        {
          "snippet_lines": "15-15",
          "description": "HTTP POST call using BASE_URL=https://api.example.com to /admin/users endpoint for user creation"
        },
        {
          "snippet_lines": "23-23",
          "description": "HTTP GET call using BASE_URL=https://api.example.com to /api/v1/orders endpoint for order retrieval"
        },
        {
          "snippet_lines": "24-24",
          "description": "HTTP GET call using BASE_URL=https://api.example.com to /api/v2/orders endpoint for order retrieval"
        },
        {
          "snippet_lines": "31-31",
          "description": "HTTP POST call using makeApiCall wrapper and BASE_URL=https://api.example.com to /admin/users endpoint for user creation"
        },
        {
          "snippet_lines": "45-45",
          "description": "HTTP GET call using makeApiCall wrapper and BASE_URL=https://api.example.com to /api/orders endpoint for order retrieval"
        }
      ]
    }
  },
  "summary": "This service handles user administration and order workflows over HTTP using the axios client. Outbound calls use direct axios requests and a makeApiCall wrapper (signature observed as makeApiCall(path, method, payloadOrParams[, config])), and include an Authorization: Bearer <token> header when authentication is required. Capabilities cover admin/user management and order retrieval at a category level."
}
```

EXAMPLE 2: ENVIRONMENT VARIABLE CONFIGURATIONS
When you receive connection data with environment variables and their values:

Input Connection Data:
```
./src/config/api.js:
  12 |     const response = await axios.get(`${process.env.BASE_URL}/update/data`)
```

Environment Variables (if provided):
```
BASE_URL=https://api.example.com
```

CORRECT Splitting:

```json
{
  // Found outgoing technology types [HTTP/HTTPS] - HTTP GET request for data synchronization using environment-based configuration
  "outgoing_connections": {
    // Found unique file paths [src/config/api.js: 1 connection]
    "HTTP/HTTPS": {
      // src/config/api.js contains HTTP GET call with environment variable - matches environment variable pattern. Code uses axios.get() with template literal. Environment variable detected: BASE_URL resolved to https://api.example.com from env file. Single outgoing connection for data synchronization.
      "src/config/api.js": [
        {
          "snippet_lines": "12-12",
          "description": "HTTP GET call using BASE_URL=https://api.example.com for endpoint /update/data"
        },
      ]
    },
  },
  "summary": "This service performs data synchronization over HTTP using axios. Configuration is environment-driven with BASE_URL=https://api.example.com."
}
```

EXAMPLE 3: SOCKET EVENTS AND MESSAGE HANDLERS
When you receive connection data with WebSocket and message queue operations:

Input Connection Data:
```
./src/socket/handlers.js:
  15 |     socket.emit('user_status_update', data)

  23 |     socket.emit('order_notification', orderData)

./src/socket/server.js:
  30 |     socket.on('user_login', handleUserLogin)

  35 |     socket.on('user_logout', handleUserLogout)

./src/queue/consumer.js:
  42 |     queue.consume('order-processing', handler)
```

CORRECT Splitting:

```json
{
  // Found outgoing technology types [WebSockets] - Real-time event emission to connected clients
  "outgoing_connections": {
    // Found unique file paths [src/socket/handlers.js: 2 connections]
    "WebSockets": {
      // Found 1 file with WebSocket emit pattern - uses socket.emit() with hardcoded event names, no variable resolution needed
      "src/socket/handlers.js": [
        {
          "snippet_lines": "15-15",
          "description": "WebSocket emit for user_status_update event"
        },
        {
          "snippet_lines": "23-23",
          "description": "WebSocket emit for order_notification event"
        }
      ]
    }
  },
  // Found incoming technology types [WebSockets, MessageQueue] - WebSockets for client event handling, MessageQueue for consuming queued tasks
  "incoming_connections": {
    // Found unique file paths [src/socket/server.js: 2 connections]
    "WebSockets": {
      // Found 1 file with WebSocket event handler pattern - uses socket.on() with hardcoded event names, no variable resolution needed
      "src/socket/server.js": [
        {
          "snippet_lines": "30-30",
          "description": "WebSocket event handler for user_login event"
        },
        {
          "snippet_lines": "35-35",
          "description": "WebSocket event handler for user_logout event"
        }
      ]
    },
    // Found unique file paths [src/queue/consumer.js: 1 connection]
    "MessageQueue": {
      // Found 1 file with message queue consumer pattern - uses queue.consume() with hardcoded queue name
      "src/queue/consumer.js": [
        {
          "snippet_lines": "42-42",
          "description": "Message queue consumer for order-processing queue"
        }
      ]
    }
  },
  "summary": "This service provides real-time user and order updates over WebSockets and processes queued work asynchronously. It receives user events via WebSocket handlers, emits notifications to clients, and consumes messages from a queue system for order processing. Capabilities cover authentication events and order notifications."
}
```

EXAMPLE 4: EXPRESS ROUTE HANDLERS
When you receive connection data with API route definitions:

Input Connection Data:
```
./src/routes/users.js:
  10 |     app.get('/api/users', getUsersHandler)

  15 |     app.post('/api/users', createUserHandler)

./src/routes/orders.js:
  8 |     router.get('/orders/:id', getOrderHandler)

  12 |     router.put('/orders/:id', updateOrderHandler)
```

CORRECT Splitting:

```json
{
  // Found incoming technology types [HTTP/HTTPS] - REST API endpoints for user and order management using Express framework
  "incoming_connections": {
    // Found unique file paths [src/routes/users.js: 2 connections, src/routes/orders.js: 2 connections]
    "HTTP/HTTPS": {
      // Found 2 files with Express route handler pattern - both use app.get()/router.get() and app.post()/router.put() with hardcoded endpoints, no variable resolution needed
      "src/routes/users.js": [
        {
          "snippet_lines": "10-10",
          "description": "GET /api/users endpoint for user retrieval"
        },
        {
          "snippet_lines": "15-15",
          "description": "POST /api/users endpoint for user creation"
        }
      ],
      "src/routes/orders.js": [
        {
          "snippet_lines": "8-8",
          "description": "GET /orders/:id endpoint for order retrieval by ID"
        },
        {
          "snippet_lines": "12-12",
          "description": "PUT /orders/:id endpoint for order update by ID"
        }
      ]
    }
  },
  "summary": "This is a REST API service implemented with Express route handlers for user and order management. The API surface provides user CRUD and order retrieval/update capabilities following typical REST patterns."
}
```

EXAMPLE 5: WRAPPER FUNCTIONS WITH SPECIFIC IDENTIFIERS
When you receive connection data with wrapper function calls:

Input Connection Data:
```
./src/services/notification.js:
  25 |     publishMessage('user-notifications', data)

  30 |     publishMessage('order-updates', orderData)

./src/services/api.js:
  18 |     makeApiCall('/admin/users', 'POST', userData)

  22 |     makeApiCall('/api/orders', 'GET', params)

./src/makeApiCall.js:
  10 |     function makeApiCall(path, method, payloadOrParams, config) {
  11 |       const url = `${process.env.BASE_URL}${path}`

  13 |       return axios.request({ url, method, data: payloadOrParams, ...config })
  14 |     }

./.env:
  3 |     BASE_URL=https://api.example.com
```

CORRECT Splitting:

```json
{
  // Found outgoing technology types [MessageQueue, HTTP/HTTPS] - MessageQueue for publishing notifications, HTTP/HTTPS for external API calls using wrapper functions
  "outgoing_connections": {
    // Found unique file paths [src/services/notification.js: 2 connections]
    "MessageQueue": {
      // Found 1 file with message publishing wrapper pattern - uses publishMessage wrapper with hardcoded queue names, no variable resolution needed
      "src/services/notification.js": [
        {
          "snippet_lines": "25-25",
          "description": "Message publishing using publishMessage wrapper to user-notifications queue"
        },
        {
          "snippet_lines": "30-30",
          "description": "Message publishing using publishMessage wrapper to order-updates queue"
        }
      ]
    },
    // Found unique file paths [src/services/api.js: 2 connections]
    "HTTP/HTTPS": {
      // Found 1 file with HTTP wrapper pattern - uses makeApiCall wrapper with environment variables, BASE_URL=https://api.example.com
      "src/services/api.js": [
        {
          "snippet_lines": "18-18",
          "description": "HTTP POST call using makeApiCall wrapper and BASE_URL=https://api.example.com to /admin/users endpoint for user creation"
        },
        {
          "snippet_lines": "22-22",
          "description": "HTTP GET call using makeApiCall wrapper and BASE_URL=https://api.example.com to /api/orders endpoint for order retrieval"
        }
      ]
    }
  },
  "summary": "This service integrates HTTP APIs and message publishing via wrapper functions. HTTP calls use a makeApiCall wrapper for administrative and order operations, and messages are published via publishMessage to notification and update channels. Capabilities cover user administration and order updates."
}
```

EXAMPLE 6: SWITCH CASE CONNECTIONS
When you receive connection data with switch statements handling different connection operations:

Input Connection Data:
```
./src/handlers/message.js:
  45 |     switch (messageType) {
  46 |       case 'USER_CREATED':
  47 |         await axios.post(`https://${process.env.BASE_URL}/user-service/notify`, userData)
  48 |         break;
  49 |       case 'ORDER_PLACED':
  50 |         await axios.post(`https://${process.env.BASE_URL}/order-service/process`, orderData)
  51 |         break;
  52 |       case 'PAYMENT_RECEIVED':
  53 |         await axios.put(`https://${process.env.BASE_URL}/payment-service/confirm`, paymentData)
  54 |         break;
  55 |     }
  56 |

./src/handlers/event.js:
  20 |     switch (event.type) {
  21 |       case 'sync':
  22 |         socket.emit('data_sync', syncData)
  23 |         break;
  24 |       case 'update':
  25 |         socket.emit('data_update', updateData)
  26 |         break;
  27 |       case 'delete':
  28 |         socket.emit('data_delete', deleteData)
  29 |         break;
  30 |     }
  31 |

./.env:
  3 |     BASE_URL=api.example.com
  4 |
```

CORRECT Splitting:

```json
{
  // Found outgoing technology types [HTTP/HTTPS, WebSockets] - HTTP/HTTPS for service-to-service communication based on message types, WebSockets for real-time client updates based on event types
  "outgoing_connections": {
    // Found unique file paths [src/handlers/message.js: 3 connections]
    "HTTP/HTTPS": {
      // Found 1 file with switch case HTTP pattern - uses axios calls within switch cases with environment variables, BASE_URL=api.example.com
      "src/handlers/message.js": [
        {
          "snippet_lines": "47-47",
          "description": "HTTP POST call to https://{BASE_URL}/user-service/notify using BASE_URL=api.example.com for USER_CREATED message type"
        },
        {
          "snippet_lines": "50-50",
          "description": "HTTP POST call to https://{BASE_URL}/order-service/process using BASE_URL=api.example.com for ORDER_PLACED message type"
        },
        {
          "snippet_lines": "53-53",
          "description": "HTTP PUT call to https://{BASE_URL}/payment-service/confirm using BASE_URL=api.example.com for PAYMENT_RECEIVED message type"
        }
      ]
    },
    // Found unique file paths [src/handlers/event.js: 3 connections]
    "WebSockets": {
      // Found 1 file with switch case WebSocket pattern - uses socket.emit() within switch cases with hardcoded event names
      "src/handlers/event.js": [
        {
          "snippet_lines": "22-22",
          "description": "WebSocket emit for data_sync event in sync case handler"
        },
        {
          "snippet_lines": "25-25",
          "description": "WebSocket emit for data_update event in update case handler"
        },
        {
          "snippet_lines": "28-28",
          "description": "WebSocket emit for data_delete event in delete case handler"
        }
      ]
    }
  },
  "summary": "This service orchestrates business events with outbound HTTP calls using axios and real-time client updates via WebSockets. It routes user, order, and payment events to downstream services and emits synchronization/update/delete events to connected clients."
}
```

IMPORTANT NOTES FOR SWITCH CASE SPLITTING:
  - Each case branch with a connection operation gets its own separate entry
  - Use the exact line number of the connection operation (not the case statement line)
  - Include the case condition in the description to provide context
  - Never group all cases together as "switch statement handling multiple operations"
  - Ignore the switch statement structure lines (switch, case labels, breaks) - only capture the actual connection operations

====

# EXAMPLES OF FORBIDDEN GROUPING

1. FORBIDDEN - Grouping Multiple Operations:
  - "40+ REST API endpoints including /get-speech-token, /get-custom-token, /check-room, /admin routes, /super-admin routes - comprehensive incoming HTTP connection points"
  - "REST API endpoints for incoming connections - includes 45+ admin, internal, techyrr-admin, and public routes with various HTTP methods"
  - "Event handlers for multiple events including user_login, user_logout, and data_update"

2. FORBIDDEN - Grouping Multiple Endpoints:
  - "HTTP requests including GET, POST, and PUT operations for user management"
  - "Multiple API endpoints for order processing and payment handling"

3. FORBIDDEN - Grouping Wrapper Function Calls:
  - "Multiple API calls using makeApiCall wrapper for various endpoints"
  - "Several HTTP operations including user, order, and payment API calls"

====

# DATA EXCLUSION RULES - DO NOT INCLUDE THIS TYPE OF DATA IN YOUR OUTPUT

The following types of connection data should NOT be included in splitting:

EXCLUDE 1: Connection Setup and Configuration Code
Connection Data That Should Be Excluded:
```
./src/queue/consumer.js:
  18 |     const connection = amqp.connect(process.env.URL)
  19 |     connection.on("connect", () => console.log("Connected!"))
  20 |     connection.on("disconnect", (err) => console.log("Disconnected.", err.stack))
  21 |

  24 |     const channel = connection.createChannel({ json: true })

  28 |     channel.assertExchange(process.env.EXCHANGE_NAME, "direct")
  29 |     channel.assertQueue(queue)
  30 |     channel.bindQueue(queue, process.env.EXCHANGE_NAME, "rooms")
  31 |     channel.prefetch(1)

./src/api/client.js:
  10 |     const httpClient = axios.create({ baseURL: process.env.API_BASE_URL })

./src/socket/server.js:
  5 |     const io = new Server(server, { cors: { origin: "*" } })

./src/websocket/client.js:
  8 |     const socket = io.connect(process.env.SOCKET_URL)
```
Why Excluded: These are infrastructure setup, not actual data transmission operations.

EXCLUDE 2: Generic Library Calls Without Identifiers
Connection Data That Should Be Excluded:
```
./src/utils/http.js:
  25 |     await axios.get(url)

  30 |     await axios.post(url, data)

./src/utils/socket.js:
  15 |     socket.emit(eventName, data)
```
Why Excluded: These use variable identifiers, not specific connection endpoints.

EXCLUDE 3: Function Definitions and Imports
Connection Data That Should Be Excluded:
```
./src/api/client.js:
  1 |     const axios = require('axios')

./src/utils/api.js:
  10 |     function apiCallFunction(endpoint, method, data) { ... }

./src/socket/handler.js:
  5 |     import { io } from 'socket.io-client'
```
Why Excluded: Library imports and generic function definitions are not actual connections.

EXCLUDE 4: Configuration Without Actual Usage
Connection Data That Should Be Excluded:
```
./src/config/settings.js:
  8 |     const API_BASE_URL = process.env.API_BASE_URL

  12 |     const QUEUE_CONFIG = { host: 'localhost', port: 5672 }
```
Why Excluded: Configuration definitions without actual connection usage.

EXCLUDE 5: Connection Placeholders
Connection Data That Should Be Excluded:
```
./src/placeholders/connection.js:
  10 |     const dbConnection = createDbConnection(config)

  15 |     const apiClient = createApiClient(baseUrl)
```
Why Excluded: These are placeholders or abstractions without concrete connection details.

====

# DATA INCLUSION RULES - MUST BE INCLUDED

INCLUDE: Only Actual Data Transmission Operations
Connection Data That SHOULD Be Included:

PRODUCERS/SENDERS/PROVIDER (Outgoing):
```
./src/queue/producer.js:
  25 |     channel.publish(exchange, routingKey, message)

  30 |     queue.send('user-notifications', userData)

./src/api/client.js:
  25 |     const response = await axios.get(`${process.env.API_BASE_URL}/users`)

  30 |     await axios.post(`${process.env.API_BASE_URL}/orders`, orderData)

./src/socket/emitter.js:
  15 |     socket.emit('user_status_update', statusData)

./src/websocket/client.js:
  20 |     ws.send(JSON.stringify({ type: 'ping', data: pingData }))
```

CONSUMERS/RECEIVERS/LISTENERS (Incoming):
```
./src/queue/consumer.js:
  40 |     channel.consume(queueName, messageHandler)

  45 |     queue.process('order-processing', orderProcessor)

./src/routes/api.js:
  20 |     app.get('/api/users', handleGetUsers)

  25 |     app.post('/api/orders', handleCreateOrder)

./src/socket/handlers.js:
  15 |     socket.on('user_login', handleUserLogin)

./src/websocket/server.js:
  30 |     ws.on('message', (data) => handleMessage(JSON.parse(data)))
```

Why Included: These show actual data transmission operations - the core purpose of connection analysis.

FOCUS ON DATA OPERATIONS ONLY AND THEIR WRAPPER FUCTIONS (Examples):
- Producers: `publish()`, `send()`, `sendToQueue()`, `produce()`
- Consumers: `consume()`, `process()`, `subscribe()`, `on('message')`
- HTTP Senders: `axios.get()`, `axios.post()`, `fetch()`, `request()`
- HTTP Receivers: Route handlers like `app.get()`, `router.post()`, endpoint definitions
- WebSocket Senders: `socket.emit()`, `ws.send()`
- WebSocket Receivers: Event handlers like `socket.on()`, `ws.on('message')`

====

# CHAIN OF THOUGHTS ANALYSIS PROCESS

1. Identify env files: Look for environment file code blocks that contain variable definitions
2. Identify all connections: Scan through all code snippets and identify every individual connection
3. Resolve env variables: For each connection using environment variables, find corresponding values from env file blocks
4. Separate each connection: For each connection found, create a separate JSON entry
5. Extract precise details: Get exact line numbers and specific details for each connection
6. Write specific descriptions: Each description must be about ONE specific connection with resolved env values when available
7. Analyze project comprehensively: Review all connections, patterns, and code structure to understand the complete project functionality
8. Generate detailed summary: Create a comprehensive project description covering purpose, architecture, integrations, and business domain
9. Resolve global/dynamic variables: If any connection uses global or dynamic variables that cannot be resolved, mention those variables in the description
10. Embed thinking process: Use // comments throughout JSON to show analysis, pattern matching, and variable resolution
11. Same repeating code from same file with same line numbers: If the same code snippet with same line number range and same file path appears multiple times in the input, include it only once in the output
====

# REQUIREMENTS

1. Chain of Thoughts Process: Use embedded JSON comments to show your reasoning throughout the JSON structure
2. Connection Counting: Count and categorize all connections by technology type and direction
3. Complete Processing: Process ALL connections - never skip or sample connections
4. Individual Separation: Never group multiple connections into one entry
5. Precise Line Numbers: Use exact line numbers for each connection location
6. Specific Descriptions: Each description must be about one connection only
7. Environment Resolution: Resolve environment variables using provided configuration files and include as ENV_VAR=actual_value
8. Technology Classification: Validate technology type classification for each connection
9. Comprehensive Summary: Generate detailed project description covering purpose, functionality, architecture, and integrations
10. Output Format: Return valid JSON with embedded chain of thoughts comments
11. Grouping Structure: Group by technology and file path as shown in format
12. FORBIDDEN LANGUAGE: No phrases like "including", "multiple", "various", "several", "operations for", "comprehensive", "40+", "45+", numbers with plus signs, "for [A], [B], and [C]", "endpoints for", "routes for"
13. INDIVIDUAL ENTRIES REQUIRED: If you find 86 different connections, create 86 separate JSON entries - No exceptions, No sampling, No grouping
14. MANDATORY SEPARATION: Every single connection must be its own separate JSON entry with specific line numbers

Summary-specific requirements:
  - Do NOT enumerate concrete endpoint paths; describe capabilities/categories only.
  - Name concrete libraries/frameworks used for connections (e.g., axios, requests, Express, FastAPI, amqplib/pika for RabbitMQ, kafkajs, socket.io, grpcio/@grpc/grpc-js, apollo-client/server, graphql-request).
  - Use only facts supported by the input; if uncertain, omit rather than hedge.
"#

template_string ConnectionSplittingUserPrompt(memory_context: string) #"
    {{ _.role("user") }}
    {{ memory_context }}

Process the above connection code snippets and transform them into structured JSON format. Classify each connection as incoming or outgoing, extract complete parameter details, and return the properly formatted JSON.
"#

function AwsBedrockConnectionSplitting(memory_context: string) -> ConnectionSplittingResponse {
  client AwsBedrock
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ ConnectionSplittingPrompt() }}
    {{ ConnectionSplittingUserPrompt(memory_context) }}
  "#
}

function AnthropicClaudeConnectionSplitting(memory_context: string) -> ConnectionSplittingResponse {
  client AnthropicClaude
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ ConnectionSplittingPrompt() }}
    {{ ConnectionSplittingUserPrompt(memory_context) }}
  "#
}

function OpenAIChatGPTConnectionSplitting(memory_context: string) -> ConnectionSplittingResponse {
  client OpenAIChatGPT
  prompt #"
    {{ _.role("system") }}
    {{ ConnectionSplittingPrompt() }}
    {{ ConnectionSplittingUserPrompt(memory_context) }}
  "#
}

function GoogleGeminiConnectionSplitting(memory_context: string) -> ConnectionSplittingResponse {
  client GoogleGemini
  prompt #"
    {{ _.role("system") }}
    {{ ConnectionSplittingPrompt() }}
    {{ ConnectionSplittingUserPrompt(memory_context) }}
  "#
}

function GCPVertexAIConnectionSplitting(memory_context: string) -> ConnectionSplittingResponse {
  client GCPVertexAI
  prompt #"
    {{ _.role("system") }}
    {{ ConnectionSplittingPrompt() }}
    {{ ConnectionSplittingUserPrompt(memory_context) }}
  "#
}

function AzureOpenAIConnectionSplitting(memory_context: string) -> ConnectionSplittingResponse {
  client AzureOpenAI
  prompt #"
    {{ _.role("system") }}
    {{ ConnectionSplittingPrompt() }}
    {{ ConnectionSplittingUserPrompt(memory_context) }}
  "#
}

function AzureAIFoundryConnectionSplitting(memory_context: string) -> ConnectionSplittingResponse {
  client AzureAIFoundry
  prompt #"
    {{ _.role("system") }}
    {{ ConnectionSplittingPrompt() }}
    {{ ConnectionSplittingUserPrompt(memory_context) }}
  "#
}

function OpenRouterConnectionSplitting(memory_context: string) -> ConnectionSplittingResponse {
  client OpenRouter
  prompt #"
    {{ _.role("system") }}
    {{ ConnectionSplittingPrompt() }}
    {{ ConnectionSplittingUserPrompt(memory_context) }}
  "#
}
