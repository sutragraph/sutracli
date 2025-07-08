"""
Terminal executor for handling terminal command actions.
"""

import subprocess
import os
from typing import Iterator, Dict, Any
from loguru import logger
from src.services.agent.agentic_core import AgentAction


def execute_terminal_action(action: AgentAction) -> Iterator[Dict[str, Any]]:
    """
    Execute terminal command action.

    Args:
        action: AgentAction containing terminal command parameters
    Yields:
        Dictionary containing the results of the terminal command execution.
    """
    try:
        parameters = action.parameters or {}
        command = parameters.get("command")
        cwd = parameters.get("cwd", os.getcwd())

        if not command:
            yield {
                "tool_name": "terminal",
                "status": "error",
                "data": {"error": "command parameter is required"},
            }
            return

        logger.debug(f"🖥️ Executing terminal command: {command}")
        logger.debug(f"📁 Working directory: {cwd}")

        # Execute the command
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
            )

            # Prepare output
            output = result.stdout if result.stdout else ""
            error = result.stderr if result.stderr else ""

            # Check if output is empty and provide appropriate message
            if not output.strip() and result.returncode == 0:
                display_output = f"No results found for command: {command}"
            else:
                display_output = output

            if result.returncode == 0:
                yield {
                    "type": "tool_use",
                    "tool_name": "terminal",
                    "status": "success",
                    "command": command,
                    "data": {
                        "command": command,
                        "output": display_output,
                        "error": error,
                        "return_code": result.returncode,
                        "cwd": cwd,
                    },
                }
            else:
                yield {
                    "type": "tool_use",
                    "tool_name": "terminal",
                    "status": "error",
                    "command": command,
                    "data": {
                        "command": command,
                        "output": output,
                        "error": error,
                        "return_code": result.returncode,
                        "cwd": cwd,
                    },
                }

        except subprocess.TimeoutExpired:
            yield {
                "tool_name": "terminal",
                "status": "error",
                "data": {"error": f"Command timed out after 30 seconds: {command}"},
            }
        except Exception as e:
            yield {
                "tool_name": "terminal",
                "status": "error",
                "data": {"error": f"Command execution failed: {str(e)}"},
            }

    except Exception as e:
        logger.error(f"Terminal action execution failed: {e}")
        yield {
            "tool_name": "terminal",
            "status": "error",
            "data": {"error": f"Terminal execution failed: {str(e)}"},
        }
