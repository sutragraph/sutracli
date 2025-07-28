"""
AST Extractors Package

This package provides extractors for different code constructs from AST trees.
Supports TypeScript and Python initially, with extensible design for other languages.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class BlockType(Enum):
    """Types of code blocks that can be extracted."""

    ENUM = "enum"
    VARIABLE = "variable"
    FUNCTION = "function"
    CLASS = "class"
    INTERFACE = "interface"
    IMPORT = "import"
    EXPORT = "export"


@dataclass
class CodeBlock:
    """Represents a code block extracted from AST."""

    type: BlockType
    name: str
    content: str
    symbols: List[str]
    start_line: int
    end_line: int
    start_col: int
    end_col: int
    children: List["CodeBlock"] = field(default_factory=list)


class BaseExtractor(ABC):
    """Base class for language-specific AST extractors."""

    def __init__(self, language: str, symbol_extractor=None):
        """Initialize the base extractor.

        Args:
            language: Programming language name
            symbol_extractor: Optional symbol extractor for enhanced analysis
        """
        self.language = language
        self.symbol_extractor = symbol_extractor
        self._all_symbols: List[Any] = []
        self._source_content: str = ""

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
            end_line = node.end_point[0] + 1      # Convert to 1-based
            start_col = node.start_point[1]
            end_col = node.end_point[1]
            return start_line, end_line, start_col, end_col
        return 0, 0, 0, 0

    def _extract_all_symbols(self, root_node: Any) -> None:
        """Extract all symbols from the entire file and store them."""
        self._all_symbols = []
        if not self.symbol_extractor:
            return

        try:
            # Get the full source content from the root node
            self._source_content = self._get_node_text(root_node)

            # Extract all symbols from the root node
            self._all_symbols = self.symbol_extractor.extract_symbols(
                root_node, self._source_content, self.language
            )
        except Exception as e:
            # Log error but don't fail completely
            print(f"Warning: Error extracting symbols: {e}")
            self._all_symbols = []

    def _get_symbols_for_block(
        self, start_line: int, end_line: int, start_col: int, end_col: int
    ) -> List[str]:
        """Find symbols that fall within the given block boundaries."""
        if not self._all_symbols:
            return []

        matching_symbols = set()  # Use set to avoid duplicates
        for symbol in self._all_symbols:
            # Check if symbol position is within block boundaries
            if (
                symbol.start_line >= start_line
                and symbol.start_line <= end_line
                and symbol.end_line >= start_line
                and symbol.end_line <= end_line
            ):
                # For symbols on boundary lines, check column positions
                if symbol.start_line == start_line and symbol.start_col < start_col:
                    continue
                if symbol.end_line == end_line and symbol.end_col > end_col:
                    continue
                matching_symbols.add(symbol.name)

        return sorted(list(matching_symbols))

    def _create_code_block(self, node: Any, block_type: BlockType, names: List[str]) -> CodeBlock:
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

        # Get symbols for this block
        symbols = self._get_symbols_for_block(start_line, end_line, start_col, end_col)

        return CodeBlock(
            type=block_type,
            name=primary_name,
            content=content,
            symbols=symbols,
            start_line=start_line,
            end_line=end_line,
            start_col=start_col,
            end_col=end_col,
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

        This method should:
        1. Call self._extract_all_symbols(root_node) first to extract symbols
        2. Extract all supported block types for the language
        3. Return all extracted blocks

        Returns:
            List of all extracted CodeBlock objects
        """
        pass


class Extractor:
    """Main extractor that uses language-specific extractors."""

    def __init__(self, symbol_extractor=None):
        """Initialize the extractor.

        Args:
            symbol_extractor: Optional symbol extractor for enhanced analysis
        """
        self.symbol_extractor = symbol_extractor
        self._extractors = {}
        self._setup_extractors()

    def _setup_extractors(self):
        """Setup language-specific extractors."""
        from .typescript_extractor import TypeScriptExtractor
        from .python_extractor import PythonExtractor

        self.register_extractor("typescript", TypeScriptExtractor)
        self.register_extractor("python", PythonExtractor)

    def register_extractor(self, language: str, extractor_class: type) -> None:
        """Register an extractor for a specific language.

        Args:
            language: Programming language name
            extractor_class: Extractor class that extends BaseExtractor
        """
        self._extractors[language] = extractor_class

    def extract_from_ast(self, ast_tree: Any, language: str) -> List[CodeBlock]:
        """Extract code blocks from an AST tree using language-specific extractor.

        Args:
            ast_tree: The AST tree to extract from
            language: Programming language

        Returns:
            List of extracted CodeBlock objects
        """
        if language not in self._extractors:
            return []

        extractor = self._extractors[language](language, self.symbol_extractor)
        return extractor.extract_all(ast_tree.root_node)

    def get_blocks_by_type(self, blocks: List[CodeBlock], block_type: BlockType) -> List[CodeBlock]:
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
