"""
Code Manager Rules

Core rules and constraints for effective connection code extraction and output format.
"""

CODE_MANAGER_RULES = """====

RULES

1. Focus EXCLUSIVELY on EXTRACTING CONNECTION CODE for DATA COMMUNICATION between different user repositories, projects, or folders.

2. CRITICAL SCOPE: Only extract connection code where one user service/repository sends/receives data to/from another user service/repository.

3. MANDATORY EXCLUSIONS - NEVER extract these:
   - Infrastructure services: Database connections (Redis, PostgreSQL, MongoDB), caching systems, cloud storage that don't represent data communication

4. CONNECTION CODE EXTRACTION CRITERIA - ONLY extract these:
   - REST API calls
   - WebSocket connections
   - Message queue publishers/consumers 
   - File-based data exchange between user repositories/folders
   - Custom wrapper functions on top of existing technologies like Axios, Socket.io, RabbitMQ, etc. that facilitate data communication
   - Media streaming connections (WebRTC, RTMP) between user services

5. ENDPOINT VALIDATION RULES:
   - EXTRACT: Environment variables

6. All file paths must be relative to the project root directory. When returning connection code, always use relative paths for consistency.

7. CONNECTION CODE EXTRACTION: Extract essential connection identifiers (API endpoints, API calls, message queue producers/consumers) discovered through search_keyword or database tools.

8. EXTRACTION PRIORITY: Extract calls based on whether CONNECTION IDENTIFIERS are literal or variable.
   - CONNECTION IDENTIFIERS: endpoint names, queue names, socket event names, routing keys
   - LITERAL CONNECTION IDENTIFIERS: Extract immediately when identifiers are literal strings
   - VARIABLE CONNECTION IDENTIFIERS: Extract wrapper function calls that contain actual connection identifiers

9. EXTRACTION FOCUS:
    - EXTRACT: Connection identifier (endpoint, queue name, event name) and request type
    - EXTRACT: Environment variables that affect connection identifiers
    - DO NOT EXTRACT: Data content, payload details, or business logic
    - DO NOT EXTRACT: Wrapper function definitions without actual connection identifiers
    - DO NOT EXTRACT: Variable assignments unless they define connection identifiers

10. DESCRIPTION FOCUS:
    - DESCRIBE: Connection identifier and its source (literal or resolved from variable)
    - DESCRIBE: Request type (GET, POST, consume, emit, etc.)
    - DESCRIBE: Environment variables that provide connection identifiers
    - DO NOT DESCRIBE: Data content, payload structure, or business context

11. WRAPPER FUNCTION ANALYSIS: Focus on extracting where wrapper functions are CALLED with actual values, not where they are defined. Extract actual function call sites with real parameters.

12. ENVIRONMENT VARIABLE RESOLUTION: When you find environment variables, include both variable name and resolved value in descriptions.

13. When extracting connections, always determine the direction: incoming (other services send data TO this service) or outgoing (this service sends data TO other services). Include this classification in your findings.

14. CALL SITE FOCUS: Extract exact line numbers where wrapper functions are called with actual parameter values, not where they are defined.

15. ACTUAL ENDPOINT IDENTIFICATION: Extract specific endpoint information with environment variable context, not generic wrapper function descriptions.

16. CRITICAL PRIORITY RULE: When extracting connection code, always prioritize wrapper function calls over base library calls. This applies to all types of wrappers including HTTP wrappers, socket wrappers, queue wrappers, and service communication wrappers:
    - Extract: `serviceApiCall("/admin/users", "POST", userData)` - shows actual endpoint and business logic
    - Do not extract: `return (await axios.post(url, data));` - internal implementation detail
    - Extract: `queuePublisher("user_added", messageData)` - shows actual queue_name="user_added" and message
    - Do not extract: `channel.publish(queue, buffer)` - internal queue library call without queue_name
    - Extract: `socketEmitter("user_update", userData)` - shows actual event and data
    - Do not extract: `socket.emit(eventName, data)` - internal socket library call

17. COMPREHENSIVE CONNECTION EXTRACTION: When multiple results are found, you must extract ALL of them, not just examples. Each connection point is important for cross-indexing analysis.
    - NO SAMPLING: Never extract "representative examples" - extract every single connection discovered
    - ZERO TOLERANCE: Missing connections is unacceptable - comprehensive extraction is required
    - COMPLETE COVERAGE: If you find 100 connections, extract all 100, not just 5-10

18. CONNECTION CODE EXTRACTION RULES:
    - Extract ALL discovered incoming/outgoing connections without missing any connection types
    - Incoming connections: Extract ALL incoming connections regardless of number
    - Outgoing connections: Extract ALL outgoing connections regardless of number
    - ZERO TOLERANCE for skipping connections: Every single connection found must be extracted
    - NO SAMPLING: Never extract "representative examples" - extract every single connection discovered
    - COMPLETE ANALYSIS: If search results return 100 results and if it is any connection type, you must extract all 100 by providing their file paths and line numbers rather than extracting just a few representative ones

19. You MUST think through your analysis in <thinking></thinking> tags before providing your response.

20. You MUST output XML format specifying what connection code to return using the format:
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

21. If no connection code is found in the tool results, return nothing - no XML output is needed.

22. When you find connection code, return it with proper file paths, line ranges, technology names, and connection direction. This ensures all necessary context is provided.

23. INCOMPLETE CODE SNIPPET HANDLING: When you encounter incomplete code snippets from search_keyword results where API calls or connection code appears truncated (missing closing parentheses, incomplete parameters, etc.), expand the line range to capture the complete code block. Use intelligent estimation to include additional lines:
    - For API calls like `axios.get(` that appear incomplete, extend by 2-4 lines to capture complete call
    - For function calls with multiple parameters, extend until logical completion (closing parenthesis, semicolon)
    - Example: If search shows lines 10-12 but code appears incomplete, extend to lines 10-14 or 10-16 based on context
    - Better to include extra lines than miss essential connection parameters or configuration
    - This ensures complete connection code context is captured for analysis
"""
