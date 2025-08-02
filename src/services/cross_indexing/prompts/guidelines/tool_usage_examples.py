"""
Tool Usage Examples for Cross-Indexing

This module provides comprehensive examples of how to use different tools
and how to include variable information from environment and config files.
"""

TOOL_USAGE_EXAMPLES = """====

TOOL USAGE EXAMPLES

This section provides comprehensive examples of how to use different tools effectively and how to include environment and configuration variable information in connection descriptions.

1. TOOL SELECTION STRATEGY FOR PHASE 3

Choose the right tool based on the number of files with imports discovered in Phase 2:

**DATABASE TOOL EXAMPLES (Use when 3-5 files have imports)**

Example 1: Few files with Express imports
- After finding `const express = require('express')` in only 3 files in Phase 2
- Use database tool to read each file completely: `database(query_type="GET_CODE_FROM_FILE", file_path="src/routes/api.js")`
- Purpose: Read entire file content and analyze all express usage patterns within that file
- Result: Get complete context of all route definitions and handlers

Example 2: Few files with Axios imports
- After finding `import axios from 'axios'` in only 4 files in Phase 2
- Use database tool to read each file: `database(query_type="GET_CODE_FROM_FILE", file_path="src/services/httpClient.js")`
- Purpose: Read entire file and analyze all axios method calls within that file
- Result: Get complete context of all HTTP client calls with parameters

**SEARCH_KEYWORD EXAMPLES (Use when 6+ files have imports OR for wrapper functions)**

Example 3: Many files with socket.io imports
- After finding socket.io imports in 8+ files in Phase 2
- search_keyword("io\\(|socket\\.(emit|on|connect)|socket", regex=true, after_lines=2)
- Purpose: Find socket.io usage across many files efficiently
- Result: Captures socket connections with endpoint and event context

Example 4: Wrapper function analysis (ALWAYS use search_keyword)
- After discovering custom wrapper function `makeApiCall` in Phase 2
- search_keyword("makeApiCall\\(", regex=true, after_lines=3)
- Purpose: Find all usage sites of wrapper functions across the entire codebase
- Result: Captures all wrapper function calls with actual parameters

**BUILT-IN PATTERNS (ALWAYS use search_keyword - these don't require imports/packages)**

Example 5: Native JavaScript patterns
- search_keyword("fetch\\(|XMLHttpRequest|new WebSocket\\(|fetch|WebSocket", regex=true, after_lines=2)
- Purpose: Find native JavaScript connection patterns that don't require imports
- Result: Captures native HTTP calls, WebSocket connections

Example 6: Node.js built-in patterns
- search_keyword("http\\.request\\(|https\\.request\\(|net\\.createConnection|http|https", regex=true, after_lines=2)
- Purpose: Find Node.js built-in HTTP and network connections
- Result: Captures built-in HTTP client calls and socket connections

Example 7: Python built-in patterns
- search_keyword("urllib\\.request|http\\.client|socket\\.socket\\(|urllib|requests", regex=true, after_lines=2)
- Purpose: Find Python built-in connection patterns
- Result: Captures built-in HTTP and socket connections

Example 8: Basic HTTP project (like express + axios only)
- After Phase 1: Found only express, axios, cors in package.json
- Phase 3 Priority: Focus on express routes, axios calls, and native fetch patterns
- search_keyword("app\\.(get|post|put|delete)\\(|axios\\.(get|post|put|delete)\\(|fetch\\(|axios|express|fetch", regex=true, after_lines=2)
- Purpose: Find actual HTTP communication patterns instead of searching for non-existent packages
- Result: Captures real connection patterns available in the project

2. WRAPPER FUNCTION DISCOVERY EXAMPLES

Step-by-step approach for wrapper function analysis:

WHEN TO ANALYZE WRAPPER FUNCTIONS VS DIRECT CALLS:

FOCUS RULE: Focus on CONNECTION IDENTIFIERS (endpoint names, queue names, socket event names), not data content.

CASE 1: DIRECT CALLS WITH LITERAL CONNECTION IDENTIFIERS
When connection identifiers are literal strings, analyze the call directly:
- `queue.consume("user-adding-queue", addUserHandler)` - ANALYZE: queue name "user-adding-queue" is literal
- `socket.emit("user_status_update", userData)` - ANALYZE: event name "user_status_update" is literal
- `app.get("/api/users", handler)` - ANALYZE: endpoint "/api/users" is literal
- `makeApiCall("/admin/users", "POST", userData)` - ANALYZE: endpoint "/admin/users" is literal

CASE 2: CALLS WITH VARIABLE CONNECTION IDENTIFIERS
When connection identifiers are variables, you must find wrapper function calls:
- `queue.consume(queueName, handler)` - ANALYZE: queueName is variable, find all wrapper calls
- `socket.emit(eventName, data)` - ANALYZE: eventName is variable, find all wrapper calls
- `app.get(routePath, handler)` - ANALYZE: routePath is variable, find all wrapper calls
- `makeApiCall(endpoint, method, data)` - ANALYZE: endpoint is variable, find all wrapper calls

Step 1: Identify if connection identifier is literal or variable
- LITERAL: "user-adding-queue", "/api/users", "user_status_update" - analyze immediately
- VARIABLE: queueName, endpoint, eventName - analyze wrapper functions

Step 2: For VARIABLE connection identifiers, find wrapper function calls
- search_keyword("makeApiCall\\(", regex=true, after_lines=2)
- Result: Find all places where wrapper function is called with actual connection identifiers
- Purpose: Get actual endpoints, queue names, event names used in real connections

Step 3: Analyze calls with actual connection identifiers
For each call site found:
- ANALYZE: The function call with actual connection identifier like:
```
const result = await makeApiCall("/admin/users", "POST", requestData)
```
- FOCUS: Connection identifier "/admin/users" is the key information
- TRACK: "API call for admin user management using endpoint '/admin/users' with POST method"
- Extract actual connection identifiers (real endpoints like "/admin/users", queue names like "user-notifications")
- Identify variable sources for connection identifiers when they use environment variables
- Purpose: Analyze actual connection identifiers, not generic variable-based calls

3. ENVIRONMENT VARIABLE INTEGRATION EXAMPLES

How to include environment and configuration variable information in descriptions:

Focus: Analyze higher-level wrapper function calls, not base library calls

Example 1: Direct call with environment variable
- Code: `const response = await axios.get(`${process.env.API_BASE_URL}/update/data`)`
- Environment: API_BASE_URL=http://localhost:3001
- Description: "HTTP GET call using environment variable API_BASE_URL for endpoint configuration"

Example 2: Wrapper function call with environment variable
- Code: `makeApiCall("/admin/users", "POST", userData, { baseURL: process.env.API_URL })`
- Environment: API_URL=http://localhost:3000
- Description: "API call for admin user management using endpoint '/admin/users' with environment variable API_URL"

4. ENVIRONMENT VARIABLE RESOLUTION WORKFLOW

Step 1: Find actual function calls (not definitions)
Step 2: Identify environment variables used in the calls
Step 3: Search for .env files, config files, or variable definitions
Step 4: Include both variable name and resolved value in description
Step 5: Analyze the actual call line with comprehensive description

Common environment variable patterns to search for:
- `search_keyword("process\\.env\\.[A-Z_]+", regex=true)` - find all env var usage in code
- Use list_files to find environment files (.env, .env.local, etc.)
- Use list_files to find config files (config.js, config.json, config.yaml)

5. DESCRIPTION TEMPLATES

Template for direct API calls:
"[HTTP method] call to [service_name] using environment variable [env_var] configured as [actual_value] for endpoint [endpoint_path] for [purpose]"

Template for wrapper function calls:
"[Connection type] using [wrapper_function] with endpoint [actual_endpoint], method [actual_method], environment variable [env_var] configured as [actual_value] for [purpose]"

BAD EXAMPLES - DO NOT ANALYZE THESE

Bad Example 1: Base HTTP library calls inside wrapper functions
- Code: `return (await axios.get(url, mergedConfig)).data;`
- Why bad: These are internal implementation details, not the actual API calls with endpoints

Bad Example 2: Wrapper function definition
- Code: `function apiCallFunction(endpoint, method, data) { ... }`
- Why bad: Generic definition, no actual endpoints being called

Bad Example 3: Import/require statements
- Code: `const axios = require('axios');`
- Why bad: Library imports are not connection points
"""
