template_string ToolUsageExamples_Phase2() #"
====

# TOOL USAGE EXAMPLES

This section provides comprehensive examples of how to use different tools effectively for import analysis and implementation task creation.

1. IMPORT PATTERN ANALYSIS EXAMPLES

DIFFERENT IMPORT SYNTAX EXAMPLES:

Example 1: JavaScript/Node.js import variations
For Example:
- const axios = require('axios')
- import axios from 'axios'
- import { get, post } from 'axios'
- const { get, post } = require('axios')

Example 2: Python import variations
For Example:
- import requests
- from requests import get, post
- import requests as req
- from requests.auth import HTTPBasicAuth

Example 3: Java import pattern examples
For Example:
- import org.springframework.web.client.RestTemplate
- import retrofit2.http.GET
- import okhttp3.OkHttpClient

Example 4: Go import pattern examples
For Example:
- import "net/http"
- import "github.com/gorilla/mux"
- import ( "net/http" "encoding/json" )

Example 5: Router framework import examples
For Example:
- const { Router } = require("express");
- import { Router } from "express";
- import express from "express";
- const express = require("express");

2. REGEX PATTERN EXAMPLES FOR SEARCH_KEYWORD

ROBUST REGEX PATTERNS WITH EXPLANATIONS"

JavaScript/Node.js Import Patterns:
- require\\s*\\(\\s*['\"]axios['\"]\\s*\\) → matches require('axios') or require("axios") with optional whitespace
- import\\s+axios\\s+from\\s+['\"]axios['\"] → matches import axios from 'axios' or import axios from "axios"
- import\\s*\\{[^}]*\\}\\s*from\\s*['\"]axios['\"] → matches import { get, post } from 'axios'
- const\\s*\\{[^}]*\\}\\s*=\\s*require\\s*\\(\\s*['\"]axios['\"]\\s*\\) → matches const { get, post } = require('axios')

Express Router Patterns:
- (app|router)\\.(get|post|put|delete|patch)\\s*\\( → matches app.get( or router.post( with optional whitespace
- express\\s*\\(\\s*\\)\\.use → matches express().use for middleware
- new\\s+express\\s*\\( → matches new express( instantiation

Python Import Patterns:
- ^\\s*import\\s+requests → matches import requests at line start
- ^\\s*from\\s+requests\\s+import → matches from requests import statements
- ^\\s*import\\s+urllib\\.(request|parse|error) → matches urllib submodule imports

COMPREHENSIVE REGEX PATTERN EXAMPLES"

Axios Complete Pattern:
require\\s*\\(\\s*['\"]axios['\"]\\s*\\)|import\\s+axios\\s+from\\s+['\"]axios['\"]; import\\s*\\{[^}]*\\}\\s*from\\s*['\"]axios['\"]|const\\s*\\{[^}]*\\}\\s*=\\s*require\\s*\\(\\s*['\"]axios['\"]\\s*\\)

Express Complete Pattern:
require\\s*\\(\\s*['\"]express['\"]\\s*\\)|import\\s+express\\s+from\\s+['\"]express['\"]|import\\s*\\{[^}]*Router[^}]*\\}\\s*from\\s*['\"]express['\"]

Socket.io Complete Pattern:
require\\s*\\(\\s*['\"]socket\\.io['\"]\\s*\\)|import\\s+[^\\s]+\\s+from\\s+['\"]socket\\.io['\"]

3. IMPLEMENTATION TASK CREATION EXAMPLES

IMPLEMENTATION ANALYSIS TASK CREATION:

Example 1: After finding axios imports in 3 files
Create 3 separate implementation tasks (database tool - individual tasks per file):
- Task 1: "Found axios imports in src/api/client.js. Use database tool to read this file completely and analyze axios.get(), axios.post(), axios.put(), axios.delete() usage patterns. Look for actual HTTP calls with real endpoints and parameters. This HTTP client is used for making requests to other services."
- Task 2: "Found axios imports in src/services/http.js. Use database tool to read this file completely and analyze axios.get(), axios.post(), axios.put(), axios.delete() usage patterns. Look for actual HTTP calls with real endpoints and parameters. This HTTP client is used for making requests to other services."
- Task 3: "Found axios imports in src/utils/request.js. Use database tool to read this file completely and analyze axios.get(), axios.post(), axios.put(), axios.delete() usage patterns. Look for actual HTTP calls with real endpoints and parameters. This HTTP client is used for making requests to other services."

Example 2: After finding express imports in 8 files
Create implementation task(Add): "Found express imports in 8 files. Use search_keyword tool with pattern '(app|router)\\.(get|post|put|delete|patch)\\s*\\(' and regex=true, after_lines=4 to find express route definitions across all files. Look for actual route handlers with real endpoint paths. This server framework receives requests from other services."

Example 3: After finding Spring imports in 6 files
Create implementation task(Add): "Found Spring framework imports in 6 files. Use search_keyword tool with pattern '@(RequestMapping|GetMapping|PostMapping|PutMapping|DeleteMapping)\\s*\\(' and regex=true, after_lines=4 to find Spring controller endpoints across all files. Look for actual REST endpoints with real paths."

Example 4: After finding Socket.io imports in 4 files
Create implementation task(Add): "Found Socket.io imports in 4 files. Use search_keyword tool with pattern 'io\\s*\\(|socket\\.(on|emit)\\s*\\(' and regex=true, after_lines=4 to find Socket.io usage patterns across all files. Look for actual WebSocket event handlers and emissions."

4. BUILT-IN PATTERN TASK CREATION (ALWAYS REQUIRED)

MULTI-LANGUAGE BUILT-IN PATTERN EXAMPLES:

Example 1: JavaScript built-in pattern task creation
Create implementation task(Add): "Create built-in pattern task for JavaScript: Use search_keyword with pattern 'fetch\\s*\\(|new\\s+XMLHttpRequest\\s*\\(|new\\s+WebSocket\\s*\\(' and regex=true, after_lines=4 to find native JavaScript connection patterns across all files."

Example 2: Python built-in pattern task creation
Create implementation task(Add): "Create built-in pattern task for Python: Use search_keyword with pattern 'urllib\\.(request|parse|error)\\.|http\\.client\\.|socket\\.(socket|create_connection)\\(' and regex=true, after_lines=4 to find Python built-in connection patterns across all files."

Example 3: Java built-in pattern task creation
Create implementation task(Add): "Create built-in pattern task for Java: Use search_keyword with pattern 'HttpURLConnection|new\\s+Socket\\s*\\(|ServerSocket\\s*\\(' and regex=true, after_lines=4 to find Java built-in connection patterns across all files."

Example 4: Go built-in pattern task creation
Create implementation task(Add): "Create built-in pattern task for Go: Use search_keyword with pattern 'http\\.(Get|Post|Put|Delete)|net\\.Dial\\s*\\(' and regex=true, after_lines=4 to find Go built-in connection patterns across all files."

5. TOOL SELECTION STRATEGY FOR IMPLEMENTATION TASKS

DATABASE TOOL TASK CREATION (3-5 files)
When imports found in few files, create separate tasks for each file:
For Example:
- Task 1: "Use database tool to read file1 and analyze [package] usage patterns"
- Task 2: "Use database tool to read file2 and analyze [package] usage patterns"
- Task 3: "Use database tool to read file3 and analyze [package] usage patterns"

SEARCH_KEYWORD TASK CREATION (6+ files)
When imports found in many files, create combined tasks:
For Example: "Use search_keyword to find [package] usage patterns across [X] files with pattern '[robust_regex_pattern]' and regex=true"

6. COMPLETION EXAMPLES

ATTEMPT_COMPLETION USAGE:

Example 1: Comprehensive import analysis with packages
attempt_completion(result="Import analysis complete. Found imports in 15 files: axios (3 files), express (8 files), socket.io (4 files). Created 5 implementation tasks (3 individual database tasks for axios files, 1 combined search_keyword task for express files, 1 combined search_keyword task for socket.io files) and 3 built-in pattern tasks for subsequent implementation analysis.")

Example 2: Built-in patterns focus
attempt_completion(result="Import analysis complete. No advanced packages found. Created 4 built-in pattern tasks for subsequent analysis: JavaScript fetch patterns, Python urllib patterns, Java HttpURLConnection patterns, Go net/http patterns."))

7. CRITICAL GUIDELINES

- Execute ALL pending tasks from previous analysis
- Use appropriate search patterns with proper regex escaping as specified in previous analysis tasks
- CRITICAL: After seeing tool results when marking a task as completed, if you found meaningful import information, create new implementation tasks for the next phase
- Create implementation analysis tasks based on number of files found with imports
- ALWAYS create built-in pattern tasks for subsequent analysis regardless of whether packages were found
- Include specific file paths and usage patterns in implementation task descriptions

"#
