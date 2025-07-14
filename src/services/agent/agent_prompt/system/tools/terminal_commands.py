TERMINAL_TOOL = """## execute_command
Description: Execute CLI commands with persistent terminal sessions. Sessions maintain working directory and environment variables across commands. Sessions auto-create when needed and can be reused for related tasks.

Parameters:
- command: (required) CLI command to execute
- cwd: (optional) Working directory (default: {current_dir})
- session_id: (optional) Existing session ID for continuity
- description: (optional) Description of what this session is used for (helps identify sessions)
- close_after: (optional) Close session automatically after command execution (default: false)
- action_type: (optional) 'execute' (default), 'create_session', 'close_session', 'list_sessions'

Usage:
<execute_command>
<command>Your command here</command>
<session_id>session-id (optional for execute, required for close_session)</session_id>
<description>Brief description of session purpose (optional)</description>
<close_after>true (optional, auto-close session after command)</close_after>
</execute_command>

Simple Workflow:
1. Execute one-off commands: <execute_command><command>your_command</command><description>task description</description><close_after>true</close_after></execute_command>
2. Execute with session reuse: <execute_command><command>your_command</command><description>task description</description></execute_command>
3. Reuse sessions for related tasks: <execute_command><command>your_command</command><session_id>existing-session-id</session_id></execute_command>
4. List sessions when needed: <execute_command><action_type>list_sessions</action_type></execute_command>

Session actions:
- execute: Run command (auto-creates session with description if none provided)
- list_sessions: Shows all active sessions with descriptions, cwd, and status
- create_session: Creates new session, returns session_id
- close_session: Closes specific session (requires session_id)
"""
