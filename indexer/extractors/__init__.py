"""
AST Extractors Package

This package provides extractors for different code constructs from AST trees.
Supports TypeScript and Python initially, with extensible design for other languages.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional, Union
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
    children: List['CodeBlock'] = field(default_factory=list)

class BaseExtractor(ABC):
    """Base class for language-specific AST extractors."""

    def __init__(self, language: str, symbol_extractor=None):
        self.language = language
        self.symbol_extractor = symbol_extractor
        self._blocks: List[CodeBlock] = []
        self._all_symbols: List[Any] = []  # Store all extracted symbols
        self._source_content: str = ""  # Store full source content
        
        # Register this extractor with the global builder
        global builder
        if builder and hasattr(builder, 'register_extractor'):
            builder.register_extractor(language, self.__class__)
            
    def _traverse_nodes(self, node: Any, node_types: List[str]) -> List[Any]:
        """Traverse AST nodes and collect nodes of specified types."""
        results = []

        def traverse(n):
            if hasattr(n, 'type') and n.type in node_types:
                results.append(n)
            if hasattr(n, 'children'):
                for child in n.children:
                    traverse(child)

        traverse(node)
        return results

    def extract_enums(self, node: Any) -> List[CodeBlock]:
        """Extract top-level enum declarations with nested elements as children."""
        return []  # Default implementation returns empty list

    def extract_variables(self, node: Any) -> List[CodeBlock]:
        """Extract top-level variable declarations with nested elements as children."""
        return []  # Default implementation returns empty list

    def extract_functions(self, node: Any) -> List[CodeBlock]:
        """Extract top-level function declarations with nested elements as children."""
        return []  # Default implementation returns empty list

    def extract_classes(self, node: Any) -> List[CodeBlock]:
        """Extract top-level class declarations with nested elements as children."""
        return []  # Default implementation returns empty list

    def extract_interfaces(self, node: Any) -> List[CodeBlock]:
        """Extract top-level interface declarations with nested elements as children."""
        return []  # Default implementation returns empty list

    def extract_imports(self, node: Any) -> List[CodeBlock]:
        """Extract import statements."""
        return []  # Default implementation returns empty list

    def extract_exports(self, node: Any) -> List[CodeBlock]:
        """Extract export statements with nested elements as children."""
        return []  # Default implementation returns empty list
        
    def _extract_top_level_exports(self, node: Any) -> List[CodeBlock]:
        """Extract only top-level export declarations."""
        return []  # Default implementation returns empty list
        
    def _extract_top_level_enums(self, node: Any) -> List[CodeBlock]:
        """Extract only top-level enum declarations."""
        return []  # Default implementation returns empty list

    def _extract_top_level_variables(self, node: Any) -> List[CodeBlock]:
        """Extract only top-level variable declarations."""
        return []  # Default implementation returns empty list

    def _extract_top_level_functions(self, node: Any) -> List[CodeBlock]:
        """Extract only top-level function declarations."""
        return []  # Default implementation returns empty list

    def _extract_top_level_classes(self, node: Any) -> List[CodeBlock]:
        """Extract only top-level class declarations."""
        return []  # Default implementation returns empty list

    def _extract_top_level_interfaces(self, node: Any) -> List[CodeBlock]:
        """Extract only top-level interface declarations."""
        return []  # Default implementation returns empty list

    def _extract_nested_elements(self, root_node: Any, parent_block: CodeBlock) -> List[CodeBlock]:
        """Extract nested elements within a parent block."""
        nested_blocks = []

        # Find the AST node that corresponds to this parent block
        parent_node = self._find_node_by_position(root_node, parent_block.start_line, parent_block.end_line)

        if parent_node:
            # Extract all types of nested blocks within this parent node
            nested_blocks.extend(self._extract_nested_functions(parent_node))
            nested_blocks.extend(self._extract_nested_classes(parent_node))
            nested_blocks.extend(self._extract_nested_variables(parent_node))
            nested_blocks.extend(self._extract_nested_enums(parent_node))
            nested_blocks.extend(self._extract_nested_interfaces(parent_node))
            
            # Check if the extractor supports exports (TypeScript/JavaScript)
            if hasattr(self, '_extract_nested_exports'):
                nested_blocks.extend(self._extract_nested_exports(parent_node))

        return nested_blocks

    def _extract_nested_functions(self, parent_node: Any) -> List[CodeBlock]:
        """Extract function declarations nested within a parent node."""
        return []  # Default implementation returns empty list

    def _extract_nested_classes(self, parent_node: Any) -> List[CodeBlock]:
        """Extract class declarations nested within a parent node."""
        return []  # Default implementation returns empty list

    def _extract_nested_variables(self, parent_node: Any) -> List[CodeBlock]:
        """Extract variable declarations nested within a parent node."""
        return []  # Default implementation returns empty list

    def _extract_nested_enums(self, parent_node: Any) -> List[CodeBlock]:
        """Extract enum declarations nested within a parent node."""
        return []  # Default implementation returns empty list

    def _extract_nested_interfaces(self, parent_node: Any) -> List[CodeBlock]:
        """Extract interface declarations nested within a parent node."""
        return []  # Default implementation returns empty list

    def _get_nested_identifier_name(self, node: Any) -> str:
        """Get identifier name from a nested node."""
        return ""  # Default implementation returns empty string

    def _get_nested_variable_names(self, node: Any) -> List[str]:
        """Get variable names from a nested assignment node."""
        return []  # Default implementation returns empty list

    def _get_node_text(self, node: Any) -> str:
        """Get text content of a node."""
        if hasattr(node, 'text'):
            if isinstance(node.text, bytes):
                return node.text.decode('utf-8')
            return node.text
        return ""

    def _get_node_position(self, node: Any) -> tuple:
        """Get position information of a node."""
        if hasattr(node, 'start_point') and hasattr(node, 'end_point'):
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            start_col = node.start_point[1]
            end_col = node.end_point[1]
            return start_line, end_line, start_col, end_col
        return 0, 0, 0, 0

    def _find_node_by_position(self, root_node: Any, start_line: int, end_line: int) -> Any:
        """Find AST node by its line position."""
        candidates = []

        def traverse(node):
            if hasattr(node, 'start_point') and hasattr(node, 'end_point'):
                node_start = node.start_point[0] + 1
                node_end = node.end_point[0] + 1
                
                # Check if this node's range contains the target range
                if node_start <= start_line and node_end >= end_line:
                    candidates.append((node, node_end - node_start))
                    
            if hasattr(node, 'children'):
                for child in node.children:
                    traverse(child)
                    
        traverse(root_node)
        
        # Sort by smallest range (most specific node)
        candidates.sort(key=lambda x: x[1])
        return candidates[0][0] if candidates else None

    def _extract_all_symbols(self, root_node: Any) -> None:
        """Extract all symbols from the entire file and store them.
        This is a default implementation that can be overridden by language-specific extractors.
        """
        self._all_symbols = []
        if not self.symbol_extractor:
            return

        try:
            # Get the full source content from the root node
            if hasattr(root_node, 'text'):
                self._source_content = root_node.text.decode('utf-8') if isinstance(root_node.text, bytes) else str(root_node.text)
            else:
                self._source_content = ""

            # Extract all symbols from the root node
            self._all_symbols = self.symbol_extractor.extract_symbols(root_node, self._source_content, self.language)
        except Exception as e:
            # Log error but don't fail completely
            print(f"Error extracting symbols: {e}")
            self._all_symbols = []

    def _get_symbols_for_block(self, start_line: int, end_line: int, start_col: int, end_col: int) -> List[str]:
        """Find symbols that fall within the given block boundaries."""
        if not self._all_symbols:
            return []

        matching_symbols = set()  # Use set to avoid duplicates
        for symbol in self._all_symbols:
            # Check if symbol position is within block boundaries
            # Symbol must start and end within the block boundaries
            if (symbol.start_line >= start_line and symbol.start_line <= end_line and
                symbol.end_line >= start_line and symbol.end_line <= end_line):
                # For symbols on the same line as block boundaries, check column positions
                if symbol.start_line == start_line and symbol.start_col < start_col:
                    continue
                if symbol.end_line == end_line and symbol.end_col > end_col:
                    continue
                matching_symbols.add(symbol.name)

        return list(matching_symbols)  # Convert back to sorted list

    def _create_code_block(self, block_type: BlockType, name: str, content: str,
                          start_line: int, end_line: int, start_col: int, end_col: int,
                          node: Any) -> CodeBlock:
        """Create a CodeBlock with symbols extracted."""
        symbols = self._get_symbols_for_block(start_line, end_line, start_col, end_col)
        return CodeBlock(
            type=block_type,
            name=name,
            content=content,
            symbols=symbols,
            start_line=start_line,
            end_line=end_line,
            start_col=start_col,
            end_col=end_col
        )

    def extract_all(self, root_node: Any) -> List[CodeBlock]:
        """Extract all supported code blocks with hierarchical structure.
        
        This method should be implemented by language-specific extractors.
        Each language extractor should override this method with its own implementation
        that extracts blocks in the appropriate order for that language.
        
        Language-specific implementations should call self._extract_all_symbols(root_node)
        first to extract all symbols from the entire file, then proceed with their
        language-specific extraction logic.
        
        Example implementation:
        ```python
        def extract_all(self, root_node: Any) -> List[CodeBlock]:
            self._blocks = []
            
            # First, extract all symbols from the entire file
            self._extract_all_symbols(root_node)
            
            # Then extract top-level blocks with their nested children
            # Language-specific order and handling
            self._blocks.extend(self.extract_imports(root_node))
            # ... other extractions ...
            
            return self._blocks
        ```
        """
        raise NotImplementedError("extract_all must be implemented by language-specific extractors")


class ExtractorBuilder:
    """Builder class for creating language-specific extractors."""

    def __init__(self, symbol_extractor=None):
        self._extractors = {}
        self.symbol_extractor = symbol_extractor

    def register_extractor(self, language: str, extractor_class: type) -> 'ExtractorBuilder':
        """Register an extractor for a specific language."""
        self._extractors[language] = extractor_class
        return self

    def build(self, language: str) -> Optional[BaseExtractor]:
        """Build an extractor for the specified language."""
        if language not in self._extractors:
            return None
        return self._extractors[language](language, self.symbol_extractor)

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        return list(self._extractors.keys())

# Global builder instance
builder = ExtractorBuilder()

class Extractor:
    """
    Main extractor that uses language-specific extractors.
    """

    def __init__(self, symbol_extractor=None):
        """Initialize the extractor."""
        self.symbol_extractor = symbol_extractor
        self._setup_extractors()

    def _setup_extractors(self):
        """Setup language-specific extractors."""
        from .typescript_extractor import TypeScriptExtractor
        from .python_extractor import PythonExtractor

        global builder
        builder = ExtractorBuilder(self.symbol_extractor)
        builder.register_extractor("typescript", TypeScriptExtractor)
        builder.register_extractor("python", PythonExtractor)

    def extract_from_ast(self, ast_tree: Any, language: str, block_types: Optional[List[BlockType]] = None) -> List[CodeBlock]:
        """
        Extract code blocks from an AST tree using language-specific extractor.

        Args:
            ast_tree: The AST tree to extract from
            language: Programming language
            block_types: List of block types to extract (None for all)

        Returns:
            List of extracted CodeBlock objects
        """
        extractor = builder.build(language)
        if not extractor:
            return []

        if block_types:
            return self._extract_specific_blocks(extractor, ast_tree.root_node, block_types)
        else:
            # Each language-specific extractor now has its own extract_all implementation
            return extractor.extract_all(ast_tree.root_node)

    def get_blocks_by_type(self, blocks: List[CodeBlock], block_type: BlockType) -> List[CodeBlock]:
        """Filter blocks by type."""
        return [block for block in blocks if block.type == block_type]

    def get_supported_languages(self) -> List[str]:
        """Get languages that support code block extraction."""
        return builder.get_supported_languages()

    def _extract_specific_blocks(self, extractor: Any, root_node: Any,
                               block_types: List[BlockType]) -> List[CodeBlock]:
        """Extract specific types of blocks."""
        blocks = []

        for block_type in block_types:
            try:
                if block_type == BlockType.ENUM:
                    if hasattr(extractor, 'extract_enums'):
                        blocks.extend(extractor.extract_enums(root_node))
                    else:
                        print(f"Warning: Extractor does not support {block_type}")
                elif block_type == BlockType.VARIABLE:
                    if hasattr(extractor, 'extract_variables'):
                        blocks.extend(extractor.extract_variables(root_node))
                    else:
                        print(f"Warning: Extractor does not support {block_type}")
                elif block_type == BlockType.FUNCTION:
                    if hasattr(extractor, 'extract_functions'):
                        blocks.extend(extractor.extract_functions(root_node))
                    else:
                        print(f"Warning: Extractor does not support {block_type}")
                elif block_type == BlockType.CLASS:
                    if hasattr(extractor, 'extract_classes'):
                        blocks.extend(extractor.extract_classes(root_node))
                    else:
                        print(f"Warning: Extractor does not support {block_type}")
                elif block_type == BlockType.INTERFACE:
                    if hasattr(extractor, 'extract_interfaces'):
                        blocks.extend(extractor.extract_interfaces(root_node))
                    else:
                        print(f"Warning: Extractor does not support {block_type}")
                elif block_type == BlockType.IMPORT:
                    if hasattr(extractor, 'extract_imports'):
                        blocks.extend(extractor.extract_imports(root_node))
                    else:
                        print(f"Warning: Extractor does not support {block_type}")
                elif block_type == BlockType.EXPORT:
                    if hasattr(extractor, 'extract_exports'):
                        blocks.extend(extractor.extract_exports(root_node))
                    else:
                        print(f"Warning: Extractor does not support {block_type}")
            except AttributeError as e:
                print(f"Warning: Extractor does not support {block_type}: {e}")
            except Exception as e:
                print(f"Error extracting {block_type}: {e}")

        return blocks


# Global builder instance
builder = ExtractorBuilder()

__all__ = [
    'BlockType',
    'CodeBlock',
    'BaseExtractor',
    'Extractor',
    'ExtractorBuilder',
    'builder'
]
