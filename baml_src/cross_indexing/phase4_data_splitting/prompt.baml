template_string ConnectionSplittingPrompt() #"
You will receive connection data of cross-indexing analysis. Your task is to split this data into incoming and outgoing connections and return them in the required JSON format. Additionally, include a comprehensive top-level "summary" that thoroughly describes the project's purpose, functionality, and architecture based on the collected connections.

## ABSOLUTE CRITICAL RULE - ONE CONNECTION PER SNIPPET

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
- "REST API endpoints for incoming connections - includes 45+ admin, internal, techyrr-admin"
- "Comprehensive incoming HTTP connection points"
- Any description mentioning "multiple", "including", "various" , "several", numbers like "40+", "45+"

REQUIRED APPROACH:
- "Message handler for eventA"
- "Message handler for eventB"  
- "Message handler for eventC"
- "GET /endpointX for data retrieval"
- "POST /endpointY for data creation"
- "GET /get-speech-token endpoint for speech token retrieval"
- "POST /check-room endpoint for room validation"
- "GET /admin/users endpoint for user management"

## OBJECTIVE

Process the collected connection data and categorize each connection as either incoming or outgoing, then return structured JSON with complete connection details. Each connection must be a separate entry with its own specific line numbers and description.

## TECHNOLOGY TYPE CLASSIFICATION

### MANDATORY TECHNOLOGY TYPES
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

### CONNECTION CLASSIFICATION

#### INCOMING CONNECTIONS
Connections where OTHER services connect TO this service:
Examples:
- API endpoints and route handlers (Express routes, Flask routes, etc.)
- WebSocket server endpoints that accept connections
- Message queue consumers that receive messages
- Server configurations that listen for connections

#### OUTGOING CONNECTIONS  
Connections where THIS service connects TO other services
Examples:
- HTTP client calls (axios, fetch, requests, etc.)
- WebSocket client connections to other services
- Message queue producers that send messages

## PROCESSING RULES

1. STRICT ONE-TO-ONE MAPPING: Analyze each connection individually - never group multiple connections
2. INDIVIDUAL ENTRIES ONLY: Create separate entries - If you find code with multiple operations, create separate entries for each
3. PRECISE LINE NUMBERS: Extract individual details - Each entry gets its own specific line numbers (single line "23-23" or very small ranges "23-25" for one logical connection only)
4. SINGLE CONNECTION FOCUS: Focus on data transmission - Only code that sends or receives data, exclude setup
5. COMPLETE PARAMETER DETAILS: Include complete parameter details:
   - Exact endpoints, event names, queue names, method names
   - Protocols, methods, parameters
   - Environment variables and their resolved values in descriptions using format ENV_VAR=actual_value
   - File paths and line numbers
6. CORRECT DIRECTION: Classify direction correctly based on data flow
7. NO DUPLICATES: No duplicates - each data transmission operation must be unique
8. NO REPEATED CONTENT: CRITICAL: IGNORE REPEATING CONTENT - If you see the same file code with the same lines appearing multiple times in the input, include it only ONCE in your response. Same lines from same files are allowed only one time in splitting.
9. ENVIRONMENT RESOLUTION: ENVIRONMENT FILE CODE RESOLUTION - If environment file code is provided as a code block, look for env var/config values and include them in connection descriptions for better context
10. FORBIDDEN LANGUAGE: Never use words like "multiple", "including", "various", "several", "comprehensive", numbers with "+" (like "40+", "45+"), "operations for", "endpoints for"

## ENVIRONMENT FILE CODE RESOLUTION

When environment file code blocks are provided in the input (e.g., .env files, config files), use them to resolve environment variables in connection descriptions:

1. IDENTIFY ENV FILES: Look for code blocks that contain environment variable definitions (KEY=value format)
2. RESOLVE VARIABLES: When connection code uses environment variables (process.env.VAR_NAME, os.environ['VAR_NAME'], etc.), find the corresponding value from env file code blocks
3. ENHANCE DESCRIPTIONS: Include resolved values in connection descriptions using format: ENV_VAR=actual_value
4. PROVIDE CONTEXT: This gives better context for later users understanding the actual connection endpoints, queue names, etc.

### EXAMPLE OF ENV RESOLUTION:
If you find connection code:
```
src/queue/consumer.js:20: queue.consume(process.env.USER_ADD_QUEUE, handler)
```

And env file code block contains:
```
USER_ADD_QUEUE="user-add"
NOTIFICATION_QUEUE="notifications"
```

Then description should be:
```
"Message queue consumer for USER_ADD_QUEUE=user-add queue"
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
- For HTTP calls: Extend until you capture method, complete URL/endpoint, and request configuration
- For message queues: Extend until you capture exchange/queue name, routing key, and message payload structure
- For WebSocket: Extend until you capture event type, recipient identification, and message content
- For database calls: Extend until you capture complete query, parameters, and connection details
- General rule: Add 3-8 additional lines based on code complexity and nesting level

INTELLIGENT LINE EXTENSION GUIDELINES:
- Simple method calls: +2-3 lines
- Complex builder patterns: +4-6 lines
- Nested configuration objects: +5-8 lines
- Multi-parameter method calls: +3-5 lines
- Always prefer capturing complete context over partial information

EXTRACT ALL connections found - no selective sampling allowed.

## GENERIC ANALYSIS INSTRUCTIONS

### FOR CONDITIONAL/SWITCH STATEMENTS:
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

### FOR MULTIPLE OPERATION DEFINITIONS:
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

### FOR ROUTER/HANDLER REGISTRATIONS:
If you find code registering multiple handlers:
```
register('/pathA', handlerA);
register('/pathB', handlerB);
register('/pathC', handlerC);
```

You MUST create separate entries for each registration.

## PROJECT SUMMARY GUIDELINES

Produce a concise, README-like project summary that an agent can rely on with high confidence without scanning other files. The summary MUST:

1) Technology inventory (explicit names)
- Name concrete libraries/frameworks detected for each connection type, e.g., axios/requests/node-fetch (HTTP client), Express/FastAPI/Flask (HTTP server), amqplib/pika (RabbitMQ), kafkajs (Kafka), socket.io/ws (WebSockets), grpcio/@grpc/grpc-js (gRPC), apollo-client/server or graphql-request (GraphQL).
- Prefer exact package names as they appear in code or dependency files.
- Only assert technologies present in the provided input. Do not speculate.

2) API surface overview (no endpoint listing)
- Do NOT list individual endpoints, routes, or event names.
- Describe endpoint/event categories and capabilities instead, e.g., "User management CRUD endpoints", "Order lifecycle operations", "Admin/reporting endpoints".

3) Messaging/streaming overview
- Identify queues/topics/streams by technology and purpose at a category level, e.g., "RabbitMQ queues for order processing and notifications". Avoid listing every queue; focus on roles/patterns.

4) Architecture and data flow
- Summarize how components interact (HTTP in/out, MQ producers/consumers, WebSocket emits/handlers, gRPC, GraphQL) and where this project sits relative to others when discernible.

5) Wrappers and abstractions (when evident)
- Identify helper/wrapper functions used to perform connections instead of direct library calls (e.g., makeApiCall, publishMessage, sendEvent).
- Name the exact function(s) and describe their argument shape from code, e.g., makeApiCall(path, method, dataOrParams[, config]).
- Note when wrappers encapsulate auth headers, base URLs, interceptors/retries, or service targeting (e.g., routes calls to order service).

6) Style
- Plain text, compact, skimmable. Short paragraphs and clear noun phrases. No endpoint lists.

7) Auth/security (when evident)
- State observed authentication methods (tokens, API keys, OAuth, cookies, headers) and where they apply.
- When visible, specify exact header names and placement, e.g., Authorization: Bearer <token> on outbound HTTP/HTTPS requests.

8) High-certainty language
- Use definitive language only for facts evidenced in code/snippets/configs here. Avoid guesses. If something cannot be confirmed, omit it instead of hedging.

9) Operational notes (when evident)
- Include tracing/logging/metrics libraries, and error-handling/retry patterns that affect connections.

Example style: "This service exposes user and order workflows over HTTP using Express and the axios client, publishes order events to RabbitMQ via amqplib for asynchronous processing, and pushes live updates via Socket.IO. Configuration uses ENV vars such as API_BASE_URL and ORDER_QUEUE. Outbound HTTP requests include an Authorization: Bearer <token> header." 

## OUTPUT FORMAT

Before you answer, please explain your reasoning step-by-step.

Reasoning content rules (all inputs):
- Do not list endpoints, file paths, or line numbers in the reasoning; those specifics belong only in the JSON output.
- Summarize counts by technology type and direction, and mention key environment resolutions (e.g., BASE_URL=api.example.com).

Reasoning size control (large inputs):
- Provide only counts by technology type and direction, and mention key environment resolutions (e.g., BASE_URL=api.example.com, QUEUE_NAME=user-processing).
- Do not list endpoints, files, or line numbers in the reasoning; those details must appear only in the JSON output.
- State that duplicates were removed and env variables were resolved where provided.

Example concise analysis for large inputs:
"I analyzed the connection data and counted operations by type and direction. Found 48 outgoing HTTP/HTTPS, 6 incoming HTTP/HTTPS, 12 outgoing MessageQueue, and 4 WebSockets. Outbound HTTP/HTTPS calls use a base URL resolved as BASE_URL=api.example.com. I processed each operation individually, resolved environment variables where available, and removed duplicates before producing the JSON."

For example:
"I analyzed all the connection data systematically. I found 34 incoming HTTP/HTTPS connections across 8 files including REST API endpoints, route handlers, and server configurations. I identified 20 incoming WebSocket connections for real-time event handling. I discovered 12 outgoing HTTP/HTTPS connections for external API calls and microservice communication. I found 8 outgoing MessageQueue connections for asynchronous processing. I processed each connection individually, extracted specific line numbers, resolved environment variables where applicable, and classified each by technology type and data flow direction."

Therefore the output is:

```json
{
  "incoming_connections": {
    "<technology_type>": {
      "file/path.ext": [
        {
          "snippet_lines": "23-23",
          "description": "Specific operation A for incoming data"
        },
        {
          "snippet_lines": "27-27",
          "description": "Specific operation B for incoming data"
        }
      ]
    }
  },
  "outgoing_connections": {
    "<technology_type>": {
      "file/path.ext": [
        {
          "snippet_lines": "37-37",
          "description": "Specific operation X for outgoing data"
        },
        {
          "snippet_lines": "54-54",
          "description": "Specific operation Y for outgoing data"
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

## MANDATORY SNIPPET SEPARATION RULES

### RULE 1: ONE OPERATION PER SNIPPET
For any code handling multiple operations:
- Each operation gets its own snippet entry
- Use specific line numbers for each operation block
- Description must mention the specific operation

### RULE 2: ONE ENDPOINT/EVENT/METHOD PER SNIPPET  
For any code defining multiple endpoints/events/methods:
- Each definition gets its own snippet entry
- Use specific line numbers for each definition
- Description must include the specific endpoint/event/method details

### RULE 3: PRECISE LINE NUMBERS
- Use exact line numbers for each individual connection
- For single-line connections: "23-23" 
- For multi-line connections: "23-25" (only if they're truly one logical connection spanning multiple lines)
- Never use large ranges that span multiple different connections
- FORBIDDEN: "264-600", "604-674", "100-500" - these indicate multiple connections being grouped
- REQUIRED: Each connection gets its own precise line number or very small range

## EXAMPLES OF CORRECT SEPARATION

### EXAMPLE 1: HTTP API CALLS WITH LITERAL ENDPOINTS
When you receive connection data with HTTP API calls:

Input Connection Data:
```
src/api/client.js:15: axios.post(`${process.env.BASE_URL}/admin/users`, userData)
src/api/client.js:23: axios.get(`${process.env.BASE_URL}/api/orders`, params)
src/api/client.js:31: makeApiCall(`${process.env.BASE_URL}/admin/users`, 'POST', userData)
src/api/client.js:45: makeApiCall(`${process.env.BASE_URL}/api/orders`, 'GET', params)
```

Environment Variables (if provided):
```
BASE_URL=https://api.example.com
```

CORRECT Splitting:

Step-by-step Analysis:
"I analyzed the HTTP API connection data systematically. I found 4 outgoing HTTP/HTTPS connections in src/api/client.js file. These include 2 direct axios calls and 2 wrapper function calls using makeApiCall. Each call uses an environment-based base URL and specific paths (BASE_URL resolved from the provided env block). All connections are outgoing since this service is making calls to external endpoints for user management and order processing."

```json
{
  "outgoing_connections": {
    "HTTP/HTTPS": {
      "src/api/client.js": [
        {
          "snippet_lines": "15-15",
          "description": "HTTP POST call using BASE_URL=https://api.example.com to /admin/users endpoint for user creation"
        },
        {
          "snippet_lines": "23-23",
          "description": "HTTP GET call using BASE_URL=https://api.example.com to /api/orders endpoint for order retrieval"
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

### EXAMPLE 2: ENVIRONMENT VARIABLE CONFIGURATIONS
When you receive connection data with environment variables and their values:

Input Connection Data:
```
src/config/api.js:12: const response = await axios.get(`${process.env.BASE_URL}/update/data`)
src/config/queue.js:8: const queueName = process.env.QUEUE_NAME || 'default-queue'
src/config/api.js:20: const apiUrl = 'https://api.example.com/api'
```

Environment Variables (if provided):
```
BASE_URL=https://api.example.com
QUEUE_NAME=user-processing
```

CORRECT Splitting:

Step-by-step Analysis:
"I analyzed the connection data and identified environment variable usage. I found 2 outgoing HTTP/HTTPS connections and 1 MessageQueue configuration. For src/config/api.js line 12, I resolved the environment variable BASE_URL=https://api.example.com from the provided env file to create the full endpoint. For src/config/queue.js line 8, I resolved QUEUE_NAME=user-processing. The static API URL on line 20 is set to https://api.example.com/api. I classified the HTTP calls as outgoing connections and the queue configuration as outgoing MessageQueue setup."

```json
{
  "outgoing_connections": {
    "HTTP/HTTPS": {
      "src/config/api.js": [
        {
          "snippet_lines": "12-12",
          "description": "HTTP GET call using BASE_URL=https://api.example.com for endpoint /update/data"
        },
        {
          "snippet_lines": "20-20",
          "description": "Static API URL configuration for https://api.example.com/api endpoint"
        }
      ]
    },
    "MessageQueue": {
      "src/config/queue.js": [
        {
          "snippet_lines": "8-8",
          "description": "Queue name configuration using environment variable QUEUE_NAME=user-processing with fallback to default-queue"
        }
      ]
    }
  },
  "summary": "This service performs data synchronization over HTTP using axios and leverages a message queue for asynchronous user processing. Configuration is environment-driven with API_BASE_URL=http://localhost:3001 and QUEUE_NAME=user-processing. Capabilities cover data update fetches and user-processing tasks."
}
```

### EXAMPLE 3: SOCKET EVENTS AND MESSAGE HANDLERS
When you receive connection data with WebSocket and message queue operations:

Input Connection Data:
```
File: src/socket/handlers.js
15 | socket.emit('user_status_update', data)
23 | socket.emit('order_notification', orderData)

File: src/socket/server.js
30 | socket.on('user_login', handleUserLogin)
35 | socket.on('user_logout', handleUserLogout)

File: src/queue/consumer.js```
42 | queue.consume('order-processing', handler)

CORRECT Splitting:

Step-by-step Analysis:
"I analyzed the WebSocket and message queue connection data systematically. I found 2 outgoing WebSocket emits, 2 incoming WebSocket handlers, and 1 incoming MessageQueue consumer. The emits are outgoing since they send data to clients, the event listeners are incoming since they receive data from clients, and the queue consumer is incoming since it receives messages from the queue system."

```json
{
  "outgoing_connections": {
    "WebSockets": {
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
  "incoming_connections": {
    "WebSockets": {
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
    "MessageQueue": {
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

### EXAMPLE 4: EXPRESS ROUTE HANDLERS
When you receive connection data with API route definitions:

Input Connection Data:
```
src/routes/users.js:10: app.get('/api/users', getUsersHandler)
src/routes/users.js:15: app.post('/api/users', createUserHandler)
src/routes/orders.js:8: router.get('/orders/:id', getOrderHandler)
src/routes/orders.js:12: router.put('/orders/:id', updateOrderHandler)
```

CORRECT Splitting:

Step-by-step Analysis:
"I analyzed the Express route handler connection data systematically. I found 4 incoming HTTP/HTTPS connections across 2 files spanning user routes and order routes. All connections are incoming since they define endpoints that accept requests from external clients. Each route handler serves a specific HTTP method and endpoint combination for REST API functionality."

```json
{
  "incoming_connections": {
    "HTTP/HTTPS": {
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

### EXAMPLE 5: WRAPPER FUNCTIONS WITH SPECIFIC IDENTIFIERS
When you receive connection data with wrapper function calls:

Input Connection Data:
```
File: src/services/notification.js
25 | publishMessage('user-notifications', data)
30 | publishMessage('order-updates', orderData)

File: src/services/api.js
18 | makeApiCall('/admin/users', 'POST', userData)
22 | makeApiCall('/api/orders', 'GET', params)

File: src/makeApiCall.js
10 | function makeApiCall(path, method, payloadOrParams, config) { 
11 |   const url = `${process.env.BASE_URL}${path}`
13 |   return axios.request({ url, method, data: payloadOrParams, ...config })
14 | }

File: .env
3: BASE_URL=https://api.example.com
```

CORRECT Splitting:

Step-by-step Analysis:
"I analyzed the wrapper function connection data systematically. I found 4 outgoing connections across 2 files using wrapper functions. In src/services/notification.js, there are 2 MessageQueue publish operations. In src/services/api.js, there are 2 HTTP/HTTPS calls using the makeApiCall wrapper. All connections are outgoing since the wrapper functions are being called to send data to external systems. Each wrapper call has specific identifiers for queues or endpoints. Wrapper fuction uses BASE_URL=https://api.example.com from the provided env file."

```json
{
  "outgoing_connections": {
    "MessageQueue": {
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
    "HTTP/HTTPS": {
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

### EXAMPLE 6: SWITCH CASE CONNECTIONS
When you receive connection data with switch statements handling different connection operations:

Input Connection Data:
```
src/handlers/message.js:45: switch (messageType) {
src/handlers/message.js:46:   case 'USER_CREATED':
src/handlers/message.js:47:     await axios.post(`https://${process.env.BASE_URL}/user-service/notify`, userData)
src/handlers/message.js:48:     break;
src/handlers/message.js:49:   case 'ORDER_PLACED':
src/handlers/message.js:50:     await axios.post(`https://${process.env.BASE_URL}/order-service/process`, orderData)
src/handlers/message.js:51:     break;
src/handlers/message.js:52:   case 'PAYMENT_RECEIVED':
src/handlers/message.js:53:     await axios.put(`https://${process.env.BASE_URL}/payment-service/confirm`, paymentData)
src/handlers/message.js:54:     break;
src/handlers/message.js:55: }
src/handlers/event.js:20: switch (event.type) {
src/handlers/event.js:21:   case 'sync':
src/handlers/event.js:22:     socket.emit('data_sync', syncData)
src/handlers/event.js:23:     break;
src/handlers/event.js:24:   case 'update':
src/handlers/event.js:25:     socket.emit('data_update', updateData)
src/handlers/event.js:26:     break;
src/handlers/event.js:27:   case 'delete':
src/handlers/event.js:28:     socket.emit('data_delete', deleteData)
src/handlers/event.js:29:     break;
src/handlers/event.js:30: }

.env:3: BASE_URL=api.example.com
```

CORRECT Splitting:

Step-by-step Analysis:
"I analyzed the switch statement connection data systematically. I found 6 outgoing connections across 2 files within switch case structures. In src/handlers/message.js, there are 3 HTTP/HTTPS connections for different message types that use a single environment-based base URL with service paths; BASE_URL=api.example.com. In src/handlers/event.js, there are 3 WebSocket connections for different event types. I focused only on the actual connection operations, not the switch structure lines. Each case represents a distinct connection with specific parameters and target services."

```json
{
  "outgoing_connections": {
    "HTTP/HTTPS": {
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
    "WebSockets": {
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

## EXAMPLES OF FORBIDDEN GROUPING

### FORBIDDEN - Grouping Multiple Operations:
```json
{
  "incoming_connections": {
    "HTTP/HTTPS": {
      "src/handlers.js": [
        {
          "snippet_lines": "264-600",
          "description": "40+ REST API endpoints including /get-speech-token, /get-custom-token, /check-room, /admin routes, /super-admin routes - comprehensive incoming HTTP connection points"
        },
        {
          "snippet_lines": "604-674", 
          "description": "REST API endpoints for incoming connections - includes 45+ admin, internal, techyrr-admin, and public routes with various HTTP methods"
        }
      ]
    },
    "WebSockets": {
      "src/handlers.js": [
        {
          "snippet_lines": "15-55",
          "description": "Event handlers for multiple events including user_login, user_logout, and data_update"
        }
      ]
    }
  }
}
```

### CORRECT - Individual Connections:
```json
{
  "incoming_connections": {
    "HTTP/HTTPS": {
      "src/handlers.js": [
        {
          "snippet_lines": "264-264",
          "description": "GET /get-speech-token endpoint for speech token retrieval"
        },
        {
          "snippet_lines": "267-267",
          "description": "POST /get-custom-token endpoint for custom token generation"
        },
        {
          "snippet_lines": "270-270",
          "description": "GET /check-room endpoint for room validation"
        },
        {
          "snippet_lines": "275-275",
          "description": "GET /admin/users endpoint for admin user management"
        }
      ]
    },
    "WebSockets": {
      "src/handlers.js": [
        {
          "snippet_lines": "15-15",
          "description": "WebSocket event handler for user_login event"
        },
        {
          "snippet_lines": "25-25",
          "description": "WebSocket event handler for user_logout event"
        },
        {
          "snippet_lines": "35-35",
          "description": "WebSocket event handler for data_update event"
        }
      ]
    }
  }
}
```
```

### FORBIDDEN - Grouping Multiple Endpoints:
```json
{
  "outgoing_connections": {
    "HTTP/HTTPS": {
      "src/client.js": [
        {
          "snippet_lines": "15-31",
          "description": "HTTP requests including GET, POST, and PUT operations for user management"
        },
        {
          "snippet_lines": "50-100",
          "description": "Multiple API endpoints for order processing and payment handling"
        }
      ]
    }
  }
}
```

### CORRECT - Individual Endpoints:
```json
{
  "outgoing_connections": {
    "HTTP/HTTPS": {
      "src/client.js": [
        {
          "snippet_lines": "15-15",
          "description": "HTTP GET request to /api/users endpoint for user retrieval"
        },
        {
          "snippet_lines": "20-20",
          "description": "HTTP POST request to /api/users endpoint for user creation"
        },
        {
          "snippet_lines": "25-25",
          "description": "HTTP PUT request to /api/users/:id endpoint for user update"
        }
      ]
    }
  }
}
```
```

### FORBIDDEN - Grouping Wrapper Function Calls:
```json
{
  "outgoing_connections": {
    "HTTP/HTTPS": {
      "src/services/api.js": [
        {
          "snippet_lines": "18-45",
          "description": "Multiple API calls using makeApiCall wrapper for various endpoints"
        },
        {
          "snippet_lines": "50-80",
          "description": "Several HTTP operations including user, order, and payment API calls"
        }
      ]
    }
  }
}
```

### CORRECT - Individual Wrapper Calls:
```json
{
  "outgoing_connections": {
    "HTTP/HTTPS": {
      "src/services/api.js": [
        {
          "snippet_lines": "18-18",
          "description": "HTTP POST call using makeApiCall wrapper to /api/users endpoint for user creation"
        },
        {
          "snippet_lines": "25-25",
          "description": "HTTP GET call using makeApiCall wrapper to /api/orders endpoint for order retrieval"
        },
        {
          "snippet_lines": "32-32",
          "description": "HTTP PUT call using makeApiCall wrapper to /api/payments endpoint for payment update"
        }
      ]
    }
  }
}
```
```

## DATA EXCLUSION RULES - DO NOT SPLIT THESE

The following types of connection data should NOT be included in splitting:

### EXCLUDE 1: Generic Library Calls Without Identifiers
Connection Data That Should Be Excluded:
```
src/utils/http.js:25: await axios.get(url)
src/utils/http.js:30: await axios.post(url, data)
src/utils/socket.js:15: socket.emit(eventName, data)
```
Why Excluded: These use variable identifiers, not specific connection endpoints.

### EXCLUDE 2: Function Definitions and Imports
Connection Data That Should Be Excluded:
```
src/api/client.js:1: const axios = require('axios')
src/utils/api.js:10: function apiCallFunction(endpoint, method, data) { ... }
src/socket/handler.js:5: import { io } from 'socket.io-client'
```
Why Excluded: Library imports and generic function definitions are not actual connections.

### EXCLUDE 3: Configuration Without Actual Usage
Connection Data That Should Be Excluded:
```
src/config/settings.js:8: const API_BASE_URL = process.env.API_BASE_URL
src/config/settings.js:12: const QUEUE_CONFIG = { host: 'localhost', port: 5672 }
```
Why Excluded: Configuration definitions without actual connection usage.

### INCLUDE: Only Actual Connection Usage
Connection Data That SHOULD Be Included:
```
src/api/client.js:25: const response = await axios.get(`${process.env.API_BASE_URL}/users`)
src/services/queue.js:15: publishMessage('user-notifications', userData)
src/routes/api.js:20: app.get('/api/users', handleGetUsers)
```
Why Included: These show actual connection usage with specific identifiers or environment variables.

## STEP-BY-STEP ANALYSIS PROCESS

1. Identify env files: Look for environment file code blocks that contain variable definitions
2. Identify all connections: Scan through all code snippets and identify every individual connection
3. Resolve env variables: For each connection using environment variables, find corresponding values from env file blocks
4. Separate each connection: For each connection found, create a separate JSON entry (excluding duplicates)
5. Extract precise details: Get exact line numbers and specific details for each connection
6. Write specific descriptions: Each description must be about ONE specific connection with resolved env values when available
7. Analyze project comprehensively: Review all connections, patterns, and code structure to understand the complete project functionality
8. Generate detailed summary: Create a comprehensive project description covering purpose, architecture, integrations, and business domain

## REQUIREMENTS

1. Step-by-step Analysis: Explain your reasoning before providing the JSON response
2. Connection Counting: Count and categorize all connections by technology type and direction
3. Complete Processing: Process ALL connections - never skip or sample connections
4. Individual Separation: Never group multiple connections into one entry
5. Precise Line Numbers: Use exact line numbers for each connection location
6. Specific Descriptions: Each description must be about one connection only
7. Environment Resolution: Resolve environment variables using provided configuration files and include as ENV_VAR=actual_value
8. Technology Classification: Validate technology type classification for each connection
9. Comprehensive Summary: Generate detailed project description covering purpose, functionality, architecture, and integrations
10. Output Format: Start with detailed analysis, then return valid JSON
11. Grouping Structure: Group by technology and file path as shown in format
12. FORBIDDEN LANGUAGE: No phrases like "including", "multiple", "various", "several", "operations for", "comprehensive", "40+", "45+", numbers with plus signs
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

function AwsConnectionSplitting(memory_context: string) -> ConnectionSplittingResponse {
  client AwsClaudeSonnet4
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ ConnectionSplittingPrompt() }}
    {{ ConnectionSplittingUserPrompt(memory_context) }}
  "#
}

function AnthropicConnectionSplitting(memory_context: string) -> ConnectionSplittingResponse {
  client AnthropicClaude
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ ConnectionSplittingPrompt() }}
    {{ ConnectionSplittingUserPrompt(memory_context) }}
  "#
}

function ChatGPTConnectionSplitting(memory_context: string) -> ConnectionSplittingResponse {
  client OpenAIChatGPT
  prompt #"
    {{ _.role("system") }}
    {{ ConnectionSplittingPrompt() }}
    {{ ConnectionSplittingUserPrompt(memory_context) }}
  "#
}

