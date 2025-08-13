"""
AST Extractors Package

This package provides extractors for different code constructs from AST trees.
Supports TypeScript and Python initially, with extensible design for other languages.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional, Set, Callable, Dict
from tree_sitter_language_pack import SupportedLanguage
from utils.incremental_hash import IncrementalHashGenerator
from models.schema import CodeBlock, BlockType


class BaseExtractor(ABC):
    """Base class for language-specific AST extractors."""

    def __init__(self, language: SupportedLanguage, file_id: int = 0):
        """Initialize the base extractor.

        Args:
            language: Programming language name
            file_id: Numeric ID of the file being processed
        """
        self.language = language
        self._hash_generator = IncrementalHashGenerator(file_id)

    def _get_node_text(self, node: Any) -> str:
        """Get text content of a node."""
        if hasattr(node, "text"):
            text = node.text
            if isinstance(text, bytes):
                return text.decode("utf-8")
            return str(text)
        return ""

    def _get_node_position(self, node: Any) -> tuple:
        """Get position information of a node.

        Returns:
            Tuple of (start_line, end_line, start_col, end_col)
        """
        if hasattr(node, "start_point") and hasattr(node, "end_point"):
            start_line = node.start_point[0] + 1  # Convert to 1-based
            end_line = node.end_point[0] + 1  # Convert to 1-based
            start_col = node.start_point[1]
            end_col = node.end_point[1]
            return start_line, end_line, start_col, end_col
        return 0, 0, 0, 0

    def _generic_traversal(
        self,
        root_node: Any,
        target_types: Set[str],
        processor: Callable[[Any], Optional[CodeBlock]],
    ) -> List[CodeBlock]:
        """Generic traversal method for extracting blocks of specific types."""
        blocks = []

        def traverse(node):
            if node.type in target_types:
                block = processor(node)
                if block:
                    blocks.append(block)

            for child in node.children:
                traverse(child)

        traverse(root_node)
        return blocks

    def _create_block_with_nested(
        self,
        node: Any,
        block_type: BlockType,
        names: List[str],
        nested_types: Dict[str, BlockType] = {},
    ) -> CodeBlock:
        """Create a code block and extract nested elements."""
        block = self._create_code_block(node, block_type, names)

        if nested_types:
            nested_blocks = []
            for node_type, nested_block_type in nested_types.items():
                nested_blocks.extend(
                    self._extract_nested_elements_by_type(
                        node, {node_type}, nested_block_type
                    )
                )
            block.children = nested_blocks

        return block

    def _extract_nested_elements_by_type(
        self, parent_node: Any, target_types: Set[str], block_type: BlockType
    ) -> List[CodeBlock]:
        """Generic method to extract nested elements of specific types."""

        def processor(node):
            names = self._extract_names_from_node(node)
            if names:
                return self._create_code_block(node, block_type, names)
            return None

        return self._generic_traversal(parent_node, target_types, processor)

    def _count_function_lines(self, node: Any) -> int:
        """Count the number of lines in a function node.

        Args:
            node: AST node representing a function

        Returns:
            Number of lines in the function
        """
        start_line, end_line, _, _ = self._get_node_position(node)
        return end_line - start_line + 1

    def _extract_nested_functions_only(
        self, parent_node: Any, function_types: set
    ) -> List[CodeBlock]:
        """Extract only nested functions from a parent function node.

        This method is specifically for extracting nested functions when the parent
        function is larger than 300 lines.

        Args:
            parent_node: Parent function AST node
            function_types: Set of function node types for the language

        Returns:
            List of nested function CodeBlocks
        """

        def processor(node):
            # Skip the parent node itself
            if node == parent_node:
                return None

            # Extract the actual function name from the node
            name_node = node.child_by_field_name("name")
            if name_node:
                function_name = self._get_node_text(name_node)
                return self._create_code_block(
                    node, BlockType.FUNCTION, [function_name]
                )
            else:
                # Fallback for anonymous functions
                return self._create_code_block(node, BlockType.FUNCTION, ["anonymous"])

        return self._generic_traversal(parent_node, function_types, processor)

    @abstractmethod
    def _replace_nested_functions_with_references(
        self, original_content: str, nested_functions: List[CodeBlock]
    ) -> str:
        """Replace nested function content with block references.

        Args:
            original_content: Original function content
            nested_functions: List of nested function blocks to replace

        Returns:
            Modified content with nested functions replaced by references
        """
        pass

    def _create_function_block_with_nested_extraction(
        self, node: Any, block_type: BlockType, names: List[str], function_types: set
    ) -> CodeBlock:
        """Create a function code block with nested function extraction if needed.

        This method checks if the function is larger than 300 lines and extracts
        nested functions if so, replacing them with references.

        Args:
            node: Function AST node
            block_type: Should be BlockType.FUNCTION
            names: List of function names
            function_types: Set of function node types for the language

        Returns:
            CodeBlock with nested functions extracted if applicable
        """
        # Count lines in the function
        line_count = self._count_function_lines(node)

        if line_count > 300 and block_type == BlockType.FUNCTION:
            # Extract nested functions
            nested_functions = self._extract_nested_functions_only(node, function_types)

            if nested_functions:
                # Create the main block
                start_line, end_line, start_col, end_col = self._get_node_position(node)
                original_content = self._get_node_text(node)

                # Replace nested functions with references
                modified_content = self._replace_nested_functions_with_references(
                    original_content, nested_functions
                )

                # Use first name as primary name, or "anonymous" if no names
                primary_name = names[0] if names else "anonymous"

                # Create the main block with modified content
                main_block = CodeBlock(
                    type=block_type,
                    name=primary_name,
                    content=modified_content,
                    start_line=start_line,
                    end_line=end_line,
                    start_col=start_col,
                    end_col=end_col,
                    id=self._hash_generator.next_id(),
                    children=nested_functions,
                )

                return main_block

        # Default behavior for functions <= 300 lines or non-function blocks
        return self._create_code_block(node, block_type, names)

    @abstractmethod
    def _extract_names_from_node(self, node: Any) -> List[str]:
        """Extract all identifier names from a node (handles various patterns).

        This method should be implemented by each language-specific extractor
        to handle language-specific naming patterns.

        Args:
            node: AST node

        Returns:
            List of identifier names found in the node
        """
        pass

    def _create_code_block(
        self, node: Any, block_type: BlockType, names: List[str]
    ) -> CodeBlock:
        """Create a CodeBlock from a node, automatically extracting position and content.

        Args:
            node: AST node
            block_type: Type of code block
            names: List of identifier names (first will be used as primary name)

        Returns:
            CodeBlock instance
        """
        start_line, end_line, start_col, end_col = self._get_node_position(node)
        content = self._get_node_text(node)

        # Use first name as primary name, or "anonymous" if no names
        primary_name = names[0] if names else "anonymous"

        return CodeBlock(
            type=block_type,
            name=primary_name,
            content=content,
            start_line=start_line,
            end_line=end_line,
            start_col=start_col,
            end_col=end_col,
            id=self._hash_generator.next_id(),
        )

    @abstractmethod
    def extract_imports(self, root_node: Any) -> List[CodeBlock]:
        """Extract import statements."""
        pass

    @abstractmethod
    def extract_exports(self, root_node: Any) -> List[CodeBlock]:
        """Extract export statements."""
        pass

    @abstractmethod
    def extract_functions(self, root_node: Any) -> List[CodeBlock]:
        """Extract function declarations."""
        pass

    @abstractmethod
    def extract_classes(self, root_node: Any) -> List[CodeBlock]:
        """Extract class declarations."""
        pass

    @abstractmethod
    def extract_variables(self, root_node: Any) -> List[CodeBlock]:
        """Extract variable declarations."""
        pass

    def extract_interfaces(self, root_node: Any) -> List[CodeBlock]:
        """Extract interface declarations. Default implementation returns empty list."""
        return []

    def extract_enums(self, root_node: Any) -> List[CodeBlock]:
        """Extract enum declarations. Default implementation returns empty list."""
        return []

    @abstractmethod
    def extract_all(self, root_node: Any) -> List[CodeBlock]:
        """Extract all supported code blocks.

        This method should extract all supported block types for the language
        and return all extracted blocks.

        Returns:
            List of all extracted CodeBlock objects
        """
        pass


class Extractor:
    """Main extractor that uses language-specific extractors."""

    def __init__(self):
        """Initialize the extractor."""
        self._extractors = {}
        self._setup_extractors()

    def _setup_extractors(self):
        """Setup language-specific extractors."""
        from indexer.extractors.typescript_extractor import TypeScriptExtractor
        from indexer.extractors.python_extractor import PythonExtractor

        self.register_extractor("typescript", TypeScriptExtractor)
        self.register_extractor("javascript", TypeScriptExtractor)
        self.register_extractor("python", PythonExtractor)

    def register_extractor(
        self, language: SupportedLanguage, extractor_class: type
    ) -> None:
        """Register an extractor for a specific language.

        Args:
            language: Programming language name
            extractor_class: Extractor class that extends BaseExtractor
        """
        self._extractors[language] = extractor_class

    def extract_from_ast(
        self, ast_tree: Any, language: SupportedLanguage, file_id: int = 0
    ) -> List[CodeBlock]:
        """Extract code blocks from an AST tree using language-specific extractor.

        Args:
            ast_tree: The AST tree to extract from
            language: Programming language
            file_id: Numeric ID of the file being processed

        Returns:
            List of extracted CodeBlock objects
        """
        if language not in self._extractors:
            return []

        extractor = self._extractors[language](language, file_id)
        return extractor.extract_all(ast_tree.root_node)

    def get_blocks_by_type(
        self, blocks: List[CodeBlock], block_type: BlockType
    ) -> List[CodeBlock]:
        """Filter blocks by type.

        Args:
            blocks: List of code blocks
            block_type: Type to filter by

        Returns:
            List of blocks matching the specified type
        """
        return [block for block in blocks if block.type == block_type]

    def get_supported_languages(self) -> List[str]:
        """Get languages that support code block extraction.

        Returns:
            List of supported language names
        """
        return list(self._extractors.keys())


__all__ = ["BlockType", "CodeBlock", "BaseExtractor", "Extractor"]
