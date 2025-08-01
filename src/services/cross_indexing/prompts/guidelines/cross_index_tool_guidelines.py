"""
Cross-Index Tool Usage Guidelines

Specific guidelines for using tools effectively in connection analysis.
"""

CROSS_INDEX_TOOL_GUIDELINES = """# Cross-Index Tool Use Guidelines

1. In <thinking> tags, first review your Sutra Memory to understand current connection analysis progress, completed discoveries, and previous tool results to avoid redundancy. Then assess what connection information you already have and what you need to discover next.

CRITICAL STORAGE DECISION PROCESS: In your <thinking> tags, always ask yourself: "Should I store this discovered code/connection in sutra memory? Will this information be needed for analysis and future reference?" If yes, store it immediately with complete parameter details.

STORAGE DECISION CRITERIA:
- Store any connection patterns, API endpoints, HTTP calls, or wrapper functions discovered
- Store search results that reveal important connection information
- Store any code that is related to incoming/outgoing connections
- Store environment variable configurations and their resolved values
- Remember: If information is not stored in sutra memory, it will not be available for future analysis and reference

Follow the systematic analysis flow and store every single connection pattern in Sutra Memory immediately after discovering it with complete parameter details.

Mandatory sutra memory storage rules:
- Store every single connection point discovered, no matter how small or similar
- For wrapper function calls like `makeApiCall(endpoint, method, data)`, `publishToQueue(queueName, message)`, `emitSocketEvent(event, data)`, store the exact line number and include comprehensive variable descriptions with actual resolved values
- Code snippets remain exactly as they appear in source code - do not modify the actual code
- In descriptions, include actual variable values and environment variable values (e.g., "API call using endpoint '/admin/users' for admin user management, method 'POST' for creating new user, data variable userData from form, environment variable API_BASE_URL configured as 'https://api.com'")

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

Phase 3: Connection Data Collection
- Based on discovered import statements and usage patterns from Phase 2, analyze actual usage of imported methods in files that have those imports
- CRITICAL: Use the files identified in Phase 2 that contain specific imports, then analyze the actual imported methods/functions being used
- TOOL SELECTION STRATEGY for Phase 3:
  - Few files (3-5 files with imports): Use `database` tool to read entire file content and analyze all connections within those files
  - Many files: Use `search_keyword` with targeted patterns based on actual imports
  - Wrapper functions: Always use `search_keyword` to find all usage sites of wrapper functions across the codebase
- For each file with imports, examine what specific methods are imported and use appropriate tool selection
- Use efficient tool selection based on actual imports rather than blind pattern matching:
  - Use database tool to read files that have specific package imports from Phase 2 (when few files)
  - Extract the imported methods/objects from the import statements
  - Analyze usage of those specific imported methods within those files
  - Use search_keyword only when there are many files or when searching for wrapper functions
  - BUILT-IN PATTERNS that should be searched using search_keyword (these don't require imports):
    - JavaScript: `fetch(`, `XMLHttpRequest`, `new WebSocket(`, Node.js `http.request(`, `https.request(`
    - Python: `urllib.request`, `http.client`, `socket.socket(`
    - Java: `HttpURLConnection`, `new Socket(`
    - Go: `http.Get(`, `http.Post(`, `net.Dial(`
    - C#: `HttpClient`, `WebRequest`
  - These built-in patterns should be included in Phase 3 analysis using search_keyword since they represent actual connection code
- METHOD EXTRACTION STRATEGY for targeted searches:
  - When you find import statements in Phase 2, extract the specific methods/objects being imported
  - Examples:
    - `import { get, post } from 'axios'` → search for `get(` and `post(` calls only in that file
    - `const express = require('express')` → search for `express.` usage patterns in that file
    - `import io from 'socket.io-client'` → search for `io(` calls in that file
    - `from requests import get, post` → search for `get(` and `post(` calls only in that file
    - `import axios from 'axios'` → search for `axios.get`, `axios.post`, etc. in that file
  - NEVER search for methods that weren't actually imported
- BUILT-IN PATTERNS (no imports required) - include these in Phase 3 analysis:
  - JavaScript: native `fetch()`, `XMLHttpRequest`, `WebSocket` constructor, Node.js built-in `http`, `https`, `net` modules
  - Python: built-in `urllib`, `http.client`, `socket` module
  - Java: `HttpURLConnection`, `Socket` classes from standard library
  - Go: `net/http`, `net` packages from standard library
  - C#: `HttpClient`, `WebRequest` from System.Net namespace
- Wrapper function analysis (high priority): When you find custom wrapper functions that make network connections, these are more important than base library calls:
  - HTTP request wrapper functions: Functions that wrap HTTP client libraries for API calls
  - Queue wrapper functions: Functions that wrap message queue operations
  - Socket wrapper functions: Functions that wrap WebSocket operations
  - Service wrapper functions: Functions that wrap service-to-service communication
  - Comprehensive analysis steps:
    - Step 1: Store the wrapper function discovery in sutra memory with its signature
    - Step 2: Immediately search for all function calls using search_keyword with sufficient context
    - Step 3: Store every single function call found - if search_keyword returns 100+ results, store all 100+, not just a few examples
    - Step 4: Storage rules: Store actual wrapper function calls, not the internal library calls inside the wrapper
    - Step 5: For each wrapper function call found, extract and store complete details using line numbers and file_path in sutra memory

3. Summary on attempt_completion tool usage:
- Remove irrelevant stored code from Sutra Memory which is not related to incoming/outgoing connections
- Mandatory: Use `attempt_completion` tool with a brief 3-4 line summary when all connection data is collected in sutra memory
- Never complete analysis without using the attempt_completion tool - the system requires this specific format

4. If multiple connection discovery actions are needed, use one tool at a time per message to accomplish the analysis iteratively, with each tool use being informed by the result of the previous tool use. Do not assume the outcome of any tool use. Each step must be informed by the previous step's result and tracked in your Sutra Memory.

5. Formulate your tool use using the XML format specified for each tool, focusing on connection-related queries and parameters.

6. After each tool use, the user will respond with the result of that tool use. This result will provide you with the necessary information to continue your connection analysis or make further decisions. This response may include:
  - Information about whether the tool succeeded or failed, along with any reasons for failure.
  - Connection-related code findings that you need to analyze and classify.
  - File and directory information that helps you understand where connections might be located.
  - Search results that reveal connection patterns and technologies used in the project.

7. Always wait for user confirmation after each tool use before proceeding. Never assume the success of a tool use without explicit confirmation of the result from the user.

8. After receiving tool results, always update your Sutra Memory with:
   - A history entry summarizing the tool use and its connection-related results
   - Any important connection findings stored for future reference using XML format with proper file paths, line numbers, technology names, and connection direction
   - Connection analysis task status updates (moving from pending to current to completed)
   - New connection discovery tasks identified during the analysis

10. By waiting for and carefully considering the user's response after each tool use, you can react accordingly and make informed decisions about how to proceed with the connection discovery. This iterative process helps ensure the overall success and accuracy of your connection analysis while maintaining comprehensive memory tracking of all discovered connections.
"""
