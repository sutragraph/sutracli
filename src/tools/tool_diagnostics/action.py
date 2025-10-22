from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, cast

from loguru import logger

from baml_client.types import DiagnosticsParams
from src.services.lsp.lint_checker import LintChecker


@dataclass
class AgentAction:
    """Simple AgentAction class to represent tool actions."""

    description: str
    parameters: Dict[str, Any]


def execute_diagnostics_action(action: AgentAction) -> Iterator[Dict[str, Any]]:
    """Execute the diagnostics action.

    Args:
        action (AgentAction): The action to execute.

    Yields:
        Iterator[Dict[str, Any]]: The result of the diagnostics action.
    """
    try:
        # Create a DiagnosticsParams object from the dict
        params = DiagnosticsParams(**action.parameters)

        file_path = Path(params.path)

        # Check if file exists
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Get the workspace root (parent directory or current directory)
        workspace_root = str(file_path.parent)

        # Run lint check using LintChecker
        lint_messages = LintChecker.check_lint(str(file_path), workspace_root)

        yield {
            "type": "tool_use",
            "tool_name": "diagnostics",
            "data": {
                "file_path": str(file_path),
                "diagnostics": lint_messages,
                "count": len(lint_messages),
            },
        }

    except Exception as e:
        logger.error(f"Error executing diagnostics action: {e}")
        yield {
            "type": "tool_error",
            "tool_name": "diagnostics",
            "error": str(e),
        }
