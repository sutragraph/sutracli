"""
TypeScript LSP server implementation.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

from src.utils.console import console

from .base_lsp import BaseLSP


class TypeScriptLSP(BaseLSP):
    """TypeScript LSP server implementation."""

    @property
    def language_name(self) -> str:
        """Return the language name for this LSP server."""
        return "typescript"

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
                "includeInlayParameterNameHints": "all",
                "includeInlayParameterNameHintsWhenArgumentMatchesName": True,
                "includeInlayFunctionParameterTypeHints": True,
                "includeInlayVariableTypeHints": True,
                "includeInlayPropertyDeclarationTypeHints": True,
                "includeInlayFunctionLikeReturnTypeHints": True,
                "includeInlayEnumMemberValueHints": True,
            }
        }

    def ensure_installed(self) -> Optional[str]:
        """
        Ensure the LSP server is installed, installing if necessary.

        For TypeScript, also creates tsconfig.json in workspace if needed.

        Returns:
            Path to the LSP server executable, or None if installation failed
        """
        # Create workspace configuration for TypeScript if needed
        self._ensure_typescript_config()

        # Call parent method to handle installation
        return super().ensure_installed()

    def _ensure_typescript_config(self) -> Optional[str]:
        """
        Create tsconfig.json in workspace if it doesn't exist.

        Returns:
            Path to the tsconfig.json file, or None if workspace_root is not set
        """
        if not self.workspace_root:
            return None

        workspace_path = Path(self.workspace_root)
        if not workspace_path.exists():
            return None

        tsconfig_path = workspace_path / "tsconfig.json"

        # Create tsconfig.json if it doesn't exist
        if not tsconfig_path.exists():
            console.process(f"Creating TypeScript configuration file: {tsconfig_path}")
            logger.debug(f"Creating tsconfig.json at {tsconfig_path}")

            tsconfig = {
                "compilerOptions": {
                    "module": "commonjs",
                    "target": "es2020",
                    "jsx": "preserve",
                    "strict": True,
                    "esModuleInterop": True,
                    "skipLibCheck": True,
                    "forceConsistentCasingInFileNames": True,
                    "moduleResolution": "node",
                    "allowSyntheticDefaultImports": True,
                    "experimentalDecorators": True,
                    "emitDecoratorMetadata": True,
                    "resolveJsonModule": True,
                    "sourceMap": True,
                    "outDir": "./dist",
                    "rootDir": "./src",
                    "lib": ["es2020", "dom"],
                },
                "include": ["src/**/*", "types/**/*"],
                "exclude": ["node_modules", "dist", "**/*.test.ts", "**/*.spec.ts"],
            }

            try:
                with open(tsconfig_path, "w") as f:
                    json.dump(tsconfig, f, indent=2)
                console.success(
                    f"Created TypeScript configuration file: {tsconfig_path}"
                )
                logger.debug(f"Successfully created tsconfig.json")
                return str(tsconfig_path)
            except Exception as e:
                console.error(f"Failed to create TypeScript configuration: {e}")
                logger.error(f"Failed to create tsconfig.json: {e}")
                return None

        logger.debug(f"TypeScript configuration already exists at {tsconfig_path}")
        return str(tsconfig_path)
