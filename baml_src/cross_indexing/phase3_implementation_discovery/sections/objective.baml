template_string Objective_Phase3() #"====

OBJECTIVE

You accomplish focused implementation discovery to find actual usage of imported connection methods and functions identified in previous import analysis. Your goal is to locate where these imported packages are actually used to establish data communication connections between different user repositories, projects, or folders.

1. Primary objective:
  Execute tasks created in previous import analysis to find actual usage of imported connection methods. You must search based on the tasks provided and can create additional tasks within this analysis for further processing based on your findings.

2. Success criteria:
  - Execute all pending tasks from import pattern discovery systematically
  - Find actual usage of imported connection methods and functions with real parameters
  - Identify data communication code that sends/receives data between services
  - Find connection code with complete details including environment variables and actual values
  - CRITICAL: Handle wrapper functions by finding their actual usage sites with real parameter values, not variable definitions
  - MANDATORY: When you find connection code with variable parameters (queueName, url, endpoint, eventName), search for wrapper function calls with actual values
  - Comprehensive analysis: analyze and find all connection usage found, not just representative examples

3. Implementation discovery scope:
  - HTTP API calls with actual endpoints and parameters that connect to other services
  - Server route definitions with real endpoint paths that receive data from other services
  - WebSocket connections and event handlers with actual events for real-time communication
  - Message queue publishers and consumers with real queue names for service communication
  - Custom wrapper function calls with actual parameters for service-to-service communication
  - Environment variable usage in connection configurations with resolved values

4. Implementation exclusions:
  - Generic function definitions without actual usage or real parameters
  - Configuration references that don't send/receive data between services
  - Utility functions that don't actively send/receive data to other services
  - Test code, mock implementations, and development debugging code
  - Infrastructure connections that don't represent service-to-service communication

5. Connection code analysis requirements:
  - CRITICAL: Find actual data communication lines with real parameters, not variable names or resolved variables
  - NEVER accept variable parameters as final connection data (queueName, url, endpoint, eventName, etc.)
  - ALWAYS search for wrapper function calls when you find variable parameters in connection code
  - Include environment variable values and their resolved configurations
  - Focus on where data communication occurs with real values to communicate with other services
  - Find wrapper function calls with actual parameters, not wrapper function definitions
  - Include complete parameter details, endpoint information, and service communication context
  - EXAMPLE: `sendToQueue(queueName, message)` → Search for wrapper calls → Find `publishMessage('user-notifications', data)`
"#
