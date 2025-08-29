template_string ToolUsageExamples_Phase1() #"
====

TOOL USAGE EXAMPLES

This section provides comprehensive examples of how to use different tools effectively for package discovery and task creation.

1. PROJECT STRUCTURE EXPLORATION

**LIST_FILES EXAMPLES**

Example 1: Initial project exploration
- list_files(path=".", max_depth=2)
- Purpose: Get overview of project structure and identify package files
- Look for package configuration files (examples: package.json, requirements.txt)

Example 2: Focused package file search
- list_files(path=".", pattern="package.json|requirements.txt")
- Purpose: Find package configuration files in the project
- Result: List of package files to analyze

2. PACKAGE FILE ANALYSIS

**DATABASE TOOL EXAMPLES**

Example 1: Node.js package analysis
- database(query_type="GET_FILE_BY_PATH", file_path="package.json")
- Purpose: Read package.json to identify connection-related dependencies
- Look for communication packages (examples: axios, express)

Example 2: Python package analysis
- database(query_type="GET_FILE_BY_PATH", file_path="requirements.txt")
- Purpose: Read requirements.txt to identify connection libraries
- Look for: HTTP client libraries, web frameworks, WebSocket libraries, message queue libraries

Example 3: Java package analysis
- database(query_type="GET_FILE_BY_PATH", file_path="pom.xml")
- Purpose: Read pom.xml to identify connection dependencies
- Look for: HTTP client libraries, web frameworks, WebSocket libraries, message queue libraries

3. TASK CREATION EXAMPLES

**COMPREHENSIVE TASK CREATION**

Example 1: After finding axios package in package.json
Create task: "Use search_keyword tool with pattern 'require\\('axios'\\)|import.*from.*'axios'|import.*axios|axios' and regex=true to find all axios import statements. This HTTP client library is used for making requests to other services. Search across all JavaScript/TypeScript files."

Example 2: After finding express package in package.json
Create task: "Use search_keyword tool with pattern 'require\\('express'\\)|import.*from.*'express'|import.*express' and regex=true to find all express import statements. This server framework is used for receiving requests from other services. Search across all JavaScript/TypeScript files."

4. COMPLETION EXAMPLES

**ATTEMPT_COMPLETION USAGE**

Example 1: Successful package discovery
attempt_completion(result="Package discovery complete. Found 5 connection packages (axios, express, socket.io, ws, cors) and created 8 tasks for import pattern discovery.")

5. CRITICAL GUIDELINES

- Create tasks instantly after analyzing each package file
- Use specific search patterns with proper regex escaping
- Include ALL discovered packages in task creation
- Use specific search patterns with proper regex escaping
- Create descriptive task names with clear search objectives
"#