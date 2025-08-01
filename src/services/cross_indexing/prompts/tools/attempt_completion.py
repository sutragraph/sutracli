"""
Attempt Completion Tool for Cross-Index Analysis

Tool definition for completing cross-index analysis with consistent format.
"""

ATTEMPT_COMPLETION_TOOL = """## attempt_completion

Complete the cross-index analysis and provide a brief summary of connection data collected in sutra memory.

Usage: attempt_completion(result="Brief summary of connection types discovered")

Expected Format:
<attempt_completion>
<result>
Analysis complete. Discovered and stored 25 HTTP API connections, 12 WebSocket connections, and 8 message queue connections in sutra memory. All connection data has been collected from the codebase including wrapper function calls and environment variable configurations.
</result>
</attempt_completion>

Summary Requirements:
- Provide only a brief 3-4 line summary
- Mention the types of connections discovered (HTTP, WebSocket, message queues, etc.)
- Include approximate counts of each connection type
- Indicate that data has been stored in sutra memory
- Do NOT include detailed connection information
- NEVER list specific endpoints or connection details
- All detailed data should remain in sutra memory
- MANDATORY: This tool MUST be used to complete analysis - never complete without it

Example Summary:
<attempt_completion>
<result>
Cross-indexing analysis complete. Identified and stored 18 HTTP API endpoints, 6 WebSocket connections, and 4 RabbitMQ message queue connections in sutra memory. All wrapper function calls and environment variable configurations have been captured.
</result>
</attempt_completion>

"""
