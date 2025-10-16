"""
Main lint checker class that coordinates all components.

The LintChecker provides a simple interface for checking lint on source files.
It automatically handles language detection, LSP server management, and
diagnostic collection.
"""

import os
from typing import Any, Dict, List

from loguru import logger

from src.utils.console import console
from src.utils.error_utils import raiseError
from src.utils.file_utils import get_language_from_extension

from .exceptions import LSPErrorType
from .lsp_manager import LSPManager


class LintChecker:
    """Main class for checking lint using LSP servers."""

    @staticmethod
    def check_lint(file_path: str, workspace_root: str) -> List[Dict[str, Any]]:
        """
        Check lint for a file using appropriate LSP server.

        This method automatically:
        - Detects the language from file extension
        - Installs the LSP server if needed (first time only)
        - Starts the server if not running
        - Collects and returns diagnostics

        Args:
            file_path: Path to the file to check
            workspace_root: Optional workspace root directory for LSP context

        Returns:
            List of lint issues/diagnostics, each containing:
                - line: Line number (1-based)
                - column: Column number (1-based)
                - message: Diagnostic message
                - severity: 1=Error, 2=Warning, 3=Info, 4=Hint
                - source: Source of the diagnostic (e.g., "pylint")
                - code: Error code (if available)

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the language is not supported by LSP
            RuntimeError: If LSP server installation or startup fails
        """
        # Validate file exists
        if not os.path.exists(file_path):
            raiseError(
                LSPErrorType.FILE_NOT_FOUND,
                f"File not found: {file_path}",
                FileNotFoundError,
            )

        # Get language from file extension using file_utils
        language = get_language_from_extension(file_path)
        if not language:
            raiseError(
                LSPErrorType.UNSUPPORTED_LANGUAGE,
                f"Unable to determine language for file: {file_path}",
                ValueError,
            )

        # Get LSP server (automatically installs and starts if needed)
        server_info = LSPManager.get_server(language, workspace_root=workspace_root)

        # Read file content
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Get diagnostics from LSP server
        client = server_info["client"]
        workspace_config = server_info.get("workspace_config", {})
        diagnostics = client.get_diagnostics(
            os.path.abspath(file_path),
            content,
            language,
            workspace_config=workspace_config,
        )

        # Extract just the messages from diagnostics
        messages = []
        for diagnostic in diagnostics:
            message = diagnostic.get("message", "")

            start_line = diagnostic.get("range", {}).get("start", {}).get("line", 0) + 1
            start_col = (
                diagnostic.get("range", {}).get("start", {}).get("character", 0) + 1
            )
            end_line = diagnostic.get("range", {}).get("end", {}).get("line", 0) + 1
            end_col = diagnostic.get("range", {}).get("end", {}).get("character", 0) + 1

            string = f"[L{start_line}:{start_col}-L{end_line}:{end_col}] - {message}"
            messages.append(string)

        return messages

    @staticmethod
    def cleanup():
        """
        Clean up all running LSP servers.

        Call this when you're done with lint checking to properly
        shut down all LSP server processes.
        """
        LSPManager.stop_all_servers()
