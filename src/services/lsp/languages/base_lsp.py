"""
Base class for language-specific LSP server implementations.
"""

import subprocess
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from loguru import logger

from src.utils.console import console

from ..downloader import Downloader


class BaseLSP(ABC):
    """
    Base class for language-specific LSP server implementations.

    This class provides common functionality for all LSP servers while allowing
    language-specific customization through abstract methods.
    """

    def __init__(self, workspace_root: Optional[str] = None):
        """
        Initialize the LSP server instance.

        Args:
            workspace_root: Optional workspace root directory for LSP context
        """
        self.workspace_root = workspace_root
        self._config = None

    @property
    @abstractmethod
    def language_name(self) -> str:
        """Return the language name for this LSP server."""
        pass

    @property
    @abstractmethod
    def server_name(self) -> str:
        """Return the server name for this LSP server."""
        pass

    @property
    @abstractmethod
    def exec_name(self) -> str:
        """Return the executable name for this LSP server."""
        pass

    @property
    def download_url(self) -> Optional[str]:
        """Return the download URL for this LSP server."""
        return None

    @property
    def install_cmd(self) -> Optional[str]:
        """Return the installation command for this LSP server."""
        return None

    @property
    def args(self) -> list:
        """Return the arguments to pass to the LSP server."""
        return ["--stdio"]

    @property
    def init_options(self) -> Dict[str, Any]:
        """Return the initialization options for this LSP server."""
        return {}

    @property
    def workspace_config(self) -> Dict[str, Any]:
        """Return the workspace configuration for this LSP server."""
        return {}

    def get_config(self) -> Dict[str, Any]:
        """
        Get the complete configuration for this LSP server.

        Returns:
            Dictionary containing all configuration options
        """
        if self._config is None:
            self._config = {
                "type": "lsp",
                "name": self.server_name,
                "exec_name": self.exec_name,
                "download_url": self.download_url,
                "install_cmd": self.install_cmd,
                "args": self.args,
                "init_options": self.init_options,
                "workspace_config": self.workspace_config,
            }
        return self._config

    def ensure_installed(self) -> Optional[str]:
        """
        Ensure the LSP server is installed, installing if necessary.

        Returns:
            Path to the LSP server executable, or None if installation failed
        """
        # Get configuration and ensure installation
        config = self.get_config()
        console.process(f"Checking LSP server installation for {self.language_name}...")
        logger.debug(
            f"Ensuring LSP server is installed for language: {self.language_name}"
        )

        exec_path = Downloader.ensure_lsp_installed(config)

        if not exec_path:
            console.error(f"Failed to install LSP server for {self.language_name}")
            logger.error(f"Failed to install LSP server for {self.language_name}")
            return None

        return exec_path

    def start_server(self, exec_path: str, config: Dict[str, Any]) -> subprocess.Popen:
        """
        Start the LSP server process.

        Args:
            exec_path: Path to the LSP server executable
            config: Configuration dictionary

        Returns:
            The subprocess.Popen instance for the server
        """
        import subprocess

        # Split the exec_path and args to handle module-style execution
        exec_parts = exec_path.split()
        process = subprocess.Popen(
            exec_parts + config["args"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
        )
        return process
