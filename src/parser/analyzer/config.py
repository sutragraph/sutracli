"""
Configuration management for the tree-sitter analyzer.

This module provides configuration management for analyzer settings,
parser configurations, and language support.
"""

import os
import json
import platform
from typing import Dict, Any, Optional, Set, List
from pathlib import Path


class ConfigurationError(Exception):
    """Exception raised for configuration-related errors."""

    pass


class ParserConfigLoader:
    """Loads and manages parser configuration from parsers.json."""

    _instance: Optional["ParserConfigLoader"] = None

    def __init__(self, config_path: Optional[str] = None):
        """Initialize parser config loader."""
        if config_path:
            self.config_path = config_path
        else:
            # Get parser config path from main configuration
            self.config_path = self._get_parser_config_path()

        self.config = self._load_config()

    def _get_parser_config_path(self) -> str:
        """Get parser config path from main configuration."""
        try:
            # Try to get from main config system
            from src.config.settings import get_config

            main_config = get_config()

            # Check if parser config path is defined in main config
            if hasattr(main_config, "parser") and hasattr(
                main_config.parser, "config_file"
            ):
                config_path = main_config.parser.config_file
                # Use Path for better cross-platform compatibility
                if config_path.startswith("~/"):
                    return str(Path.home() / config_path[2:])
                else:
                    return config_path
        except Exception as e:
            raise ConfigurationError(
                f"Failed to get parser config path from main configuration: {e}"
            )

        raise ConfigurationError("Parser configuration not found in main config")

    def _get_build_directory_from_config(self) -> str:
        """Get parser build directory from main configuration."""
        try:
            # Try to get from main config system
            from src.config.settings import get_config

            main_config = get_config()

            # Check if parser build directory is defined in main config
            if hasattr(main_config, "parser") and hasattr(
                main_config.parser, "build_directory"
            ):
                build_dir = main_config.parser.build_directory
                return os.path.expanduser(build_dir)
        except Exception as e:
            raise ConfigurationError(
                f"Failed to get parser build directory from main configuration: {e}"
            )

        raise ConfigurationError("Parser build directory not found in main config")

    def _get_system_file_extension(self) -> str:
        """Get the appropriate file extension for parser libraries based on the system."""
        system = platform.system()
        if system == "Darwin":
            return ".dylib"
        elif system == "Linux":
            return ".so"
        else:
            # Default to Linux for other systems
            return ".so"

    @classmethod
    def get_instance(cls, config_path: Optional[str] = None) -> "ParserConfigLoader":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls(config_path)
        return cls._instance

    def _load_config(self) -> Dict[str, Any]:
        """Load parser configuration from JSON file."""
        if not os.path.exists(self.config_path):
            raise ConfigurationError(
                f"Parser configuration file not found: {self.config_path}"
            )

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                raw_config = json.load(f)

            # Convert from the parsers.json format to our internal format
            if "parsers" in raw_config:
                build_dir = raw_config.get("settings", {}).get(
                    "build_directory", "./build"
                )
                # Convert relative path to use configured build directory
                if build_dir in ["./build", "src/parser/build"]:
                    build_dir = self._get_build_directory_from_config()

                converted_config = {
                    "build_directory": build_dir,
                    "languages": {},
                }

                # Get system-specific file extension
                file_extension = self._get_system_file_extension()

                for lang_name, lang_config in raw_config["parsers"].items():
                    converted_config["languages"][lang_name] = {
                        "extensions": lang_config.get("extensions", []),
                        "parser": f"{lang_config.get('parser_name', lang_name)}{file_extension}",
                    }

                return converted_config
            else:
                # Already in our format
                return raw_config

        except Exception as e:
            raise ConfigurationError(f"Failed to load parser config: {e}")

    def get_build_directory(self) -> str:
        """Get build directory for parser libraries."""
        # Get from config, with fallback to configuration-based default
        default_build_dir = self._get_build_directory_from_config()
        return self.config.get("build_directory", default_build_dir)

    def get_supported_languages(self) -> Set[str]:
        """Get set of supported languages."""
        return set(self.config.get("languages", {}).keys())

    def get_language_from_extension(self, extension: str) -> Optional[str]:
        """Get language from file extension."""
        for lang, config in self.config.get("languages", {}).items():
            if extension.lower() in config.get("extensions", []):
                return lang
        return None

    def get_extension_to_language_mapping(self) -> Dict[str, str]:
        """Get mapping of extensions to languages."""
        mapping = {}
        for lang, config in self.config.get("languages", {}).items():
            for ext in config.get("extensions", []):
                mapping[ext.lower()] = lang
        return mapping

    def is_language_supported(self, language: str) -> bool:
        """Check if language is supported."""
        return language in self.get_supported_languages()


class ConfigManager:
    """Configuration manager for analyzer settings."""

    _instance: Optional["ConfigManager"] = None

    # Default configuration (build_directory should come from main config)
    DEFAULT_CONFIG = {
        "settings": {
            "cache_analyzers": True,
            "max_file_size": 10 * 1024 * 1024,  # 10MB
            "parallel_processing": True,
            "batch_size": 50,
            "timeout_seconds": 30,
        },
        "exclusions": {
            "file_patterns": [
                "__pycache__",
                ".git",
                ".svn",
                ".hg",
                "node_modules",
                ".pytest_cache",
                ".coverage",
                "*.pyc",
                "*.pyo",
                "*.class",
                "*.o",
                "*.obj",
                "*.exe",
                "*.dll",
                "*.so",
                "*.db",
                "*.sqlite",
                "*.sqlite3",
                "*.gz",
                "*.zip",
                "*.tar",
                "*.bz2",
                "*.xz",
                ".DS_Store",
                "Thumbs.db",
                "*.tmp",
                "*.temp",
                "*.log",
                "*.backup",
                "*.bak",
            ],
            "directory_patterns": [
                "__pycache__",
                ".git",
                ".svn",
                ".hg",
                "node_modules",
                ".pytest_cache",
                "venv",
                "env",
                ".venv",
                ".env",
                "build",
                "dist",
                ".idea",
                ".vscode",
                "target",
                ".gradle",
                ".maven",
                "bin",
                "obj",
            ],
            "max_depth": 20,
        },
        "analysis": {
            "extract_functions": True,
            "extract_classes": True,
            "extract_variables": True,
            "extract_imports": True,
            "extract_comments": False,
            "resolve_dependencies": True,
            "create_call_graph": True,
            "detect_patterns": True,
        },
        "output": {
            "format": "json",
            "include_content": False,
            "include_metadata": True,
            "pretty_print": True,
            "output_directory": "./results",
        },
    }

    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager."""
        self.config_path = config_path
        self.config: Dict[str, Any] = self.DEFAULT_CONFIG.copy()
        if config_path and os.path.exists(config_path):
            self._load_configuration()

    @classmethod
    def get_instance(cls, config_path: Optional[str] = None) -> "ConfigManager":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls(config_path)
        return cls._instance

    def _load_configuration(self) -> None:
        """Load configuration from file."""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            self._merge_config(self.config, user_config)
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")

    def _merge_config(self, base: Dict, update: Dict) -> None:
        """Recursively merge configuration dictionaries."""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    # Settings accessors
    def get_build_directory(self) -> str:
        """Get build directory path from main configuration."""
        try:
            # Get from main config system
            from src.config.settings import get_config

            main_config = get_config()

            if hasattr(main_config, "parser") and hasattr(
                main_config.parser, "build_directory"
            ):
                build_dir = main_config.parser.build_directory
                return os.path.abspath(os.path.expanduser(build_dir))
        except Exception as e:
            raise ConfigurationError(
                f"Failed to get build directory from main configuration: {e}"
            )

        raise ConfigurationError("Build directory not found in main configuration")

    def get_cache_analyzers(self) -> bool:
        """Get analyzer caching setting."""
        return self.config["settings"]["cache_analyzers"]

    def get_max_file_size(self) -> int:
        """Get maximum file size for analysis."""
        return self.config["settings"]["max_file_size"]

    def get_file_exclusion_patterns(self) -> Set[str]:
        """Get file exclusion patterns."""
        return set(self.config["exclusions"]["file_patterns"])

    def get_directory_exclusion_patterns(self) -> Set[str]:
        """Get directory exclusion patterns."""
        return set(self.config["exclusions"]["directory_patterns"])

    def get_output_directory(self) -> str:
        """Get output directory path."""
        return os.path.abspath(self.config["output"]["output_directory"])


# Global instances
_global_config: Optional[ConfigManager] = None
_global_parser_config: Optional[ParserConfigLoader] = None


def get_config_manager(config_path: Optional[str] = None) -> ConfigManager:
    """Get global configuration manager instance."""
    global _global_config
    if _global_config is None:
        _global_config = ConfigManager(config_path)
    return _global_config


def get_parser_config_loader(config_path: Optional[str] = None) -> ParserConfigLoader:
    """Get global parser configuration loader instance."""
    global _global_parser_config
    if _global_parser_config is None:
        _global_parser_config = ParserConfigLoader(config_path)
    return _global_parser_config


def reset_config_manager() -> None:
    """Reset global configuration manager (useful for testing)."""
    global _global_config, _global_parser_config
    _global_config = None
    _global_parser_config = None
    ConfigManager._instance = None
    ParserConfigLoader._instance = None
