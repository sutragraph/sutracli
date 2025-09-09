template_string ToolUsageExamples_Phase3() #"
====

# TOOL USAGE EXAMPLES

This section provides comprehensive examples of how to use different tools effectively for implementation discovery and connection code analysis across different programming languages.

1. TASK EXECUTION EXAMPLES

DATABASE TOOL EXAMPLES (3-5 files)

Example 1: JavaScript - Axios usage analysis in few files
- database(query_type="GET_FILE_BY_PATH", file_path="src/api/client.js")
- Purpose: Read entire file to analyze all axios method calls within that file
- Look for: axios.get(), axios.post(), axios.put(), axios.delete() with actual parameters
- Find: Actual API calls with real endpoints and environment variables

Example 2: Python - Requests usage analysis in specific files
- database(query_type="GET_FILE_BY_PATH", file_path="src/services/api_client.py")
- Purpose: Read entire file to analyze all requests method calls within that file
- Look for: requests.get(), requests.post() with actual parameters and endpoints
- Find: Actual API calls with real URLs and configuration data

SEARCH_KEYWORD EXAMPLES (6+ files or wrapper functions)

Example 1: JavaScript - Express usage across many files
- search_keyword("(app|router)\\.(get|post|put|delete|patch)\\s*\\(", regex=true, after_lines=2)
- Purpose: Find express route definitions across multiple files efficiently
- Look for: Route definitions with actual endpoint paths
- Find: All route definitions found with real endpoints

Example 2: Python - Flask usage across many files
- search_keyword("@(app|bp)\\.route\\s*\\(\\s*['\"][^'\"]*['\"]", regex=true, after_lines=2)
- Purpose: Find Flask route definitions across multiple files efficiently
- Look for: Route decorators with actual endpoint paths
- Find: All route definitions found with real endpoints

Example 3: Multi-language - Wrapper function usage analysis
- search_keyword("(makeApiCall|apiClient\\.|sendRequest)\\s*\\(", regex=true, after_lines=3)
- Purpose: Find all usage sites of wrapper functions across the codebase
- Look for: Wrapper function calls with actual parameters
- Find: Wrapper function calls with real endpoints and data

Example 4: HTTP calls with improved quote handling
- search_keyword("axios\\.(get|post|put|delete)\\s*\\(\\s*['\"][^'\"]*['\"]", regex=true, after_lines=2)
- Purpose: Find axios HTTP calls with actual endpoint URLs
- Handles both single and double quotes in endpoint strings
- Look for: HTTP method calls with real URLs and parameters

2. CONNECTION CODE ANALYSIS

WHAT TO FIND (ACTUAL USAGE WITH REAL VALUES)

Example 1: JavaScript - HTTP API calls with real endpoints
```javascript
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
```python
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
```javascript
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
```python
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
```javascript
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

WHAT NOT TO FOCUS ON (GENERIC DEFINITIONS)

Example 1: JavaScript - Generic wrapper functions
```javascript
// DON'T FOCUS ON THIS - generic wrapper function definition
function makeApiCall(url, method, data) {
  return axios({ url, method, data })
}

// DON'T FOCUS ON THIS - generic client creation
const apiClient = axios.create({
  baseURL: process.env.API_BASE_URL
})
```

Example 2: Python - Generic wrapper functions
```python
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

Before creating any task, ask yourself these specific questions:
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

WRAPPER FUNCTION DEFINITION CHECK EXAMPLES

Example: Python - Socket wrapper function pattern (similar to Socket.IO)
```python
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
IMMEDIATE ACTION: CREATE TASK: "Use search_keyword to find socket_handler function definition: def socket_handler\\("
EXPECTED RESULT: Find the actual function definition in handlers.py where socketio connection object is used for real socket operations.

WHEN TO CREATE TASKS FOR WRAPPER FUNCTION SEARCHES - EXAMPLES

Example 1: Queue operation with variable parameter - CREATE TASK IMMEDIATELY
When you find connection code like:
```javascript
// Found in file analysis
this.channel.sendToQueue(queueName, Buffer.from(message), {
  persistent: true,
});
```
THINKING: "I found queue operation with variable 'queueName' instead of actual queue name. This is a wrapper function implementation. I need to find where this function is called with real queue names."
IMMEDIATE ACTION:
1. Read complete file to find wrapper function name (e.g., `publishMessage`)
2. CREATE TASK: {
  "sutra_memory": {
    "tasks": [
      {
        "action": "add",
        "id": "21", 
        "to_status": "current",
        "description": "Use search_keyword to find publishMessage wrapper function calls with actual queue names: publishMessage\\s*\\(\\s*['\"][^'\"]*['\"]"
      }
    ]
  }
}
EXPECTED RESULT: Find calls like `publishMessage('user-notifications', data)`, `publishMessage('email-queue', emailData)`

Example 2: HTTP operation with variable endpoint - CREATE TASK IMMEDIATELY
When you find connection code like:
```javascript
// Found in file analysis
const response = await axios.get(url, config);
```
THINKING: "I found HTTP call with variable 'url' instead of actual endpoint. This is wrapper function usage. I need to find where this function is called with real URLs."
IMMEDIATE ACTION:
1. Read complete file to find wrapper function name (e.g., `makeApiCall`)
2. CREATE TASK: {
  "sutra_memory": {
    "tasks": [
      {
        "action": "add",
        "id": "22",
        "to_status": "current", 
        "description": "Use search_keyword to find makeApiCall wrapper function calls with actual endpoints: makeApiCall\\s*\\(\\s*['\"][^'\"]*['\"]"
      }
    ]
  }
}
EXPECTED RESULT: Find calls like `makeApiCall('/api/users', 'GET')`, `makeApiCall('/admin/data', 'POST', userData)`

Example 2: Message queue wrapper function with dynamic topics - CREATE TASK
When you find a queue wrapper function like:
```python
def publish_message(topic, message_data):
    return publisher.send(topic, json.dumps(message_data))
```
THINKING: "I found a message queue wrapper function that takes dynamic topic parameter. I need to search for all publish_message() calls to find the actual topics and message types being sent."
CREATE TASK: {
  "sutra_memory": {
    "tasks": [
      {
        "action": "add",
        "id": "22",
        "to_status": "current",
        "description": "Use search_keyword to find all publish_message( wrapper function usage: publish_message\\s*\\(\\s*['\"][^'\"]*['\"]"
      }
    ]
  }
}
Reason: Need to find all actual usage sites to collect the real topics and message data being published

Example 3: Socket wrapper function with dynamic events - CREATE TASK
When you find a socket wrapper function like:
```javascript
function emitEvent(eventName, eventData) {
  return socket.emit(eventName, eventData)
}
```
THINKING: "This wrapper function takes dynamic event name and data parameters. I need to find all emitEvent() calls to see what events are being emitted."
CREATE TASK: {
  "sutra_memory": {
    "tasks": [
      {
        "action": "add",
        "id": "23",
        "to_status": "current",
        "description": "Use search_keyword to find all emitEvent( wrapper function calls: emitEvent\\s*\\(\\s*['\"][^'\"]*['\"]"
      }
    ]
  }
}
Reason: Need to find all usage sites to collect the actual event names and data being emitted

Example 4: Custom client class with dynamic communication methods - CREATE TASK
When you find a custom client class like:
```python
class ServiceClient:
    def send_request(self, service_name, action, payload): ...
    def subscribe_to_events(self, channel, callback): ...
```
THINKING: "I found a custom service client class with dynamic parameters. I need to search for all instances where this client is used to find the actual services, actions, and channels being used."
CREATE TASK: {
  "sutra_memory": {
    "tasks": [
      {
        "action": "add",
        "id": "24",
        "to_status": "current",
        "description": "Use search_keyword to find all serviceClient usage patterns: serviceClient\\.(send_request|subscribe_to_events)\\s*\\("
      }
    ]
  }
}
Reason: Need to find all method calls on this custom client across the project with real service communication parameters

WHEN NOT TO CREATE TASKS - DECISION MAKING

Example 1: Already found actual connection usage with hardcoded values - DON'T CREATE TASK
When you find direct connection calls with real parameters:
```javascript
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
```python
publish_message('user_created', user_data)
publish_message('order_processed', order_info)
```
THINKING: "These are actual queue publish calls with real topic names and data. This is the connection code I need to collect."
DON'T CREATE TASK: This is already actual connection code showing real message topics

Example 3: Already found actual socket usage with real events - DON'T CREATE TASK
When you find actual socket calls with real event names:
```javascript
emitEvent('room_joined', { userId, roomId })
emitEvent('message_sent', messageData)
emitEvent("user_status_update", statusData)
```
THINKING: "These are actual socket emit calls with real event names and data. This is the connection code I need to collect."
DON'T CREATE TASK: This is already actual connection code showing real socket events

Example 4: Direct library usage with real communication parameters - DON'T CREATE TASK
When you find direct library calls with real communication details:
```python
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
```javascript
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
     - "THINKING: Found queue operation `sendToQueue(queueName, message)` with variable 'queueName'. This is wrapper function implementation. Need to search for actual calls with real queue names."
     - "THINKING: Found HTTP call `axios.get(url, config)` with variable 'url'. This is wrapper function usage. Need to search for actual calls with real endpoints."
     - "THINKING: Found direct queue call `sendToQueue('user-notifications', message)` with hardcoded queue name. This IS the actual connection code to collect."
     - "THINKING: Found direct HTTP call `axios.get('/api/users')` with hardcoded endpoint. This IS the actual connection code to collect."

5. SPECIFIC QUEUE EXAMPLE WORKFLOW:
   
   SCENARIO: Found this code during analysis
   ```javascript
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
   5. CREATE TASK: "Use search_keyword to find [wrapperFunctionName] calls with actual queue names: [wrapperFunctionName]\\("
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
attempt_completion(result="Implementation discovery complete. Analyzed connection usage in 20 files across JavaScript and Python: found 35 HTTP API calls, 18 server routes, 12 WebSocket connections, and 8 message queue operations. All connection code found and analyzed.")

Example 2: Wrapper function analysis
attempt_completion(result="Implementation discovery complete. Found 45 wrapper function calls across 15 files with real endpoints and parameters. All connection implementations found and analyzed for data splitting.")

7. CRITICAL GUIDELINES
- Execute ALL pending tasks from import pattern discovery systematically
- Use tool selection guidance provided in tasks from previous phase
- Focus on actual usage with real parameters, not generic definitions
- Connection code is handled automatically after each tool call
- Create additional tasks within implementation discovery when discovering new patterns
- ALWAYS THINK EXPLICITLY about whether you need to create tasks for further searching
"#
