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

    def extract_enums(self, node: Any) -> List[CodeBlock]:
        """Extract top-level enum declarations with nested elements as children."""
        enums = self._extract_top_level_enums(node)
        for enum in enums:
            enum.children = self._extract_nested_elements(node, enum)
        return enums

    def extract_variables(self, node: Any) -> List[CodeBlock]:
        """Extract top-level variable declarations with nested elements as children."""
        variables = self._extract_top_level_variables(node)
        for variable in variables:
            variable.children = self._extract_nested_elements(node, variable)
        return variables

    def extract_functions(self, node: Any) -> List[CodeBlock]:
        """Extract top-level function declarations with nested elements as children."""
        functions = self._extract_top_level_functions(node)
        for function in functions:
            function.children = self._extract_nested_elements(node, function)
        return functions

    def extract_classes(self, node: Any) -> List[CodeBlock]:
        """Extract top-level class declarations with nested elements as children."""
        classes = self._extract_top_level_classes(node)
        for class_block in classes:
            class_block.children = self._extract_nested_elements(node, class_block)
        return classes

    def extract_interfaces(self, node: Any) -> List[CodeBlock]:
        """Extract top-level interface declarations with nested elements as children."""
        interfaces = self._extract_top_level_interfaces(node)
        for interface in interfaces:
            interface.children = self._extract_nested_elements(node, interface)
        return interfaces

    @abstractmethod
    def extract_imports(self, node: Any) -> List[CodeBlock]:
        """Extract import statements."""
        pass

    @abstractmethod
    def extract_exports(self, node: Any) -> List[CodeBlock]:
        """Extract export statements."""
        pass

    def extract_all(self, root_node: Any) -> List[CodeBlock]:
        """Extract all supported code blocks with hierarchical structure."""
        self._blocks = []

        # Extract top-level blocks with their nested children
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

    def _extract_top_level_enums(self, node: Any) -> List[CodeBlock]:
        """Extract only top-level enum declarations."""
        return self._extract_direct_children_of_type(node, ['enum_declaration'], BlockType.ENUM)

    def _extract_top_level_variables(self, node: Any) -> List[CodeBlock]:
        """Extract only top-level variable declarations."""
        return self._extract_direct_children_of_type(node, ['assignment', 'variable_declaration', 'lexical_declaration'], BlockType.VARIABLE)

    def _extract_top_level_functions(self, node: Any) -> List[CodeBlock]:
        """Extract only top-level function declarations."""
        return self._extract_direct_children_of_type(node, ['function_definition', 'async_function_definition', 'function_declaration'], BlockType.FUNCTION)

    def _extract_top_level_classes(self, node: Any) -> List[CodeBlock]:
        """Extract only top-level class declarations."""
        return self._extract_direct_children_of_type(node, ['class_definition', 'class_declaration'], BlockType.CLASS)

    def _extract_top_level_interfaces(self, node: Any) -> List[CodeBlock]:
        """Extract only top-level interface declarations."""
        return self._extract_direct_children_of_type(node, ['interface_declaration'], BlockType.INTERFACE)

    def _extract_direct_children_of_type(self, node: Any, node_types: List[str], block_type: BlockType) -> List[CodeBlock]:
        """Extract direct children of specific node types from the root."""
        blocks = []

        def extract_direct_children(parent_node, depth=0):
            if hasattr(parent_node, 'children'):
                for child in parent_node.children:
                    if hasattr(child, 'type') and child.type in node_types:
                        if block_type == BlockType.VARIABLE:
                            names = self._get_nested_variable_names(child)
                            if names:
                                start_line, end_line, start_col, end_col = self._get_node_position(child)
                                content = self._get_node_text(child)
                                for name in names:
                                    blocks.append(self._create_code_block(
                                        block_type,
                                        name,
                                        content,
                                        start_line,
                                        end_line,
                                        start_col,
                                        end_col,
                                        child
                                    ))
                        else:
                            name = self._get_nested_identifier_name(child)
                            if name:
                                start_line, end_line, start_col, end_col = self._get_node_position(child)
                                content = self._get_node_text(child)
                                blocks.append(self._create_code_block(
                                    block_type,
                                    name,
                                    content,
                                    start_line,
                                    end_line,
                                    start_col,
                                    end_col,
                                    child
                                ))

                    # For module-level or program-level nodes, continue searching
                    elif hasattr(child, 'type') and child.type in ['module', 'program', 'source_file']:
                        extract_direct_children(child, depth + 1)

        extract_direct_children(node)
        return blocks

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

            # For now, only go one level deep to avoid recursion issues
            # TODO: Add controlled recursion in the future if needed

        return nested_blocks

    def _find_node_by_position(self, root_node: Any, start_line: int, end_line: int) -> Any:
        """Find AST node by its line position."""
        def traverse(node):
            if hasattr(node, 'start_point') and hasattr(node, 'end_point'):
                node_start = node.start_point[0] + 1
                node_end = node.end_point[0] + 1

                if node_start == start_line and node_end == end_line:
                    return node

            if hasattr(node, 'children'):
                for child in node.children:
                    result = traverse(child)
                    if result:
                        return result
            return None

        return traverse(root_node)

    def _extract_nested_functions(self, parent_node: Any) -> List[CodeBlock]:
        """Extract function declarations nested within a parent node."""
        nested_functions = []

        def traverse(node, depth=0):
            if hasattr(node, 'type'):
                # Language-specific function node types
                function_types = ['function_definition', 'async_function_definition', 'method_definition',
                                'function_declaration', 'method_declaration']

                if node.type in function_types and depth > 0:  # Skip direct children, only nested
                    name = self._get_nested_identifier_name(node)
                    if name:
                        start_line, end_line, start_col, end_col = self._get_node_position(node)
                        content = self._get_node_text(node)

                        nested_functions.append(self._create_code_block(
                            BlockType.FUNCTION,
                            name,
                            content,
                            start_line,
                            end_line,
                            start_col,
                            end_col,
                            node
                        ))
                        return  # Don't traverse deeper from this function

            if hasattr(node, 'children'):
                for child in node.children:
                    traverse(child, depth + 1)

        if hasattr(parent_node, 'children'):
            for child in parent_node.children:
                traverse(child, 0)

        return nested_functions

    def _extract_nested_classes(self, parent_node: Any) -> List[CodeBlock]:
        """Extract class declarations nested within a parent node."""
        nested_classes = []

        def traverse(node, depth=0):
            if hasattr(node, 'type'):
                class_types = ['class_definition', 'class_declaration']

                if node.type in class_types and depth > 0:
                    name = self._get_nested_identifier_name(node)
                    if name:
                        start_line, end_line, start_col, end_col = self._get_node_position(node)
                        content = self._get_node_text(node)

                        nested_classes.append(self._create_code_block(
                            BlockType.CLASS,
                            name,
                            content,
                            start_line,
                            end_line,
                            start_col,
                            end_col,
                            node
                        ))
                        return

            if hasattr(node, 'children'):
                for child in node.children:
                    traverse(child, depth + 1)

        if hasattr(parent_node, 'children'):
            for child in parent_node.children:
                traverse(child, 0)

        return nested_classes

    def _extract_nested_variables(self, parent_node: Any) -> List[CodeBlock]:
        """Extract variable declarations nested within a parent node."""
        nested_variables = []

        def traverse(node, depth=0):
            if hasattr(node, 'type'):
                variable_types = ['assignment', 'variable_declaration', 'lexical_declaration']

                if node.type in variable_types and depth > 0:
                    names = self._get_nested_variable_names(node)
                    if names:
                        start_line, end_line, start_col, end_col = self._get_node_position(node)
                        content = self._get_node_text(node)

                        for name in names:
                            nested_variables.append(self._create_code_block(
                                BlockType.VARIABLE,
                                name,
                                content,
                                start_line,
                                end_line,
                                start_col,
                                end_col,
                                node
                            ))

            if hasattr(node, 'children'):
                for child in node.children:
                    traverse(child, depth + 1)

        if hasattr(parent_node, 'children'):
            for child in parent_node.children:
                traverse(child, 0)

        return nested_variables

    def _extract_nested_enums(self, parent_node: Any) -> List[CodeBlock]:
        """Extract enum declarations nested within a parent node."""
        nested_enums = []

        def traverse(node, depth=0):
            if hasattr(node, 'type'):
                enum_types = ['enum_declaration']

                if node.type in enum_types and depth > 0:
                    name = self._get_nested_identifier_name(node)
                    if name:
                        start_line, end_line, start_col, end_col = self._get_node_position(node)
                        content = self._get_node_text(node)

                        nested_enums.append(self._create_code_block(
                            BlockType.ENUM,
                            name,
                            content,
                            start_line,
                            end_line,
                            start_col,
                            end_col,
                            node
                        ))
                        return

            if hasattr(node, 'children'):
                for child in node.children:
                    traverse(child, depth + 1)

        if hasattr(parent_node, 'children'):
            for child in parent_node.children:
                traverse(child, 0)

        return nested_enums

    def _extract_nested_interfaces(self, parent_node: Any) -> List[CodeBlock]:
        """Extract interface declarations nested within a parent node."""
        nested_interfaces = []

        def traverse(node, depth=0):
            if hasattr(node, 'type'):
                interface_types = ['interface_declaration']

                if node.type in interface_types and depth > 0:
                    name = self._get_nested_identifier_name(node)
                    if name:
                        start_line, end_line, start_col, end_col = self._get_node_position(node)
                        content = self._get_node_text(node)

                        nested_interfaces.append(self._create_code_block(
                            BlockType.INTERFACE,
                            name,
                            content,
                            start_line,
                            end_line,
                            start_col,
                            end_col,
                            node
                        ))
                        return

            if hasattr(node, 'children'):
                for child in node.children:
                    traverse(child, depth + 1)

        if hasattr(parent_node, 'children'):
            for child in parent_node.children:
                traverse(child, 0)

        return nested_interfaces

    def _get_nested_identifier_name(self, node: Any) -> str:
        """Get identifier name from a nested node (can be overridden by subclasses)."""
        if hasattr(node, 'children'):
            for child in node.children:
                if hasattr(child, 'type') and child.type in ['identifier', 'type_identifier']:
                    return self._get_node_text(child)
        return ""

    def _get_nested_variable_names(self, node: Any) -> List[str]:
        """Get variable names from a nested assignment node (can be overridden by subclasses)."""
        names = []
        if hasattr(node, 'children'):
            for child in node.children:
                if hasattr(child, 'type') and child.type == 'identifier':
                    names.append(self._get_node_text(child))
        return names

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
        return (1, 1, 0, 0)

    def _extract_all_symbols(self, root_node: Any) -> None:
        """Extract all symbols from the entire file and store them."""
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
        """Extract all supported code blocks with hierarchical structure."""
        self._blocks = []

        # First, extract all symbols from the entire file
        self._extract_all_symbols(root_node)

        # Then extract top-level blocks with their nested children
        self._blocks.extend(self.extract_enums(root_node))
        self._blocks.extend(self.extract_variables(root_node))
        self._blocks.extend(self.extract_functions(root_node))
        self._blocks.extend(self.extract_classes(root_node))
        self._blocks.extend(self.extract_interfaces(root_node))
        self._blocks.extend(self.extract_imports(root_node))
        self._blocks.extend(self.extract_exports(root_node))

        return self._blocks


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
