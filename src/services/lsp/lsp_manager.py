"""
Static class to manage running LSP server instances.

The LSPManager provides a high-level interface for obtaining running LSP servers.
It automatically handles installation and startup, so callers only need to call
get_server() and receive a running server.
"""

import os
import subprocess
import threading
from typing import Dict, Optional, TextIO, cast

from loguru import logger

from src.utils.console import console
from src.utils.error_utils import raiseError

from .exceptions import LSPErrorType
from .jsonrpc_client import JSONRPCClient


class LSPManager:
    """
    Static class to manage LSP server instances.

    This class provides a simple interface: get_server() returns a running server,
    handling installation and startup automatically.
    """

    _servers: Dict[str, Dict] = {}
    _lock = threading.Lock()

    @classmethod
    def get_server(cls, language: str, workspace_root: str) -> Dict:
        """
        Get a running LSP server for a language.

        This method automatically handles:
        - Checking if server is already running
        - Installing the LSP server if not installed
        - Starting the server if not running
        - Returning the running server info

        Args:
            language: Language name (must exist in LANGUAGE_MAP)
            workspace_root: Optional workspace root directory for LSP context

        Returns:
            Dictionary containing:
                - process: subprocess.Popen instance
                - client: JSONRPCClient instance
                - language: language name
                - workspace_root: workspace root path

        Raises:
            ValueError: If language is not supported
            RuntimeError: If installation or startup fails
        """
        with cls._lock:
            # Check if server exists and is running
            if language in cls._servers:
                server_info = cls._servers[language]
                if cls._is_process_alive(server_info["process"]):
                    # Check if workspace_root matches
                    if (
                        workspace_root
                        and server_info.get("workspace_root") != workspace_root
                    ):
                        console.process(
                            f"Workspace changed for {language}, restarting server..."
                        )
                        logger.debug(
                            f"Workspace root changed for {language}, removing from registry"
                        )
                        cls.stop_server(language)
                    else:
                        return server_info
                else:
                    # Server died, clean it up
                    console.warning(
                        f"LSP server for {language} has died, restarting..."
                    )
                    logger.debug(
                        f"LSP server process for {language} is no longer alive, removing from registry"
                    )
                    del cls._servers[language]

            # Need to start a new server
            return cls._ensure_server_started(language, workspace_root)

    @classmethod
    def _is_process_alive(cls, process: subprocess.Popen) -> bool:
        """Check if a process is still alive."""
        return process.poll() is None

    @classmethod
    def _ensure_server_started(cls, language: str, workspace_root: str) -> Dict:
        """
        Ensure LSP server is installed and started for a language.

        This is the core logic that handles installation and startup.

        Args:
            language: Language name
            workspace_root: Optional workspace root directory
        """
        # Import here to avoid circular dependencies
        from .languages.lsp_factory import LSPFactory

        # Create LSP instance for the language
        try:
            lsp_instance = LSPFactory.create_lsp(language, workspace_root)
        except ValueError as e:
            raiseError(LSPErrorType.UNSUPPORTED_LANGUAGE, str(e), ValueError)

        # Ensure LSP server is installed (installs only if not found)
        console.process(f"Checking LSP server installation for {language}...")
        logger.debug(f"Ensuring LSP server is installed for language: {language}")
        exec_path = lsp_instance.ensure_installed()

        if not exec_path:
            raiseError(
                LSPErrorType.SERVER_INSTALL_FAILED,
                f"Failed to install LSP server for {language}",
                RuntimeError,
            )

        console.process(f"Starting LSP server for {language}...")
        logger.debug(
            f"Starting LSP server process for language: {language} with exec: {exec_path}"
        )

        # Start the server
        try:
            # Get configuration from LSP instance
            config = lsp_instance.get_config()
            logger.debug(f"Starting LSP server with config: {config}")

            # Start the server with line buffered I/O for proper JSON-RPC communication
            process = lsp_instance.start_server(exec_path, config)

            # Give the server a moment to start up
            import time

            time.sleep(0.1)

            # Validate process streams
            if process.stdin is None or process.stdout is None:
                process.kill()
                raiseError(
                    LSPErrorType.SERVER_START_FAILED,
                    f"Failed to create pipes for LSP server {language}",
                    RuntimeError,
                )

            # Create JSON-RPC client
            client = JSONRPCClient(
                cast(TextIO, process.stdin), cast(TextIO, process.stdout)
            )

            # Get init options and workspace config from LSP instance
            init_options = config.get("init_options", {})
            workspace_config = config.get("workspace_config", {})

            # Initialize LSP server with workspace context and init options
            client.initialize(workspace_root=workspace_root, init_options=init_options)

            server_info = {
                "process": process,
                "client": client,
                "language": language,
                "workspace_root": workspace_root,
                "workspace_config": workspace_config,
            }

            cls._servers[language] = server_info
            console.success(f"LSP server for {language} started successfully")
            logger.debug(f"LSP server for {language} initialized and added to registry")
            return server_info

        except Exception as e:
            raiseError(
                LSPErrorType.SERVER_START_FAILED,
                f"Failed to start LSP server for {language}: {e}",
                RuntimeError,
            )

    @classmethod
    def stop_server(cls, language: str) -> bool:
        """
        Stop LSP server for a language.

        Args:
            language: Language name

        Returns:
            True if server was stopped, False if server wasn't running
        """
        with cls._lock:
            if language not in cls._servers:
                return False

            server_info = cls._servers[language]
            process = server_info["process"]

            try:
                process.kill()
                logger.debug(f"Killed process for {language}")
            except:
                pass  # Process might already be dead

            del cls._servers[language]
            return True

    @classmethod
    def stop_all_servers(cls):
        """Stop all running LSP servers."""
        with cls._lock:
            languages = list(cls._servers.keys())
            for language in languages:
                cls.stop_server(language)

    @classmethod
    def is_server_running(cls, language: str) -> bool:
        """
        Check if LSP server is running for a language.

        Note: You typically don't need to call this. Just use get_server()
        which will start the server if needed.

        Args:
            language: Language name

        Returns:
            True if server is running, False otherwise
        """
        with cls._lock:
            if language not in cls._servers:
                return False

            server_info = cls._servers[language]
            return cls._is_process_alive(server_info["process"])
