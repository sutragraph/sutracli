"""
Connection Splitting Prompt

This prompt receives collected connection data from sutra memory and splits it into 
incoming and outgoing connections with detailed JSON format for database storage.
"""

CONNECTION_SPLITTING_PROMPT = """CONNECTION SPLITTING ANALYSIS

You will receive connection data of cross-indexing analysis. Your task is to split this data into incoming and outgoing connections and return them in the required JSON format. Additionally, include a concise top-level "summary" describing what the project does based on the collected connections.

## ABSOLUTE CRITICAL RULE - ONE CONNECTION PER SNIPPET

MANDATORY: Each snippet entry must represent EXACTLY ONE connection. You are FORBIDDEN from grouping multiple connections together.

EXAMPLES OF FORBIDDEN GROUPING:
- "Message handlers for incoming events including eventA, eventB, eventC"
- "API endpoints including endpointX, endpointY, endpointZ"  
- "Multiple operations for data processing"
- "Connection handlers including X, Y, Z"

REQUIRED APPROACH:
- "Message handler for eventA"
- "Message handler for eventB"  
- "Message handler for eventC"
- "GET /endpointX for data retrieval"
- "POST /endpointY for data creation"

## OBJECTIVE

Process the collected connection data and categorize each connection as either incoming or outgoing, then return structured JSON with complete connection details. Each connection must be a separate entry with its own specific line numbers and description.

## CONNECTION CLASSIFICATION

### INCOMING CONNECTIONS
Connections where OTHER services connect TO this service:
Examples:
- API endpoints and route handlers (Express routes, Flask routes, etc.)
- WebSocket server endpoints that accept connections
- Message queue consumers that receive messages
- Server configurations that listen for connections

### OUTGOING CONNECTIONS  
Connections where THIS service connects TO other services
Examples:
- HTTP client calls (axios, fetch, requests, etc.)
- WebSocket client connections to other services
- Message queue producers that send messages

## PROCESSING RULES

1. Analyze each connection individually - never group multiple connections
2. Create separate entries - If you find code with multiple operations, create separate entries for each
3. Extract individual details - Each entry gets its own specific line numbers and operation details
4. Focus on data transmission - Only code that sends or receives data, exclude setup
5. Include complete parameter details:
   - Exact endpoints, event names, queue names, method names
   - Protocols, methods, parameters
   - Environment variables and their resolved values in descriptions
   - File paths and line numbers
6. Classify direction correctly based on data flow
7. No duplicates - each data transmission operation must be unique

## GENERIC ANALYSIS INSTRUCTIONS

### FOR CONDITIONAL/SWITCH STATEMENTS:
If you find code with multiple branches handling different operations:
```
switch/if (condition) {
  case/condition A: { /* handler code */ }
  case/condition B: { /* handler code */ }
  case/condition C: { /* handler code */ }
}
```

You MUST create separate entries:
- One for operation A handler
- One for operation B handler  
- One for operation C handler

### FOR MULTIPLE OPERATION DEFINITIONS:
If you find code defining multiple operations:
```
operation1(params);
operation2(params);
operation3(params);
```

You MUST create separate entries:
- One for operation1
- One for operation2
- One for operation3

### FOR ROUTER/HANDLER REGISTRATIONS:
If you find code registering multiple handlers:
```
register('/pathA', handlerA);
register('/pathB', handlerB);
register('/pathC', handlerC);
```

You MUST create separate entries for each registration.

## OUTPUT FORMAT

Return ONLY a valid JSON response with this exact structure:

```json
{
  "incoming_connections": {
    "technology_name": {
      "file/path.ext": [
        {
          "snippet_lines": "23-23",
          "description": "Specific operation A for incoming data"
        },
        {
          "snippet_lines": "27-27",
          "description": "Specific operation B for incoming data"
        }
      ]
    }
  },
  "outgoing_connections": {
    "technology_name": {
      "file/path.ext": [
        {
          "snippet_lines": "37-37",
          "description": "Specific operation X for outgoing data"
        },
        {
          "snippet_lines": "54-54",
          "description": "Specific operation Y for outgoing data"
        }
      ]
    }
  },
  "summary": "Brief summary of the project's purpose and main data flows based on observed connections"
}
```

## MANDATORY SNIPPET SEPARATION RULES

### RULE 1: ONE OPERATION PER SNIPPET
For any code handling multiple operations:
- Each operation gets its own snippet entry
- Use specific line numbers for each operation block
- Description must mention the specific operation

### RULE 2: ONE ENDPOINT/EVENT/METHOD PER SNIPPET  
For any code defining multiple endpoints/events/methods:
- Each definition gets its own snippet entry
- Use specific line numbers for each definition
- Description must include the specific endpoint/event/method details

### RULE 3: ONE DATA TRANSMISSION PER SNIPPET
For any code performing multiple data transmissions:
- Each transmission operation gets its own snippet entry
- Use specific line numbers for each transmission
- Description must specify what data is being transmitted

### RULE 4: PRECISE LINE NUMBERS
- Use exact line numbers for each individual connection
- For single-line connections: "23-23"
- For multi-line connections: "23-27" (only if they're truly one logical connection)
- Never use large ranges that span multiple different connections

## EXAMPLES OF CORRECT SEPARATION

### CORRECT - Multiple Event Handlers:
```json
{
  "incoming_connections": {
    "event_system": {
      "src/handlers.js": [
        {
          "snippet_lines": "15-25",
          "description": "Event handler for user_login event"
        },
        {
          "snippet_lines": "30-40", 
          "description": "Event handler for user_logout event"
        },
        {
          "snippet_lines": "45-55",
          "description": "Event handler for data_update event"
        }
      ]
    }
  }
}
```

### CORRECT - Multiple Operations:
```json
{
  "outgoing_connections": {
    "http_client": {
      "src/client.js": [
        {
          "snippet_lines": "15-15",
          "description": "GET request for user data retrieval"
        },
        {
          "snippet_lines": "23-23",
          "description": "POST request for user data creation"
        },
        {
          "snippet_lines": "31-31",
          "description": "PUT request for user data update"
        }
      ]
    }
  }
}
```

## EXAMPLES OF FORBIDDEN GROUPING

### FORBIDDEN - Grouping Multiple Operations:
```json
{
  "incoming_connections": {
    "event_system": {
      "src/handlers.js": [
        {
          "snippet_lines": "15-55",
          "description": "Event handlers for multiple events including user_login, user_logout, and data_update"
        }
      ]
    }
  }
}
```

### FORBIDDEN - Grouping Multiple Endpoints:
```json
{
  "outgoing_connections": {
    "http_client": {
      "src/client.js": [
        {
          "snippet_lines": "15-31",
          "description": "HTTP requests including GET, POST, and PUT operations for user management"
        }
      ]
    }
  }
}
```

## STEP-BY-STEP ANALYSIS PROCESS

1. Identify all connections: Scan through all code snippets and identify every individual connection
2. Separate each connection: For each connection found, create a separate JSON entry
3. Extract precise details: Get exact line numbers and specific details for each connection
4. Write specific descriptions: Each description must be about ONE specific connection

## CRITICAL REQUIREMENTS

1. Process all connections - never skip or sample connections
2. Separate all connections - never group multiple connections into one entry
3. Use exact line numbers - be precise about where each connection is located
4. Write specific descriptions - each description must be about one connection only
5. Return valid JSON only - no additional text or explanations
6. No phrases like: "including", "multiple", "various", "several", "operations for"

## RESPONSE REQUIREMENTS

- Return ONLY valid JSON with no additional text
- Process every single connection from sutra memory data
- Create separate entries for each individual connection
- Use precise line numbers for each connection
- Write specific descriptions for each connection
- Include environment variable information in descriptions
- Group by technology and file path as shown in format

Remember: If you find 26 different connections, you must create 26 separate JSON entries. No exceptions.
"""
