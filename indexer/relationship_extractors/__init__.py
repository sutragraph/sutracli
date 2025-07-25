"""
Relationship Extractors Package

This package provides extractors for relationships between files based on import statements.
Supports TypeScript and Python initially, with extensible design for other languages.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class Relationship:
    """Represents a relationship between two files."""
    source_file: str  # ID of the source file
    target_file: str  # ID of the target file
    import_content: str  # The original import statement
    symbols: List[str]  # Symbols imported
    type: str = "import"  # Type of relationship (default: import)


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
    def extract_relationships(self, extraction_results: Dict[str, Dict[str, Any]]) -> List[Relationship]:
        """Extract relationships between files based on import statements."""
        pass


class RelationshipExtractorBuilder:
    """Builder class for creating language-specific relationship extractors."""

    def __init__(self):
        self._extractors = {}

    def register_extractor(self, language: str, extractor_class: type) -> 'RelationshipExtractorBuilder':
        """Register an extractor for a specific language."""
        self._extractors[language] = extractor_class
        return self

    def build(self, language: str) -> Optional[BaseRelationshipExtractor]:
        """Build an extractor for the specified language."""
        if language not in self._extractors:
            return None
        return self._extractors[language]()

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        return list(self._extractors.keys())


# Note: Global builder pattern removed - now using instance-based pattern


class RelationshipExtractor:
    """Main extractor that uses language-specific relationship extractors."""

    def __init__(self):
        """Initialize the extractor."""
        self.builder = RelationshipExtractorBuilder()
        self._setup_extractors()

    def _setup_extractors(self):
        """Setup language-specific extractors."""
        from .python_extractor import PythonRelationshipExtractor
        from .typescript_extractor import TypeScriptRelationshipExtractor

        self.builder.register_extractor("python", PythonRelationshipExtractor)
        self.builder.register_extractor("typescript", TypeScriptRelationshipExtractor)

    def extract_relationships(self, extraction_results: Dict[str, Dict[str, Any]]) -> List[Relationship]:
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
            extractor = self.builder.build(language)
            if extractor:
                language_relationships = extractor.extract_relationships(language_results)
                relationships.extend(language_relationships)

        return relationships

    def register_extractor(self, language: str, extractor: BaseRelationshipExtractor) -> None:
        """Register a custom extractor instance.

        This allows adding or replacing extractors after initialization.

        Args:
            language: Language name (e.g., "python", "typescript")
            extractor: Extractor instance
        """
        # Register the extractor class with the builder
        self.builder.register_extractor(language, extractor.__class__)
        # Replace the current instance in the builder's cache
        self.builder._extractors[language] = lambda: extractor

    def get_supported_languages(self) -> List[str]:
        """Get languages that support relationship extraction."""
        return self.builder.get_supported_languages()


__all__ = [
    'Relationship',
    'BaseRelationshipExtractor',
    'RelationshipExtractor',
    'RelationshipExtractorBuilder'
]
