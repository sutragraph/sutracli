"""
Enhanced AST Parser with Code Block Extraction

This module provides an enhanced AST parser that can extract specific code blocks
from parsed AST trees using language-specific extractors.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from tree_sitter_language_pack import get_parser

from utils.file_utils import (
    get_language_from_extension,
    should_ignore_file,
    should_ignore_directory,
    is_text_file,
    read_file_content,
)
from extractors import builder, BlockType, CodeBlock
from extractors.typescript_extractor import TypeScriptExtractor
from extractors.python_extractor import PythonExtractor


class EnhancedASTParser:
    """
    Enhanced AST parser with code block extraction capabilities.
    """

    def __init__(self):
        """Initialize the enhanced AST parser."""
        self._parser_cache: Dict[str, Any] = {}
        self._setup_extractors()

    def _setup_extractors(self):
        """Setup language-specific extractors."""
        builder.register_extractor("typescript", TypeScriptExtractor)
        builder.register_extractor("python", PythonExtractor)

    def _get_parser(self, language: str) -> Optional[Any]:
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
        except Exception as e:
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

    def parse_directory(self, dir_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Parse all supported files in a directory recursively.

        Args:
            dir_path: Path to the directory to parse

        Returns:
            Dictionary with file paths as keys and AST trees as values
        """
        dir_path = Path(dir_path)
        results = {}

        if not dir_path.exists() or not dir_path.is_dir():
            print(f"Directory not found: {dir_path}")
            return results

        print(f"Parsing directory: {dir_path}")

        for root, dirs, files in os.walk(dir_path):
            root_path = Path(root)

            # Filter out ignored directories
            original_dirs = dirs[:]
            dirs[:] = [d for d in dirs if not should_ignore_directory(root_path / d)]

            ignored_dirs = set(original_dirs) - set(dirs)
            for ignored_dir in ignored_dirs:
                print(f"Ignoring directory: {root_path / ignored_dir}")

            # Parse files in current directory
            for file in files:
                file_path = root_path / file

                ast_tree = self.parse_file(file_path)
                if ast_tree:
                    results[str(file_path)] = ast_tree

        print(f"Parsed {len(results)} files from directory: {dir_path}")
        return results

    def parse_and_extract(self, file_path: Union[str, Path],
                         block_types: Optional[List[BlockType]] = None) -> Dict[str, Any]:
        """
        Parse a file and extract code blocks.

        Args:
            file_path: Path to the file to parse
            block_types: List of block types to extract (None for all)

        Returns:
            Dictionary containing AST tree and extracted blocks
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
                "error": f"Unsupported file type: {file_path}"
            }

        extractor = builder.build(language)
        if not extractor:
            return {
                "ast": ast_tree,
                "blocks": [],
                "error": f"No extractor available for language: {language}"
            }

        # Extract blocks
        if block_types:
            blocks = self._extract_specific_blocks(extractor, ast_tree.root_node, block_types)
        else:
            blocks = extractor.extract_all(ast_tree.root_node)

        return {
            "ast": ast_tree,
            "blocks": blocks,
            "language": language,
            "file_path": str(file_path)
        }

    def extract_from_directory(self, dir_path: Union[str, Path],
                             block_types: Optional[List[BlockType]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Parse all files in a directory and extract code blocks.

        Args:
            dir_path: Path to the directory
            block_types: List of block types to extract (None for all)

        Returns:
            Dictionary with file paths as keys and extraction results as values
        """
        results = {}
        parsed_files = self.parse_directory(dir_path)

        for file_path, ast_tree in parsed_files.items():
            language = get_language_from_extension(Path(file_path))
            if not language:
                results[file_path] = {
                    "ast": ast_tree,
                    "blocks": [],
                    "error": f"Unsupported file type: {file_path}"
                }
                continue

            extractor = builder.build(language)
            if not extractor:
                results[file_path] = {
                    "ast": ast_tree,
                    "blocks": [],
                    "error": f"No extractor for language: {language}"
                }
                continue

            if block_types:
                blocks = self._extract_specific_blocks(extractor, ast_tree.root_node, block_types)
            else:
                blocks = extractor.extract_all(ast_tree.root_node)

            results[file_path] = {
                "ast": ast_tree,
                "blocks": blocks,
                "language": language,
                "file_path": file_path
            }

        return results

    def extract_functions(self, file_path: Union[str, Path]) -> List[CodeBlock]:
        """Extract only function declarations from a file."""
        result = self.parse_and_extract(file_path, [BlockType.FUNCTION])
        return result.get("blocks", [])

    def extract_classes(self, file_path: Union[str, Path]) -> List[CodeBlock]:
        """Extract only class declarations from a file."""
        result = self.parse_and_extract(file_path, [BlockType.CLASS])
        return result.get("blocks", [])

    def extract_imports(self, file_path: Union[str, Path]) -> List[CodeBlock]:
        """Extract only import statements from a file."""
        result = self.parse_and_extract(file_path, [BlockType.IMPORT])
        return result.get("blocks", [])

    def get_summary(self, file_path: Union[str, Path]) -> Dict[str, int]:
        """Get a summary of code blocks in a file."""
        result = self.parse_and_extract(file_path)
        blocks = result.get("blocks", [])

        summary = {block_type.value: 0 for block_type in BlockType}
        for block in blocks:
            summary[block.type.value] += 1

        return summary



    def get_blocks_by_type(self, blocks: List[CodeBlock], block_type: BlockType) -> List[CodeBlock]:
        """Filter blocks by type."""
        return [block for block in blocks if block.type == block_type]



    def get_supported_languages(self) -> List[str]:
        """
        Get a list of supported programming languages.

        Returns:
            List of supported language names
        """
        from utils.supported_languages import SUPPORTED_LANGUAGES
        return list(SUPPORTED_LANGUAGES.keys())

    def get_supported_extraction_languages(self) -> List[str]:
        """Get languages that support code block extraction."""
        return builder.get_supported_languages()

    def get_file_count(self, path: Union[str, Path]) -> int:
        """
        Count the number of parseable files in a path without parsing them.

        Args:
            path: Path to file or directory

        Returns:
            Number of files that would be parsed
        """
        path = Path(path)
        count = 0

        if path.is_file():
            if not should_ignore_file(path) and get_language_from_extension(path):
                count = 1
        elif path.is_dir():
            for root, dirs, files in os.walk(path):
                root_path = Path(root)

                # Filter out ignored directories
                dirs[:] = [
                    d for d in dirs if not should_ignore_directory(root_path / d)
                ]

                for file in files:
                    file_path = root_path / file
                    if not should_ignore_file(
                        file_path
                    ) and get_language_from_extension(file_path):
                        count += 1

        return count

    def clear_cache(self) -> None:
        """
        Clear the parser cache to free memory.
        """
        self._parser_cache.clear()
        print("Parser cache cleared")

    def get_available_languages(self) -> List[str]:
        """
        Get a list of actually available languages that can be used for parsing.
        This method tests which languages are actually available in the current
        installation of tree-sitter-language-pack.

        Returns:
            List of available language names
        """
        available_languages = []
        test_languages = self.get_supported_languages()

        for language in test_languages:
            try:
                get_parser(language)
                available_languages.append(language)
            except Exception:
                # Language not available in current installation
                continue

        return available_languages

    def is_language_supported(self, language: str) -> bool:
        """
        Check if a specific language is supported by the current installation.

        Args:
            language: Language name to check

        Returns:
            True if language is supported, False otherwise
        """
        try:
            get_parser(language)
            return True
        except Exception:
            return False

    def _extract_specific_blocks(self, extractor: Any, root_node: Any,
                               block_types: List[BlockType]) -> List[CodeBlock]:
        """Extract specific types of blocks."""
        blocks = []

        for block_type in block_types:
            if block_type == BlockType.ENUM:
                blocks.extend(extractor.extract_enums(root_node))
            elif block_type == BlockType.VARIABLE:
                blocks.extend(extractor.extract_variables(root_node))
            elif block_type == BlockType.FUNCTION:
                blocks.extend(extractor.extract_functions(root_node))
            elif block_type == BlockType.CLASS:
                blocks.extend(extractor.extract_classes(root_node))
            elif block_type == BlockType.INTERFACE:
                blocks.extend(extractor.extract_interfaces(root_node))
            elif block_type == BlockType.IMPORT:
                blocks.extend(extractor.extract_imports(root_node))
            elif block_type == BlockType.EXPORT:
                blocks.extend(extractor.extract_exports(root_node))

        return blocks
