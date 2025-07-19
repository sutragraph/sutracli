"""
AST Extractors Package

This package provides extractors for different code constructs from AST trees.
Supports TypeScript and Python initially, with extensible design for other languages.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional, Union
from dataclasses import dataclass
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
    start_line: int
    end_line: int
    start_col: int
    end_col: int

class BaseExtractor(ABC):
    """Base class for language-specific AST extractors."""

    def __init__(self, language: str):
        self.language = language
        self._blocks: List[CodeBlock] = []

    @abstractmethod
    def extract_enums(self, node: Any) -> List[CodeBlock]:
        """Extract enum declarations."""
        pass

    @abstractmethod
    def extract_variables(self, node: Any) -> List[CodeBlock]:
        """Extract variable declarations."""
        pass

    @abstractmethod
    def extract_functions(self, node: Any) -> List[CodeBlock]:
        """Extract function declarations."""
        pass

    @abstractmethod
    def extract_classes(self, node: Any) -> List[CodeBlock]:
        """Extract class declarations."""
        pass

    @abstractmethod
    def extract_interfaces(self, node: Any) -> List[CodeBlock]:
        """Extract interface declarations."""
        pass

    @abstractmethod
    def extract_imports(self, node: Any) -> List[CodeBlock]:
        """Extract import statements."""
        pass

    @abstractmethod
    def extract_exports(self, node: Any) -> List[CodeBlock]:
        """Extract export statements."""
        pass

    def extract_all(self, root_node: Any) -> List[CodeBlock]:
        """Extract all supported code blocks from AST."""
        self._blocks = []

        # Extract all block types
        self._blocks.extend(self.extract_enums(root_node))
        self._blocks.extend(self.extract_variables(root_node))
        self._blocks.extend(self.extract_functions(root_node))
        self._blocks.extend(self.extract_classes(root_node))
        self._blocks.extend(self.extract_interfaces(root_node))
        self._blocks.extend(self.extract_imports(root_node))
        self._blocks.extend(self.extract_exports(root_node))

        return self._blocks

    def get_blocks_by_type(self, block_type: BlockType) -> List[CodeBlock]:
        """Get all blocks of a specific type."""
        return [block for block in self._blocks if block.type == block_type]

    def _get_node_text(self, node: Any) -> str:
        """Get text content of a node."""
        if hasattr(node, 'text'):
            return node.text.decode('utf-8') if isinstance(node.text, bytes) else node.text
        return ""

    def _get_node_position(self, node: Any) -> tuple:
        """Get position information of a node."""
        if hasattr(node, 'start_point') and hasattr(node, 'end_point'):
            return (
                node.start_point[0] + 1,  # line (1-indexed)
                node.end_point[0] + 1,    # end line (1-indexed)
                node.start_point[1],      # column (0-indexed)
                node.end_point[1]         # end column (0-indexed)
            )
        return (0, 0, 0, 0)

class ExtractorBuilder:
    """Builder class for creating language-specific extractors."""

    def __init__(self):
        self._extractors = {}

    def register_extractor(self, language: str, extractor_class: type) -> 'ExtractorBuilder':
        """Register an extractor for a specific language."""
        self._extractors[language] = extractor_class
        return self

    def build(self, language: str) -> Optional[BaseExtractor]:
        """Build an extractor for the specified language."""
        if language not in self._extractors:
            return None
        return self._extractors[language](language)

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        return list(self._extractors.keys())

# Global builder instance
builder = ExtractorBuilder()

__all__ = [
    'BlockType',
    'CodeBlock',
    'BaseExtractor',
    'ExtractorBuilder',
    'builder'
]
