"""
Connection Splitting Prompt

This prompt receives collected connection data from sutra memory and splits it into 
incoming and outgoing connections with detailed JSON format for database storage.
"""

CONNECTION_SPLITTING_PROMPT = """CONNECTION SPLITTING ANALYSIS

You will receive connection data of cross-indexing analysis. Your task is to split this data into incoming and outgoing connections and return them in the required JSON format. Additionally, include a concise top-level "summary" describing what the project does based on the collected connections.

## OBJECTIVE

Process the collected connection data and categorize each connection as either incoming or outgoing, then return structured JSON with complete connection details. Also include a brief, evidence-based "summary" of the project's purpose and data flows.

## CONNECTION CLASSIFICATION

### INCOMING CONNECTIONS
Connections where OTHER services connect TO this service:
- API endpoints and route handlers (Express routes, Flask routes, etc.)
- WebSocket server endpoints that accept connections
- Message queue consumers that receive messages
- Server configurations that listen for connections

### OUTGOING CONNECTIONS  
Connections where THIS service connects TO other services:
- HTTP client calls (axios, fetch, requests, etc.)
- WebSocket client connections to other services
- Message queue producers that send messages
- Database connections and external service calls

## PROCESSING RULES

1. **Analyze each connection individually** - never group multiple connections
2. **Extract complete parameter details** including:
   - Exact endpoints, queue names, event names
   - HTTP methods, protocols, ports
   - Environment variables and their resolved values
   - File paths and line numbers
3. **Classify direction correctly** based on data flow
4. **Include comprehensive descriptions** with variable context
5. **Maintain original code snippets** exactly as stored

## OUTPUT FORMAT

Return ONLY a valid JSON response with this exact structure:

```json
{
  "incoming_connections": {
    "express": {
      "backend/server.js": [
        {
          "snippet_lines": "23-23",
          "description": "GET /api/health endpoint for health check"
        },
        {
          "snippet_lines": "27-27",
          "description": "GET /api/users endpoint for user retrieval"
        }
      ]
    },
    "socket.io": {
      "backend/server.js": [
        {
          "snippet_lines": "79-79",
          "description": "WebSocket connection handler for real-time communication"
        }
      ]
    },
    "rabbitmq": {
      "backend/services/messageService.js": [
        {
          "snippet_lines": "45-47",
          "description": "RabbitMQ consumer for order processing queue"
        }
      ]
    }
  },
  "outgoing_connections": {
    "axios": {
      "frontend/src/App.js": [
        {
          "snippet_lines": "37-37",
          "description": "GET /users API call to backend service"
        },
        {
          "snippet_lines": "54-54",
          "description": "POST /users API call to backend service"
        }
      ],
      "frontend/src/services/apiService.js": [
        {
          "snippet_lines": "40-40",
          "description": "GET /users API call to backend service"
        }
      ]
    },
    "socket.io-client": {
      "frontend/src/App.js": [
        {
          "snippet_lines": "18-18",
          "description": "WebSocket client connection to backend"
        }
      ]
    },
    "kafka": {
      "backend/services/eventService.js": [
        {
          "snippet_lines": "23-25",
          "description": "Kafka producer for user events topic using environment variable KAFKA_BROKERS"
        }
      ]
    }
  },
  "summary": "Brief 1-3 sentence summary of the project's purpose and main data flows based on observed connections"
}
```

Structure Requirements:
- Group connections by direction: "incoming_connections" and "outgoing_connections"
- Include a top-level string field "summary" (10-15 sentences) explaining what the project does and how components interact, derived strictly from the collected connections; neutral tone; no speculation beyond evidence
- Place "summary" after both "incoming_connections" and "outgoing_connections" in the JSON object
- Within each direction, group by technology name (flask, express, springboot, etc.)
- Within each technology, group by file path
- Each file path contains an array of connection snippets
- Each snippet has "snippet_lines" (range format like "15-20") and "description"
- Use actual technology names as they appear in the project
- Provide relative file paths from project root
- Use line ranges for cleaner database storage
- Include concise descriptions focusing on purpose and environment variables when relevant (e.g., "HTTP GET call for user data using environment variable API_BASE_URL")

## PROJECT SUMMARY GENERATION RULES

1. Write 10-15 sentences summarizing the project's purpose and architecture inferred from the connections.
2. Base the summary solely on evidence from incoming and outgoing connections (endpoints, clients, message queues, protocols, env vars).
3. Write about the project's purpose and architecture, and how the connections are used to achieve the purpose.
4. Keep it concise and strictly based on observed connections.

## CRITICAL LINE SELECTION RULES - STORE ACTUAL CALLS NOT WRAPPER DEFINITIONS:
- For API endpoints: Store ONLY the route decorator lines (@app.route, @api.route, etc.), NOT the function implementation
- For HTTP client calls: Store ACTUAL API calls like `axios.get('${process.env.API_URL}get-data')`, NOT wrapper function definitions
- For wrapper function calls: Store the CALL SITES with actual parameters like `apiCallFunction('/users', 'GET')`, NOT the wrapper definition
- For database connections: Store ONLY the connection establishment lines, NOT query execution code
- For external API calls: Store ACTUAL fetch/axios calls with real URLs, NOT generic wrapper implementations
- For cache connections: Store ONLY the cache client creation lines, NOT cache usage code
- **PRIORITY**: Focus on where connections are USED with real values, not where they are defined generically
- **ENVIRONMENT VARIABLES**: Include resolved environment variable values in descriptions

Examples of what TO store (ACTUAL CALLS WITH REAL VALUES):
- @app.route('/login', methods=['POST'])  # Store this line
- const response = await axios.get(`${process.env.API_BASE_URL}/get-data`)  # Store this line
- const response = await fetch(`${process.env.SERVICE_URL}/api/users/${userId}`)  # Store this line
- apiCallFunction('/admin/users', 'POST', userData)  # Store this call with actual parameters

Examples of what NOT to store (WRAPPER DEFINITIONS AND GENERIC CODE):
- function apiCallFunction(endpoint, method, data) { ... }  # Don't store wrapper definitions
- const sendData = (url, payload) => { ... }  # Don't store generic wrapper implementations
- const endpointUrl = `${process.env.SERVER}path`  # Don't store variable assignments
- def login_user(): ...                   # Don't store function body
- user = User.query.filter_by(...)        # Don't store query code
- cache.set('key', value)                 # Don't store cache usage code

## CRITICAL SNIPPET RULES - ONE ENDPOINT PER SNIPPET:
- **MANDATORY**: Each snippet must represent EXACTLY ONE connection - NEVER group multiple connections
- **ONE ENDPOINT RULE**: Each API endpoint must be stored as a separate snippet with its own specific line numbers
- **SEPARATE ENTRIES**: If you find 10 API endpoints, create 10 separate snippet entries - NOT 1 grouped entry
- **INDIVIDUAL DESCRIPTIONS**: Each snippet must describe ONE specific endpoint, method, and purpose
- **NO GROUPING**: Never use descriptions like "Multiple endpoints" or "API endpoints including X, Y, Z"
- **STORE CALL SITES**: Store where wrapper functions are called with actual values, not where they are defined
- **INCLUDE ENVIRONMENT VALUES**: Add resolved environment variable values to descriptions
- **ACTUAL ENDPOINTS**: Focus on real endpoints, methods, and data being sent/received

## GOOD EXAMPLE - Each snippet is ONE connection with environment variable values:
```json
{
  "incoming_connections": {
    "express": {
      "src/routers/userRouter.js": [
        {
          "snippet_lines": "15-18",
          "description": "POST /api/users endpoint for user creation"
        },
        {
          "snippet_lines": "25-28",
          "description": "GET /api/users/:id endpoint for user retrieval"
        },
        {
          "snippet_lines": "35-38",
          "description": "PUT /api/users/:id endpoint for user updates"
        }
      ]
    }
  },
  "outgoing_connections": {
    "axios": {
      "src/services/userService.js": [
        {
          "snippet_lines": "12-14",
          "description": "HTTP GET call for initial data retrieval using environment variable API_BASE_URL"
        },
        {
          "snippet_lines": "28-30",
          "description": "HTTP GET call for user data using environment variable SERVICE_URL"
        }
      ]
    }
  },
  "summary": "Express-based user service exposing CRUD endpoints; Axios client integrates with external services; env-based configuration for base URLs."
}
```

## BAD EXAMPLE - Grouping multiple endpoints (NEVER DO THIS):
```json
{
  "incoming_connections": {
    "express": {
      "src/routers/userRouter.js": [
        {
          "snippet_lines": "15-45",
          "description": "API endpoints for communication using route prefix including check-room-demo, store-embeddings, get-embeddings, health-check, and end-interview endpoints"
        }
      ],
      "src/routers/adminRouter.js": [
        {
          "snippet_lines": "71-133",
          "description": "Multiple user service endpoints for admin"
        }
      ]
    }
  }
}
```

## BAD EXAMPLE - Storing wrapper function definitions instead of calls (NEVER DO THIS):
```json
{
  "outgoing_connections": {
    "axios": {
      "src/utils/apiClient.js": [
        {
          "snippet_lines": "41-41",
          "description": "HTTP GET wrapper function for service communication"
        },
        {
          "snippet_lines": "43-43",
          "description": "HTTP POST wrapper function for service communication"
        }
      ]
    }
  }
}
```

## BAD EXAMPLE - Vague descriptions without environment variable values (NEVER DO THIS):
```json
{
  "incoming_connections": {
    "express": {
      "src/index.js": [
        {
          "snippet_lines": "71-78",
          "description": "Router mounts for 8 different service endpoints"
        }
      ]
    }
  }
}
```

REMEMBER: If you find 26 API endpoints, create 26 separate snippet entries, each with specific line numbers and descriptions for that ONE endpoint.

**CRITICAL ENDPOINT SEPARATION RULE**:
- NEVER group multiple endpoints in one snippet description
- NEVER use phrases like "including X, Y, Z endpoints" or "Multiple endpoints for..."
- ALWAYS create separate snippet entries for each individual endpoint
- Each endpoint gets its own snippet_lines and description
- Example: If you find 5 endpoints on lines 10, 15, 20, 25, 30 - create 5 separate snippets, NOT 1 snippet with "10-30" lines

**CORRECT APPROACH FOR MULTIPLE ENDPOINTS**:
Instead of:
```json
{
  "snippet_lines": "648-658",
  "description": "API endpoints including endpoint-a, endpoint-b, endpoint-c, endpoint-d, and endpoint-e"
}
```

Do this:
```json
{
  "snippet_lines": "650-650",
  "description": "GET /endpoint-a/:id endpoint for resource verification"
},
{
  "snippet_lines": "651-651",
  "description": "POST /endpoint-b endpoint for data storage"
},
{
  "snippet_lines": "652-652",
  "description": "GET /endpoint-c/:uid endpoint for data retrieval"
},
{
  "snippet_lines": "657-657",
  "description": "GET /endpoint-d endpoint for service health monitoring"
},
{
  "snippet_lines": "658-658",
  "description": "POST /endpoint-e endpoint for process termination"
}
```

## EXAMPLE FOR NO CONNECTIONS FOUND:
If no connections are discovered during analysis, you MUST still return JSON with empty objects:

```json
{
  "incoming_connections": {},
  "outgoing_connections": {},
  "summary": "No connections discovered in code; insufficient data to infer project purpose."
}
```

## CRITICAL REQUIREMENTS

1. **Process ALL connections** - never skip or sample connections
2. **Maintain exact code snippets** as stored in sutra memory
3. **Use the exact format** shown in examples above
4. **Include complete variable context** in descriptions
5. **Classify direction accurately** based on data flow
6. **Return valid JSON only** - no additional text or explanations
7. **DEDUPLICATION RULE** - Avoid overlapping code snippets in the same file:
   - If you have snippets with lines "13-19" and "12-20" in the same file, they overlap significantly
   - Choose the snippet with the most complete context
   - Exception: Non-overlapping snippets in the same file should all be included

## RESPONSE REQUIREMENTS

- Return ONLY valid JSON with no additional text
- Process every single connection from sutra memory data
- Include a concise top-level "summary" as described above
- Group by technology and file path as shown in format
- Use line ranges for snippet_lines (e.g., "15-20" or "23-23")
- Include environment variable information in descriptions
- **AVOID OVERLAPPING SNIPPETS**: If multiple code snippets overlap in the same file, include only the most comprehensive one

## DEDUPLICATION EXAMPLES

**GOOD - No overlapping snippets:**
```json
{
  "outgoing_connections": {
    "axios": {
      "src/api/client.js": [
        {
          "snippet_lines": "10-12",
          "description": "HTTP GET call to user service"
        },
        {
          "snippet_lines": "25-27",
          "description": "HTTP POST call to order service"
        }
      ]
    }
  }
}
```

**BAD - Overlapping snippets (lines 13-19 overlap with 12-20):**
```json
{
  "outgoing_connections": {
    "axios": {
      "src/api/client.js": [
        {
          "snippet_lines": "13-19",
          "description": "HTTP GET call to user service"
        },
        {
          "snippet_lines": "12-20",
          "description": "HTTP GET call to user service with config"
        }
      ]
    }
  }
}
```

**CORRECTED - Keep only the more comprehensive snippet:**
```json
{
  "outgoing_connections": {
    "axios": {
      "src/api/client.js": [
        {
          "snippet_lines": "12-20",
          "description": "HTTP GET call to user service with config"
        }
      ]
    }
  }
}
```

The system expects complete processing of all connection data with no omissions or grouping of multiple connections into single entries, but without redundant overlapping code snippets.
"""
