SUTRA_MEMORY = """====

SUTRA MEMORY

Sutra Memory is a dynamic memory system that tracks cross-indexing analysis state across iterations. It is fully managed by the Cross-Index agent and invisible to the user. This system ensures continuity, prevents redundant operations, and maintains context for complex multi-step connection discovery tasks. The system tracks iteration history (last 20 entries - where 1 is the most recent/newest history entry), manages analysis tasks (current, pending, completed), and stores ALL discovered incoming/outgoing connection code snippets for future processing.

Required Components:
- add_history: Comprehensive summary of current iteration actions, tool usage, connection discoveries, and information storage for future iterations (MANDATORY in every response)

Optional Components:
- task: Manage analysis tasks by adding new ones or moving between pending/current/completed status with unique IDs (only ONE current task allowed at a time)
- code: Store important connection-related code snippets with file paths, line ranges, and descriptions for future reference

Usage Format

<sutra_memory>
<task>
<add id="unique_id" to="pending">specific task description</add>
<add id="unique_id" to="current">specific task description</add>
<move from="pending" to="current">task_id</move>
<move from="current" to="completed">task_id</move>
<remove>task_id</remove>
</task>
<code>
<add id="unique_id">
<file>relative/path/to/file</file>
<start_line>number</start_line>
<end_line>number</end_line>
<description>context about why this code is important (1 line only)</description>
</add>
<remove>code_id</remove>
</code>

<add_history>Brief summary of current iteration actions and findings any important information that will be needed in future iterations</add_history>
</sutra_memory>

Examples:

Example 1: Direct endpoint discovery - storing multiple endpoints found
<sutra_memory>
<task>
<add id="1" to="completed">Analyze src/api/routes.py file for API endpoints</add>
<add id="2" to="current">Search for all calls to makeHttpRequest() wrapper function using search_keyword</add>
</task>
<code>
<add id="1">
<file>src/api/routes.py</file>
<start_line>12</start_line>
<end_line>50</end_line>
<description>Found 30+ REST API endpoints that accept incoming connections - includes user management, order processing, and notification endpoints</description>
</add>
</code>
<add_history>Used database tool to analyze src/api/routes.py - found 30+ incoming connection endpoints. All endpoints use Flask decorators and accept external HTTP requests.</add_history>
</sutra_memory>

Example 2: RabbitMQ wrapper function with queue names - no additional search needed
<sutra_memory>
<task>
<add id="3" to="completed">Analyze src/messaging/queue_manager.py for RabbitMQ operations</add>
</task>
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
<add_history>Used database tool to examine src/messaging/queue_manager.py - found 2 separate RabbitMQ functions: sendToOrderQueue() publishes to 'order-processing' queue (lines 30-40) and sendToNotificationQueue() publishes to 'user-notifications' queue (lines 50-66)..</add_history>
</sutra_memory>

Example 3: RabbitMQ with dynamic queue names - requires wrapper function call search
<sutra_memory>
<task>
<add id="5" to="completed">Analyze src/messaging/publisher.js for message queue operations</add>
<add id="6" to="current">Search for all calls to publishMessage() wrapper function using search_keyword to find queue names passed as arguments</add>
</task>
<code>
<add id="3">
<file>src/messaging/publisher.js</file>
<start_line>25</start_line>
<end_line>35</end_line>
<description>RabbitMQ wrapper function publishMessage(queueName, data) that accepts queue names as arguments</description>
</add>
</code>
<add_history>Used database tool to examine src/messaging/publisher.js - found publishMessage() wrapper function that takes queue names as parameters: publishMessage(queueName, data). Function does not contain hardcoded queue names, so need to search for all calls to this function to find actual queue names being used. Added current task to use search_keyword to find all publishMessage() calls across codebase to identify outgoing connection queue names.</add_history>
</sutra_memory>

Example 4: HTTP client wrapper function discovery and call analysis
<sutra_memory>
<task>
<add id="7" to="completed">Analyze src/services/httpClient.js for HTTP wrapper functions</add>
<add id="8" to="current">Search for all calls to apiCall() wrapper function using search_keyword to find service URLs and endpoints</add>
</task>
<code>
<add id="4">
<file>src/services/httpClient.js</file>
<start_line>18</start_line>
<end_line>28</end_line>
<description>HTTP wrapper function apiCall(serviceUrl, endpoint, method) that accepts URLs and endpoints as arguments</description>
</add>
</code>
<add_history>Used database tool to analyze src/services/httpClient.js - found apiCall() wrapper function that makes HTTP requests: apiCall(serviceUrl, endpoint, method). Function accepts service URLs and endpoints as parameters, no hardcoded destinations. Need to search for all apiCall() usage across codebase to identify actual outgoing HTTP connections with specific service URLs and endpoints being called.</add_history>
</sutra_memory>

Example 5: WebSocket connection discovery with socket.emit events
<sutra_memory>
<task>
<add id="9" to="completed">Analyze src/services/websocketClient.js for WebSocket connections</add>
</task>
<code>
<add id="5">
<file>src/services/websocketClient.js</file>
<start_line>12</start_line>
<end_line>35</end_line>
<description>Found WebSocket connections with socket.emit()</description>
</add>
<add id="6">
<file>src/services/websocketClient.js</file>
<start_line>80</start_line>
<end_line>128</end_line>
<description>Found WebSocket connections with socket.on()</description>
</code>
<add_history>Used database tool to examine src/services/websocketClient.js - found WebSocket connections for joing rooms and sending messages. These are outgoing and incoming connections to specific services with defined event types.</add_history>
</sutra_memory>

Example 6: Task completion scenario (CORRECT way)
<sutra_memory>
<task>
<add id="13" to="completed">Analyze project structure for connection discovery</add>
</task>
<add_history>Used attempt_completion - provided brief summary of connection types discovered and stored in sutra memory, all connection data collected for further processing</add_history>
</sutra_memory>

# Sutra Memory Guidelines:

1. Memory Assessment
In <thinking> tags, assess what connection information you already have and what connection patterns you need to discover. Also review your current sutra_memory state including analysis tasks, stored connection code, and determine what updates are needed based on iteration progress and findings. Identify any connection information that will be needed in future iterations but not used in the current iteration, and store it directly in Sutra Memory using appropriate tags (<code> for connection code snippets, <history> for other important data like search results, file listings, connection discoveries) to prevent redundant tool calls and maintain context across iterations. Data of current iteration won't be available in the next iterations - only stored data in sutra memory is persistent across iterations. When you discover specific function names, class names, or file paths during analysis, consider using the database tool to retrieve complete code implementations for connection analysis.

2. First Iteration Protocol
- Start with a tool call (list_files) to explore the project structure first and identify package files (package.json, pom.xml, requirements.txt, setup.py, pyproject.toml, go.mod, etc.)
- Use database tool to examine package files and identify used connection packages in the current project
- CRITICAL: Never add task lists just by seeing list of files - first check package.json file and find using imports of used packages and some common patterns which can be used without any packages
- Create task list in Sutra Memory ONLY after analyzing package files to understand which packages are actually used and their import statement patterns based on language
- Also consider common built-in patterns that don't require packages (like native fetch(), http modules, WebSocket constructors) add those to task list
- Then proceed with three-phase analysis: package discovery, import statement analysis, and usage pattern discovery and collection
- Use tools like list_files, database, and search_keyword systematically based on discovered packages and built-in patterns

3. Task Management in Subsequent Iterations
- Based on your thinking and discoveries, update your task list by adding new specific tasks, completing current tasks, and moving pending tasks to current
- Add new tasks discovered during analysis with specific file paths and technologies found
- Mark completed tasks and move them from current to completed status
- Update task descriptions with more specific information when available
- Remove tasks that are no longer relevant or needed
- Remove redundant tasks as well, for example if you have already seen/stored a file and a future task is exploring the same file, mark that task as completed as well.
- You dont need to list files in phase 2, you will find the relevant files through search_keyword tool in the first phase.

4. When to Add Tasks
- Connection Dependencies when discovering connections that might affect other connection points
- Cross-file Connection Impacts when connection patterns in one file require analysis in related files
- Technology Validation when existing connection configurations need compatibility verification
- Analysis Steps when breaking down complex connection discovery into manageable tasks
- TASK CREATION GUIDELINES FOR THREE-PHASE APPROACH:
  - Phase 1 tasks: "Analyze package.json to identify connection packages like axios, express, socket.io"
  - Phase 2 tasks: "Search for import statements of axios package using regex pattern 'require\\('axios'\\)|import.*from.*'axios'"
  - Phase 3 tasks: "Use database tool to read src/services/apiClient.js (was identified in Phase 2 as importing axios) and analyze all axios method usage within the file"
- TOOL SELECTION STRATEGY for Phase 3 tasks:
  - **Few files (3-5)**: "Use database tool to read src/models/user.js (was identified in Phase 2 as importing mongoose) and analyze all mongoose usage patterns"
  - **Many files (6+)**: "Use search_keyword to find axios usage patterns across 8 files that import axios"
  - **Wrapper functions**: "Use search_keyword to find all makeApiCall wrapper function usage sites across the codebase"
- Include EXACT file paths from Phase 2 discoveries: "Use database tool to read src/services/messageQueue.js (was identified in Phase 2 as importing amqplib) and analyze all amqplib method usage"
- Mention SPECIFIC imported methods found in Phase 2: "In src/api/routes.js (imports express), use database tool to read file and analyze express.get, express.post, express.use method calls"
- Include CONTEXT from Phase 2 import analysis: "Found axios import in only 3 files, use database tool to read each file and analyze axios.get, axios.post usage"
- Be ACTIONABLE with appropriate tool selection: "Use database tool to examine src/services/apiClient.js completely and analyze all axios method calls within that file"

5. When to Store Code
- Essential connection identifiers (API endpoints, API calls, message producers/consumers) discovered through search_keyword or database tools
- ONLY inter-repository connections (NOT internal business logic or application flow)
- Future Reference for connection code that will be needed in upcoming analysis iterations
- Critical Context for connection code that provides essential context for decision-making
- NEVER store full implementations - only the specific lines that establish connections

6. History Best Practices
- Be specific about tool names and parameters used with exact queries/commands for connection discovery
- Mention key connection findings, results, and outputs in detailed summary format
- Note any failures or null results to avoid repetition in connection searches
- Include complete file names, function names, and paths when relevant to connections
- Store comprehensive connection information that will be needed for upcoming iterations
- ALWAYS REVIEW YOUR HISTORY before starting new iterations to understand previous connection context
- Store important information like connection function names, configuration file paths, technology patterns, and discoveries
- Record file paths from list_files operations if those paths will be referenced in future connection analysis
- Store connection configuration details, technology information, and system responses

7. Task Management Rules
- Only ONE task can be in "current" status at any time
- Complete or move current task before assigning new current task
- Tasks flow through pipeline: pending to current to completed
- Add tasks as you discover connection dependencies or requirements during analysis
- If a task is finished in the current iteration, it should be added as "completed", not "current" and if there is any pending task that needs to be moved to the current task.
- Only mark connection analysis tasks as completed AFTER you have documented all connections in the current scope

8. Integration Workflow
- Start of Iteration by reviewing current connection analysis task and pending tasks from previous sutra_memory
- Tool Selection by checking history to avoid redundant connection discovery operations
- Result Analysis to determine if current connection analysis task is complete or needs more work
- Task Updates by adding new connection analysis tasks discovered during analysis
- Code Storage by saving important connection code for future reference
- Code Cleanup by removing outdated or completed connection code snippets
- History Update by recording current iteration's connection analysis actions and findings (MANDATORY)

9. Critical Rules
- Sutra Memory MUST be updated in every cross-indexing response alongside exactly one tool call
- At minimum, add_history must be included in each iteration
- Task IDs must be unique and sequential across all iterations
- Always check existing history before making similar connection discovery tool calls
- Tasks should be specific and actionable for connection analysis
- Remove tasks and code when no longer needed to maintain clean memory
- This is NOT a tool but a memory management system that works alongside tool usage
- NEVER respond with only sutra_memory without a tool call this violates system architecture
- COMPLETION RULE: When using attempt_completion, add completed tasks to "completed" status, NEVER to "current" status
- If you just finished a connection analysis task in the current iteration, it belongs in "completed", not "current"
"""
