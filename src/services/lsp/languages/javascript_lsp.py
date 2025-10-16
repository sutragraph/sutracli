"""
JavaScript LSP server implementation.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

from src.utils.console import console

from .base_lsp import BaseLSP


class JavaScriptLSP(BaseLSP):
    """JavaScript LSP server implementation."""

    @property
    def language_name(self) -> str:
        """Return the language name for this LSP server."""
        return "javascript"

    @property
    def server_name(self) -> str:
        """Return the server name for this LSP server."""
        return "typescript-language-server"

    @property
    def exec_name(self) -> str:
        """Return the executable name for this LSP server."""
        return "typescript-language-server"

    @property
    def install_cmd(self) -> Optional[str]:
        """Return the installation command for this LSP server."""
        return "npm i -g typescript-language-server typescript"

    @property
    def init_options(self) -> Dict[str, Any]:
        """Return the initialization options for this LSP server."""
        return {
            "preferences": {
                "quotePreference": "double",
                "includeCompletionsForModuleExports": True,
                "includeCompletionsWithInsertText": True,
            }
        }

    @property
    def workspace_config(self) -> Dict[str, Any]:
        """Return the workspace configuration for this LSP server."""
        return {
            "javascript": {
                "suggest": {
                    "enabled": True,
                    "completeFunctionCalls": True,
                },
                "validate": {"enable": True},
                "implicitProjectConfig": {
                    "checkJs": True,
                    "experimentalDecorators": True,
                    "module": "commonjs",
                    "target": "ES2020",
                    "moduleResolution": "node",
                },
            }
        }

    def ensure_installed(self) -> Optional[str]:
        """
        Ensure the LSP server is installed, installing if necessary.

        For JavaScript, also creates jsconfig.json in workspace if needed.

        Returns:
            Path to the LSP server executable, or None if installation failed
        """
        # Create workspace configuration for JavaScript if needed
        self._ensure_javascript_config()

        # Call parent method to handle installation
        return super().ensure_installed()

    def _ensure_javascript_config(self) -> Optional[str]:
        """
        Create jsconfig.json in workspace if it doesn't exist.

        Returns:
            Path to the jsconfig.json file, or None if workspace_root is not set
        """
        if not self.workspace_root:
            return None

        workspace_path = Path(self.workspace_root)
        if not workspace_path.exists():
            return None

        jsconfig_path = workspace_path / "jsconfig.json"

        # Create jsconfig.json if it doesn't exist
        if not jsconfig_path.exists():
            console.process(f"Creating JavaScript configuration file: {jsconfig_path}")
            logger.debug(f"Creating jsconfig.json at {jsconfig_path}")

            jsconfig = {
                "compilerOptions": {
                    "module": "commonjs",
                    "target": "es2020",
                    "checkJs": True,
                    "strict": True,
                    "esModuleInterop": True,
                    "skipLibCheck": True,
                    "forceConsistentCasingInFileNames": True,
                    "moduleResolution": "node",
                    "allowSyntheticDefaultImports": True,
                    "experimentalDecorators": True,
                    "resolveJsonModule": True,
                    "sourceMap": True,
                    "outDir": "./dist",
                    "lib": ["es2020", "dom"],
                },
                "include": ["src/**/*", "types/**/*"],
                "exclude": ["node_modules", "dist", "**/*.test.js", "**/*.spec.js"],
            }

            try:
                with open(jsconfig_path, "w") as f:
                    json.dump(jsconfig, f, indent=2)
                console.success(
                    f"Created JavaScript configuration file: {jsconfig_path}"
                )
                logger.debug(f"Successfully created jsconfig.json")
                return str(jsconfig_path)
            except Exception as e:
                console.error(f"Failed to create JavaScript configuration: {e}")
                logger.error(f"Failed to create jsconfig.json: {e}")
                return None

        logger.debug(f"JavaScript configuration already exists at {jsconfig_path}")
        return str(jsconfig_path)
