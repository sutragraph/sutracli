"""
Cross-Index Analysis Objective

Clear objective and systematic approach for cross-indexing analysis.
"""

CROSS_INDEX_OBJECTIVE = """====

OBJECTIVE

You accomplish focused cross-indexing analysis to discover only data sending/receiving connections between different user repositories, folders, or projects within the same codebase ecosystem. Focus exclusively on APIs, message queues, WebSockets, and similar data communication mechanisms between user's own services.

1. Analysis objective:
   Your goal is to discover every single data communication connection between different user repositories, folders, or projects within the user's codebase ecosystem. Focus exclusively on APIs, message queues, WebSockets, and similar inter-service data exchange mechanisms between user's own services. NEVER include external third-party APIs or cloud services.

2. Success criteria:
   - Find all incoming connections (where other services connect to this service)
   - Find all outgoing connections (where this service connects to other services)
   - Document all connection wrapper function calls with comprehensive variable descriptions and environment context
   - Store every single discovered connection with complete details including environment variable information
   - Include all connection identifiers from all files with focus on endpoint names, queue names, socket event names
   - Never group multiple connections - each connection gets separate entry with connection identifier and request type
   - Comprehensive analysis: analyze and store all connection identifiers found, not just examples
   - ZERO TOLERANCE for incomplete analysis: Every single connection identifier found must be analyzed and stored individually

3. Three-phase analysis methodology:
   - Phase 1: Package Discovery - Identify used connection packages in the project
   - Phase 2: Import Statement Analysis - Find import statements of discovered packages using language-specific patterns
   - Phase 3: Usage Pattern Discovery - Find wrapper functions and user-defined patterns that use these packages

4. Connection types to identify:
   - HTTP API endpoints and client calls between user's own services (localhost, user domains, relative paths)
   - WebSocket connections and event handlers between user's own services
   - Message queue publishers and consumers between user's own services
   - Custom connection wrapper functions for service communication
   - File-based data exchange mechanisms between user repositories/folders
   - Inter-service communication within user's codebase ecosystem

5. Connection types to exclude:
   - Import/require statements and library imports
   - Module imports and package imports
   - Configuration references that don't send/receive data
   - External API calls to third-party services
   - Third-party service integrations that cannot be matched as incoming/outgoing pairs
   - Database connections and infrastructure services
   - External service connections that don't represent inter-service communication within user's codebase

Remember: Focus only on data communication between services. Store every single connection point with full parameter details and resolved environment variable values. Incomplete analysis with missing connections or unresolved variables is unacceptable.
"""
