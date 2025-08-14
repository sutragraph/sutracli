"""
Connection Matching Prompt

This prompt runs after cross-indexing analysis to match incoming and outgoing connections
and provide JSON response with matched connection IDs for database storage.
"""

CONNECTION_MATCHING_PROMPT = """CONNECTION MATCHING ANALYSIS

Analyze incoming and outgoing connections to find matches between them by examining the actual code snippets and connection patterns. Return ONLY a JSON response with matched pairs.

## OBJECTIVE

Identify which outgoing connections correspond to incoming connections by analyzing:
1. **Code patterns**: Actual API calls, endpoints, routes, and connection code
2. **Endpoint matching**: URL paths, HTTP methods, and parameters
3. **Technology compatibility**: Matching client calls with server endpoints
4. **Data flow patterns**: Request/response, publisher/subscriber relationships

## IMPORTANT MATCHING RULES

- ONLY match incoming connections with outgoing connections
- DO NOT match incoming connections with other incoming connections  
- DO NOT match outgoing connections with other outgoing connections
- Each match must be between one incoming and one outgoing connection
- Base matching decisions on actual code analysis, not just descriptions

## DETAILED MATCHING CRITERIA

### 1. CODE PATTERN ANALYSIS
Analyze the actual code snippets to identify:
- **API Endpoints**: Extract actual URLs, paths, and endpoints from code
- **HTTP Methods**: GET, POST, PUT, DELETE, PATCH from both client calls and server routes
- **Parameters**: Query parameters, path parameters, request bodies
- **Headers**: Content-Type, Authorization, custom headers
- **Environment Variables**: Resolved base URLs, service endpoints

### 2. ENDPOINT MATCHING RULES
- **Exact Path Matching**: `/api/users` matches `/api/users` exactly
- **Router Prefix Resolution**: 
  - `app.use('/api', router)` + `router.get('/users')` = `/api/users`
  - `axios.get('/api/users')` matches the above
- **Path Parameter Matching**: 
  - `/users/:id` matches `/users/123` or `/users/{userId}`
  - `/api/posts/:postId/comments` matches `/api/posts/456/comments`
- **Query Parameter Normalization**: `/api/data?sort=name` matches `/api/data`
- **Protocol Normalization**: `http://` and `https://` are considered equivalent
- **Trailing Slash Normalization**: `/api/users/` matches `/api/users`

### 3. HTTP METHOD MATCHING
- **Direct Method Matching**: `app.get()` matches `axios.get()`
- **Method Inference**: 
  - `createUser()` function suggests POST method
  - `deleteUser()` function suggests DELETE method
  - `updateUser()` function suggests PUT/PATCH method
  - `getUser()` function suggests GET method
- **RESTful Convention Matching**: Standard REST patterns

### 4. TECHNOLOGY STACK COMPATIBILITY
- **Same Stack**: Express.js routes match axios/fetch calls
- **Cross-Language**: Node.js Express matches Python requests/FastAPI
- **Protocol Matching**: 
  - HTTP/HTTPS APIs
  - WebSocket connections (ws/wss)
  - Message queues (RabbitMQ, Kafka, Redis)
  - Database connections
  - GraphQL endpoints

### 5. CONNECTION TYPE PATTERNS

#### REST API Connections
- **Incoming**: `app.get('/api/users', handler)`, `@app.route('/users', methods=['GET'])`
- **Outgoing**: `axios.get('/api/users')`, `fetch('/api/users')`, `requests.get('/api/users')`

#### WebSocket Connections  
- **Incoming**: `io.on('connection')`, `websocket.on('message')`
- **Outgoing**: `socket.emit()`, `websocket.send()`, `io.connect()`

#### Message Queue Connections
- **Incoming**: `consumer.on('message')`, `channel.consume(queue)`
- **Outgoing**: `producer.send()`, `channel.publish()`, `queue.put()`

#### Database Connections
- **Incoming**: Database server listening on port
- **Outgoing**: Database client connections, ORM queries

### 6. CONFIDENCE LEVELS

- **HIGH (0.9)**: Exact endpoint + method + technology match with clear code evidence
- **MEDIUM (0.7)**: Close endpoint match with method compatibility and reasonable inference
- **LOW (0.5)**: Possible match based on technology and general patterns but with uncertainty

### 7. MATCHING EXCLUSIONS

**DO NOT MATCH**:
- Different HTTP methods unless clearly compatible (GET ≠ POST)
- Partial path matches (`/users` ≠ `/users/profile`)
- Similar but different endpoints (`/login` ≠ `/logout`)
- Different protocols (HTTP ≠ WebSocket unless bridged)
- Internal utility functions vs external API calls
- Mock/test code vs production endpoints

## ANALYSIS PROCESS

For each potential match:

1. **Extract Connection Details**:
   - Parse actual endpoints/URLs from code snippets
   - Identify HTTP methods or connection types
   - Note technology stack and protocols
   - Resolve environment variables where possible

2. **Compare Patterns**:
   - Match endpoint paths (with normalization)
   - Verify HTTP method compatibility  
   - Check technology stack compatibility
   - Analyze data flow direction

3. **Validate Match**:
   - Ensure logical request/response relationship
   - Verify no conflicts in timing or data flow
   - Check for supporting evidence in descriptions

4. **Assign Confidence**:
   - High: Clear, unambiguous match with strong evidence
   - Medium: Good match with minor uncertainties
   - Low: Possible match requiring human verification

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

- Return ONLY valid JSON with no additional text or explanations
- Base all matches on actual code analysis, not just descriptions
- Provide detailed match_reason with specific code evidence
- Include endpoint_analysis for REST API matches
- Be conservative: prefer no match over incorrect match
- Focus on actual data flow and communication patterns
"""
