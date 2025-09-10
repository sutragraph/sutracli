"""AST Parser with Code Block Extraction

This module provides an AST parser that can extract specific code blocks
from parsed AST trees using language-specific extractors and establish
relationships between files based on import statements.
"""

import os
import zlib
from pathlib import Path
from typing import Any, Dict, Optional, Union, cast

from loguru import logger
from tree_sitter import Parser
from tree_sitter_language_pack import SupportedLanguage, get_parser

from utils.file_utils import (
    get_language_from_extension,
    is_text_file,
    read_file_content,
    should_ignore_directory,
    should_ignore_file,
)
from utils.hash_utils import compute_file_hash

from .extractors import Extractor
from .relationship_extractors import RelationshipExtractor


class ASTParser:
    """
    AST parser with code block extraction capabilities.
    """

    def __init__(self):
        """
        Initialize the AST parser.
        """
        self._parser_cache: Dict[str, Parser] = {}
        self._extractor = Extractor()
        self._relationship_extractor = RelationshipExtractor()

    def _get_parser(self, language: SupportedLanguage) -> Optional[Any]:
        """
        Get a tree-sitter parser for the specified language.
        Caches parsers for better performance.

        Args:
            language: Language name

        Returns:
            Tree-sitter parser instance or None if not available
        """
        if language in self._parser_cache:
            return self._parser_cache[language]

        try:
            parser = get_parser(language)
            self._parser_cache[language] = parser
            return parser
        except (ImportError, AttributeError, RuntimeError):
            return None

    def parse_file(self, file_path: Union[str, Path]) -> Optional[Any]:
        """
        Parse a single file and return its AST.

        Args:
            file_path: Path to the file to parse

        Returns:
            AST tree if successful, None if parsing failed or unsupported
        """
        file_path = Path(file_path)

        # Check if file exists
        if not file_path.exists() or not file_path.is_file():
            logger.debug(f"File not found: {file_path}")
            return None

        # Check if file should be ignored
        if should_ignore_file(file_path):
            logger.debug(f"Ignoring file: {file_path}")
            return None

        # Check if file is text
        if not is_text_file(file_path):
            logger.debug(f"Skipping binary file: {file_path}")
            return None

        # Get language from extension
        language = get_language_from_extension(file_path)
        if not language:
            logger.debug(f"Unsupported file type: {file_path}")
            return None

        # Get parser for the language
        parser = self._get_parser(language)
        if not parser:
            logger.debug(f"No parser available for language '{language}': {file_path}")
            return None

        try:
            # Read file content
            content = read_file_content(file_path)
            if content is None:
                logger.debug(f"Failed to read file: {file_path}")
                return None

            # Parse the content
            tree = parser.parse(content.encode("utf-8"))
            logger.debug(f"Successfully parsed: {file_path}")
            return tree

        except (UnicodeEncodeError, AttributeError, RuntimeError) as e:
            logger.debug(f"Error parsing file {file_path}: {e}")
            return None

    def parse_and_extract(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Parse a file and extract code blocks with hierarchical structure.

        Args:
            file_path: Path to the file to parse

        Returns:
            Dictionary containing AST tree and extracted blocks with nested children
        """
        file_path = Path(file_path)

        # Create file ID first (needed for all cases)
        file_id = zlib.crc32(str(file_path).encode()) & 0xFFFFFFFF

        # Parse the file first
        ast_tree = self.parse_file(file_path)
        if not ast_tree:
            # Return a complete object with all required fields for failed parsing
            return {
                "ast": None,
                "blocks": [],
                "language": "unknown",
                "id": file_id,
                "file_path": str(file_path),
                "content": read_file_content(file_path) or "",
                "content_hash": compute_file_hash(file_path) or "",
                "relationships": [],
                "unsupported": True,
                "error": "Failed to parse file",
            }

        # Get language and check if extractor is available
        language = get_language_from_extension(file_path)
        if not language:
            # Return a complete object with all required fields for unsupported files
            return {
                "ast": ast_tree,
                "blocks": [],
                "language": "unknown",
                "id": file_id,
                "file_path": str(file_path),
                "content": read_file_content(file_path) or "",
                "content_hash": compute_file_hash(file_path) or "",
                "relationships": [],
                "unsupported": True,  # Mark as unsupported file type
                "error": f"Unsupported file type: {file_path}",
            }

        # Check if we have an extractor for this language
        supported_languages = self._extractor.get_supported_languages()
        if language not in supported_languages:
            # Language detected but no extractor available - mark as unsupported
            return {
                "ast": ast_tree,
                "blocks": [],
                "language": language,
                "id": file_id,
                "file_path": str(file_path),
                "content": ast_tree.root_node.text,
                "content_hash": compute_file_hash(file_path) or "",
                "relationships": [],
                "unsupported": True,  # Mark as unsupported - no extractor available
                "error": f"No extractor available for language '{language}': {file_path}",
            }

        # Extract blocks
        blocks = self._extractor.extract_from_ast(ast_tree, language, file_id)

        return {
            "ast": ast_tree,
            "blocks": blocks,
            "language": language,
            "id": file_id,
            "file_path": str(file_path),
            "content": ast_tree.root_node.text,
            "content_hash": compute_file_hash(file_path) or "",
            "relationships": [],  # Initialize empty relationships list
            "unsupported": False,  # Mark as supported file type
        }

    def process_relationships(
        self, results: Dict[str, Dict[str, Any]], id_to_path: Dict[int, str]
    ) -> None:
        """
        Extract and process relationships between files based on import statements.

        Args:
            results: Dictionary with file paths as keys and extraction results as values
            id_to_path: Mapping from file IDs to file paths for efficient lookup
        """
        if not results:
            return

        logger.debug("Extracting relationships between files...")
        relationships = self._relationship_extractor.extract_relationships(results)

        # Remove AST trees after relationship extraction to save memory
        # (relationships only need the extracted blocks, not the AST)
        for result in results.values():
            if "ast" in result:
                del result["ast"]

        # Add relationships to the results using efficient ID mapping
        for relationship in relationships:
            source_file_id = relationship.source_id
            target_file_id = relationship.target_id

            # Use efficient ID to path mapping instead of O(n) search
            source_file_path = id_to_path.get(source_file_id)

            if source_file_path:
                # Initialize relationships list if it doesn't exist
                if "relationships" not in results[source_file_path]:
                    results[source_file_path]["relationships"] = []

                # Add the relationship to the source file's results
                results[source_file_path]["relationships"].append(
                    {
                        "source_id": source_file_id,
                        "target_id": target_file_id,
                        "import_content": relationship.import_content,
                    }
                )

    def extract_from_directory(
        self, dir_path: Union[str, Path]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Parse all files in a directory and extract code blocks with hierarchical structure.
        Also extracts relationships between files based on import statements.

        Args:
            dir_path: Path to the directory

        Returns:
            Dictionary with file paths as keys and extraction results as values,
            each result following the same format as parse_and_extract with added relationships
        """
        dir_path = Path(dir_path)
        results = {}

        if not dir_path.exists() or not dir_path.is_dir():
            logger.debug(f"Directory not found: {dir_path}")
            return results

        logger.debug(f"Parsing and extracting from directory: {dir_path}")

        # Create ID to path mapping for efficient relationship lookup
        id_to_path = {}

        for root, dirs, files in os.walk(dir_path):
            root_path = Path(root)

            # Filter out ignored directories
            original_dirs = dirs[:]
            dirs[:] = [d for d in dirs if not should_ignore_directory(root_path / d)]

            ignored_dirs = set(original_dirs) - set(dirs)
            for ignored_dir in ignored_dirs:
                logger.debug(f"Ignoring directory: {root_path / ignored_dir}")

            # Parse and extract from files in current directory
            for file in files:
                file_path = root_path / file

                # Skip ignored files
                if should_ignore_file(file_path):
                    continue

                result = self.parse_and_extract(file_path)
                if result.get("ast") or result.get("error"):
                    file_path_str = str(file_path)
                    results[file_path_str] = result

                    # Build ID to path mapping for efficient lookup
                    file_id = result.get("id")
                    if file_id:
                        id_to_path[file_id] = file_path_str

        # Process relationships between files
        self.process_relationships(results, id_to_path)

        logger.debug(
            f"Parsed and extracted from {len(results)} files in directory: {dir_path}"
        )
        return results
