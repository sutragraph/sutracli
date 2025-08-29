"""
Rovodev CLI agent provider implementation.
"""

import subprocess
import os
from typing import Dict, Any
from .config import AgentProviderConfig


class RovodevProvider:
    """Provider for Rovodev CLI agent."""

    def __init__(self, config: AgentProviderConfig):
        self.config = config
        self.name = "rovodev"

    def execute_prompt(self, project_path: str, prompt: str) -> Dict[str, Any]:
        """Execute a prompt using Rovodev CLI in the specified project path.

        Args:
            project_path: Path to the project directory
            prompt: The prompt to execute

        Returns:
            Dict containing success status, output, and error information
        """

        if not os.path.exists(project_path):
            return {
                "success": False,
                "error": f"Project path does not exist: {project_path}",
                "output": ""
            }

        try:
            # Change to project directory and execute rovodev command
            cmd = [f"echo {prompt}", "acli", "rovodev"]

            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else "",
                "return_code": result.returncode
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "output": ""
            }
