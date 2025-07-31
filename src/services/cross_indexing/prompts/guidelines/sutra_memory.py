SUTRA_MEMORY = """====

SUTRA MEMORY

Sutra Memory is a dynamic memory system that tracks cross-indexing analysis state across iterations. It is fully managed by the Cross-Index agent and invisible to the user. This system ensures continuity, prevents redundant operations, and maintains context for complex multi-step connection discovery tasks. The system tracks iteration history (last 20 entries - where 1 is the most recent/newest history entry), manages analysis tasks (current, pending, completed), and stores important connection code snippets for future reference.

1. Required Components:
   - add_history: Comprehensive summary of current iteration actions, tool usage, connection discoveries, and information storage for future iterations (MANDATORY in every response)

2. Optional Components:
   - task: Manage analysis tasks by adding new ones or moving between pending/current/completed status with unique IDs (only ONE current task allowed at a time)
   - code: Store important connection-related code snippets with file paths, line ranges, and descriptions for future reference

## Usage Format

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

Example 1: Basic history update with connection discovery information storage
<sutra_memory>
<add_history>Used semantic_search query "HTTP client calls" - found makeApiCall, callInternalService, fetchUserData functions in src/services/apiClient.js lines 15-42, identified axios-based HTTP client wrapper functions. Functions found: makeApiCall(endpoint, method, data) uses process.env.API_BASE_URL, callInternalService() for inter-service communication, fetchUserData() calls internal user service. Located in /src/services/apiClient.js, /src/controllers/UserController.js, /src/utils/httpClient.js. Need to search for actual CALL SITES of these wrapper functions with real parameters. Next: search for makeApiCall( calls and environment variable values.</add_history>
</sutra_memory>

Example 2: Task management with connection analysis
<sutra_memory>
<task>
<add id="1" to="pending">Look at src/api/routes.py file for API endpoints - check app.route decorators and endpoint functions</add>
<add id="2" to="pending">Look at src/services/httpClient.js file for HTTP client calls - check axios wrapper functions and call sites</add>
<move from="pending" to="current">1</move>
</task>
<add_history>Used list_files to explore project structure - found key files: src/api/routes.py contains REST endpoints, src/services/httpClient.js has HTTP client wrapper functions, src/server.js has server startup code. Added pending tasks to systematically analyze each file for connection patterns. Need to examine routes for incoming connections, HTTP client for outgoing connections, and server config for listening ports and protocols.</add_history>
</sutra_memory>

Example 3: RabbitMQ producers - multiple connections in one file
<sutra_memory>
<task>
<move from="current" to="completed">1</move>
<move from="pending" to="current">2</move>
<remove>5</remove>
</task>
<code>
<add id="1">
<file>src/messaging/rabbitmq_producers.py</file>
<start_line>15</start_line>
<end_line>28</end_line>
<description>Order processing producer call with actual queue name and environment variable RABBITMQ_URL</description>
</add>
<add id="2">
<file>src/messaging/rabbitmq_producers.py</file>
<start_line>45</start_line>
<end_line>58</end_line>
<description>Notification producer call with actual queue name and environment variable RABBITMQ_URL</description>
</add>
<remove>3</remove>
</code>
<add_history>Analyzed RabbitMQ producers in src/messaging/rabbitmq_producers.py - found 2 outgoing connections: OrderProducer publishes to order processing queue using RABBITMQ_URL environment variable, NotificationProducer publishes to notification queue on same server. Both use pika library with connection pooling. OrderProducer called from OrderService line 67, NotificationProducer called from UserController line 134. Stored both producer CALL SITES with actual queue names and environment variables for cross-indexing analysis.</add_history>
</sutra_memory>

Example 4: Inter-service HTTP calls - outgoing connections between user services
<sutra_memory>
<task>
<add id="3" to="pending">Look at src/services/userService.js file for HTTP calls to other user services - check getUserData function line 23-35</add>
<add id="4" to="pending">Look at src/services/orderService.js file for HTTP calls to user service - check validateUser function line 67-78</add>
</task>
<code>
<add id="3">
<file>src/services/userService.js</file>
<start_line>23</start_line>
<end_line>35</end_line>
<description>HTTP call to internal notification service using environment variable NOTIFICATION_SERVICE_URL</description>
</add>
<add id="4">
<file>src/services/orderService.js</file>
<start_line>67</start_line>
<end_line>78</end_line>
<description>HTTP call to internal user service using environment variable USER_SERVICE_URL</description>
</add>
</code>
<add_history>Used semantic_search for "await fetch" - found 2 inter-service HTTP connections: UserService.getUserData() calls internal notification service using NOTIFICATION_SERVICE_URL environment variable, OrderService.validateUser() calls internal user service using USER_SERVICE_URL environment variable. Both use fetch() with async/await pattern for communication between user's own services. UserService called from NotificationController line 45, OrderService called from OrderController line 23. Stored both actual fetch call sites with environment variables for cross-indexing analysis.</add_history>
</sutra_memory>

Example 5: Connection discovery with pending task management
<sutra_memory>
<task>
<add id="5" to="pending">Look at src/api/routes.py file for API endpoints</add>
<add id="6" to="pending">Look at src/messaging/publisher.js file for message queue operations</add>
<add id="7" to="pending">Look at src/server.js file for server configuration</add>
</task>
<add_history>Completed initial project structure analysis. Found main application files: src/api/routes.py contains REST endpoints, src/messaging/publisher.js has message queue publisher functions, src/server.js has server startup code. Added pending tasks to systematically analyze each file for connection patterns. Need to examine routes for incoming connections, message queue publishers for outgoing connections, and server config for listening ports and protocols.</add_history>
</sutra_memory>

Example 6: Task completion scenario (CORRECT way)
<sutra_memory>
<task>
<add id="8" to="completed">Analyze project structure for connection discovery</add>
</task>
<add_history>Used attempt_completion - provided comprehensive connection analysis with all discovered incoming and outgoing connections, task completed successfully</add_history>
</sutra_memory>

Example 7: Task completion scenario (WRONG - do NOT do this)
<sutra_memory>
<task>
<add id="9" to="current">Analyze project structure for connection discovery</add>
</task>
<add_history>Completed connection analysis with attempt_completion</add_history>
</sutra_memory>

Example 8: Router Files - Multiple Specific Tasks Instead of One Broad Task
<sutra_memory>
<task>
<add id="10" to="pending">Check src/routes/userRouter.js file for user-related API endpoints - look for app.get, app.post, app.put, app.delete methods</add>
<add id="11" to="pending">Check src/routes/authRouter.js file for authentication endpoints - look for login, logout, register, token validation routes</add>
<add id="12" to="pending">Check src/routes/orderRouter.js file for order management endpoints - look for order creation, status updates, payment processing routes</add>
<add id="13" to="pending">Check src/routes/adminRouter.js file for admin panel connections - look for user management, system configuration, reporting endpoints</add>
<move from="pending" to="current">10</move>
</task>
<add_history>Found 4 router files during project structure analysis: userRouter.js, authRouter.js, orderRouter.js, adminRouter.js. Created separate specific tasks for each router file to systematically examine their endpoints. Each task focuses on specific functionality - user operations, authentication, order management, and admin operations. This approach ensures thorough analysis of each router's connection patterns without missing any endpoints.</add_history>
</sutra_memory>

# Sutra Memory Guidelines:

1. In <thinking> tags, assess what connection information you already have and what connection patterns you need to discover. Also review your current sutra_memory state including analysis tasks, stored connection code, and determine what updates are needed based on iteration progress and findings. Identify any connection information that will be needed in future iterations but not used in the current iteration, and store it directly in Sutra Memory using appropriate tags (<code> for connection code snippets, <history> for other important data like search results, file listings, connection discoveries) to prevent redundant tool calls and maintain context across iterations. Data of current iteration won't be available in the next iterations - only stored data in sutra memory is persistent across iterations. When you discover specific function names, class names, or file paths during analysis, consider using the database tool to retrieve complete code implementations for thorough connection analysis.

FIRST ITERATION RULE:
- Start with a tool call (list_files) to explore the project structure first and identify package files (package.json, pom.xml, requirements.txt, setup.py, pyproject.toml, go.mod, etc.)
- Use database tool to examine package files and identify used connection packages in the current project
- CRITICAL: Never add task lists just by seeing list of files - first check package.json file and find using imports of used packages and some common patterns which can be used without any packages
- Create task list in Sutra Memory ONLY after analyzing package files to understand which packages are actually used and their import statement patterns based on language
- Also consider common built-in patterns that don't require packages (like native fetch(), http modules, WebSocket constructors) add those to task list
- Then proceed with three-phase analysis: package discovery, import statement analysis, and usage pattern discovery
- Use tools like list_files, database, semantic_search, and search_keyword systematically based on discovered packages and built-in patterns

TASK LIST UPDATES IN SUBSEQUENT ITERATIONS:
- Based on your thinking and discoveries, update your task list by adding new specific tasks, completing current tasks, and moving pending tasks to current
- Add new tasks discovered during analysis with specific file paths and technologies found
- Mark completed tasks and move them from current to completed status
- Update task descriptions with more specific information when available
- Remove tasks that are no longer relevant or needed

2. When to Add Tasks:
   - Connection Dependencies when discovering connections that might affect other connection points
   - Cross-file Connection Impacts when connection patterns in one file require analysis in related files
   - Technology Validation when existing connection configurations need compatibility verification
   - Analysis Steps when breaking down complex connection discovery into manageable tasks
   - TASK CREATION GUIDELINES FOR THREE-PHASE APPROACH:
     - Phase 1 tasks: "Analyze package.json to identify connection packages like axios, express, socket.io"
     - Phase 2 tasks: "Search for import statements of axios package using regex pattern 'require\\('axios'\\)|import.*from.*'axios'"
     - Phase 3 tasks: "Search for axios usage patterns and wrapper functions in files that import axios"
     - Be SPECIFIC and INFORMATIVE: Instead of "Search for database connection patterns" write "Search for mongoose usage patterns in files that import mongoose package"
     - Include EXACT file paths when known: "Look for RabbitMQ usage in src/services/messageQueue.js after finding amqplib import"
     - Mention SPECIFIC technologies found in packages: "Search for axios HTTP calls in src/api/ directory (after finding axios in package.json)"
     - Include CONTEXT from previous discoveries: "Found axios import in src/services/apiClient.js, search for axios usage patterns"
     - Be ACTIONABLE: "Use database tool to examine axios wrapper function in src/services/apiClient.js"
     - GOOD EXAMPLES:
       - "Phase 1: Analyze package.json to identify connection packages"
       - "Phase 2: Search for amqplib import statements using regex 'require\\('amqplib'\\)'"
       - "Phase 3: Search for amqplib usage patterns in src/messaging/producer.js"
     - BAD EXAMPLES:
       - "Search for database connection patterns"
       - "Look for message queue implementations"
       - "Check for API connections"

3. When to Store Code:
   - Essential connection identifiers (API endpoints, API calls, message producers/consumers) discovered through search_keyword, semantic_search, or database tools
   - ONLY inter-repository connections (NOT internal business logic or application flow)
   - Future Reference for connection code that will be needed in upcoming analysis iterations
   - Critical Context for connection code that provides essential context for decision-making
   - NEVER store full implementations - only the specific lines that establish connections

4. When to Remove Code:
   - Code that doesn't represent actual inter-repository connections
   - Internal business logic or application flow that was mistakenly stored
   - Full implementations when only connection identifiers are needed
   - Outdated Information when stored connection code is no longer relevant to current analysis
   - Completed Analysis when connection analysis is finished and no longer needed
   - Memory Optimization when code storage becomes cluttered with unused connection snippets
   - Context Change when analysis direction changes making stored connection code irrelevant
   - Before completion - clean up to keep only essential connection identifiers

5. History Best Practices:
   - Be specific about tool names and parameters used with exact queries/commands for connection discovery
   - Mention key connection findings, results, and outputs in detail
   - Note any failures or null results to avoid repetition in connection searches
   - Include complete file names, function names, and paths when relevant to connections
   - Store comprehensive connection information that will be needed for upcoming iterations
   - ALWAYS REVIEW YOUR HISTORY before starting new iterations to understand previous connection context
   - Store important information like connection function names, configuration file paths, technology patterns, and discoveries
   - Include relevant search results, tool responses, and connection data that may be needed later
   - Record file paths from list_files operations if those paths will be referenced in future connection analysis
   - Store connection configuration details, technology information, and system responses
   - Add connection findings that can be used for future searches or implementations to pending tasks
   - Record any important connection patterns, configurations, or technology structures discovered during analysis
   - Include error messages, warnings, and diagnostic information that might be relevant to connection analysis later
   - Store connection search results, database query results, and other data outputs when they provide context for future operations
   - Document connection discovery outputs, technology identification results, and system information that affects subsequent iterations

6. Task Management Rules:
   - Only ONE task can be in "current" status at any time
   - Complete or move current task before assigning new current task
   - Tasks flow through pipeline: pending to current to completed
   - Remove completed tasks when no longer needed for reference
   - Add tasks as you discover connection dependencies or requirements during analysis
   - If a task is finished in the current iteration, it should be added as "completed", not "current" and if there is any pending task that needs to be moved to the current task.
   - Only mark connection analysis tasks as completed AFTER you have documented all connections in the current scope

7. Integration Workflow:
   - Start of Iteration by reviewing current connection analysis task and pending tasks from previous sutra_memory
   - Tool Selection by checking history to avoid redundant connection discovery operations
   - Result Analysis to determine if current connection analysis task is complete or needs more work
   - Task Updates by adding new connection analysis tasks discovered during analysis
   - Code Storage by saving important connection code for future reference
   - Code Cleanup by removing outdated or completed connection code snippets
   - History Update by recording current iteration's connection analysis actions and findings (MANDATORY)

8. Critical Rules:
   - Sutra Memory MUST be updated in every cross-indexing response alongside exactly one tool call
   - At minimum, add_history must be included in each iteration
   - Task IDs must be unique and sequential across all iterations
   - Code storage should include descriptive context explaining connection importance
   - Always check existing history before making similar connection discovery tool calls
   - Tasks should be specific and actionable for connection analysis
   - Only one current task allowed at a time
   - Remove tasks and code when no longer needed to maintain clean memory
   - This is NOT a tool but a memory management system that works alongside tool usage
   - NEVER respond with only sutra_memory without a tool call - this violates system architecture
   - COMPLETION RULE: When using attempt_completion, add completed tasks to "completed" status, NEVER to "current" status
   - If you just finished a connection analysis task in the current iteration, it belongs in "completed", not "current"

9. CRITICAL STORAGE RULES - SUTRA MEMORY VS ATTEMPT_COMPLETION:
   - Sutra memory: Store code together in one code block if possible - can include multiple related connections in one code block for analysis purposes without unnecessary chunking
   - Attempt_completion output: Must return each connection point lines separately with specific line numbers - create separate entries for each individual API endpoint, HTTP call, or connection point
   - CRITICAL: If you find 60+ connections using search_keyword, you must store ALL 60+ in sutra memory using <code> rahther than storing just a few representative ones
   - This allows comprehensive analysis in sutra memory while ensuring every single connection gets its own detailed entry in final output
   - ZERO TOLERANCE for skipping connections: Every single connection found must be included in attempt_completion
   - MANDATORY: When using search_keyword and finding multiple connection calls, you MUST store every single one
   - NO SAMPLING: Never store "representative examples" - store every single connection discovered
   - COMPLETE ANALYSIS: If search_keyword returns 100 results and if it is an any connection type, you must store all 100 by providing their file paths and line numbers in sutra memory
   - EXAMPLE: If search_keyword finds 40 connections for "callUserApi(" you MUST store ALL 40 connections in sutra memory. This is MANDATORY and NON-NEGOTIABLE. and while giving attempt_completion, you must include all 40 connections with their file paths and line numbers.
"""
