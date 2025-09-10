"""
Rovodev CLI agent provider implementation.
"""

import subprocess
import os
import time
import shlex
from typing import Dict, Any
from .config import AgentProviderConfig
from src.tools.tool_terminal_commands.action import TerminalSessionManager


class RovodevProvider:
    """Provider for Rovodev CLI agent."""

    def __init__(self, config: AgentProviderConfig):
        self.config = config
        self.name = "rovodev"

    def is_available(self) -> bool:
        """Check if rovodev CLI is available."""
        try:
            # Try to run 'acli rovodev --version' to check availability
            result = subprocess.run(
                ["acli", "rovodev", "--version"],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except (FileNotFoundError, Exception):
            return False

    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider information."""
        return {
            "name": self.name,
            "description": self.config.description,
            "command": self.config.command,
            "available": self.is_available(),
            "enabled": self.config.enabled,
        }

    def _format_prompt_for_command(self, prompt: str) -> str:
        """Format prompt for command line execution by escaping special characters."""
        # Replace newlines with literal \n for proper command line handling
        formatted_prompt = prompt.replace("\n", "\\n")
        # Escape hash/pound characters to prevent shell comment interpretation
        formatted_prompt = formatted_prompt.replace("#", "\\#")
        return shlex.quote(formatted_prompt)

    def execute_prompt(
        self, project_path: str, prompt: str, session_description: str = None
    ) -> Dict[str, Any]:
        """Execute a prompt using Rovodev CLI in a new terminal session.

        Args:
            project_path: Path to the project directory
            prompt: The prompt to execute
            session_description: Optional custom description for the terminal session

        Returns:
            Dict containing success status, output, error information, and session details
        """

        if not os.path.exists(project_path):
            return {
                "success": False,
                "error": f"Project path does not exist: {project_path}",
                "output": "",
                "session_id": None,
            }

        try:
            # Create a new terminal session for this agent execution
            session_description = (
                session_description
                or f"Rovodev Agent - {os.path.basename(project_path)}"
            )
            session_id = TerminalSessionManager.create_session(
                cwd=project_path, description=session_description
            )

            # Build the command to execute with properly formatted prompt
            formatted_prompt = self._format_prompt_for_command(prompt)
            cmd = f"acli rovodev {formatted_prompt}"

            # Execute the command in the new terminal session as a long-running process
            # This allows the user to see the agent working in real-time in a separate terminal
            session = TerminalSessionManager.get_session(session_id)
            if not session:
                return {
                    "success": False,
                    "error": f"Failed to get created session {session_id}",
                    "output": "",
                    "session_id": session_id,
                }

            # Execute the command in the terminal
            result = session.execute_command(cmd, timeout=1200, is_long_running=True)

            # Wait a moment to let the command start
            time.sleep(2.0)

            # Get initial output to confirm the agent started
            initial_output = session.get_new_output()

            return {
                "success": result.get("status") == "success",
                "output": initial_output or result.get("output", ""),
                "error": result.get("error", ""),
                "return_code": 0 if result.get("status") == "success" else 1,
                "session_id": session_id,
                "terminal_info": f"Agent running in terminal session: {session_id}",
                "monitor_command": f"Use session_id '{session_id}' to monitor progress",
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "output": "",
                "session_id": None,
            }
