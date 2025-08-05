"""
Attempt Completion Tool for Cross-Index Analysis

Tool definition for completing cross-index analysis with JSON format inside XML tags.
"""

ATTEMPT_COMPLETION_TOOL = """## attempt_completion

Complete the cross-index analysis and provide results in JSON format within XML tags for database storage.

Usage: attempt_completion(result="JSON formatted connection results")

CRITICAL: You MUST use this tool to complete the analysis. The system expects this specific tool format.
IMPORTANT: Even if you find no connections, you MUST still use this tool with empty arrays to properly complete the analysis.

Expected Format:
<attempt_completion>
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
  }
}
</attempt_completion>

Structure Requirements:
- Group connections by direction: "incoming_connections" and "outgoing_connections"
- Within each direction, group by technology name (flask, express, springboot, etc.)
- Within each technology, group by file path
- Each file path contains an array of connection snippets
- Each snippet has "snippet_lines" (range format like "15-20") and "description"
- Use actual technology names as they appear in the project
- Provide relative file paths from project root
- Use line ranges for cleaner database storage
- Include concise descriptions focusing on purpose and environment variables when relevant (e.g., "HTTP GET call for user data using environment variable API_BASE_URL")

CRITICAL LINE SELECTION RULES - STORE ACTUAL CALLS NOT WRAPPER DEFINITIONS:
- For API endpoints: Store ONLY the route decorator lines (@app.route, @api.route, etc.), NOT the function implementation
- For HTTP client calls: Store ACTUAL API calls like `axios.get('${process.env.API_URL}get-initial-data')`, NOT wrapper function definitions
- For wrapper function calls: Store the CALL SITES with actual parameters like `apiCallFunction('/users', 'GET')`, NOT the wrapper definition
- For database connections: Store ONLY the connection establishment lines, NOT query execution code
- For external API calls: Store ACTUAL fetch/axios calls with real URLs, NOT generic wrapper implementations
- For cache connections: Store ONLY the cache client creation lines, NOT cache usage code
- **PRIORITY**: Focus on where connections are USED with real values, not where they are defined generically
- **ENVIRONMENT VARIABLES**: Include resolved environment variable values in descriptions

Examples of what TO store (ACTUAL CALLS WITH REAL VALUES):
- @app.route('/login', methods=['POST'])  # Store this line
- const response = await axios.get(`${process.env.API_BASE_URL}/get-initial-data`)  # Store this line
- const response = await fetch(`${process.env.SERVICE_URL}/api/users/${userId}`)  # Store this line
- apiCallFunction('/admin/users', 'POST', userData)  # Store this call with actual parameters

Examples of what NOT to store (WRAPPER DEFINITIONS AND GENERIC CODE):
- function apiCallFunction(endpoint, method, data) { ... }  # Don't store wrapper definitions
- const sendData = (url, payload) => { ... }  # Don't store generic wrapper implementations
- const endpointUrl = `${process.env.SERVER}path`  # Don't store variable assignments
- def login_user(): ...                   # Don't store function body
- user = User.query.filter_by(...)        # Don't store query code
- cache.set('key', value)                 # Don't store cache usage code

CRITICAL SNIPPET RULES - ONE ENDPOINT PER SNIPPET:
- **MANDATORY**: Each snippet must represent EXACTLY ONE connection - NEVER group multiple connections
- **ONE ENDPOINT RULE**: Each API endpoint must be stored as a separate snippet with its own specific line numbers
- **SEPARATE ENTRIES**: If you find 10 API endpoints, create 10 separate snippet entries - NOT 1 grouped entry
- **INDIVIDUAL DESCRIPTIONS**: Each snippet must describe ONE specific endpoint, method, and purpose
- **NO GROUPING**: Never use descriptions like "Multiple endpoints" or "API endpoints including X, Y, Z"
- **STORE CALL SITES**: Store where wrapper functions are called with actual values, not where they are defined
- **INCLUDE ENVIRONMENT VALUES**: Add resolved environment variable values to descriptions
- **ACTUAL ENDPOINTS**: Focus on real endpoints, methods, and data being sent/received

GOOD EXAMPLE - Each snippet is ONE connection with environment variable values:
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
  }
}

BAD EXAMPLE - Grouping multiple endpoints (NEVER DO THIS):
{
  "incoming_connections": {
    "express": {
      "src/routers/userRouter.js": [
        {
          "snippet_lines": "15-45",
          "description":  API endpoints for inter-service communication using  route prefix including check-room-demo, store-embeddings, get-embeddings, health-check, and end-interview endpoints"
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

BAD EXAMPLE - Storing wrapper function definitions instead of calls (NEVER DO THIS):
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

BAD EXAMPLE - Vague descriptions without environment variable values (NEVER DO THIS):
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

REMEMBER: If you find 26 API endpoints, create 26 separate snippet entries, each with specific line numbers and descriptions for that ONE endpoint.

**CRITICAL ENDPOINT SEPARATION RULE**:
- NEVER group multiple endpoints in one snippet description
- NEVER use phrases like "including X, Y, Z endpoints" or "Multiple endpoints for..."
- ALWAYS create separate snippet entries for each individual endpoint
- Each endpoint gets its own snippet_lines and description
- Example: If you find 5 endpoints on lines 10, 15, 20, 25, 30 - create 5 separate snippets, NOT 1 snippet with "10-30" lines

**CORRECT APPROACH FOR MULTIPLE ENDPOINTS**:
Instead of:
```
{
  "snippet_lines": "648-658",
  "description": "API endpoints including endpoint-a, endpoint-b, endpoint-c, endpoint-d, and endpoint-e"
}
```

Do this:
```
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

EXAMPLE FOR NO CONNECTIONS FOUND:
If no connections are discovered during analysis, you MUST still use attempt_completion with empty arrays:

<attempt_completion>
{
  "incoming_connections": {},
  "outgoing_connections": {}
}
</attempt_completion>

This ensures proper completion of the analysis even when no connections exist."""
