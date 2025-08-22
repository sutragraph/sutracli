"""
Tool Guidelines for Implementation Discovery

Specific guidelines for tool usage during implementation discovery.
"""

IMPLEMENTATION_DISCOVERY_TOOL_GUIDELINES = """====

TOOL GUIDELINES

This section provides specific guidelines for using tools effectively during implementation discovery to find actual usage of imported connection methods.

1. In <thinking> tags, first review your Sutra Memory to understand current implementation discovery progress, completed discoveries, and previous tool results to avoid redundancy. Then assess what implementation information you already have and what you need to discover next.

CRITICAL ANALYSIS DECISION PROCESS: In your <thinking> tags, always ask yourself: "Should I track this discovered implementation pattern in sutra memory? Will this information be needed for analysis and future reference?" If yes, track it immediately with complete parameter details.

ANALYSIS DECISION CRITERIA:
- Track any connection implementation patterns, API calls, route definitions discovered
- Track search results that reveal important connection usage with real parameters
- Track any patterns that are related to actual service-to-service communication
- Track wrapper function usage and environment variable configurations
- Remember: If information is not tracked in sutra memory, it will not be available for future analysis and reference

Follow the systematic analysis flow and track every single implementation discovery in Sutra Memory immediately after discovering it with complete parameter details.

Critical: Update your task list in every iteration based on your thinking:
- Execute pending tasks systematically by moving from pending to current to completed
- Add new specific tasks discovered during analysis when needed for deeper analysis
- Remove tasks that are no longer relevant
- Update task descriptions with more specific information when available

2. TOOL SELECTION STRATEGY

**DATABASE TOOL USAGE**
- Use when import discovery found few files (2-3) with specific imports
- Read entire file content to analyze all connection usage within those files
- Essential for understanding complete context and relationships between methods
- Provides comprehensive view of all connections and their actual usage patterns
- Best for thorough analysis when dealing with limited number of files

**SEARCH_KEYWORD TOOL USAGE**
- Use when import discovery found many files (4+) with imports
- Use for wrapper function usage discovery across entire codebase
- Efficient for finding specific usage patterns across multiple files
- Essential for built-in language patterns that don't require imports
- Include appropriate context lines (after_lines=2-3) to capture complete usage

2. TASK EXECUTION WORKFLOW

**Step 1: Review Pending Tasks**
- Check sutra_memory for pending tasks from import pattern discovery
- Execute tasks one by one systematically based on their guidance
- Follow tool selection guidance provided in each task

**Step 2: Execute Implementation Analysis**
- Use database tool for few files with complete file analysis
- Use search_keyword for many files or wrapper function patterns
- Focus on actual usage with real parameters and endpoint values
- Analyze connection establishment code, not generic definitions
- MANDATORY: When you find environment variables (process.env.*, config.*), immediately check sutra memory and create config file search tasks if needed

**Step 3: Create Additional Tasks**
- Add tasks for wrapper function usage when discovered during analysis
- Create tasks for environment variable resolution with specific tool guidance
- Add tasks for complex connection patterns requiring deeper analysis

3. WHAT TO ANALYZE AND FIND

**FIND THESE (Actual usage with real values):**
- API calls with actual endpoints and parameters that connect to other services
- Route definitions with real endpoint paths that receive data from other services
- WebSocket connections with actual event names for real-time communication
- Message queue operations with real queue names for service communication
- Wrapper function calls with actual parameters for service-to-service communication
- Environment variable usage in connection configurations with resolved values

**DON'T FOCUS ON THESE (Generic definitions):**
- Generic wrapper function definitions without actual usage
- Generic client creation without usage or real endpoints
- Middleware configuration without endpoint definitions
- Utility functions without actual connections to other services
- Test code, mock implementations, and development debugging code

4. WRAPPER FUNCTION ANALYSIS GUIDELINES

**Critical Workflow for Dynamic Parameters:**
- When you find wrapper functions with dynamic parameters (url, endpoint variables), MUST read complete file first with database tool
- Identify the actual function name containing the wrapper calls
- Create search_keyword task to find all usage sites with real parameter values
- DO NOT move to next task until actual usage patterns are found

**Task Format Examples:**
- "Found wrapper function with dynamic parameters in src/utils/helper.js. Use database tool to read complete file and identify function name. Then create task to find actual usage patterns."
- "Found apiCallFunction() wrapper with url parameter. Use search_keyword to find apiCallFunction usage patterns: apiCallFunction\\("
- "Found makeRequest() function with dynamic endpoint. Use search_keyword to find makeRequest calls: makeRequest\\("

5. COMPLETION CRITERIA

**When to Use attempt_completion:**
- All import pattern discovery tasks have been executed systematically
- All connection usage has been analyzed based on discovered imports
- All relevant connection code has been found and analyzed
- Additional tasks (if any) have been completed successfully

**Completion Summary Format:**
- Number of connection implementations found and analyzed
- Types of connections discovered (HTTP, WebSocket, message queues, etc.)
- Files analyzed and connection code found
- Summary of connection patterns found with service communication context

6. ERROR HANDLING AND TROUBLESHOOTING

**Common Issues and Solutions:**
- No usage found: Verify search patterns match actual imports and try pattern variations
- Too many generic results: Focus on actual usage patterns with real parameters
- Missing context: Use appropriate after_lines parameter (2-3) to capture complete usage
- Incomplete results: Ensure tool calls return relevant connection code for analysis

**Best Practices:**
- Always execute import pattern discovery tasks before creating additional tasks
- Use tool selection guidance provided in tasks
- Focus on actual usage with real parameters, not generic definitions
- Analyze connection code thoroughly to understand service communication patterns
"""
