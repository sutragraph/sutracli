"""
Relationship Extractors Package

This package provides extractors for relationships between files based on import statements.
Supports TypeScript and Python initially, with extensible design for other languages.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from tree_sitter_language_pack import SupportedLanguage
from models.schema import Relationship


class BaseRelationshipExtractor(ABC):
    """Base class for language-specific relationship extractors."""

    def __init__(self):
        """Initialize the relationship extractor."""
        # Note: Auto-registration removed - extractors are now registered explicitly
        pass

    def _safe_text_extract(self, node) -> str:
        """Safely extract text from a tree-sitter node, handling both bytes and string cases."""
        try:
            text = node.text
            if isinstance(text, bytes):
                return text.decode("utf-8")
            return str(text)
        except (UnicodeDecodeError, AttributeError):
            return ""

    @abstractmethod
    def extract_relationships(
        self, extraction_results: Dict[str, Dict[str, Any]]
    ) -> List[Relationship]:
        """Extract relationships between files based on import statements."""
        pass


class RelationshipExtractor:
    """Main extractor that uses language-specific relationship extractors."""

    def __init__(self):
        """Initialize the extractor."""
        self._extractors = {}
        self._setup_extractors()

    def _setup_extractors(self):
        """Setup language-specific extractors."""
        from .python_extractor import PythonRelationshipExtractor
        from .typescript_extractor import TypeScriptRelationshipExtractor

        self.register_extractor("python", PythonRelationshipExtractor)
        self.register_extractor("typescript", TypeScriptRelationshipExtractor)
        self.register_extractor("javascript", TypeScriptRelationshipExtractor)

    def register_extractor(
        self, language: SupportedLanguage, extractor_class: type
    ) -> None:
        """Register an extractor for a specific language."""
        self._extractors[language] = extractor_class

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        return list(self._extractors.keys())

    def extract_relationships(
        self, extraction_results: Dict[str, Dict[str, Any]]
    ) -> List[Relationship]:
        """Extract relationships between files based on import statements."""
        relationships = []

        # Group files by language
        files_by_language = {}
        for file_path, result in extraction_results.items():
            language = result.get("language")
            if language:
                if language not in files_by_language:
                    files_by_language[language] = {}
                files_by_language[language][file_path] = result

        # Process each language with its specific extractor
        for language, language_results in files_by_language.items():
            if language in self._extractors:
                extractor = self._extractors[language]()
                language_relationships = extractor.extract_relationships(
                    language_results
                )
                relationships.extend(language_relationships)

        return relationships


__all__ = [
    "Relationship",
    "BaseRelationshipExtractor",
    "RelationshipExtractor",
]
