"""AST Parser with Code Block Extraction

This module provides an AST parser that can extract specific code blocks
from parsed AST trees using language-specific extractors and establish
relationships between files based on import statements.
"""

import os
import json
import hashlib
import zlib
from pathlib import Path
from typing import Dict, Optional, Union, Any, cast
from datetime import datetime
from tree_sitter import Parser
from tree_sitter_language_pack import get_parser, SupportedLanguage

from utils.file_utils import (
    get_language_from_extension,
    should_ignore_file,
    should_ignore_directory,
    is_text_file,
    read_file_content,
)
from extractors import Extractor
from relationship_extractors import RelationshipExtractor


class ASTParser:
    """
    AST parser with code block extraction capabilities.
    """

    def __init__(self, symbol_extractor=None):
        """
        Initialize the AST parser.

        Args:
            symbol_extractor: Optional symbol extractor for enhanced code block analysis.
                            If provided, will be used by code block extractors to identify
                            symbols within extracted blocks.
        """
        self._parser_cache: Dict[str, Parser] = {}
        self._extractor = Extractor(symbol_extractor=symbol_extractor)
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
        except Exception:
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
            print(f"File not found: {file_path}")
            return None

        # Check if file should be ignored
        if should_ignore_file(file_path):
            print(f"Ignoring file: {file_path}")
            return None

        # Check if file is text
        if not is_text_file(file_path):
            print(f"Skipping binary file: {file_path}")
            return None

        # Get language from extension
        language = get_language_from_extension(file_path)
        if not language:
            print(f"Unsupported file type: {file_path}")
            return None

        # Get parser for the language
        parser = self._get_parser(language)
        if not parser:
            print(f"No parser available for language '{language}': {file_path}")
            return None

        try:
            # Read file content
            content = read_file_content(file_path)
            if content is None:
                print(f"Failed to read file: {file_path}")
                return None

            # Parse the content
            tree = parser.parse(content.encode("utf-8"))
            print(f"Successfully parsed: {file_path}")
            return tree

        except Exception as e:
            print(f"Error parsing file {file_path}: {e}")
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

        # Parse the file first
        ast_tree = self.parse_file(file_path)
        if not ast_tree:
            return {"ast": None, "blocks": [], "error": "Failed to parse file"}

        # Get language and create extractor
        language = get_language_from_extension(file_path)
        if not language:
            return {
                "ast": ast_tree,
                "blocks": [],
                "error": f"Unsupported file type: {file_path}",
            }

        # Create file ID and extract blocks
        file_id = zlib.crc32(str(file_path).encode()) & 0xFFFFFFFF
        blocks = self._extractor.extract_from_ast(ast_tree, language, file_id)

        return {
            "ast": ast_tree,
            "blocks": blocks,
            "language": language,
            "id": file_id,
            "file_path": str(file_path),
            "content": ast_tree.root_node.text,
            "content_hash": hashlib.sha256(ast_tree.root_node.text).hexdigest(),
        }

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
            print(f"Directory not found: {dir_path}")
            return results

        print(f"Parsing and extracting from directory: {dir_path}")

        # Create ID to path mapping for efficient relationship lookup
        id_to_path = {}

        for root, dirs, files in os.walk(dir_path):
            root_path = Path(root)

            # Filter out ignored directories
            original_dirs = dirs[:]
            dirs[:] = [d for d in dirs if not should_ignore_directory(root_path / d)]

            ignored_dirs = set(original_dirs) - set(dirs)
            for ignored_dir in ignored_dirs:
                print(f"Ignoring directory: {root_path / ignored_dir}")

            # Parse and extract from files in current directory
            for file in files:
                file_path = root_path / file
                result = self.parse_and_extract(file_path)
                if result.get("ast") or result.get("error"):
                    file_path_str = str(file_path)
                    results[file_path_str] = result

                    # Build ID to path mapping for efficient lookup
                    file_id = result.get("id")
                    if file_id:
                        id_to_path[file_id] = file_path_str

        # Extract relationships between files based on import statements
        if results:
            print("Extracting relationships between files...")
            relationships = self._relationship_extractor.extract_relationships(results)

            # Remove AST trees after relationship extraction to save memory
            # (relationships only need the extracted blocks, not the AST)
            for result in results.values():
                if "ast" in result:
                    del result["ast"]

            # Add relationships to the results using efficient ID mapping
            for relationship in relationships:
                source_file_id = relationship.source_file
                target_file_id = relationship.target_file

                # Use efficient ID to path mapping instead of O(n) search
                source_file_path = id_to_path.get(source_file_id)

                if source_file_path:
                    # Initialize relationships list if it doesn't exist
                    if "relationships" not in results[source_file_path]:
                        results[source_file_path]["relationships"] = []

                    # Add the relationship to the source file's results
                    results[source_file_path]["relationships"].append(
                        {
                            "source_file": source_file_id,
                            "target_file": target_file_id,
                            "import_content": relationship.import_content,
                            "symbols": relationship.symbols,
                        }
                    )

        print(
            f"Parsed and extracted from {len(results)} files in directory: {dir_path}"
        )
        return results

    def _make_json_serializable(self, obj: Any) -> Any:
        """
        Convert complex objects to JSON-serializable format.

        Args:
            obj: Object to convert

        Returns:
            JSON-serializable version of the object
        """
        from enum import Enum

        if isinstance(obj, Enum):
            # Handle Enum objects by returning their value
            return obj.value
        elif hasattr(obj, "__dict__"):
            # Handle custom objects with __dict__
            result = {}
            for key, value in obj.__dict__.items():
                if not key.startswith("_"):  # Skip private attributes
                    result[key] = self._make_json_serializable(value)
            return result
        elif isinstance(obj, dict):
            return {
                key: self._make_json_serializable(value) for key, value in obj.items()
            }
        elif isinstance(obj, (list, tuple)):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, bytes):
            # Convert bytes to string representation
            try:
                return obj.decode("utf-8")
            except UnicodeDecodeError:
                return f"<bytes: {len(obj)} bytes>"
        elif isinstance(obj, Path):
            return str(obj)
        elif hasattr(obj, "__str__") and not isinstance(
            obj, (str, int, float, bool, type(None))
        ):
            # Handle other complex objects by converting to string
            return str(obj)
        else:
            # Return as-is for basic types (str, int, float, bool, None)
            return obj

    def export_to_json(
        self,
        extraction_results: Dict[str, Dict[str, Any]],
        output_file: Union[str, Path],
        indent: int = 2,
    ) -> bool:
        """
        Export extraction results to a JSON file.

        Args:
            extraction_results: Results from extract_from_directory method
            output_file: Path to the output JSON file
            indent: JSON indentation level (default: 2)

        Returns:
            True if export was successful, False otherwise
        """
        try:
            output_path = Path(output_file)

            # Create output directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert to JSON-serializable format
            serializable_data = self._make_json_serializable(extraction_results)

            # Add metadata
            export_data = {
                "metadata": {
                    "export_timestamp": datetime.now().isoformat(),
                    "total_files": len(extraction_results),
                    "extractor_version": "1.0.0",
                },
                "files": serializable_data,
            }

            # Write to JSON file
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=indent, ensure_ascii=False)

            print(f"Successfully exported extraction results to: {output_path}")
            print(f"Total files exported: {len(extraction_results)}")
            return True

        except Exception as e:
            print(f"Error exporting to JSON: {e}")
            return False

    def extract_and_export_directory(
        self, dir_path: Union[str, Path], output_file: Union[str, Path], indent: int = 2
    ) -> bool:
        """
        Extract from directory and directly export to JSON file.

        Args:
            dir_path: Path to the directory to extract from
            output_file: Path to the output JSON file
            indent: JSON indentation level (default: 2)

        Returns:
            True if extraction and export were successful, False otherwise
        """
        print(f"Extracting from directory: {dir_path}")
        results = self.extract_from_directory(dir_path)

        if not results:
            print("No results to export")
            return False

        return self.export_to_json(results, output_file, indent)
