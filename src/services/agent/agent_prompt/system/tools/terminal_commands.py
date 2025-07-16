TERMINAL_TOOL = """## execute_command
Description: Execute CLI commands using foreground terminal sessions with intelligent long-running process support. Sessions automatically reuse existing compatible sessions (same working directory, no running tasks) or create new ones as needed. All sessions maintain working directory and environment variables across commands. Long-running processes (servers, watchers, etc.) are automatically detected and handled appropriately.

Parameters:
- command: (required) CLI command to execute
- cwd: (optional) Working directory (default: {current_dir})
- session_id: (optional) Specific session ID to use (overrides automatic session reuse)
- description: (optional) Description of what this session is used for (helps identify sessions)
- duration: (optional) For monitor_output: duration in seconds to monitor (default: 5.0)
- action_type: (optional) 'execute' (default), 'create_session', 'close_session', 'list_sessions', 'get_output', 'monitor_output', 'get_running_processes', 'get_session_stats'

Usage:
<execute_command>
<command>Your command here</command>
<cwd>working_directory (optional)</cwd>
<session_id>session-id (optional, forces specific session)</session_id>
<description>Brief description of session purpose (optional)</description>
</execute_command>

Automatic Session Reuse:
- Sessions are automatically reused when the same working directory is requested and the previous session has no running tasks
- This provides seamless continuation of work in the same directory context
- No need to manually manage session IDs for basic workflows

Simple Workflow:
1. Execute command (auto-reuses compatible session): <execute_command><command>your_command</command><description>task description</description></execute_command>
2. Execute in specific directory: <execute_command><command>your_command</command><cwd>/path/to/dir</cwd></execute_command>
3. Force specific session: <execute_command><command>your_command</command><session_id>existing-session-id</session_id></execute_command>
4. List active sessions: <execute_command><action_type>list_sessions</action_type></execute_command>

Session Management Actions:
- execute: Run command (automatically reuses compatible session or creates new one)
- list_sessions: Shows all active sessions with descriptions, working directory, and status
- create_session: Creates new session explicitly, returns session_id
- close_session: Closes specific session (requires session_id)
- get_output: Retrieves output from a session (requires session_id)

Session Compatibility:
A session is considered compatible for reuse when:
- Same working directory (cwd)
- No currently running tasks
- Session is still alive/functional

This approach eliminates the need for manual session lifecycle management while ensuring efficient resource usage.

Long-Running Process Support:
- Automatically detects server commands (http.server, npm start, flask run, etc.)
- Maintains session state for long-running processes
- Provides real-time output monitoring capabilities
- Allows parallel task execution while servers run
- Smart completion detection for different command types

Advanced Actions:
- monitor_output: Monitor real-time output from long-running processes
- get_running_processes: List all sessions with active long-running processes
- get_session_stats: Get comprehensive statistics about session usage

Long-Running Process Examples:
1. Start server: <execute_command><command>python3 -m http.server 8080</command><description>Development server</description></execute_command>
2. Monitor server: <execute_command><action_type>monitor_output</action_type><session_id>server-session-id</session_id><duration>10</duration></execute_command>
3. List running processes: <execute_command><action_type>get_running_processes</action_type></execute_command>

This approach eliminates the need for manual session lifecycle management while ensuring efficient resource usage.
"""
