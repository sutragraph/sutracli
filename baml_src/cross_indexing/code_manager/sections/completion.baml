template_string Completion_Manager() #"
====

CODE MANAGER OUTPUT FORMAT

The Code Manager is responsible for determining what connection-related code should be extracted and returned based on tool results from cross-indexing analysis. The Code Manager receives tool results and outputs JSON format specifying exactly what connection code to return with proper file paths, line ranges, and descriptions.

Core Responsibilities:
- Analyze tool results from cross-indexing analysis in `thinking` field in json
- Identify essential connection code that should be extracted
- Generate JSON format for connection code output
- Ensure comprehensive coverage of all connection points

Output Format:

{
  "thinking": "detailed analysis of tool results and reasoning for connection code extraction decisions",
  "connection_code": [
    {
      "id": "unique_id",
      "file": "relative/path/to/file",
      "start_line": int,
      "end_line": int,
      "description": "context about why this code is important (1 line only)",
    }
  ]
}

Output Examples:

Example 1: Direct endpoint discovery - extracting multiple endpoints found
{
  "thinking": "Tool results show multiple REST API endpoints in src/api/routes.py. These are direct incoming connection points that need to be extracted as they represent entry points for external services to connect to this application.",
  "connection_code": [
    {
      "id": "1",
      "file": "src/api/routes.py",
      "start_line": 12,
      "end_line": 250,
      "description": "Found 30+ REST API endpoints that accept incoming connections - includes user management, order processing, and notification endpoints"
    }
  ]
}

Example 2: RabbitMQ wrapper function with queue names - extracting multiple functions
{
  "thinking": "Tool results identified RabbitMQ functions with hardcoded queue names. These represent outgoing connections to message queues and should be extracted because they show explicit connection destinations that other services need to know about.",
  "connection_code": [
    {
      "id": "2",
      "file": "src/messaging/queue_manager.py",
      "start_line": 30,
      "end_line": 40,
      "description": "RabbitMQ function sendToOrderQueue() with hardcoded queue name 'order-processing'"
    },
    {
      "id": "3",
      "file": "src/messaging/queue_manager.py",
      "start_line": 50,
      "end_line": 66,
      "description": "RabbitMQ function sendToNotificationQueue() with hardcoded queue name 'user-notifications'"
    }
  ]
}

Example 3: RabbitMQ with dynamic queue names - wrapper function calls
{
  "thinking": "Tool results show a wrapper function pattern where queue names are passed as parameters. Need to extract both the wrapper function definition and all its usage calls to capture the complete connection picture including actual queue names being used.",
  "connection_code": [
    {
      "id": "4",
      "file": "src/messaging/publisher.js",
      "start_line": 25,
      "end_line": 35,
      "description": "RabbitMQ wrapper function publishMessage(queueName, data) that accepts queue names as arguments"
    },
    {
      "id": "5",
      "file": "src/services/orderService.js",
      "start_line": 45,
      "end_line": 47,
      "description": "publishMessage() call with queue name 'order-processing' for order management"
    },
    {
      "id": "6",
      "file": "src/services/notificationService.js",
      "start_line": 23,
      "end_line": 25,
      "description": "publishMessage() call with queue name 'user-notifications' for user notifications"
    }
  ]
}

Example 4: HTTP client wrapper function discovery and call analysis
{
  "thinking": "Tool results revealed an HTTP wrapper function pattern. The wrapper function shows how HTTP calls are made, while the usage calls reveal actual endpoints and HTTP methods being used. All should be extracted to understand the complete HTTP connection landscape.",
  "connection_code": [
    {
      "id": "7",
      "file": "src/services/httpClient.js",
      "start_line": 18,
      "end_line": 28,
      "description": "HTTP wrapper function apiCall(serviceUrl, endpoint, method) that accepts URLs and endpoints as arguments"
    },
    {
      "id": "8",
      "file": "src/services/userService.js",
      "start_line": 34,
      "end_line": 36,
      "description": "apiCall() usage with endpoint '/admin/users' and POST method for user management"
    },
    {
      "id": "9",
      "file": "src/services/orderService.js",
      "start_line": 67,
      "end_line": 69,
      "description": "apiCall() usage with endpoint '/api/orders' and GET method for order retrieval"
    }
  ]
}

Example 5: WebSocket connection discovery with socket.emit events
{
  "thinking": "Tool results found WebSocket implementation with both outgoing (socket.emit) and incoming (socket.on) connection patterns. Both directions need to be extracted as they represent bidirectional communication channels that are essential for understanding real-time connection architecture.",
  "connection_code": [
    {
      "id": "10",
      "file": "src/services/websocketClient.js",
      "start_line": 12,
      "end_line": 35,
      "description": "WebSocket outgoing connections with socket.emit() for room joining and message sending"
    },
    {
      "id": "11",
      "file": "src/services/websocketClient.js",
      "start_line": 80,
      "end_line": 128,
      "description": "WebSocket incoming connections with socket.on() for message receiving and room updates"
    }
  ]
}

# Connection Code Extraction Guidelines:

1. Extraction Assessment
Analyze tool results to identify connection code that should be extracted. Focus on actual connection establishment code, wrapper function calls with real parameters, and environment variable usage for connection configuration.

2. Extraction Strategy
- CASE 1: Direct calls with literal connection identifiers → Extract immediately
- CASE 2: Wrapper function calls with variable identifiers → Extract ALL wrapper calls with actual identifiers
- CASE 3: Environment variables or static values → Extract the line directly
- EXCLUDE: Internal implementation details, generic definitions, variable assignments without calls

3. Extraction Decision Criteria
- Extract any connection patterns, API endpoints, HTTP calls, or wrapper functions related to connections
- Extract code that reveals important connection information between services
- Extract any code that is related to incoming/outgoing connections
- Extract environment variable configurations and their resolved values

4. Comprehensive Extraction Requirements
- Extract ALL discovered incoming/outgoing connections without missing any connection types
- Incoming connections: Extract ALL incoming connections regardless of number
- Outgoing connections: Extract ALL outgoing connections regardless of number
- ZERO TOLERANCE for skipping connections: Every single connection found must be extracted
- NO SAMPLING: Never extract "representative examples" - extract every single connection discovered
- COMPLETE COVERAGE: If tool results contain 100 connections, extract all 100, not just 5-10

5. Output Format Requirements
- Use relative file paths from project root
- Include exact line numbers for start and end of code snippets
- Provide descriptive context in one line explaining why the code is important
- Use unique IDs for each code snippet
- Group related code snippets in single JSON output

6. Description Best Practices
- Be specific about connection type (HTTP, WebSocket, Queue, etc.)
- Include actual connection identifiers (endpoints, queue names, event names)
- Mention technology used (axios, socket.io, RabbitMQ, etc.)
- Include environment variable context when applicable
- Keep descriptions to one line for clarity

7. Quality Assurance
- Verify all file paths are relative to project root
- Ensure line numbers are accurate and inclusive
- Check that descriptions are informative and concise
- Confirm all connection types are covered
- Validate JSON format is properly structured

8. Output Requirements
- Always output complete JSON format for connection code when found
- Include all identified connection code in single response
- Ensure proper JSON structure with arrays for multiple connections
- Use consistent ID numbering across all code snippets
- Provide comprehensive coverage without missing any connections
- If no connection code is found, return nothing
"#