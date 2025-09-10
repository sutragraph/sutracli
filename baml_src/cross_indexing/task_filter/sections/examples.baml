template_string Examples_TaskFilter() #"
# Task Filtering Examples

## Example 1: Merging Similar Search Pattern Tasks

Input Tasks:
- Task 2: Use search_keyword tool with pattern 'require\\('axios'\\)|import.*from.*'axios'|import.*axios|axios' and regex=true to find axios import statements. Look for HTTP client library imports enabling requests to other services.
- Task 5: Use search_keyword tool with pattern 'require\\('axios'\\)|import.*from.*'axios'|import.*axios' and regex=true to find axios import statements. Look for HTTP client library imports enabling requests to other services.

Analysis: Task 5 is missing '|axios' from the pattern but otherwise identical.

Output:
```json
{
  "tasks": [
    {
      "id": 1,
      "description": "Use search_keyword tool with pattern 'require\\('axios'\\)|import.*from.*'axios'|import.*axios|axios' and regex=true to find axios import statements. Look for HTTP client library imports enabling requests to other services."
    }
  ]
}
```

### Example 2: Merging Multiple Package Search Tasks

Input Tasks:
- Task 3: Use search_keyword tool with pattern 'express' to find Express.js usage
- Task 7: Use search_keyword tool with pattern 'require\\('express'\\)|import.*express' to find Express imports
- Task 12: Use database tool to analyze Express.js server setup in main files

Analysis: All tasks relate to Express.js analysis but use different approaches.

Output:
```json
{
  "tasks": [
    {
      "id": 1,
      "description": "Use search_keyword tool with pattern 'require\\('express'\\)|import.*express|express' and regex=true to find Express.js imports and usage patterns. Look for web server framework imports and setup."
    },
    {
      "id": 2,
      "description": "Use database tool to analyze Express.js server configuration and setup in main application files. Focus on server initialization and middleware setup."
    }
  ]
}
```

## Example 3: Merging Database Tool Tasks for Same File

Input Tasks:
- Task 4: Use database tool to find patterns like app.get(), app.post() in src/index.js file
- Task 8: Use database tool to find patterns like router.get(), router.post() in src/index.js file
- Task 12: Use database tool to analyze Express.js middleware setup in src/index.js file

Analysis: All tasks target the same file (src/index.js) and uses the database tool so it can be merged into one comprehensive analysis.

Output:
```json
{
  "tasks": [
    {
      "id": 1,
      "description": "Use database tool to read src/index.js file completely and analyze Express.js patterns: app.get(), app.post(), app.put(), app.delete(), router.get(), router.post(), router.put(), router.delete(), and middleware setup. Look for route definitions, endpoint paths, and server configuration."
    }
  ]
}
```

## Example 4: Merging Implementation Analysis Tasks

Input Tasks:
- Task 6: Found axios imports in src/api/client.js. Use database tool to read this file and analyze axios.get(), axios.post() usage patterns.
- Task 9: Found axios imports in src/services/http.js. Use database tool to read this file and analyze axios.get(), axios.post() usage patterns.
- Task 13: Found axios imports in src/utils/request.js. Use database tool to read this file and analyze axios.get(), axios.post() usage patterns.

Analysis: Similar axios analysis tasks for different files - keep separate as they analyze different files.

Output:
```json
{
  "tasks": [
    {
      "id": 1,
      "description": "Found axios imports in src/api/client.js. Use database tool to read this file completely and analyze axios.get(), axios.post(), axios.put(), axios.delete() usage patterns. Look for actual HTTP calls with real endpoints and parameters."
    },
    {
      "id": 2,
      "description": "Found axios imports in src/services/http.js. Use database tool to read this file completely and analyze axios.get(), axios.post(), axios.put(), axios.delete() usage patterns. Look for actual HTTP calls with real endpoints and parameters."
    },
    {
      "id": 3,
      "description": "Found axios imports in src/utils/request.js. Use database tool to read this file completely and analyze axios.get(), axios.post(), axios.put(), axios.delete() usage patterns. Look for actual HTTP calls with real endpoints and parameters."
    }
  ]
}
```

## Example 5: Preserving Distinct Technologies

Input Tasks:
- Task 7: Use search_keyword tool with pattern 'socket\\.io' to find Socket.IO usage
- Task 10: Use search_keyword tool with pattern 'ws|websocket' to find WebSocket usage
- Task 14: Use database tool to analyze real-time communication setup

Analysis: Different technologies (Socket.IO vs WebSocket) should remain separate.

Output:
```json
{
  "tasks": [
    {
      "id": 1,
      "description": "Use search_keyword tool with pattern 'socket\\.io|require\\('socket\\.io'\\)|import.*socket\\.io' and regex=true to find Socket.IO imports and usage. Look for real-time communication library setup."
    },
    {
      "id": 2,
      "description": "Use search_keyword tool with pattern 'ws|websocket|require\\('ws'\\)|import.*ws' and regex=true to find WebSocket imports and usage. Look for WebSocket client/server implementations."
    },
    {
      "id": 3,
      "description": "Use database tool to analyze real-time communication setup and configuration in application files. Focus on Socket.IO and WebSocket implementations."
    }
  ]
}
```

## Example 6: Merging Built-in Pattern Tasks

Input Tasks:
- Task 11: Create built-in pattern task for JavaScript: Use search_keyword with pattern 'fetch\\(' to find native fetch API usage
- Task 15: Create built-in pattern task for JavaScript: Use search_keyword with pattern 'XMLHttpRequest' to find XMLHttpRequest usage
- Task 18: Create built-in pattern task for JavaScript: Use search_keyword with pattern 'new WebSocket\\(' to find WebSocket usage

Analysis: All are JavaScript built-in patterns and can be combined into one comprehensive search.

Output:
```json
{
  "tasks": [
    {
      "id": 1,
      "description": "Create built-in pattern task for JavaScript: Use search_keyword with pattern 'fetch\\(|XMLHttpRequest|new WebSocket\\(' and regex=true, after_lines=2 to find native JavaScript connection patterns across all files. Look for HTTP client calls and WebSocket connections."
    }
  ]
}
```"#
