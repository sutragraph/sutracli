"""
Analyzer Factory for creating language-specific analyzers.

This module provides a simplified factory pattern for creating analyzers
for different programming languages.
"""

import os
import platform
from typing import Dict, Optional, Any

from .utils import ValidationUtils, PathUtils, LanguageUtils


class AnalyzerCreationError(Exception):
    """Exception raised when analyzer creation fails."""

    pass


class AnalyzerFactory:
    """Factory for creating language-specific analyzers."""

    def __init__(self, build_directory: str = "src/parser/build"):
        """Initialize the analyzer factory."""
        from .config import get_config_manager

        config = get_config_manager()
        self.build_directory = config.get_build_directory()
        self._analyzer_cache: Dict[str, Any] = {}

        # Validate build directory
        if not ValidationUtils.is_valid_directory_path(self.build_directory):
            raise AnalyzerCreationError(
                f"Build directory does not exist: {self.build_directory}"
            )

    def create_analyzer(
        self,
        language: str,
        repo_id: str = "default_repo",
        **kwargs,
    ) -> Optional[Any]:
        """Create an analyzer for the specified language."""
        if not LanguageUtils.is_language_supported(language):
            return None

        # Check cache first
        cache_key = f"{language}_{repo_id}"
        if cache_key in self._analyzer_cache:
            return self._analyzer_cache[cache_key]

        try:
            analyzer = self._create_analyzer_instance(language, repo_id, **kwargs)

            # Cache the analyzer
            if analyzer:
                self._analyzer_cache[cache_key] = analyzer

            return analyzer

        except Exception as e:
            raise AnalyzerCreationError(
                f"Failed to create analyzer for {language}: {e}"
            )

    def _create_analyzer_instance(
        self, language: str, repo_id: str, **kwargs
    ) -> Optional[Any]:
        """Create a new analyzer instance."""
        # Get language file path
        language_path = self._get_language_path(language)
        if not language_path:
            return None

        # Import and create YAML analyzer
        from .yaml_analyzer import YamlAnalyzer

        analyzer = YamlAnalyzer(
            repo_id=repo_id,
            language_path=language_path,
            language_name=language,
            **kwargs,
        )

        return analyzer

    def _get_system_info(self) -> tuple[str, str]:
        """Get system name and appropriate file extension for parser libraries."""
        system = platform.system()
        if system == "Darwin":
            return "Darwin", ".dylib"
        elif system == "Linux":
            return "Linux", ".so"
        else:
            # Default to Linux for other systems
            return "Linux", ".so"

    def _get_language_path(self, language: str) -> Optional[str]:
        """Get the path to the language parser library."""
        system_name, file_extension = self._get_system_info()
        language_file = f"{language}{file_extension}"

        # Build path with system-specific subdirectory
        system_build_dir = PathUtils.join_paths(self.build_directory, system_name)
        language_path = PathUtils.join_paths(system_build_dir, language_file)

        if not ValidationUtils.is_valid_file_path(language_path):
            return None

        return language_path

    def create_analyzer_for_file(
        self,
        file_path: str,
        repo_id: str = "default_repo",
        node_id_generator=None,
        **kwargs,
    ) -> Optional[Any]:
        """Create analyzer based on file extension."""
        if not ValidationUtils.is_valid_file_path(file_path):
            return None

        language = LanguageUtils.get_language_from_file_path(file_path)

        # If language is supported, create the specific analyzer
        if language and self.is_language_supported(language):
            return self.create_analyzer(
                language, repo_id, node_id_generator=node_id_generator, **kwargs
            )

        # For unsupported files, create an unsupported analyzer
        return self.create_unsupported_analyzer(
            repo_id, node_id_generator=node_id_generator, **kwargs
        )

    def create_unsupported_analyzer(
        self, repo_id: str = "default_repo", node_id_generator=None, **kwargs
    ):
        """Create an analyzer for unsupported file types."""
        from .yaml_analyzer import UnsupportedFileAnalyzer

        cache_key = f"unsupported_{repo_id}"
        if cache_key in self._analyzer_cache:
            return self._analyzer_cache[cache_key]

        analyzer = UnsupportedFileAnalyzer(repo_id, node_id_generator=node_id_generator)
        self._analyzer_cache[cache_key] = analyzer
        return analyzer

    def is_language_supported(self, language: str) -> bool:
        """
        Check if language is supported.

        A language is considered supported if:
        1. It's in the parsers.json configuration
        2. The language parser library exists
        3. A YAML configuration file exists for the language
        """
        # Check if language is in parsers.json and has a parser library
        if not (
            LanguageUtils.is_language_supported(language)
            and self._get_language_path(language) is not None
        ):
            return False

        # Check if YAML configuration file exists
        yaml_config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "yaml_configs",
            f"{language}.yaml",
        )
        return os.path.isfile(yaml_config_path)

    def get_supported_languages(self) -> set:
        """Get set of supported languages."""
        from .config import get_parser_config_loader

        parser_config = get_parser_config_loader()
        return parser_config.get_supported_languages()


# Global factory instance
_global_factory: Optional[AnalyzerFactory] = None


def get_analyzer_factory() -> AnalyzerFactory:
    """Get global analyzer factory instance."""
    global _global_factory
    if _global_factory is None:
        _global_factory = AnalyzerFactory()
    return _global_factory


def create_analyzer_for_language(
    language: str,
    repo_id: str = "default_repo",
    **kwargs,
) -> Optional[Any]:
    """Convenience function to create analyzer for language."""
    factory = get_analyzer_factory()
    return factory.create_analyzer(language, repo_id, **kwargs)


def create_analyzer_for_file(
    file_path: str,
    repo_id: str = "default_repo",
    **kwargs,
) -> Optional[Any]:
    """Convenience function to create analyzer for file."""
    factory = get_analyzer_factory()
    return factory.create_analyzer_for_file(file_path, repo_id, **kwargs)
