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

## CRITICAL REQUIREMENT: COMPLETE ANALYSIS

**YOU MUST ANALYZE EVERY SINGLE CONNECTION AND RETURN ALL POSSIBLE MATCHES**

- Analyze ALL incoming connections provided in the input (REST APIs, WebSockets, Message Queues, Database connections, etc.)
- Analyze ALL outgoing connections provided in the input (HTTP clients, Socket clients, Queue producers, Database clients, etc.)
- Return EVERY SINGLE MATCH you find across ALL connection types, not just examples or samples
- Do not limit your analysis to a few connections - process the complete dataset
- Match REST API endpoints, WebSocket events, RabbitMQ queues, Socket.IO events, database operations, and any other connection types
- If there are 50 possible matches across different technologies, return all 50 matches
- If there are 100 possible matches across REST/WebSocket/Queue/Database, return all 100 matches
- NEVER truncate or sample the results - provide the complete matching analysis for ALL connection types

This is not a demonstration or example - this is production analysis that requires complete coverage of all connection data across all technologies.

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

## WRAPPER FUNCTION MATCHING EXAMPLES

Based on actual Phase 3 and Phase 4 patterns, here are realistic wrapper function matching scenarios:

### Example 1: HTTP Client Wrapper with Dynamic Endpoints
**Outgoing Connection:**
```javascript
// File: utils/callAPI.js
async function callAPI(endpoint, companyId, method, data) {
    const url = `${process.env.DATA_LAYER_URL}${endpoint}`;
    return axios({
        method: method,
        url: url,
        data: data,
        headers: { 'company-id': companyId }
    });
}
// Usage: callAPI('/admin/addUsers', companyId, 'POST', formData)
```

**Incoming Connection:**
```javascript
// File: routers/defaultRouter.js
app.post('/admin/addUsers', (req, res) => {
    const { formId, candidates } = req.body;
    // Handle candidate addition
});
```

**Match Analysis:**
- Endpoint: `/admin/addCandidate` (exact match)
- Method: `POST` (exact match)
- Wrapper Function: `callDataLayer` abstracts the HTTP call
- Environment Variable: `DATA_LAYER_URL` resolves to base URL
- Technology: HTTP Client/Express Router
- Confidence: HIGH (0.95)

### Example 2: Message Queue Wrapper with Dynamic Queue Names
**Outgoing Connection:**
```javascript
// File: utils/messageQueue.js
async function sendToQueue(queueName, messageData) {
    await channel.sendToQueue(
        process.env[queueName],
        Buffer.from(JSON.stringify(messageData))
    );
}
// Usage: sendToQueue('QUEUE_NAME_ASSIGNMENT_GENERATOR', candidateData)
```

**Incoming Connection:**
```javascript
// File: consumers/assignmentGenerator.js
channel.consume(process.env.QUEUE_NAME_ASSIGNMENT_GENERATOR, (msg) => {
    const candidateData = JSON.parse(msg.content.toString());
    // Process assignment generation
});
```

**Match Analysis:**
- Queue Name: `QUEUE_NAME_ASSIGNMENT_GENERATOR` environment variable (exact match)
- Message Format: JSON serialized data (structure match)
- Wrapper Function: `sendToQueue` abstracts queue operations
- Technology: RabbitMQ
- Confidence: HIGH (0.92)

### Example 3: Socket.IO Event Wrapper with Dynamic Events
**Outgoing Connection:**
```javascript
// File: models/roomHandler.js
emitToRoom(eventName, roomId, data) {
    this.socket.emit(eventName, {
        roomId: roomId,
        ...data
    });
}
// Usage: emitToRoom('joinRoom', this.roomId, { peerId: botId })
```

**Incoming Connection:**
```javascript
// File: socketHandlers/roomHandler.js
socket.on('joinRoom', (data) => {
    const { roomId, peerId } = data;
    // Handle room joining
});
```

**Match Analysis:**
- Event Name: `joinRoom` (exact match)
- Data Structure: `roomId`, `peerId` parameters (structure match)
- Wrapper Function: `emitToRoom` abstracts socket emission
- Technology: Socket.IO
- Confidence: HIGH (0.90)

### Example 4: Database Client Wrapper with Dynamic Queries
**Outgoing Connection:**
```javascript
// File: services/apiService.js
async function executeQuery(queryName, params) {
    const query = queries[queryName];
    return await db.execute(query, params);
}
// Usage: executeQuery('GET_USER_BY_ID', [userId])
```

**Incoming Connection:**
```sql
-- File: queries/userQueries.sql
-- GET_USER_BY_ID
SELECT id, name, email FROM users WHERE id = ?;
```

**Match Analysis:**
- Query Name: `GET_USER_BY_ID` (exact match)
- Parameters: `userId` parameter (structure match)
- Wrapper Function: `executeQuery` abstracts database operations
- Technology: Database/SQL
- Confidence: MEDIUM (0.75)

### Example 5: API Client Class with Method Wrappers
**Outgoing Connection:**
```javascript
// File: clients/serviceClient.js
class ServiceClient {
    async makeRequest(endpoint, method, data) {
        return await this.httpClient.request({
            url: `${this.baseUrl}${endpoint}`,
            method: method,
            data: data
        });
    }
}
// Usage: serviceClient.makeRequest('/users', 'GET')
```

**Incoming Connection:**
```javascript
// File: routes/userRoutes.js
app.get('/users', (req, res) => {
    // Handle user listing
});
```

**Match Analysis:**
- Endpoint: `/users` (exact match)
- Method: `GET` (exact match)
- Wrapper Class: `ServiceClient` abstracts HTTP operations
- Technology: HTTP Client/Express Router
- Confidence: HIGH (0.88)

### Example 6: Event Publisher Wrapper with Topic Patterns
**Outgoing Connection:**
```javascript
// File: services/eventService.js
publishEvent(eventType, entityId, eventData) {
    const topic = `${eventType}.${entityId}`;
    return this.publisher.publish(topic, eventData);
}
// Usage: publishEvent('user', userId, userData)
```

**Incoming Connection:**
```javascript
// File: subscribers/userSubscriber.js
subscriber.subscribe('user.*', (topic, data) => {
    const [eventType, entityId] = topic.split('.');
    // Handle user events
});
```

**Match Analysis:**
- Topic Pattern: `user.*` matches `user.${userId}` (pattern match)
- Event Type: `user` (exact match)
- Wrapper Function: `publishEvent` abstracts event publishing
- Technology: Event System
- Confidence: MEDIUM (0.80)

### Example 7: WebSocket Message Wrapper with Command Patterns
**Outgoing Connection:**
```javascript
// File: clients/wsClient.js
sendCommand(command, payload) {
    const message = {
        type: command,
        data: payload,
        timestamp: Date.now()
    };
    this.websocket.send(JSON.stringify(message));
}
// Usage: sendCommand('GET_USER_DATA', { userId: 123 })
```

**Incoming Connection:**
```javascript
// File: handlers/wsHandler.js
websocket.on('message', (data) => {
    const message = JSON.parse(data);
    if (message.type === 'GET_USER_DATA') {
        const { userId } = message.data;
        // Handle user data request
    }
});
```

**Match Analysis:**
- Command Type: `GET_USER_DATA` (exact match)
- Message Structure: `type`, `data`, `timestamp` (structure match)
- Wrapper Function: `sendCommand` abstracts WebSocket messaging
- Technology: WebSocket
- Confidence: HIGH (0.87)

### 6. CONFIDENCE LEVELS

- **HIGH (0.9)**: Exact endpoint + method + technology match with clear code evidence
- **MEDIUM (0.7)**: Close endpoint match with method compatibility and reasonable inference
- **LOW (0.5)**: Possible match based on technology and general patterns but with uncertainty

### 7. MATCHING EXCLUSIONS

**DO NOT MATCH**:
- Different HTTP methods unless clearly compatible (GET != POST)
- Similar but different endpoints (`/login` != `/logout`)
- Different protocols (HTTP != WebSocket unless bridged)

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
}
```

## RESPONSE REQUIREMENTS

- Return ONLY valid JSON with no additional text or explanations
- Base all matches on actual code analysis, not just descriptions
- Provide detailed match_reason with specific code evidence
- Include endpoint_analysis for REST API matches
- Be conservative: prefer no match over incorrect match
- Focus on actual data flow and communication patterns

## MANDATORY COMPLETENESS REQUIREMENT

**ANALYZE AND RETURN ALL MATCHES ACROSS ALL CONNECTION TYPES - NO EXCEPTIONS**

- Process EVERY incoming connection in the provided list (REST endpoints, WebSocket handlers, Queue consumers, etc.)
- Process EVERY outgoing connection in the provided list (HTTP clients, Socket emitters, Queue producers, etc.)
- Return ALL valid matches found during analysis across ALL technologies
- Match REST APIs with HTTP clients, WebSocket events with Socket emitters, Queue publishers with Queue consumers, etc.
- Do NOT limit results to examples, samples, or subsets of any connection type
- If you find 50+ matches across REST/WebSocket/Queue/more conenction related nodes return all 50+ matches
- The total_matches count must reflect ALL matches found across ALL connection technologies
- This is production analysis requiring 100% coverage of matching connections across all communication patterns

**FAILURE TO RETURN ALL MATCHES ACROSS ALL CONNECTION TYPES IS UNACCEPTABLE**
"""
