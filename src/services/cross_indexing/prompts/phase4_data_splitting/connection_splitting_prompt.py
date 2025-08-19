"""
Connection Splitting Prompt

This prompt receives collected connection data from sutra memory and splits it into 
incoming and outgoing connections with detailed JSON format for database storage.
"""

CONNECTION_SPLITTING_PROMPT = """CONNECTION SPLITTING ANALYSIS

You will receive connection data of cross-indexing analysis. Your task is to split this data into incoming and outgoing connections and return them in the required JSON format. Additionally, include a concise top-level "summary" describing what the project does based on the collected connections.

## ABSOLUTE CRITICAL RULE - ONE CONNECTION PER SNIPPET

MANDATORY: Each snippet entry must represent EXACTLY ONE connection. You are FORBIDDEN from grouping multiple connections together.

EXAMPLES OF FORBIDDEN GROUPING:
- "Message handlers for incoming events including eventA, eventB, eventC"
- "API endpoints including endpointX, endpointY, endpointZ"  
- "Multiple operations for data processing"
- "Connection handlers including X, Y, Z"

REQUIRED APPROACH:
- "Message handler for eventA"
- "Message handler for eventB"  
- "Message handler for eventC"
- "GET /endpointX for data retrieval"
- "POST /endpointY for data creation"

## OBJECTIVE

Process the collected connection data and categorize each connection as either incoming or outgoing, then return structured JSON with complete connection details. Each connection must be a separate entry with its own specific line numbers and description.

## CONNECTION CLASSIFICATION

### INCOMING CONNECTIONS
Connections where OTHER services connect TO this service:
Examples:
- API endpoints and route handlers (Express routes, Flask routes, etc.)
- WebSocket server endpoints that accept connections
- Message queue consumers that receive messages
- Server configurations that listen for connections

### OUTGOING CONNECTIONS  
Connections where THIS service connects TO other services
Examples:
- HTTP client calls (axios, fetch, requests, etc.)
- WebSocket client connections to other services
- Message queue producers that send messages

## PROCESSING RULES

1. Analyze each connection individually - never group multiple connections
2. Create separate entries - If you find code with multiple operations, create separate entries for each
3. Extract individual details - Each entry gets its own specific line numbers and operation details
4. Focus on data transmission - Only code that sends or receives data, exclude setup
5. Include complete parameter details:
   - Exact endpoints, event names, queue names, method names
   - Protocols, methods, parameters
   - Environment variables and their resolved values in descriptions using format ENV_VAR=actual_value
   - File paths and line numbers
6. Classify direction correctly based on data flow
7. No duplicates - each data transmission operation must be unique

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

## OUTPUT FORMAT

Return ONLY a valid JSON response with this exact structure:

```json
{
  "incoming_connections": {
    "technology_name": {
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
    "technology_name": {
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
  "summary": "Brief summary of the project's purpose and main data flows based on observed connections"
}
```

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
- For multi-line connections: "23-27" (only if they're truly one logical connection)
- Never use large ranges that span multiple different connections

## EXAMPLES OF CORRECT SEPARATION

### EXAMPLE 1: HTTP API CALLS WITH LITERAL ENDPOINTS
When you receive connection data with HTTP API calls:

**Input Connection Data:**
```
src/api/client.js:15: axios.post('/admin/users', userData)
src/api/client.js:23: axios.get('/api/orders', params)
src/api/client.js:31: makeApiCall('/admin/users', 'POST', userData)
src/api/client.js:45: makeApiCall('/api/orders', 'GET', params)
```

**CORRECT Splitting:**
```json
{
  "outgoing_connections": {
    "http_client": {
      "src/api/client.js": [
        {
          "snippet_lines": "15-15",
          "description": "HTTP POST call to /admin/users endpoint for user creation"
        },
        {
          "snippet_lines": "23-23",
          "description": "HTTP GET call to /api/orders endpoint for order retrieval"
        },
        {
          "snippet_lines": "31-31",
          "description": "HTTP POST call using makeApiCall wrapper to /admin/users endpoint for user creation"
        },
        {
          "snippet_lines": "45-45",
          "description": "HTTP GET call using makeApiCall wrapper to /api/orders endpoint for order retrieval"
        }
      ]
    }
  }
}
```

### EXAMPLE 2: ENVIRONMENT VARIABLE CONFIGURATIONS
When you receive connection data with environment variables and their values:

**Input Connection Data:**
```
src/config/api.js:12: const response = await axios.get(`${process.env.API_BASE_URL}/update/data`)
src/config/queue.js:8: const queueName = process.env.QUEUE_NAME || 'default-queue'
src/config/api.js:20: const apiUrl = 'http://localhost:3000/api'
```

**Environment Variables (if provided):**
```
API_BASE_URL=http://localhost:3001
QUEUE_NAME=user-processing
```

**CORRECT Splitting:**
```json
{
  "outgoing_connections": {
    "http_client": {
      "src/config/api.js": [
        {
          "snippet_lines": "12-12",
          "description": "HTTP GET call using environment variable API_BASE_URL=http://localhost:3001 for endpoint /update/data"
        },
        {
          "snippet_lines": "20-20",
          "description": "Static API URL configuration for http://localhost:3000/api endpoint"
        }
      ]
    },
    "message_queue": {
      "src/config/queue.js": [
        {
          "snippet_lines": "8-8",
          "description": "Queue name configuration using environment variable QUEUE_NAME=user-processing with fallback to default-queue"
        }
      ]
    }
  }
}
```

### EXAMPLE 3: SOCKET EVENTS AND MESSAGE HANDLERS
When you receive connection data with WebSocket and message queue operations:

**Input Connection Data:**
```
src/socket/handlers.js:15: socket.emit('user_status_update', data)
src/socket/handlers.js:23: socket.emit('order_notification', orderData)
src/socket/server.js:30: socket.on('user_login', handleUserLogin)
src/socket/server.js:35: socket.on('user_logout', handleUserLogout)
src/queue/consumer.js:42: queue.consume('order-processing', handler)
```

**CORRECT Splitting:**
```json
{
  "outgoing_connections": {
    "websocket": {
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
    },
    "message_queue": {
      "src/queue/consumer.js": [
        {
          "snippet_lines": "42-42",
          "description": "Message queue consumer for order-processing queue"
        }
      ]
    }
  },
  "incoming_connections": {
    "websocket": {
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
    }
  }
}
```

### EXAMPLE 4: EXPRESS ROUTE HANDLERS
When you receive connection data with API route definitions:

**Input Connection Data:**
```
src/routes/users.js:10: app.get('/api/users', getUsersHandler)
src/routes/users.js:15: app.post('/api/users', createUserHandler)
src/routes/orders.js:8: router.get('/orders/:id', getOrderHandler)
src/routes/orders.js:12: router.put('/orders/:id', updateOrderHandler)
```

**CORRECT Splitting:**
```json
{
  "incoming_connections": {
    "express_routes": {
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
  }
}
```

### EXAMPLE 5: WRAPPER FUNCTIONS WITH SPECIFIC IDENTIFIERS
When you receive connection data with wrapper function calls:

**Input Connection Data:**
```
src/services/notification.js:25: publishMessage('user-notifications', data)
src/services/notification.js:30: publishMessage('order-updates', orderData)
src/services/api.js:18: makeApiCall('/admin/users', 'POST', userData)
src/services/api.js:22: makeApiCall('/api/orders', 'GET', params)
```

**CORRECT Splitting:**
```json
{
  "outgoing_connections": {
    "message_queue": {
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
    "http_client": {
      "src/services/api.js": [
        {
          "snippet_lines": "18-18",
          "description": "HTTP POST call using makeApiCall wrapper to /admin/users endpoint for user creation"
        },
        {
          "snippet_lines": "22-22",
          "description": "HTTP GET call using makeApiCall wrapper to /api/orders endpoint for order retrieval"
        }
      ]
    }
  }
}
```

## EXAMPLES OF FORBIDDEN GROUPING

### FORBIDDEN - Grouping Multiple Operations:
```json
{
  "incoming_connections": {
    "event_system": {
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

### FORBIDDEN - Grouping Multiple Endpoints:
```json
{
  "outgoing_connections": {
    "http_client": {
      "src/client.js": [
        {
          "snippet_lines": "15-31",
          "description": "HTTP requests including GET, POST, and PUT operations for user management"
        }
      ]
    }
  }
}
```

### FORBIDDEN - Grouping Wrapper Function Calls:
```json
{
  "outgoing_connections": {
    "http_client": {
      "src/services/api.js": [
        {
          "snippet_lines": "18-45",
          "description": "Multiple API calls using makeApiCall wrapper for various endpoints"
        }
      ]
    }
  }
}
```

## DATA EXCLUSION RULES - DO NOT SPLIT THESE

The following types of connection data should NOT be included in splitting:

### EXCLUDE 1: Generic Library Calls Without Identifiers
**Connection Data That Should Be Excluded:**
```
src/utils/http.js:25: await axios.get(url)
src/utils/http.js:30: await axios.post(url, data)
src/utils/socket.js:15: socket.emit(eventName, data)
```
**Why Excluded:** These use variable identifiers, not specific connection endpoints.

### EXCLUDE 2: Function Definitions and Imports
**Connection Data That Should Be Excluded:**
```
src/api/client.js:1: const axios = require('axios')
src/utils/api.js:10: function apiCallFunction(endpoint, method, data) { ... }
src/socket/handler.js:5: import { io } from 'socket.io-client'
```
**Why Excluded:** Library imports and generic function definitions are not actual connections.

### EXCLUDE 3: Configuration Without Actual Usage
**Connection Data That Should Be Excluded:**
```
src/config/settings.js:8: const API_BASE_URL = process.env.API_BASE_URL
src/config/settings.js:12: const QUEUE_CONFIG = { host: 'localhost', port: 5672 }
```
**Why Excluded:** Configuration definitions without actual connection usage.

### INCLUDE: Only Actual Connection Usage
**Connection Data That SHOULD Be Included:**
```
src/api/client.js:25: const response = await axios.get(`${process.env.API_BASE_URL}/users`)
src/services/queue.js:15: publishMessage('user-notifications', userData)
src/routes/api.js:20: app.get('/api/users', handleGetUsers)
```
**Why Included:** These show actual connection usage with specific identifiers or environment variables.

## STEP-BY-STEP ANALYSIS PROCESS

1. Identify all connections: Scan through all code snippets and identify every individual connection
2. Separate each connection: For each connection found, create a separate JSON entry
3. Extract precise details: Get exact line numbers and specific details for each connection
4. Write specific descriptions: Each description must be about ONE specific connection

## CRITICAL REQUIREMENTS

1. Process all connections - never skip or sample connections
2. Separate all connections - never group multiple connections into one entry
3. Use exact line numbers - be precise about where each connection is located
4. Write specific descriptions - each description must be about one connection only
5. Return valid JSON only - no additional text or explanations
6. No phrases like: "including", "multiple", "various", "several", "operations for"

## RESPONSE REQUIREMENTS

- Return ONLY valid JSON with no additional text
- Process every single connection from sutra memory data
- Create separate entries for each individual connection
- Use precise line numbers for each connection
- Write specific descriptions for each connection
- Include environment variable information in descriptions using format ENV_VAR=actual_value when values are provided
- Group by technology and file path as shown in format

Remember: If you find 26 different connections, you must create 26 separate JSON entries. No exceptions.
"""
