SUTRA_MEMORY = """====

SUTRA MEMORY

Sutra Memory is a dynamic memory system that tracks cross-indexing analysis state across iterations. It is fully managed by the Cross-Index agent and invisible to the user. This system ensures continuity, prevents redundant operations, and maintains context for complex multi-step connection discovery tasks. The system tracks iteration history (last 20 entries - where 1 is the most recent/newest history entry) and manages analysis tasks (current, pending, completed) for comprehensive connection analysis.

Required Components:
- add_history: Comprehensive summary of current iteration actions, tool usage, connection discoveries, and information tracking for future iterations (MANDATORY in every response)

Optional Components:
- task: Manage analysis tasks by adding new ones or moving between pending/current/completed status with unique IDs (only ONE current task allowed at a time)
- code: Remove irrelevant or incorrect connection code snippets from memory when they are not actual connections between user services

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
<remove>code_id</remove>
</code>

<add_history>Brief summary of current iteration actions and findings any important information that will be needed in future iterations</add_history>
</sutra_memory>

Examples:

Example 1: Task management for connection analysis
<sutra_memory>
<task>
<add id="1" to="completed">Analyze src/api/routes.py file for API endpoints</add>
<add id="2" to="current">Search for all calls to makeHttpRequest() wrapper function using search_keyword</add>
</task>
<add_history>Used database tool to analyze src/api/routes.py - found 30+ incoming connection endpoints. All endpoints use Flask decorators and accept external HTTP requests.</add_history>
</sutra_memory>

Example 2: Comprehensive task creation for all discovered packages
<sutra_memory>
<task>
<add id="3" to="completed">Analyze package.json - found express, axios, cors, data-client, communication-lib</add>
<add id="4" to="current">Search for import statements of express using search_keyword for require/import patterns</add>
<add id="5" to="pending">Search for import statements of axios using search_keyword for require/import patterns</add>
<add id="6" to="pending">Search for import statements of data-client using search_keyword for require/import patterns</add>
<add id="7" to="pending">Search for import statements of communication-lib using search_keyword for require/import patterns</add>
<add id="8" to="pending">Search for native fetch and built-in HTTP patterns using search_keyword</add>
</task>
<add_history>Used database tool to examine package.json - found ALL packages including client variants and communication libraries. Created comprehensive task list for all discovered packages.</add_history>
</sutra_memory>

Example 3: Task completion scenario
<sutra_memory>
<task>
<add id="5" to="completed">Analyze project structure for connection discovery</add>
</task>
<add_history>Used attempt_completion - provided brief summary of connection types discovered and analyzed, all connection analysis completed</add_history>
</sutra_memory>

Example 4: Import-based search pattern execution
<sutra_memory>
<task>
<add id="9" to="completed">Search for import statements of data-client - found imports in 3 files</add>
<add id="10" to="current">Use import-based search patterns for data-client usage: search for Client() and client.connect() patterns</add>
</task>
<add_history>Found imports 'import { Client } from 'data-client'' in 3 files. Now using import-based search patterns to find actual usage of Client() and client methods rather than opening whole files.</add_history>
</sutra_memory>

Example 5: Removing irrelevant code from memory
<sutra_memory>
<task>
<add id="11" to="current">Analyze remaining HTTP client wrapper functions</add>
</task>
<code>
<remove>code_3</remove>
</code>
<add_history>Used search_keyword to analyze axios calls - found that code_3 was actually a third-party API call to external service, not internal connection. Removed irrelevant code from memory and continuing analysis of internal service connections.</add_history>
</sutra_memory>


# Sutra Memory Guidelines:

1. Memory Assessment
In <thinking> tags, assess what connection information you already have and what connection patterns you need to discover. Also review your current sutra_memory state including analysis tasks and determine what updates are needed based on iteration progress and findings. Identify any connection information that will be needed in future iterations but not used in the current iteration, and track it directly in Sutra Memory using appropriate tags to prevent redundant tool calls and maintain context across iterations. Data of current iteration won't be available in the next iterations - only tracked data in sutra memory is persistent across iterations. When you discover specific function names, class names, or file paths during analysis, consider using the database tool to retrieve complete code implementations for connection analysis.

2. First Iteration Protocol
- Start with a tool call (list_files) to explore the project structure first and identify package files (package.json, pom.xml, requirements.txt, setup.py, pyproject.toml, go.mod, etc.)
- Use database tool to examine package files and identify used connection packages in the current project
- CRITICAL: Never add task lists just by seeing list of files - first check package.json file and find using imports of used packages and some common patterns which can be used without any packages
- Create comprehensive task list in Sutra Memory ONLY after analyzing package files to understand which packages are actually used:
  - Include ALL packages found in package files, not just a subset
  - Create tasks for communication libraries with descriptive names indicating their purpose
- ALWAYS consider common built-in patterns that don't require packages (like native fetch(), http modules, WebSocket constructors) and add those to task list
- ADAPTIVE STRATEGY: If no advanced packages are found, prioritize built-in patterns over searching for non-existent libraries
- Then proceed with three-phase analysis: package discovery, import statement analysis, and usage pattern discovery and collection
- Use tools like list_files, database, and search_keyword systematically based on ACTUALLY discovered packages and built-in patterns
- CRITICAL: Never search for packages patterns if those packages don't exist in the project

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
- Include EXACT file paths from Phase 2 discoveries: "Use database tool to read src/services/apiClient.js (was identified in Phase 2 as importing axios) and analyze all axios method usage"
- Mention SPECIFIC imported methods found in Phase 2: "In src/api/routes.js (imports express), use database tool to read file and analyze express.get, express.post, express.use method calls"
- Include CONTEXT from Phase 2 import analysis: "Found axios import in only 3 files, use database tool to read each file and analyze axios.get, axios.post usage"
- Be ACTIONABLE with appropriate tool selection: "Use database tool to examine src/services/apiClient.js completely and analyze all axios method calls within that file"

5. History Best Practices
- Be specific about tool names and parameters used with exact queries/commands for connection discovery
- Mention key connection findings, results, and outputs in detailed summary format
- Note any failures or null results to avoid repetition in connection searches
- Include complete file names, function names, and paths when relevant to connections
- Track comprehensive connection information that will be needed for upcoming iterations
- ALWAYS REVIEW YOUR HISTORY before starting new iterations to understand previous connection context
- Track important information like connection function names, configuration file paths, technology patterns, and discoveries
- Record file paths from list_files operations if those paths will be referenced in future connection analysis
- Track connection configuration details, technology information, and system responses

6. Task Management Rules
- Only ONE task can be in "current" status at any time
- Complete or move current task before assigning new current task
- Tasks flow through pipeline: pending to current to completed
- Add tasks as you discover connection dependencies or requirements during analysis
- If a task is finished in the current iteration, it should be added as "completed", not "current" and if there is any pending task that needs to be moved to the current task.
- Only mark connection analysis tasks as completed AFTER you have documented all connections in the current scope

7. Integration Workflow
- Start of Iteration by reviewing current connection analysis task and pending tasks from previous sutra_memory
- Tool Selection by checking history to avoid redundant connection discovery operations
- Result Analysis to determine if current connection analysis task is complete or needs more work
- Task Updates by adding new connection analysis tasks discovered during analysis
- History Update by recording current iteration's connection analysis actions and findings (MANDATORY)

8. Code Removal Guidelines
- Remove code snippets that are discovered to be external API calls or third-party service integrations
- Remove code that doesn't represent actual connections between user's own services
- Remove duplicate or redundant code snippets that provide no additional connection information
- Remove code that was incorrectly identified as connection code during initial analysis
- Use <remove>code_id</remove> format to remove specific code snippets by their ID

9. Critical Rules
- Sutra Memory MUST be updated in every cross-indexing response alongside exactly one tool call
- At minimum, add_history must be included in each iteration
- Task IDs must be unique and sequential across all iterations
- Always check existing history before making similar connection discovery tool calls
- Tasks should be specific and actionable for connection analysis
- Remove tasks when no longer needed to maintain clean memory
- Remove code snippets when they are found to be irrelevant to data connections
- This is NOT a tool but a memory management system that works alongside tool usage
- NEVER respond with only sutra_memory without a tool call this violates system architecture
- COMPLETION RULE: When using attempt_completion, add completed tasks to "completed" status, NEVER to "current" status
- If you just finished a connection analysis task in the current iteration, it belongs in "completed", not "current"
"""
