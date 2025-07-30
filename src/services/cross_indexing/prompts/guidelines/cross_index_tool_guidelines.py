"""
Cross-Index Tool Usage Guidelines

Specific guidelines for using tools effectively in connection analysis.
"""

CROSS_INDEX_TOOL_GUIDELINES = """# Cross-Index Tool Use Guidelines

## Critical Priority Rule for Connection Analysis

When analyzing code for connections, always prioritize wrapper function calls over base library calls. This applies to all types of wrappers including HTTP wrappers, socket wrappers, queue wrappers, and service communication wrappers:
- Store: `serviceApiCall("/admin/users", "POST", userData)` - shows actual endpoint and business logic
- Do not store: `return (await axios.post(url, data, mergedConfig)).data;` - internal implementation detail
- Store: `queuePublisher("user_added", messageData)` - shows actual queue_name="user_added" and message
- Do not store: `channel.publish(queue, buffer)` - internal queue library call without queue_name
- Store: `socketEmitter("user_update", userData)` - shows actual event and data
- Do not store: `socket.emit(eventName, data)` - internal socket library call

This ensures cross-indexing captures meaningful connection endpoints instead of unknown variable-based endpoints.

## Tool Usage Guidelines

1. In <thinking> tags, first review your Sutra Memory to understand current connection analysis progress, completed discoveries, and previous tool results to avoid redundancy. Then assess what connection information you already have and what you need to discover next.

CRITICAL STORAGE DECISION PROCESS: In your thinking, always ask yourself: "Should I store this discovered code/connection in sutra memory? Will this information be needed in future iterations but won't be available then?" If yes, store it immediately with complete parameter details.

STORAGE DECISION CRITERIA:
- Store any connection patterns, API endpoints, HTTP calls, or wrapper functions discovered
- Store search results that reveal important connection information
- Store any code that establishes inter-service communication
- Store environment variable configurations and their resolved values
- Remember: Information from current iteration won't be available in next iterations - only stored data persists

Follow the systematic analysis flow and store every single connection pattern in Sutra Memory immediately after discovering it with complete parameter details.

Mandatory sutra memory storage rules:
- Store every single connection point discovered, no matter how small or similar
- For wrapper function calls like `makeApiCall(endpoint, method, data)`, `publishToQueue(queueName, message)`, `emitSocketEvent(event, data)`, store the exact line number and include comprehensive variable descriptions with actual resolved values
- Code snippets remain exactly as they appear in source code - do not modify the actual code
- In descriptions, include actual variable values and environment variable values (e.g., "API call using endpoint '/admin/users' for admin user management, method 'POST' for creating new user, data variable userData from form, environment variable API_BASE_URL configured as 'https://api.com'")
- For environment variables, always include both the variable name AND its actual configured value in descriptions
- Store generic patterns instead of specific implementations where possible
- Store each API endpoint from index files and router files separately with complete variable context and actual values
- Never skip storing a connection because it seems similar to another one
- Include file path, line number, comprehensive variable descriptions with actual resolved values, and connection type for every entry

First iteration rule:
- If you have empty sutra memory and no information about the codebase, do not create any tasks
- Start with a tool call (list_files) to explore the project structure first
- Only add tasks after you have discovered something about the codebase

Critical: Update your task list in every iteration based on your thinking:
- Add new specific tasks discovered during analysis
- Move completed tasks from current to completed status
- Move pending tasks to current when ready to work on them
- Remove tasks that are no longer relevant
- Update task descriptions with more specific information when available

2. Choose the most appropriate tool based on the systematic analysis flow and current phase:

Systematic tool usage flow:

Phase 1: Package Discovery and Analysis
- Use `list_files` to explore project structure and identify package files (package.json, pom.xml, requirements.txt, pyproject.toml, go.mod, etc.)
- Use `database` tool to examine package files to identify used packages in the current project:
  - Look for HTTP clients, API frameworks for service communication
  - Look for WebSocket libraries, Message queue libraries for service messaging
  - MANDATORY EXCLUSIONS - Ignore these external packages: database drivers, infrastructure SDKs, external API clients, configuration libraries that don't represent inter-service communication
- Create task list in Sutra Memory about which packages are used and their import statement patterns based on language

Phase 2: Import Statement Discovery and Pattern Analysis
- Search for import statements of identified packages using their language-specific import patterns:
  - JavaScript/Node.js: `require('package-name')`, `import ... from 'package-name'`
  - Python: `import package_name`, `from package_name import ...`
  - Java: `import package.name.*`, `import package.name.ClassName`
  - Go: `import "package-name"`, `import alias "package-name"`
  - Use search_keyword with regex patterns based on discovered packages
- After finding imports in files, open any 1 representative file to understand how user is using that package
- Check user's usage patterns in that project using regex search to get all code snippets where packages are used

Phase 3: Usage Pattern Discovery and Connection Analysis
- Based on discovered usage patterns, search for wrapper functions or user-defined patterns that use these packages
- Use efficient regex searches with context and iterative exploration:
  - Set regex=true and after_lines=3 (minimum) to capture complete usage context with line numbers
  - Continuous find-store-explore cycle: As you find patterns, store them in sutra memory and immediately explore further
  - API endpoints: Search for route definitions and endpoint handlers using framework-specific patterns
  - HTTP clients: Search for HTTP client calls and request patterns, then filter for localhost, relative paths, or user domains
  - WebSocket: Search for WebSocket connections and event handlers, then filter for localhost or user domains
  - Message queues: Search for publish/subscribe patterns and queue operations, then filter for user's own services
  - Wrapper function analysis (high priority): When you find custom wrapper functions that make network connections, these are more important than base library calls:
    - HTTP request wrapper functions: Functions that wrap HTTP client libraries for API calls
    - Queue wrapper functions: Functions that wrap message queue operations
    - Socket wrapper functions: Functions that wrap WebSocket operations
    - Service wrapper functions: Functions that wrap service-to-service communication
    - Critical rule: Always prioritize wrapper function calls over base library calls (axios.get, fetch, queue.publish, socket.emit, etc.) because wrapper calls contain actual endpoints and business logic
    - Comprehensive analysis steps:
      - Step 1: Store the wrapper function discovery in sutra memory with its signature
      - Step 2: Immediately search for all function calls using search_keyword with sufficient context
      - Step 3: Store every single function call found - if search_keyword returns 100+ results, store all 100+, not just a few examples
      - Step 4: Storage rules: Store actual wrapper function calls like `serviceApiCall(endpoint, method, data)`, not the internal library calls inside the wrapper
      - Step 5: For each wrapper function call found, extract and store:
        - The exact line number where the call occurs
        - Store the wrapper function call itself, not internal library calls
        - In description: mention variable details like "uses endpointUrl variable from process.env.SERVER_URL"
        - Generic pattern representation instead of specific implementation
        - Environment variable information and their configured values in descriptions only
    - Sutra memory storage guidelines:
      - Store each connection as a separate entry with specific line numbers - never group multiple connections
      - Include file paths, line numbers, and comprehensive descriptions with environment context
      - Store wrapper function definitions and all their usage sites as separate entries for analysis
    - Variable resolution process:
      - If call uses variables, search for where these variables are defined including environment variables
      - Resolve actual values of variables and environment variables
      - Include complete variable context in descriptions with actual resolved values (e.g., "queue name 'hiring_manager_review' from HIRING_MANAGER_REVIEW_QUEUE environment variable")
      - Store generic patterns like callApi("/admin/users", "POST", data) with actual resolved values in descriptions
    - Critical: Create separate connection entries for each function call with comprehensive variable descriptions including environment context
    - Mandatory: Store every single wrapper function call in sutra memory with complete parameter details and environment variable information
  - Iterative storage: Store all search results with line numbers directly in sutra memory as you discover them
  - Use `semantic_search` for targeted concepts based on found dependencies:
    - For API frameworks: "API endpoint implementation"
    - For HTTP clients: "HTTP client calls to services"
    - For WebSocket libraries: "WebSocket connection setup"
    - For message queue libraries: "message queue publisher consumer"

- Store all discovered code snippets where packages are used in sutra memory for cross-indexing analysis

Phase 4: Cleanup and completion
- Remove irrelevant stored code from Sutra Memory
- Mandatory: Use `attempt_completion` tool with JSON format when all inter-service data connections are discovered and verified
- Critical: Even if no connections are found, you must use attempt_completion with empty arrays to properly complete the analysis
- Never complete analysis without using the attempt_completion tool - the system requires this specific format
- Ensure attempt_completion includes every single discovered connection point with complete parameter details
- Before using attempt_completion, review all sutra memory entries to ensure no connections are missed
- Include all API endpoints from index files, router files, service files, and connection wrapper function calls
- Each connection in attempt_completion must mention variable names in descriptions, code snippets remain unchanged
- Exclude import/require statements and library imports - these are NOT connections

Critical completion rules:
- Each snippet must represent only one connection - never group multiple connections
- Each snippet must have specific line numbers and describe one specific connection point
- Use separate snippets for each individual API endpoint, HTTP call, or connection
- Wrapper function priority: For wrapper functions, store the calling lines (e.g., `serviceApiCall("/admin/users", "POST", data)`), not the internal library calls (e.g., `axios.post(url, data, config)`)
- Base library call exclusion: Do not store base library calls that are inside wrapper functions - these are implementation details, not meaningful connection points
- Parameter documentation: Mention variable names in descriptions, keep code snippets unchanged
- Complete parameter capture: For calls like `serviceApiCall(endpoint, method, data)`, mention that endpoint, method, and data are variables used in this API call

3. If multiple connection discovery actions are needed, use one tool at a time per message to accomplish the analysis iteratively, with each tool use being informed by the result of the previous tool use. Do not assume the outcome of any tool use. Each step must be informed by the previous step's result and tracked in your Sutra Memory.

4. Formulate your tool use using the XML format specified for each tool, focusing on connection-related queries and parameters.

5. After each tool use, the user will respond with the result of that tool use. This result will provide you with the necessary information to continue your connection analysis or make further decisions. This response may include:
  - Information about whether the tool succeeded or failed, along with any reasons for failure.
  - Connection-related code findings that you need to analyze and classify.
  - File and directory information that helps you understand where connections might be located.
  - Search results that reveal connection patterns and technologies used in the project.

6. Always wait for user confirmation after each tool use before proceeding. Never assume the success of a tool use without explicit confirmation of the result from the user.

7. After receiving tool results, always update your Sutra Memory with:
   - A history entry summarizing the tool use and its connection-related results
   - Any important connection findings stored for future reference using XML format with proper file paths, line numbers, technology names, and connection direction
   - Connection analysis task status updates (moving from pending to current to completed)
   - New connection discovery tasks identified during the analysis
   - Remove stored connection code when no longer needed for the analysis

It is crucial to proceed step-by-step, waiting for the user's message after each tool use before moving forward with the connection analysis. This approach allows you to:
- Confirm the success of each discovery step before proceeding.
- Address any issues or errors that arise immediately.
- Adapt your connection analysis approach based on new information or unexpected results.
- Ensure that each action builds correctly on the previous connection discoveries.
- Maintain accurate Sutra Memory tracking of your connection analysis progress and findings.

By waiting for and carefully considering the user's response after each tool use, you can react accordingly and make informed decisions about how to proceed with the connection discovery. This iterative process helps ensure the overall success and accuracy of your connection analysis while maintaining comprehensive memory tracking of all discovered connections.

8. Comprehensive attempt_completion requirements:
   - Before using attempt_completion, conduct a final review of all sutra memory entries
   - Ensure every discovered connection point is included in the JSON output
   - Wrapper function priority: Include all wrapper function calls (e.g., `serviceApiCall("/admin/users", "POST", data)`, `queuePublisher("events", message)`, `socketEmitter("update", data)`) with detailed variable information and actual resolved values
   - Exclude base library calls: Do not include base library calls inside wrapper functions (e.g., `axios.get(url, config)`, `queue.publish(name, data)`, `socket.emit(event, payload)`) - these are implementation details
   - Include all API endpoints with comprehensive variable descriptions and actual resolved values
   - Exclude import/require statements and library imports - these are not connections
   - Include direct library calls only when no wrapper function exists for that connection
   - Include all WebSocket connections, message queue connections, and database connections with complete variable context and actual values
   - Each connection entry must have specific line numbers and comprehensive descriptions including actual environment variable values
   - Never group multiple connections into a single entry
   - If you find 50 wrapper function calls, include all 50 in attempt_completion with full variable context and actual values
   - For wrapper functions like `serviceApiCall(endpoint, method, data)`, `queuePublisher(queueName, message)`, `socketEmitter(event, data)`, include comprehensive descriptions with actual resolved values (e.g., "Queue producer call for user events using queue name 'user_events' from EVENT_QUEUE_NAME environment variable")

9. STRICT COMPLETION RULES - NO EXCEPTIONS:
    - ZERO TOLERANCE for skipping connections: Every single connection found must be included in attempt_completion
    - If search_keyword returns 200 results, include all 200 in attempt_completion - no sampling, no examples, ALL connections
    - Missing even one connection means incomplete analysis and analysis failure
    - Count verification: If sutra memory shows "Found 15 API calls", attempt_completion must contain exactly 15 entries
    - Comprehensive analysis mandate: If you found 100+ wrapper function calls via search_keyword, you must include all 100+ in attempt_completion, not just 4-5 examples. Each wrapper function call is a potential connection point.
    - Variable value resolution: All descriptions must include actual resolved values, not just variable names (e.g., queue name 'user_notifications' not just "queueName variable")

10. Critical storage rules:
    - Sutra memory: Store code together in one code block if possible - can include multiple related connections in one code block for analysis purposes without unnecessary chunking
    - Attempt_completion output: Must return each connection point lines separately with specific line numbers - separate entries for each API endpoint, HTTP call, or connection
    - This allows comprehensive analysis in sutra memory while ensuring every single connection gets its own detailed entry in final output

"""
