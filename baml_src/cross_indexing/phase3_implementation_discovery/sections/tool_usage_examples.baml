template_string ToolUsageExamples_Phase3() #"
====

# TOOL USAGE EXAMPLES

This section provides comprehensive examples of how to use different tools effectively for implementation discovery and connection code analysis across different programming languages.

1. TASK EXECUTION EXAMPLES

LIST_FILES TASK HANDLING EXAMPLES:

Example 1: Conditional task handling - Check for specific list_files task
WHEN you see this EXACT task: "No packages/dependencies found in previous analysis. Use list_files tool to list all files recursively in current directory to identify files that might contain connection code."
THEN use list_files approach, OTHERWISE use normal flow.

Execute list_files tool:
{
  "tool_call": {
    "tool_name": "list_files",
    "parameters": {
      "path": ".",
      "recursive": true
    }
  }
}

Example 2: Creating database tasks after list_files results
After list_files returns file list, create individual database tasks for potential connection files:

{
  "tool_call": {
    "tool_name": "database",
    "parameters": {
      "query_type": "GET_FILE_BY_PATH",
      "file_path": "index.html"
    }
  },
  "sutra_memory": {
    "tasks": [
      {
        "action": "add",
        "id": "1",
        "to_status": "current",
        "description": "Use database tool to read index.html file completely and analyze for any connection patterns: script tags importing packages (axios, socket.io), CDN imports, WebSocket connections (new WebSocket), fetch API calls, XMLHttpRequest usage, and embedded JavaScript connection code."
      },
      {
        "action": "add",
        "id": "2",
        "to_status": "pending",
        "description": "Use database tool to read server.js file completely and analyze for built-in server connections (http.createServer, net.createServer), endpoint definitions, and incoming connection handlers."
      },
      {
        "action": "add",
        "id": "3",
        "to_status": "pending",
        "description": "Use database tool to read client.js file completely and analyze for outgoing HTTP requests using built-in modules (http, https), fetch API usage, and client-side connection patterns."
      }
    ]
  }
}

DATABASE TOOL EXAMPLES (3-5 files):

Example 1: Axios usage analysis in few files
  - Purpose: Read entire file to analyze all axios method calls within that file
  - Look for: axios.get(), axios.post(), axios.put(), axios.delete() with actual parameters
  - Find: Actual API calls with real endpoints and environment variables
    {
      "sutra_memory": {
        "tasks": [
          {
            "action": "add",
            "id": "1",
            "to_status": "current",
            "description": "Use database tool to read client.js completely to find actual axios HTTP calls with real endpoints and parameters."
          },
          {
            "action": "add",
            "id": "2",
            "to_status": "pending",
            "description": "Use database tool to read api.js completely to find actual axios HTTP calls with real endpoints and parameters."
          }
        ]
      }
      "tool_call": {
        "tool_name": "database",
        "parameters": {
          "query_type": "GET_FILE_BY_PATH",
          "file_path": "src/api/client.js"
        }
      }
    }

Example 2:Requests usage analysis in specific files
  - Purpose: Read entire file to analyze all requests method calls within that file
  - Look for: requests.get(), requests.post() with actual parameters and endpoints
  - Find: Actual API calls with real URLs and configuration data
    {
      "tool_call": {
        "tool_name": "database",
        "parameters": {
          "query_type": "GET_FILE_BY_PATH",
          "file_path": "src/services/api_client.py"
        }
      }
    }

SEARCH_KEYWORD EXAMPLES (6+ files or wrapper functions):

Example 1: JavaScript - Express usage across many files
  - Purpose: Find express route definitions across multiple files efficiently
  - Look for: Route definitions with actual endpoint paths
  - Find: All route definitions found with real endpoints
    {
      "tool_call": {
        "tool_name": "search_keyword",
        "parameters": {
          "pattern": "(app|router)\.(get|post|put|delete|patch)",
          "regex": true,
          "case_sensitive": false,
          "after_lines": 2
        }
      }
    }

Example 2: Python - Flask usage across many files
  - Purpose: Find Flask route definitions across multiple files efficiently
  - Look for: Route decorators with actual endpoint paths
  - Find: All route definitions found with real endpoints
    {
      "tool_call": {
        "tool_name": "search_keyword",
        "parameters": {
          "pattern": "@app.route|@bp.route",
          "regex": true,
          "case_sensitive": false,
          "after_lines": 2
        }
      }
    }

Example 3: Multi-language - Wrapper function usage analysis
  - Purpose: Find all usage sites of wrapper functions across the codebase
  - Look for: Wrapper function calls with actual parameters
  - Find: Wrapper function calls with real endpoints and data
    {
      "tool_call": {
        "tool_name": "search_keyword",
        "parameters": {
          "pattern": "makeApiCall|apiClient|sendRequest",
          "regex": true,
          "case_sensitive": false,
          "after_lines": 3
        }
      }
    }

Example 4: HTTP calls with improved quote handling
  - Purpose: Find axios HTTP calls with actual endpoint URLs
  - Handles both single and double quotes in endpoint strings
  - Look for: HTTP method calls with real URLs and parameters
    {
      "tool_call": {
        "tool_name": "search_keyword",
        "parameters": {
          "pattern": "axios\.(get|post|put|delete)",
          "regex": true,
          "case_sensitive": false,
          "after_lines": 2
        }
      }
    }

2. CONNECTION CODE ANALYSIS

WHAT TO FIND (ACTUAL USAGE WITH REAL VALUES)

Example 1: JavaScript - HTTP API calls with real endpoints
```
// FIND THIS - actual API call with real endpoint
const response = await axios.get(`${process.env.API_BASE_URL}/users/${userId}`)

// FIND THIS - actual API call with environment variable
const result = await fetch(`${process.env.SERVICE_URL}/api/data`, {
  method: 'POST',
  body: JSON.stringify(data)
})

// FIND THIS - with single quotes
const data = await axios.post('/api/users', userData)

// FIND THIS - with double quotes
const info = await fetch("/api/orders", { method: 'GET' })
```

Example 2: Python - HTTP API calls with real endpoints
```
# FIND THIS - actual API call with real endpoint
response = requests.get(f"{os.getenv('API_BASE_URL')}/users/{user_id}")

# FIND THIS - actual API call with environment variable
result = requests.post(f"{os.getenv('SERVICE_URL')}/api/data", json=data)

# FIND THIS - with single quotes
data = requests.get('/api/users')

# FIND THIS - with double quotes
info = requests.post("/api/orders", json=order_data)
```

Example 3: JavaScript - Server routes with real endpoints
```
// FIND THIS - actual route definition with real endpoint
app.get('/api/users/:id', (req, res) => {
  // handler code
})

// FIND THIS - actual route with real path
router.post('/admin/users', authenticateAdmin, (req, res) => {
  // handler code
})

// FIND THIS - with single quotes
app.put('/api/orders/:orderId', updateOrder)

// FIND THIS - with double quotes
router.delete("/api/products/:id", deleteProduct)
```

Example 4: Python - Server routes with real endpoints
```
# FIND THIS - actual route definition with real endpoint
@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    # handler code

# FIND THIS - actual route with real path
@bp.route('/admin/users', methods=['POST'])
def create_user():
    # handler code

# FIND THIS - with single quotes
@app.route('/api/orders', methods=['POST'])
def create_order():
    # handler code

# FIND THIS - with double quotes
@bp.route("/api/products/<int:product_id>", methods=['DELETE'])
def delete_product(product_id):
    # handler code
```

Example 5: WebSocket and Queue operations with quote variations
```
// FIND THIS - WebSocket events with single quotes
socket.emit('user_joined', { userId, roomId })
io.on('connection', handleConnection)

// FIND THIS - WebSocket events with double quotes
socket.emit("message_sent", messageData)
io.on("disconnect", handleDisconnect)

// FIND THIS - Queue operations with single quotes
channel.sendToQueue('user-notifications', Buffer.from(message))

// FIND THIS - Queue operations with double quotes
producer.send("email-queue", emailData)
```

WHAT NOT TO FOCUS ON (GENERIC DEFINITIONS/CONNECTION SETUP ONLY)

Example 1: AMQP - Connection establishment WITHOUT data communication
```
// DON'T STOP HERE - connection establishment only
const amqp = require("amqp-connection-manager");
const connection = amqp.connect(process.env.URL);

// DON'T STOP HERE - channel creation without usage
const channel = connection.createChannel();

// MANDATORY: Find the actual usage like:
// channel.sendToQueue('notifications', Buffer.from(data))
// channel.consume('events', processMessage)
```

Example 2: Generic wrapper functions
```
// DON'T FOCUS ON THIS - generic wrapper function definition
function makeApiCall(url, method, data) {
  return axios({ url, method, data })
}

// DON'T FOCUS ON THIS - generic client creation
const apiClient = axios.create({
  baseURL: process.env.API_BASE_URL
})
```

Example 3: Generic wrapper functions
```
# DON'T FOCUS ON THIS - generic wrapper function definition
def make_api_call(url, method, data):
    return requests.request(method, url, json=data)

# DON'T FOCUS ON THIS - generic session creation
session = requests.Session()
session.headers.update({'Authorization': f'Bearer {token}'})
```

3. TOOL SELECTION STRATEGY

DATABASE TOOL USAGE (Few files)
When import discovery found few files (3-5):
  - Use for complete file analysis to understand all usage patterns
  - Read entire file content to analyze context and relationships between methods
  - Get comprehensive view of all connections and their actual usage within the file
  - Best for thorough analysis when dealing with limited number of files

SEARCH_KEYWORD USAGE (Many files or wrapper functions)
When import discovery found many files (6+) or wrapper functions:
  - Use targeted patterns to find specific usage across multiple files efficiently
  - Essential for wrapper function usage discovery across entire codebase
  - Essential for built-in language patterns that don't require imports
  - Include appropriate context lines (after_lines=2-3) to capture complete usage

4. TASK CREATION EXAMPLES

CRITICAL THINKING PROCESS FOR TASK CREATION - WRAPPER FUNCTION DETECTION

Before creating any task, ask yourself these specific questions in `thinking` feild:
1. "Did I find connection code with VARIABLE NAMES instead of actual hardcoded values?"
  - Examples: `sendToQueue(queueName, message)`, `axios.get(url)`, `socket.emit(eventName, data)`
  - These indicate wrapper functions that need further analysis
2. "Are these variables being passed as parameters from a calling function?"
  - This means I found the low-level implementation, not the actual usage
3. "Do I need to search for where this wrapper function is called with real connection values?"
  - YES if I see variables/parameters, NO if I see hardcoded strings
4. "Have I already found the actual usage sites with real endpoint/queue/event names?"
  - If YES, collect this data. If NO, create search tasks.

VARIABLE PARAMETER DETECTION PATTERNS:
  - Queue Operations: `queueName`, `topicName`, `channelName` → Search for wrapper calls
  - HTTP Operations: `url`, `endpoint`, `apiUrl`, `baseUrl` → Search for wrapper calls
  - Socket Operations: `eventName`, `event`, `channel` → Search for wrapper calls
  - Database Operations: `tableName`, `collection`, `query` → Search for wrapper calls

VARIABLE RESOLUTION IN SAME FILE DETECTION:
  - If variable found in connection code → First check same file for variable definition
  - If variable defined with hardcoded value → Use that value directly
  - If variable defined with env variable → Search for env file if not in sutra memory
  - Pattern: `const queueName = process.env.QUEUE_NAME` or `queue_name = "hardcoded-queue"`

## WRAPPER FUNCTION DEFINITION CHECK EXAMPLES

Example: Python - Socket wrapper function pattern (similar to Socket.IO)
```
# main.py - function call with connection object (found in one file)
from flask_socketio import SocketIO
from handlers import socket_handler

socketio = SocketIO(app)
socket_handler(socketio)  # ← Found this call in main.py

# handlers.py - actual function definition (in different file)
def socket_handler(socketio):
    @socketio.on('connect')
    def handle_connect():
        emit('status', {'msg': 'Connected'})

    @socketio.on('user_message')
    def handle_message(data):
        emit('response', {'reply': f"Got: {data['message']}"})
```

THINKING: "Found `socket_handler(socketio)` call in main.py - this is in two different files. The call passes connection object to wrapper function. Must use search_keyword to find actual function definition where io is used."
IMMEDIATE ACTION: CREATE TASK: "Use search_keyword to find socket_handler function definition: def socket_handler\("
EXPECTED RESULT: Find the actual function definition in handlers.py where socketio connection object is used for real socket operations.

## WHEN TO CREATE TASKS FOR WRAPPER FUNCTION SEARCHES - EXAMPLES

Example 1: Queue operation with variable parameter - CREATE TASK IMMEDIATELY
When you find connection code like:
```
// Found in file analysis
this.channel.sendToQueue(queueName, Buffer.from(message), {
  persistent: true,
});
```
ANALYSIS:
{
  "thinking": "Found queue operation with variable 'queueName' instead of actual queue name. This is a wrapper function implementation. I need to find where this function is called with real queue names."
}

EFFICIENT WORKFLOW:
1. First, search for wrapper function calls to find all usage sites
{
  "tool_call": {
    "tool_name": "search_keyword",
    "parameters": {
      "pattern": "publishMessage\(",
      "regex": true,
      "case_sensitive": false,
      "after_lines": 2
    }
  },
  "sutra_memory": {
    "tasks": [
      {
        "action": "add",
        "id": "21",
        "to_status": "current",
        "description": "Use search_keyword to find publishMessage wrapper function calls with actual queue names: publishMessage\("
      }
    ]
  }
}

2. IF wrapper function is using any variable values, search for variable definition across all files
{
  "tool_call": {
    "tool_name": "search_keyword",
    "parameters": {
      "pattern": "queueName\s*=",
      "regex": true,
      "case_sensitive": true,
      "after_lines": 1
    }
  },
  "sutra_memory": {
    "tasks": [
      {
        "action": "add",
        "id": "22",
        "to_status": "current",
        "description": "Search for queueName variable definition across all files if wrapper function uses variables"
      }
    ]
  }
}

3. ANALYZE RESULTS:
  - If hardcoded: `queueName = "user-notifications"` → Use this value, move to next task
  - If env variable: `queueName = process.env.QUEUE_NAME` → Check sutra memory first
  - If not in sutra memory, create task to find env definition. find env or config file using list_file tool

EXPECTED RESULT: Find calls like `publishMessage('user-notifications', data)` or resolve variable to actual queue names

Example 2: HTTP operation with variable endpoint - CREATE TASK IMMEDIATELY
When you find connection code like:
```
// Found in file analysis
const response = await axios.get(url, config);
```
ANALYSIS:
{
  "thinking": "Found HTTP call with variable 'url' instead of actual endpoint. This is wrapper function usage. I need to find where this function is called with real URLs."
}

IMMEDIATE ACTION:
1. Search for wrapper function calls with actual endpoints
{
  "tool_call": {
    "tool_name": "search_keyword",
    "parameters": {
      "pattern": "makeApiCall\(",
      "regex": true,
      "case_sensitive": false,
      "after_lines": 2
    }
  },
  "sutra_memory": {
    "tasks": [
      {
        "action": "add",
        "id": "23",
        "to_status": "current",
        "description": "Use search_keyword to find makeApiCall wrapper function calls with actual endpoints: makeApiCall\("
      }
    ]
  }
}

2. If variables found, search for variable definitions in specific files
{
  "tool_call": {
    "tool_name": "search_keyword",
    "parameters": {
      "pattern": "url\s*=",
      "file_paths": "src/api/client.js,src/services/http.js",
      "regex": true,
      "case_sensitive": true,
      "after_lines": 1
    }
  }
}

EXPECTED RESULT: Find calls like `makeApiCall('/api/users', 'GET')`, `makeApiCall('/admin/data', 'POST', userData)`

Example 3: Message queue wrapper function with dynamic topics - CREATE TASK
When you find a queue wrapper function like:
```
def publish_message(topic, message_data):
    return publisher.send(topic, json.dumps(message_data))
```
ANALYSIS:
{
  "thinking": "Found a message queue wrapper function that takes dynamic topic parameter. I need to search for all publish_message() calls to find the actual topics and message types being sent."
}

ACTION:
{
  "tool_call": {
    "tool_name": "search_keyword",
    "parameters": {
      "pattern": "publish_message\(",
      "regex": true,
      "case_sensitive": false,
      "after_lines": 2
    }
  },
  "sutra_memory": {
    "tasks": [
      {
        "action": "add",
        "id": "24",
        "to_status": "current",
        "description": "Use search_keyword to find all publish_message( wrapper function usage: publish_message\("
      }
    ]
  }
}

EXPECTED RESULT: Find all actual usage sites to collect the real topics and message data being published

Example 4: Socket wrapper function with dynamic events - CREATE TASK
When you find a socket wrapper function like:
```
function emitEvent(eventName, eventData) {
  return socket.emit(eventName, eventData)
}
```
ANALYSIS:
{
  "thinking": "This wrapper function takes dynamic event name and data parameters. I need to find all emitEvent() calls to see what events are being emitted."
}

ACTION:
{
  "tool_call": {
    "tool_name": "search_keyword",
    "parameters": {
      "pattern": "emitEvent\(",
      "regex": true,
      "case_sensitive": false,
      "after_lines": 2
    }
  },
  "sutra_memory": {
    "tasks": [
      {
        "action": "add",
        "id": "28",
        "to_status": "current",
        "description": "Use search_keyword to find all emitEvent( wrapper function calls: emitEvent\("
      }
    ]
  }
}

EXPECTED RESULT: Find all usage sites to collect the actual event names and data being emitted

Example 5: Custom client class with dynamic communication methods - CREATE TASK
When you find a custom client class like:
```
class ServiceClient:
    def send_request(self, service_name, action, payload): ...
    def subscribe_to_events(self, channel, callback): ...
```
ANALYSIS:
{
  "thinking": "Found a custom service client class with dynamic parameters. I need to search for all instances where this client is used to find the actual services, actions, and channels being used."
}

ACTION:
ACTION:
{
  "tool_call": {
    "tool_name": "search_keyword",
    "parameters": {
      "pattern": "serviceClient\(",
      "regex": true,
      "case_sensitive": false,
      "after_lines": 2
    }
  },
  "sutra_memory": {
    "tasks": [
      {
        "action": "add",
        "id": "29",
        "to_status": "current",
        "description": "Use search_keyword to find all serviceClient usage patterns: serviceClient\("
      }
    ]
  }
}

EXPECTED RESULT: Find all method calls on this custom client across the project with real service communication parameters

Example 8: Complete variable resolution workflow - EFFICIENT APPROACH
SCENARIO: Found wrapper function with variable parameters across multiple files

ANALYSIS:
{
  "thinking": "Found wrapper function with variables. I need to efficiently resolve these variables by first finding config files directly, then searching in specific files only."
}

STEP 1: Search for wrapper function usage across codebase
{
  "tool_call": {
    "tool_name": "search_keyword",
    "parameters": {
      "pattern": "sendMessage\(",
      "regex": true,
      "case_sensitive": false,
      "after_lines": 2
    }
  },
  "sutra_memory": {
    "tasks": [
      {
        "action": "add",
        "id": "27",
        "to_status": "current",
        "description": "Find sendMessage wrapper function usage across codebase"
      }
    ]
  }
}

RESULT: Found wrapper function in 2 files:
- src/services/notification.js: `sendMessage(queueName, data)`
- src/handlers/email.js: `sendMessage(topicName, emailData)`

STEP 2: Search for variable definitions in those specific files
{
  "tool_call": {
    "tool_name": "search_keyword",
    "parameters": {
      "pattern": "(queueName|topicName)\s*=",
      "file_paths": "src/services/notification.js, src/handlers/email.js",
      "regex": true,
      "case_sensitive": true,
      "after_lines": 1
    }
  }
}

STEP 3: ANALYZE RESULTS:
Case A - Hardcoded values found:
```
// In notification.js
const queueName = "user-notifications"
// In email.js
const topicName = "email-processing"
```
ACTION: Use these values directly, move to next task

Case B - Environment variables found:
```
// In notification.js
const queueName = process.env.NOTIFICATION_QUEUE
// In email.js
const topicName = process.env.EMAIL_TOPIC
```
ACTION: Check sutra memory for these env variables

Case C - If env variables NOT in sutra memory, find config files directly:
{
  "tool_call": {
    "tool_name": "list_files",
    "parameters": {
      "path": ".",
      "recursive": true
    }
  }
}
then read config files directly
{
  "tool_call": {
    "tool_name": "database",
    "parameters": {
      "query_type": "GET_FILE_BY_PATH",
      "file_path": ".env"
    }
  }
}

Case D - Fallback to search_keyword only if no config files found:
{
  "tool_call": {
    "tool_name": "search_keyword",
    "parameters": {
      "pattern": "NOTIFICATION_QUEUE|EMAIL_TOPIC",
      "regex": true,
      "case_sensitive": true,
      "after_lines": 1
    }
  }
}

EXPECTED RESULT: Resolve all variables to actual connection values efficiently without reading entire files

Example 6: Environment variable in wrapper function - EFFICIENT CONFIG FILE DISCOVERY
When you find connection code with environment variables like:
```
// Found in file analysis
const response = await axios.get(`${process.env.API_BASE_URL}/users/${userId}`)
```

ANALYSIS:
{
  "thinking": "Found environment variable 'API_BASE_URL'. Instead of searching through all files, I should first try to find .env or config files directly using list_files, then read them directly."
}

EFFICIENT WORKFLOW:

STEP 1: Check sutra memory first
- If API_BASE_URL already in sutra memory → Use that value, continue to next task

STEP 2: If NOT in sutra memory, find config files directly
{
  "tool_call": {
    "tool_name": "list_files",
    "parameters": {
      "path": ".",
      "recursive": true
    }
  },
  "sutra_memory": {
    "tasks": [
      {
        "action": "add",
        "id": "25",
        "to_status": "current",
        "description": "Find .env files to locate API_BASE_URL environment variable"
      }
    ]
  }
}

STEP 3: Read found config files directly
{
  "tool_call": {
    "tool_name": "database",
    "parameters": {
      "query_type": "GET_FILE_BY_PATH",
      "file_path": ".env"
    }
  }
}

STEP 4: Only if no config files found, fallback to search_keyword
{
  "tool_call": {
    "tool_name": "search_keyword",
    "parameters": {
      "pattern": "API_BASE_URL",
      "regex": false,
      "case_sensitive": true,
      "after_lines": 1
    }
  }
}

EXPECTED RESULT: Find environment variable definition efficiently by directly accessing config files

## WHEN NOT TO CREATE TASKS - DECISION MAKING

Example 1: Already found actual connection usage with hardcoded values - DON'T CREATE TASK
When you find direct connection calls with real parameters:
```
// Direct HTTP calls with actual endpoints
const result = await axios.get('/api/users', config)
const response = await fetch('https://api.service.com/data', options)
const data = await axios.post("/api/orders", orderData)

// Direct queue operations with actual queue names
channel.sendToQueue('user-notifications', Buffer.from(message))
producer.send('email-queue', emailData)
channel.sendToQueue("order-processing", Buffer.from(orderData))

// Direct socket operations with actual event names
socket.emit('user-joined', { userId, roomId })
io.emit('status-update', statusData)
socket.emit("message-sent", messageData)
```
THINKING: "These are direct connection calls with hardcoded connection details (actual endpoints, queue names, event names). This IS the actual connection code I need to collect."
DON'T CREATE TASK: This is already actual connection code with real values - collect this data immediately

Example 2: Already found actual queue usage with real topics - DON'T CREATE TASK
When you find actual message queue calls with real topics:
```
publish_message('user_created', user_data)
publish_message('order_processed', order_info)
```
THINKING: "These are actual queue publish calls with real topic names and data. This is the connection code I need to collect."
DON'T CREATE TASK: This is already actual connection code showing real message topics

Example 3: Already found actual socket usage with real events - DON'T CREATE TASK
When you find actual socket calls with real event names:
```
emitEvent('room_joined', { userId, roomId })
emitEvent('message_sent', messageData)
emitEvent("user_status_update", statusData)
```
THINKING: "These are actual socket emit calls with real event names and data. This is the connection code I need to collect."
DON'T CREATE TASK: This is already actual connection code showing real socket events

Example 4: Direct library usage with real communication parameters - DON'T CREATE TASK
When you find direct library calls with real communication details:
```
# HTTP communication
response = requests.get(f"{os.getenv('API_URL')}/users/{user_id}")
# Queue communication
producer.send('user_events', value=json.dumps(event_data))
# Socket communication
socket.emit('status_update', {'status': 'online', 'userId': user_id})
```
THINKING: "These are direct library calls with actual communication parameters. This is the connection code I need to collect."
DON'T CREATE TASK: This is already actual connection code, not wrapper function usage

Example 5: Wrapper function with hardcoded communication details - DON'T CREATE TASK
When you find wrapper functions with hardcoded communication parameters:
```
function sendNotification() {
  return axios.post('https://api.notifications.com/send', notificationData)
}
function publishUserEvent() {
  return publisher.send('user_topic', eventData)
}
```
THINKING: "These wrapper functions have hardcoded communication details. The actual connection information is already visible here."
DON'T CREATE TASK: The communication parameters are hardcoded, so this is the actual connection information

5. DECISION-MAKING FLOWCHART FOR TASK CREATION

STEP-BY-STEP THINKING PROCESS

When you find any code during analysis, follow this thinking process:

1. IDENTIFY: "What type of code did I find?"
  - Direct library call (HTTP: axios.get, requests.post; Queue: producer.send, consumer.subscribe; Socket: socket.emit, io.on)
  - Wrapper function definition (function apicall(...), def publish_message(...), function emitEvent(...))
  - Wrapper function usage (apicall('/api/users'), publish_message('user_topic', data), emitEvent('join_room', roomData))
  - Configuration/setup code

2. ANALYZE PARAMETERS: "Are the parameters dynamic or hardcoded?"
  - Dynamic: Takes variables, environment variables, function parameters (endpoints, topics, event names, channels)
  - Hardcoded: Has fixed strings (URLs, topic names, event names, channel names)

3. DECIDE: "Do I need to search further?"
  - If wrapper function definition with dynamic parameters → CREATE TASK to find usage
  - If wrapper function usage with real values → DON'T CREATE TASK (collect this code)
  - If direct library call with real values → DON'T CREATE TASK (collect this code)
  - If wrapper function with hardcoded values → DON'T CREATE TASK (collect this code)

4. THINK EXPLICITLY: Always include your reasoning with specific examples
  - "THINKING: Found queue operation `sendToQueue(queueName, message)` with variable 'queueName'. This is wrapper function implementation. Need to search for actual calls with real queue names. so, i will create a task to find actual calls with real queue names."
  - "THINKING: Found HTTP call `axios.get(url, config)` with variable 'url'. This is wrapper function usage. Need to search for actual calls with real endpoints. so, i will create a task to find actual calls with real endpoints."
  - "THINKING: Found direct queue call `sendToQueue('user-notifications', message)` with hardcoded queue name. This IS the actual connection code to collect."
  - "THINKING: Found direct HTTP call `axios.get('/api/users')` with hardcoded endpoint. This IS the actual connection code to collect."

5. SPECIFIC QUEUE EXAMPLE WORKFLOW:

  SCENARIO: Found this code during analysis
    ```
    // Line 49-51 in message-service.js
    this.channel.sendToQueue(queueName, Buffer.from(message), {
      persistent: true,
    });
    ```

  CORRECT ANALYSIS PROCESS:
    1. DETECT: "Found `sendToQueue(queueName, message)` with variable 'queueName' - this is NOT the actual queue name"
    2. IDENTIFY: "This is a wrapper function implementation, not the actual usage site"
    3. READ FILE: Use database tool to read complete message-service.js file
    4. FIND WRAPPER: Look for function name containing this code (e.g., `publishMessage`, `sendNotification`, etc.)
    5. CREATE TASK: "Use search_keyword to find [wrapperFunctionName] calls with actual queue names: [wrapperFunctionName]\("
    6. EXPECTED RESULTS: Find calls like:
      - `publishMessage('user-notifications', userData)`
      - `publishMessage('email-queue', emailData)`
      - `publishMessage('order-processing', orderData)`

  WRONG APPROACH (WHAT NOT TO DO):
    - Collecting `sendToQueue(queueName, message)` as final connection data
    - Moving to next task without searching for actual queue names
    - Accepting variable names as connection endpoints

6. COMPLETION EXAMPLES

ATTEMPT_COMPLETION USAGE

Example 1: Multi-language comprehensive implementation discovery
  - Purpose: Complete implementation discovery after analyzing all connection patterns
  - Result: Comprehensive summary of all discovered connections across the codebase
    {
      "tool_call": {
        "tool_name": "attempt_completion",
        "parameters": {
          "result": "Implementation discovery complete. Analyzed connection usage in 20 files across JavaScript and Python: found 35 HTTP API calls, 18 server routes, 12 WebSocket connections, and 8 message queue operations. All connection code found and analyzed."
        }
      }
    }

Example 2: Wrapper function analysis completion
  - Purpose: Complete analysis after discovering all wrapper function usage patterns
  - Result: Summary of wrapper function analysis with real endpoint discoveries
    {
      "tool_call": {
        "tool_name": "attempt_completion",
        "parameters": {
          "result": "Implementation discovery complete. Found 45 wrapper function calls across 15 files with real endpoints and parameters. All connection implementations found and analyzed for data splitting."
        }
      }
    }

7. CRITICAL GUIDELINES
  - Execute ALL pending tasks from import pattern discovery systematically
  - Use tool selection guidance provided in tasks from previous phase
  - Focus on actual usage with real parameters, not generic definitions
  - Connection code is handled automatically after each tool call
  - Create additional tasks within implementation discovery when discovering new patterns
  - ALWAYS THINK EXPLICITLY about whether you need to create tasks for further searching
"#
