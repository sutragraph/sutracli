"""
Connection Matching Prompt

This prompt runs after cross-indexing analysis to match incoming and outgoing connections
and provide JSON response with matched connection IDs for database storage.
"""

CONNECTION_MATCHING_PROMPT = """CONNECTION MATCHING ANALYSIS

Analyze incoming and outgoing connections to find matches between them. Return ONLY a JSON response with matched connection pairs.

## OBJECTIVE

Identify which outgoing connections correspond to incoming connections and return structured JSON with matched pairs.

## IMPORTANT MATCHING RULES

- ONLY match incoming connections with outgoing connections
- DO NOT match incoming connections with other incoming connections
- DO NOT match outgoing connections with other outgoing connections
- Each match must be between one incoming and one outgoing connection

## MATCHING CRITERIA

Match connections based on these enhanced criteria:

### STRICT ENDPOINT MATCHING
- **Exact path matches only**: `/api/users` matches `/api/users` exactly
- **Router prefix matching**: `/admin/assignment-submission` matches `app.post("/assignment-submission")` when router uses `app.use("/admin")`
- **Path normalization**: Remove leading/trailing slashes, normalize separators
- **Variable parameter matching**: `/users/:id` matches `/users/123` or `/users/{id}` - but ONLY if the base path is identical
- **Query parameter ignoring**: `/api/data?param=value` matches `/api/data`
- **NO partial matches**: `/assignment-submission` does NOT match `/assignment-submission-authorize`
- **NO substring matches**: `/assignmentSubmissions` does NOT match `/assignment-submission`
- **NO similar name matches**: Different endpoint names should NOT be matched even if they seem related

### STRICT METHOD COMPATIBILITY
- HTTP methods must match exactly: GET with GET, POST with POST, DELETE with DELETE
- Consider router method definitions: `router.delete()` matches HTTP DELETE calls
- Handle method extraction from function names: `deleteUser()` suggests DELETE method
- NO cross-method matching: POST should NOT match GET even if endpoints are similar

### TECHNOLOGY COMPATIBILITY
- Same technology stack: Express.js endpoints match axios/fetch calls
- Cross-language compatibility: Node.js API can match Python requests calls
- Protocol matching: HTTP/HTTPS, WebSocket (ws/wss), message queues

### REGEX-BASED ENDPOINT EXTRACTION
- Extract endpoints from descriptions using regex patterns:
  - `/api/[a-zA-Z0-9/_-]+` for API paths
  - `[a-zA-Z0-9]+\.(get|post|put|delete)\("([^"]+)"` for router definitions
  - `fetch\("([^"]+)"` for fetch calls
  - `axios\.(get|post|put|delete)\("([^"]+)"` for axios calls

### STRICT LOGICAL RELATIONSHIP ANALYSIS
- Function name correlation: Only match if endpoint paths are identical or follow router prefix rules
- Service boundary analysis: Internal service calls vs external API calls
- Data flow direction: Request/response patterns, publisher/subscriber relationships
- NO functional similarity matching: Similar functionality does NOT mean endpoints match

## OUTPUT FORMAT

Return ONLY a valid JSON response with this exact structure:

```json
{
  "matches": [
    {
      "outgoing_id": "string",
      "incoming_id": "string",
      "match_confidence": "high|medium|low",
      "match_reason": "Brief explanation of why these connections match",
      "connection_type": "string"
    }
  ],
  "total_matches": 0
}
```

## RESPONSE REQUIREMENTS

Return ONLY valid JSON with no additional text. Match connections VERY STRICTLY - only exact endpoint matches or router prefix matches. Do NOT match similar-sounding endpoints or functionally related endpoints.
"""

