template_string ConnectionMatchingSystemPrompt() #"
    CONNECTION MATCHING ANALYSIS

    Identify ALL connection points between incoming and outgoing connections by comprehensively matching identifiers, parameters, values, and connection patterns.

    ## OBJECTIVE

    Match outgoing connections with incoming connections by identifying:
    - API endpoints: URL paths, route names, and endpoint patterns
    - WebSocket events: Event names and socket identifiers
    - Message queues: Queue names, topic names, and channel identifiers
    - Function calls: Direct calls and wrapper function parameters
    - Variable values: Exact parameter values and configuration values
    - Environment variables: Variable names and resolved values

    ## MATCHING RULES

    - ONLY match incoming connections with outgoing connections
    - DO NOT match incoming connections with other incoming connections
    - DO NOT match outgoing connections with other outgoing connections
    - Each match must be between one incoming and one outgoing connection

    ## COMPLETE ANALYSIS REQUIREMENT

    RETURN ALL MATCHES - NO EXCEPTIONS
    - If you find 50 matches, return all 50 matches
    - If you find 100 matches, return all 100 matches
    - If you find 500 matches, return all 500 matches
    - Process EVERY incoming and outgoing connection provided
    - Return EVERY valid match found across ALL connection types
    - Do NOT limit, sample, or truncate results
    - This is production analysis requiring 100% coverage

    ## COMPREHENSIVE CONNECTION MATCHING STRATEGIES

    ### 1. EXACT IDENTIFIER MATCHES (HIGH CONFIDENCE)

    #### API Endpoints - Exact Path Matching
    - Match: `/api/users` with `/api/users`
    - Match: `/users/:id` with `/users/123` or `/users/{id}`
    - Match: `POST /api/login` with `POST /api/login`
    - Match: `GET /api/data` with `app.get('/api/data')`

    #### WebSocket Events - Exact Event Names
    - Match: `socket.emit('joinRoom')` with `socket.on('joinRoom')`
    - Match: `io.emit('userUpdate')` with `io.on('userUpdate')`
    - Match: `ws.send('message')` with `ws.on('message')`

    #### Message Queue Names - Exact Queue Identifiers
    - Match: `channel.publish('user_queue')` with `channel.consume('user_queue')`
    - Match: `sendToQueue('ASSIGNMENT_QUEUE')` with `consume('ASSIGNMENT_QUEUE')`
    - Match: `producer.send('notifications')` with `consumer.subscribe('notifications')`

    ### 2. PARAMETER VALUE MATCHES (HIGH CONFIDENCE)

    #### Function Parameter Matching
    - Match: `callAPI('/users', 'GET')` with `app.get('/users')` (first parameter matches endpoint)
    - Match: `makeRequest({url: '/api/login'})` with `app.post('/api/login')` (url property matches endpoint)
    - Match: `httpClient.request('/data', 'POST')` with `router.post('/data')` (parameter matches route)
    - Match: `sendMessage('user-queue', data)` with `consumeFrom('user-queue')` (queue name parameter matches)

    #### Object Property Matching
    - Match: `fetch({endpoint: '/api/users'})` with `app.get('/api/users')` (endpoint property matches)
    - Match: `publish({topic: 'notifications'})` with `subscribe({topic: 'notifications'})` (topic property matches)
    - Match: `emit({event: 'userJoined'})` with `on({event: 'userJoined'})` (event property matches)

    #### Variable Value Matching
    - Match: `const endpoint = '/api/users'; fetch(endpoint)` with `app.get('/api/users')` (variable value matches)
    - Match: `const queueName = 'tasks'; sendTo(queueName)` with `consume('tasks')` (variable value matches)

    ### 3. ENVIRONMENT VARIABLE MATCHES (MEDIUM-HIGH CONFIDENCE)

    #### Exact Environment Variable Names
    - Match: `process.env.USER_QUEUE` with `process.env.USER_QUEUE` (exact variable name)
    - Match: `process.env.API_ENDPOINT` with `process.env.API_ENDPOINT` (exact variable name)

    #### Similar Environment Variable Patterns
    - Match: `process.env.USER_QUEUE` with `process.env.USER_QUEUE_NAME` (similar naming pattern)
    - Match: `process.env.NOTIFICATION_QUEUE` with `process.env.NOTIFY_QUEUE` (abbreviated form)
    - Match: `process.env.API_BASE_URL` with `process.env.BASE_API_URL` (reordered words)

    #### Environment Variable with Resolved Values
    - Match: `process.env.API_BASE + '/users'` with `app.get('/users')` (when API_BASE resolves to base URL)
    - Match: `${process.env.SERVICE_URL}/api/data` with `app.get('/api/data')` (template literal resolution)

    ### 4. WRAPPER FUNCTION COMPREHENSIVE MATCHING

    #### HTTP Client Wrappers - All Parameter Positions
    - Match: `callAPI('/users', 'GET')` with `app.get('/users')` (first parameter is endpoint)
    - Match: `makeRequest('POST', '/api/login')` with `app.post('/api/login')` (second parameter is endpoint)
    - Match: `httpRequest({method: 'GET', url: '/data'})` with `router.get('/data')` (object parameter)
    - Match: `apiCall('/users', {method: 'POST'})` with `app.post('/users')` (mixed parameters)

    #### Queue Wrapper Functions - All Parameter Variations
    - Match: `sendToQueue('USER_QUEUE', data)` with `channel.consume('USER_QUEUE')` (first parameter)
    - Match: `publishMessage(data, 'notifications')` with `consumer.on('notifications')` (second parameter)
    - Match: `queueManager.send({queue: 'tasks', data: payload})` with `worker.process('tasks')` (object property)
    - Match: `messageQueue.publish('orders', msg)` with `orderProcessor.consume('orders')` (queue name match)

    #### Socket Wrapper Functions - Event Name Matching
    - Match: `emitEvent('userJoined', data)` with `socket.on('userJoined')` (first parameter)
    - Match: `broadcastToRoom(roomId, 'gameUpdate', data)` with `socket.on('gameUpdate')` (second parameter)
    - Match: `socketService.emit({event: 'notification'})` with `io.on('notification')` (object property)

    ### 5. ROUTER PREFIX AND PATH COMPOSITION MATCHING

    #### Router Prefix Resolution
    - Match: `app.use('/admin', router)` + `router.get('/create-user')` with `fetch('/admin/create-user')`
    - Match: `app.use('/api', routes)` + `routes.post('/delete-user')` with `axios.post('/api/delete-user')`
    - Match: `router.use('/v1', subRouter)` + `subRouter.get('/users')` with `request('/v1/users')`

    #### Path Concatenation Matching
    - Match: `baseURL + '/users'` with `app.get('/users')` (when baseURL is known)
    - Match: `API_PREFIX + endpoint` with route definitions (when variables are resolved)

    ### 6. ADVANCED PATTERN MATCHING

    #### Partial Path Matching
    - Match: `/api/v1/users` with `/v1/users` (when api is prefix)
    - Match: `/admin/users/create` with `/users/create` (when admin is permission prefix)

    #### Protocol-Agnostic Matching
    - Match: `http://api.service.com/users` with `https://api.service.com/users` (same endpoint, different protocol)
    - Match: `ws://localhost:3000/socket` with `wss://localhost:3000/socket` (same socket, different security)

    #### Port and Host Normalization
    - Match: `localhost:3000/api` with `127.0.0.1:3000/api` (localhost equivalence)
    - Match: `api.service.com:80/data` with `api.service.com/data` (default port omission)

    ### 7. WHEN NOT TO MATCH (INVALID MATCHES)

    #### Different Endpoints (DO NOT MATCH)
    - `/user/get-data` with `/get-user-data` - Different endpoint paths
    - `/api/login` with `/api/logout` - Opposite operations
    - `/users/create` with `/users/delete` - Different operations
    - `socket.emit('join')` with `socket.on('leave')` - Opposite actions

    #### Different Parameters (DO NOT MATCH)
    - `callAPI('/users')` with `app.get('/orders')` - Different endpoint parameters
    - `sendToQueue('user-queue')` with `consume('order-queue')` - Different queue names
    - `emit('userJoined')` with `on('userLeft')` - Different event names

    ## ANALYSIS APPROACH

    ### Step-by-Step Matching Process
    1. Extract all identifiers: From descriptions, code snippets, and technology names
    2. Normalize identifiers: Remove prefixes, suffixes, and formatting differences
    3. Match exact values: Look for identical strings, parameters, and configuration values
    4. Match resolved variables: Consider environment variables and their potential values
    5. Match wrapper parameters: Extract parameters from function calls and match with direct usage
    6. Match composed paths: Consider router prefixes and path concatenation
    7. Validate matches: Ensure technical compatibility and logical connection flow

    ### Identifier Extraction Rules
    - Extract endpoint paths from URLs, route definitions, and API calls
    - Extract event names from socket operations and message handlers
    - Extract queue names from messaging operations and consumers
    - Extract parameter values from function calls and object properties
    - Extract variable names and their assigned values
    - Extract environment variable names and resolved values

    ## OUTPUT FORMAT

    Before you answer, please explain your reasoning step-by-step.

    For example:
    "I analyzed all connections systematically by extracting identifiers from descriptions, code snippets, and parameters. I found exact matches for API endpoints, queue names, and socket events. I also identified wrapper function parameter matches and environment variable patterns. I processed every connection and validated each match for technical compatibility."

    Therefore the output is:
    {
      "matches": [
        {
          "outgoing_id": "string",
          "incoming_id": "string",
          "match_confidence": "high|medium|low",
          "match_reason": "info about the match"
        }
      ]
    }

    ## REQUIREMENTS

    - Explain your step-by-step reasoning before providing the JSON response
    - Process ALL connections and return ALL valid matches
    - Extract and match ALL identifiers, parameters, and values
    - Match wrapper function parameters with direct usage
    - Consider environment variables and their resolved values
    - Match router prefixes and path compositions
    - Validate technical compatibility for each match
    - Provide specific technical justification for each match

    MANDATORY: ANALYZE ALL CONNECTIONS COMPREHENSIVELY AND RETURN ALL CONNECTION POINT MATCHES
"#

template_string ConnectionMatchingUserPrompt(incoming_connections: string, outgoing_connections: string) #"
    {{ _.role("user") }}
    ### INCOMING CONNECTIONS
    {{ incoming_connections }}

    ### OUTGOING CONNECTIONS  
    {{ outgoing_connections }}

    Find all connection matches and return as JSON.
"#

function AwsConnectionMatching(incoming_connections: string, outgoing_connections: string) -> ConnectionMatchingResponse {
  client AwsClaudeSonnet4
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ ConnectionMatchingSystemPrompt() }}
    {{ ConnectionMatchingUserPrompt(incoming_connections, outgoing_connections) }}
  "#
}

function AnthropicConnectionMatching(incoming_connections: string, outgoing_connections: string) -> ConnectionMatchingResponse {
  client AnthropicClaude
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ ConnectionMatchingSystemPrompt() }}
    {{ ConnectionMatchingUserPrompt(incoming_connections, outgoing_connections) }}
  "#
}

function ChatGPTConnectionMatching(incoming_connections: string, outgoing_connections: string) -> ConnectionMatchingResponse {
  client OpenAIChatGPT
  prompt #"
    {{ _.role("system") }}
    {{ ConnectionMatchingSystemPrompt() }}
    {{ ConnectionMatchingUserPrompt(incoming_connections, outgoing_connections) }}
  "#
}

