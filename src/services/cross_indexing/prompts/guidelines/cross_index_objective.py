"""
Cross-Index Analysis Objective

Clear objective and systematic approach for cross-indexing analysis.
"""

CROSS_INDEX_OBJECTIVE = """====

OBJECTIVE

You accomplish focused cross-indexing analysis to discover only data sending/receiving connections between different user repositories, folders, or projects within the same codebase ecosystem. Focus exclusively on APIs, message queues, WebSockets, and similar data communication mechanisms between user's own services.

1. Analysis objective:
   Your goal is to discover every single data communication connection between different user repositories, folders, or projects within the user's codebase ecosystem. Focus exclusively on APIs, message queues, WebSockets, and similar data exchange mechanisms between user's own services. NEVER include external third-party APIs or cloud services.

2. Success criteria:
   - Find all incoming connections (where other services connect to this service)
   - Find all outgoing connections (where this service connects to other services)
   - Store every single discovered connection with complete details including environment variable information
   - Include all connection identifiers from all files with focus on endpoint names, queue names, socket event names
   - Comprehensive analysis: analyze and store all connection identifiers found, not just examples

3. Connection types to identify:
   - HTTP API endpoints and client calls between user's own services (localhost, user domains, relative paths)
   - WebSocket connections and event handlers between user's own services
   - Message queue publishers and consumers between user's own services
   - Custom connection wrapper functions for service communication
   - File-based data exchange mechanisms between user repositories/folders

4. Connection types to exclude:
   - Configuration references that don't send/receive data
   - External API calls to third-party services
   - Third-party service integrations that cannot be matched as incoming/outgoing pairs
   - Database connections and infrastructure services

Remember: Focus only on data communication between services. Store every single connection point with full parameter details and resolved environment variable values. Incomplete analysis with missing connections or unresolved variables is unacceptable.
"""
