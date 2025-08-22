"""
Code Manager Extraction Examples

Comprehensive examples of how to identify and extract connection code using proper output format.
"""

CODE_MANAGER_EXAMPLES = """====

CODE MANAGER EXTRACTION EXAMPLES

Comprehensive examples of how to extract connection code from tool results based on connection identifier patterns.

1. EXTRACTION STRATEGY - CONNECTION IDENTIFIER ANALYSIS

FOCUS RULE: Focus on CONNECTION IDENTIFIERS (endpoint names, queue names, socket event names), not data content.

CASE 1: DIRECT CALLS WITH LITERAL CONNECTION IDENTIFIERS
When connection identifiers are literal strings, extract the call directly:
- `axios.post('/admin/users', userData)` - EXTRACT: endpoint '/admin/users' is literal
- `socket.emit('user_status_update', data)` - EXTRACT: event 'user_status_update' is literal
- `queue.consume('order-processing', handler)` - EXTRACT: queue 'order-processing' is literal
- `makeApiCall('/api/orders', 'GET', params)` - EXTRACT: endpoint '/api/orders' is literal

CASE 2: CALLS WITH VARIABLE CONNECTION IDENTIFIERS
When connection identifiers are variables, extract ALL wrapper function calls with actual identifiers:
- `axios.post(endpoint, data)` - DON'T EXTRACT: endpoint is variable, find wrapper calls instead
- `socket.emit(eventName, data)` - DON'T EXTRACT: eventName is variable, find wrapper calls instead
- `makeApiCall(endpoint, method, data)` - DON'T EXTRACT: endpoint is variable, find wrapper calls instead

Then extract ALL calls with actual identifiers:
- `makeApiCall('/admin/users', 'POST', userData)` - EXTRACT: shows actual endpoint '/admin/users'
- `makeApiCall('/api/orders', 'GET', params)` - EXTRACT: shows actual endpoint '/api/orders'
- `publishMessage('user-notifications', data)` - EXTRACT: shows actual queue 'user-notifications'

CASE 3: ENVIRONMENT VARIABLES OR STATIC VALUES
When using environment variables or hardcoded values, extract the line directly:
- `const response = await fetch(`${process.env.API_BASE_URL}/data`)` - EXTRACT: environment variable usage
- `const apiUrl = 'http://localhost:3000/api'` - EXTRACT: static configuration
- `const queueName = process.env.QUEUE_NAME || 'default-queue'` - EXTRACT: environment variable with fallback

2. ENVIRONMENT VARIABLE INTEGRATION

Example 1: Direct call with environment variable
- Code: `const response = await axios.get(`${process.env.API_BASE_URL}/update/data`)`
- Environment: API_BASE_URL=http://localhost:3001
- Extraction Decision: EXTRACT - shows environment variable usage for connection configuration
- Description: "HTTP GET call using environment variable API_BASE_URL for endpoint configuration"

Example 2: Environment variable with fallback
- Code: `const queueName = process.env.QUEUE_NAME || 'default-queue'`
- Environment: QUEUE_NAME=user-processing
- Extraction Decision: EXTRACT - environment variable with fallback value
- Description: "Queue name configuration using environment variable QUEUE_NAME with fallback"

3. BAD EXAMPLES - DO NOT EXTRACT THESE

Bad Example 1: Base HTTP library calls inside wrapper functions
- Code: `await axios.get(url));`
- Code: `await axios.post(url, data));`
- Extraction Decision: DO NOT EXTRACT - internal implementation details, not the actual API calls with endpoints
- Why bad: These are internal implementation details, not the actual API calls with endpoints

Bad Example 2: Wrapper function definition
- Code: `function apiCallFunction(endpoint, method, data) { ... }`
- Extraction Decision: DO NOT EXTRACT - generic definition, extract the actual calls instead
- Why bad: Generic definition, no actual endpoints being called

Bad Example 3: Import/require statements
- Code: `const axios = require('axios');`
- Extraction Decision: DO NOT EXTRACT - library imports are not connection points
- Why bad: Library imports are not connection points

4. DESCRIPTION TEMPLATES

Template for direct API calls:
"HTTP [METHOD] call to [service_name] using environment variable [env_var] configured as [actual_value] for endpoint [endpoint_path] for [purpose]"

Template for wrapper function calls:
"[Connection type] using [wrapper_function] with endpoint [actual_endpoint], method [actual_method], environment variable [env_var] configured as [actual_value] for [purpose]"

**EXTRACT ALL connections found - no selective sampling allowed.**
"""
