"""
Python LSP server implementation.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

from src.utils.console import console

from .base_lsp import BaseLSP


class PythonLSP(BaseLSP):
    """Python LSP server implementation using pylsp."""

    @property
    def language_name(self) -> str:
        """Return the language name for this LSP server."""
        return "python"

    @property
    def server_name(self) -> str:
        """Return the server name for this LSP server."""
        return "pylsp"

    @property
    def exec_name(self) -> str:
        """Return the executable name for this LSP server."""
        # Use pylsp from Python environment
        return "~/.sutra/lsp_servers/python_env/bin/pylsp"

    @property
    def install_cmd(self) -> Optional[str]:
        """Return the installation command for this LSP server."""
        return "python3 -m venv ~/.sutra/lsp_servers/python_env && ~/.sutra/lsp_servers/python_env/bin/pip install 'python-lsp-server[all]'"

    @property
    def workspace_config(self) -> Dict[str, Any]:
        """Return the workspace configuration for this LSP server."""
        return {
            "pylsp": {
                "plugins": {
                    "pycodestyle": {"enabled": False, "maxLineLength": 88},
                    "pyflakes": {"enabled": True},
                    "pylint": {"enabled": False},
                    "mccabe": {"enabled": True, "threshold": 10},
                    "pydocstyle": {"enabled": True},
                    "yapf": {"enabled": False},
                    "autopep8": {"enabled": False},
                    "rope_autoimport": {"enabled": False},
                    "jedi_completion": {"enabled": True},
                    "jedi_definition": {"enabled": True},
                    "jedi_hover": {"enabled": True},
                    "jedi_references": {"enabled": True},
                    "jedi_signature_help": {"enabled": True},
                    "jedi_symbols": {"enabled": True},
                    "folding": {"enabled": True},
                    "preload": {
                        "enabled": True,
                        "modules": [
                            "setuptools",
                            "numpy",
                            "pandas",
                            "matplotlib",
                            "scipy",
                            "sklearn",
                        ],
                    },
                },
                "configurationSources": [],
                "settings": {"rope_completion": {"enabled": False}},
            }
        }

    def ensure_installed(self) -> Optional[str]:
        """
        Ensure the LSP server is installed, installing if necessary.

        Returns:
            Path to the LSP server executable, or None if installation failed
        """
        # Call parent method to handle installation
        return super().ensure_installed()

    def start_server(self, exec_path: str, config: Dict[str, Any]) -> subprocess.Popen:
        """
        Start the Python LSP server process with special handling for virtualenv.

        Args:
            exec_path: Path to the LSP server executable
            config: Configuration dictionary

        Returns:
            The subprocess.Popen instance for the server
        """
        import os
        import subprocess

        # Use the pylsp executable directly
        pylsp_exec = os.path.expanduser(exec_path)
        # Add the virtualenv site-packages to PYTHONPATH
        env = os.environ.copy()
        site_packages = "~/.sutra/lsp_servers/python_env/lib/python3.12/site-packages"
        env["PYTHONPATH"] = os.path.expanduser(site_packages)
        process = subprocess.Popen(
            [pylsp_exec, "-v"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
            env=env,
        )

        # Log any stderr output for debugging
        def log_stderr():
            if process.stderr:
                for line in process.stderr:
                    logger.error(f"pylsp stderr: {line.strip()}")

        import threading

        stderr_thread = threading.Thread(target=log_stderr)
        stderr_thread.daemon = True
        stderr_thread.start()

        return process
