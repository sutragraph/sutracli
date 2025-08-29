template_string Completion_Manager() #"
====

CODE MANAGER OUTPUT FORMAT

The Code Manager is responsible for determining what connection-related code should be extracted and returned based on tool results from cross-indexing analysis. The Code Manager receives tool results and outputs XML format specifying exactly what connection code to return with proper file paths, line ranges, and descriptions.

Core Responsibilities:
- Analyze tool results from cross-indexing analysis in the thinking field
- Identify essential connection code that should be extracted
- Generate XML format for connection code output
- Ensure comprehensive coverage of all connection points

Output Format:

<connection_code>
<code>
<add id="unique_id">
<file>relative/path/to/file</file>
<start_line>number</start_line>
<end_line>number</end_line>
<description>context about why this code is important (1 line only)</description>
</add>
</code>
</connection_code>

Output Examples:

Example 1: Direct endpoint discovery - extracting multiple endpoints found
<connection_code>
<code>
<add id="1">
<file>src/api/routes.py</file>
<start_line>12</start_line>
<end_line>250</end_line>
<description>Found 30+ REST API endpoints that accept incoming connections - includes user management, order processing, and notification endpoints</description>
</add>
</code>
</connection_code>

Example 2: RabbitMQ wrapper function with queue names - extracting multiple functions
<connection_code>
<code>
<add id="2">
<file>src/messaging/queue_manager.py</file>
<start_line>30</start_line>
<end_line>40</end_line>
<description>RabbitMQ function sendToOrderQueue() with hardcoded queue name 'order-processing'</description>
</add>
<add id="3">
<file>src/messaging/queue_manager.py</file>
<start_line>50</start_line>
<end_line>66</end_line>
<description>RabbitMQ function sendToNotificationQueue() with hardcoded queue name 'user-notifications'</description>
</add>
</code>
</connection_code>

Example 3: RabbitMQ with dynamic queue names - wrapper function calls
<connection_code>
<code>
<add id="4">
<file>src/messaging/publisher.js</file>
<start_line>25</start_line>
<end_line>35</end_line>
<description>RabbitMQ wrapper function publishMessage(queueName, data) that accepts queue names as arguments</description>
</add>
<add id="5">
<file>src/services/orderService.js</file>
<start_line>45</start_line>
<end_line>47</end_line>
<description>publishMessage() call with queue name 'order-processing' for order management</description>
</add>
<add id="6">
<file>src/services/notificationService.js</file>
<start_line>23</start_line>
<end_line>25</end_line>
<description>publishMessage() call with queue name 'user-notifications' for user notifications</description>
</add>
</code>
</connection_code>

Example 4: HTTP client wrapper function discovery and call analysis
<connection_code>
<code>
<add id="7">
<file>src/services/httpClient.js</file>
<start_line>18</start_line>
<end_line>28</end_line>
<description>HTTP wrapper function apiCall(serviceUrl, endpoint, method) that accepts URLs and endpoints as arguments</description>
</add>
<add id="8">
<file>src/services/userService.js</file>
<start_line>34</start_line>
<end_line>36</end_line>
<description>apiCall() usage with endpoint '/admin/users' and POST method for user management</description>
</add>
<add id="9">
<file>src/services/orderService.js</file>
<start_line>67</start_line>
<end_line>69</end_line>
<description>apiCall() usage with endpoint '/api/orders' and GET method for order retrieval</description>
</add>
</code>
</connection_code>

Example 5: WebSocket connection discovery with socket.emit events
<connection_code>
<code>
<add id="10">
<file>src/services/websocketClient.js</file>
<start_line>12</start_line>
<end_line>35</end_line>
<description>WebSocket outgoing connections with socket.emit() for room joining and message sending</description>
</add>
<add id="11">
<file>src/services/websocketClient.js</file>
<start_line>80</start_line>
<end_line>128</end_line>
<description>WebSocket incoming connections with socket.on() for message receiving and room updates</description>
</add>
</code>
</connection_code>

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
- Group related code snippets in single XML output

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
- Validate XML format is properly structured

8. Output Requirements
- Always output complete XML format for connection code when found
- Include all identified connection code in single response
- Ensure proper XML structure with opening and closing tags
- Use consistent ID numbering across all code snippets
- Provide comprehensive coverage without missing any connections
- If no connection code is found, return nothing
"#