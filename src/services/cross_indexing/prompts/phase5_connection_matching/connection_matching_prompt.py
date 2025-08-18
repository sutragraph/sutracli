"""
Connection Matching Prompt

This prompt runs after cross-indexing analysis to match incoming and outgoing connections
and provide JSON response with matched connection IDs for database storage.
"""

CONNECTION_MATCHING_PROMPT = """CONNECTION MATCHING ANALYSIS

Identify connection points between incoming and outgoing connections by matching endpoint names, event names, queue names, and other connection identifiers.

## OBJECTIVE

Match outgoing connections with incoming connections by identifying:
- **API endpoints**: URL paths and route names
- **WebSocket events**: Event names
- **Message queues**: Queue names
- **Socket events**: Event names
- **Wrapper Function calls**: passed parameters

## MATCHING RULES

- ONLY match incoming connections with outgoing connections
- DO NOT match incoming connections with other incoming connections
- DO NOT match outgoing connections with other outgoing connections
- Each match must be between one incoming and one outgoing connection

## COMPLETE ANALYSIS REQUIREMENT

**RETURN ALL MATCHES - NO EXCEPTIONS**
- If you find 50 matches, return all 50 matches
- If you find 100 matches, return all 100 matches
- If you find 500 matches, return all 500 matches
- Process EVERY incoming and outgoing connection provided
- Return EVERY valid match found across ALL connection types
- Do NOT limit, sample, or truncate results
- This is production analysis requiring 100% coverage

## CONNECTION POINT MATCHING

### 1. EXACT MATCHES (HIGH CONFIDENCE)

#### REST API Endpoints
- Match: `/api/users` with `/api/users`
- Match: `/users/:id` with `/users/123`
- Match: `POST /api/login` with `POST /api/login`

#### Router Prefix Matching
- Match: `app.use('/admin')` + `router.get('/create-user')` with `fetch('/admin/create-user')`
- Match: `app.use('/api')` + `router.post('/delete-user')` with `axios.post('/api/delete-user')`
- Match: `router.get('/users')` (with `/admin` prefix) with `fetch('/admin/users')`

#### WebSocket Events
- Match: `socket.emit('joinRoom')` with `socket.on('joinRoom')`
- Match: `io.emit('userUpdate')` with `io.on('userUpdate')`

#### Message Queue Names
- Match: `channel.publish('user_queue')` with `channel.consume('user_queue')`
- Match: `sendToQueue('ASSIGNMENT_QUEUE')` with `consume('ASSIGNMENT_QUEUE')`

### 2. ENVIRONMENT VARIABLE MATCHES (MEDIUM CONFIDENCE)

#### Queue Names with Environment Variables
- Match: `process.env.USER_QUEUE` with `process.env.USER_QUEUE_NAME` (if no other exact matches found)
- Match: `process.env.NOTIFICATION_QUEUE` with `process.env.NOTIFY_QUEUE` (similar naming pattern)

#### API Endpoints with Environment Variables
- Match: `${process.env.API_BASE}/users` with `process.env.USER_SERVICE_URL + '/users'`
- Match: `process.env.SERVICE_URL + '/api/data'` with `app.get('/api/data')`

### 3. WRAPPER FUNCTION MATCHES

#### HTTP Client Wrappers
- Match: `callAPI('/users', 'GET')` with `app.get('/users')` (wrapper function with endpoint parameter)
- Match: `makeRequest({url: '/api/login', method: 'POST'})` with `app.post('/api/login')`
- Match: `httpClient.get('/data')` with `router.get('/data')`

#### Queue Wrapper Functions
- Match: `sendToQueue('USER_QUEUE', data)` with `channel.consume(process.env.USER_QUEUE)`
- Match: `publishMessage('notifications', msg)` with `consumer.on('notifications')`
- Match: `queueManager.send('tasks', payload)` with `worker.process('tasks')`

#### Socket Wrapper Functions
- Match: `emitEvent('userJoined', data)` with `socket.on('userJoined')`
- Match: `broadcastToRoom('gameUpdate', roomId, data)` with `socket.on('gameUpdate')`
- Match: `socketService.emit('notification')` with `io.on('notification')`

### 4. WHEN NOT TO MATCH (INVALID MATCHES)

#### Different Endpoints (DO NOT MATCH)
- `/user/get-data` with `fetch('/get-user-data')` - Different endpoint paths
- `/api/login` with `/api-login` - Different functionality
- `/users/create` with `/users-create` - Opposite operations
- `socket.emit('join')` with `socket.on('joinRoom')` - Opposite actions


## OUTPUT FORMAT

Return ONLY a valid JSON response:

```json
{
  "matches": [
    {
      "outgoing_id": "string",
      "incoming_id": "string",
      "match_confidence": "high|medium|low",
      "match_reason": "Brief explanation of connection point match",
      "connection_type": "string"
    }
  ]
}
```

## REQUIREMENTS

- Return ONLY valid JSON with no additional text
- Process ALL connections and return ALL valid matches
- Match connection points by name/identifier
- Be conservative: prefer no match over incorrect match

**MANDATORY: ANALYZE ALL CONNECTIONS AND RETURN ALL CONNECTION POINT MATCHES**

**FAILURE TO RETURN ALL MATCHES IS UNACCEPTABLE**
"""
