template_string Examples_TaskFilter() #"
# Task Filtering Examples

## Example 1: Merging Similar Search Pattern Tasks

Input Tasks:
  - Task 2: Use search_keyword tool with pattern 'import.*axios|from.*axios' and regex=true to find axios import statements. Look for HTTP client library imports enabling requests to other services.
  - Task 5: Use search_keyword tool with pattern 'import.*axios|axios' and regex=true to find axios import statements. Look for HTTP client library imports enabling requests to other services.

Analysis: Task 5 is missing 'from.*axios' pattern but otherwise identical.

Output:
```json
{
  "tasks": [
    {
      "id": 1,
      "description": "Use search_keyword tool with pattern 'import.*axios|from.*axios|axios' and regex=true to find axios import statements. Look for HTTP client library imports enabling requests to other services."
    }
  ]
}
```

## Example 2: search_keyword Tasks CAN Be Merged (Related Patterns)

Input Tasks:
  - Task 7: Use search_keyword tool with pattern '(app)\.(get|post|put|delete)' and regex=true to find Express.js app route definitions
  - Task 10: Use search_keyword tool with pattern '(router)\.(get|post|put|delete)' and regex=true to find Express.js router route definitions

Analysis: Both search_keyword tasks are finding Express.js route patterns and can be merged into one comprehensive pattern.

Output:
```json
{
  "tasks": [
    {
      "id": 1,
      "description": "Use search_keyword tool with pattern '(app|router)\.(get|post|put|delete)' and regex=true to find Express.js route definitions. Look for both app and router route handlers with endpoint paths."
    }
  ]
}
```

## Example 3: Database Tasks Should NOT Be Merged (Different Files)

Input Tasks:
  - Task 6: Found axios imports in src/api/client.js. Use database tool to read this file to find patterns like app.get(), app.post(), app.put(), app.delete().
  - Task 9: Found axios imports in src/services/http.js. Use database tool to read this file to find patterns like app.get(), app.post(), app.put(), app.delete().
  - Task 13: Found axios imports in src/utils/request.js. Use database tool to read this file and analyze makeApiCall\( wrapper function usage patterns.

Analysis: Database tasks analyzing different files must remain separate - each file requires individual analysis.

Output:
```json
{
  "tasks": [
    {
      "id": 1,
      "description": "Found axios imports in src/api/client.js. Use database tool to read this file completely to find patterns like app.get(), app.post(), app.put(), app.delete(). Look for actual HTTP calls with real endpoints and parameters."
    },
    {
      "id": 2,
      "description": "Found axios imports in src/services/http.js. Use database tool to read this file completely to find patterns like app.get(), app.post(), app.put(), app.delete(). Look for actual HTTP calls with real endpoints and parameters."
    },
    {
      "id": 3,
      "description": "Found axios imports in src/utils/request.js. Use database tool to read this file completely and analyze makeApiCall\( wrapper function usage patterns. Look for wrapper function calls with real endpoints and parameters."
    }
  ]
}
```

## Example 4: Database Tasks CAN Be Merged (Same File)
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

## Example 5: Preserving Distinct Technologies

Input Tasks:
  - Task 7: Use search_keyword tool with pattern 'import.*socket\.io|from.*socket\.io' and regex=true to find Socket.IO usage
  - Task 10: Use search_keyword tool with pattern 'import.*ws|websocket\(' and regex=true to find WebSocket usage

Analysis: Different technologies (Socket.IO vs WebSocket) should remain separate.

Output:
```json
{
  "tasks": [
    {
      "id": 1,
      "description": "Use search_keyword tool with pattern 'import.*socket\.io|from.*socket\.io|socket\.io' and regex=true to find Socket.IO imports and usage. Look for real-time communication library setup."
    },
    {
      "id": 2,
      "description": "Use search_keyword tool with pattern 'import.*ws|websocket\(|new.*WebSocket\(' and regex=true to find WebSocket imports and usage. Look for WebSocket client/server implementations."
    }
  ]
}
```

## Example 6: Merging Built-in Pattern Tasks

Input Tasks:
  - Task 11: Create built-in pattern task for JavaScript: Use search_keyword with pattern 'fetch\(' and regex=true to find native fetch API usage
  - Task 15: Create built-in pattern task for JavaScript: Use search_keyword with pattern 'new.*XMLHttpRequest\(' and regex=true to find XMLHttpRequest usage
  - Task 18: Create built-in pattern task for JavaScript: Use search_keyword with pattern 'new.*WebSocket\(' and regex=true to find WebSocket usage

Analysis: All are JavaScript built-in patterns and can be combined into one comprehensive search.

Output:
```json
{
  "tasks": [
    {
      "id": 1,
      "description": "Create built-in pattern task for JavaScript: Use search_keyword with pattern 'fetch\(|new.*XMLHttpRequest\(|new.*WebSocket\(' and regex=true, after_lines=2 to find native JavaScript connection patterns across all files. Look for HTTP client calls and WebSocket connections."
    }
  ]
}
```"#
