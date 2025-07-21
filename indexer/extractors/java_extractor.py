"""
Java AST Extractor

Extracts Java code constructs from AST trees.
"""

from typing import Any, List
from . import BaseExtractor, BlockType, CodeBlock


class JavaExtractor(BaseExtractor):
    """Extractor for Java code blocks."""

    def __init__(self, language: str = "java"):
        super().__init__(language)

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

    def _get_identifier_name(self, node: Any) -> str:
        """Get identifier name from a node."""
        if hasattr(node, 'children'):
            for child in node.children:
                if hasattr(child, 'type') and child.type == 'identifier':
                    return self._get_node_text(child)
        return ""



    def extract_imports(self, node: Any) -> List[CodeBlock]:
        """Extract import statements."""
        blocks = []

        # Extract import statements
        import_nodes = self._traverse_nodes(node, ['import_statement', 'import_from_statement'])

        for import_node in import_nodes:
            start_line, end_line, start_col, end_col = self._get_node_position(import_node)
            content = self._get_node_text(import_node)

            # Extract the module name or first imported name as the identifier
            name = self._extract_import_name(import_node)

            blocks.append(CodeBlock(
                type=BlockType.IMPORT,
                name=name,
                content=content,
                start_line=start_line,
                end_line=end_line,
                start_col=start_col,
                end_col=end_col
            ))

        return blocks

    def extract_exports(self, node: Any) -> List[CodeBlock]:
        """Extract export statements (Python uses __all__ for explicit exports)."""
        blocks = []

        # Look for __all__ assignments
        assignment_nodes = self._traverse_nodes(node, ['assignment'])

        for assignment_node in assignment_nodes:
            if hasattr(assignment_node, 'children'):
                for child in assignment_node.children:
                    if hasattr(child, 'type') and child.type == 'identifier':
                        if self._get_node_text(child) == '__all__':
                            start_line, end_line, start_col, end_col = self._get_node_position(assignment_node)
                            content = self._get_node_text(assignment_node)

                            blocks.append(CodeBlock(
                                type=BlockType.EXPORT,
                                name='__all__',
                                content=content,
                                start_line=start_line,
                                end_line=end_line,
                                start_col=start_col,
                                end_col=end_col
                            ))
                            break

        return blocks

    def _extract_assignment_names(self, assignment_node: Any) -> List[str]:
        """Extract variable names from assignment statement."""
        names = []

        if hasattr(assignment_node, 'children'):
            for child in assignment_node.children:
                if hasattr(child, 'type'):
                    if child.type == 'identifier':
                        names.append(self._get_node_text(child))
                    elif child.type == 'pattern_list':
                        names.extend(self._extract_pattern_names(child))

        return names

    def _extract_pattern_names(self, pattern_node: Any) -> List[str]:
        """Extract names from pattern (for tuple unpacking, etc.)."""
        names = []

        if hasattr(pattern_node, 'children'):
            for child in pattern_node.children:
                if hasattr(child, 'type') and child.type == 'identifier':
                    names.append(self._get_node_text(child))

        return names

    def _extract_import_name(self, import_node: Any) -> str:
        """Extract the primary name from an import statement."""
        if hasattr(import_node, 'children'):
            for child in import_node.children:
                if hasattr(child, 'type'):
                    if child.type == 'dotted_name':
                        return self._get_node_text(child)
                    elif child.type == 'identifier':
                        return self._get_node_text(child)
                    elif child.type == 'aliased_import':
                        # For "import x as y", return "y"
                        if hasattr(child, 'children'):
                            for grandchild in child.children:
                                if hasattr(grandchild, 'type') and grandchild.type == 'identifier':
                                    return self._get_node_text(grandchild)

        return 'unknown'

    def _get_nested_identifier_name(self, node: Any) -> str:
        """Get identifier name from a nested Python node."""
        if hasattr(node, 'children'):
            for child in node.children:
                if hasattr(child, 'type') and child.type == 'identifier':
                    return self._get_node_text(child)
        return ""

    def _get_nested_variable_names(self, node: Any) -> List[str]:
        """Get variable names from a nested Python assignment node."""
        names = []

        if hasattr(node, 'children'):
            for child in node.children:
                if hasattr(child, 'type'):
                    if child.type == 'identifier':
                        names.append(self._get_node_text(child))
                    elif child.type == 'pattern_list':
                        names.extend(self._extract_pattern_names(child))

        return names

    def _extract_nested_functions(self, parent_node: Any) -> List[CodeBlock]:
        """Extract function declarations nested within a Python parent node."""
        nested_functions = []

        def traverse(node, depth=0):
            if hasattr(node, 'type'):
                function_types = ['function_definition', 'async_function_definition']

                if node.type in function_types and depth > 0:
                    name = self._get_identifier_name(node)
                    if name:
                        start_line, end_line, start_col, end_col = self._get_node_position(node)
                        content = self._get_node_text(node)

                        nested_functions.append(CodeBlock(
                            type=BlockType.FUNCTION,
                            name=name,
                            content=content,
                            start_line=start_line,
                            end_line=end_line,
                            start_col=start_col,
                            end_col=end_col
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
        """Extract class declarations nested within a Python parent node."""
        nested_classes = []

        def traverse(node, depth=0):
            if hasattr(node, 'type'):
                if node.type == 'class_definition' and depth > 0:
                    name = self._get_identifier_name(node)
                    if name:
                        start_line, end_line, start_col, end_col = self._get_node_position(node)
                        content = self._get_node_text(node)

                        nested_classes.append(CodeBlock(
                            type=BlockType.CLASS,
                            name=name,
                            content=content,
                            start_line=start_line,
                            end_line=end_line,
                            start_col=start_col,
                            end_col=end_col
                        ))
                        return

            if hasattr(node, 'children'):
                for child in node.children:
                    traverse(child, depth + 1)

        if hasattr(parent_node, 'children'):
            for child in parent_node.children:
                traverse(child, 0)

        return nested_classes

    def _extract_top_level_functions(self, node: Any) -> List[CodeBlock]:
        """Extract only top-level function declarations from Python module."""
        blocks = []

        # Look for direct children of the module that are function definitions
        if hasattr(node, 'children'):
            for child in node.children:
                if hasattr(child, 'type') and child.type in ['function_definition', 'async_function_definition']:
                    name = self._get_identifier_name(child)
                    if name:
                        start_line, end_line, start_col, end_col = self._get_node_position(child)
                        content = self._get_node_text(child)
                        blocks.append(CodeBlock(
                            type=BlockType.FUNCTION,
                            name=name,
                            content=content,
                            start_line=start_line,
                            end_line=end_line,
                            start_col=start_col,
                            end_col=end_col
                        ))

        return blocks

    def _extract_top_level_classes(self, node: Any) -> List[CodeBlock]:
        """Extract only top-level class declarations from Python module."""
        blocks = []

        # Look for direct children of the module that are class definitions
        if hasattr(node, 'children'):
            for child in node.children:
                if hasattr(child, 'type') and child.type == 'class_definition':
                    name = self._get_identifier_name(child)
                    if name:
                        start_line, end_line, start_col, end_col = self._get_node_position(child)
                        content = self._get_node_text(child)
                        blocks.append(CodeBlock(
                            type=BlockType.CLASS,
                            name=name,
                            content=content,
                            start_line=start_line,
                            end_line=end_line,
                            start_col=start_col,
                            end_col=end_col
                        ))

        return blocks

    def _extract_top_level_variables(self, node: Any) -> List[CodeBlock]:
        """Extract only top-level variable declarations from Python module."""
        blocks = []

        # Look for direct children of the module that are assignments
        # In Python AST, module-level assignments are often wrapped in expression_statement nodes
        if hasattr(node, 'children'):
            for child in node.children:
                if hasattr(child, 'type'):
                    if child.type == 'assignment':
                        names = self._extract_assignment_names(child)
                        if names:
                            start_line, end_line, start_col, end_col = self._get_node_position(child)
                            content = self._get_node_text(child)
                            for name in names:
                                blocks.append(CodeBlock(
                                    type=BlockType.VARIABLE,
                                    name=name,
                                    content=content,
                                    start_line=start_line,
                                    end_line=end_line,
                                    start_col=start_col,
                                    end_col=end_col
                                ))
                    elif child.type == 'expression_statement':
                        # Look for assignment nodes inside expression_statement
                        if hasattr(child, 'children'):
                            for grandchild in child.children:
                                if hasattr(grandchild, 'type') and grandchild.type == 'assignment':
                                    names = self._extract_assignment_names(grandchild)
                                    if names:
                                        start_line, end_line, start_col, end_col = self._get_node_position(grandchild)
                                        content = self._get_node_text(grandchild)
                                        for name in names:
                                            blocks.append(CodeBlock(
                                                type=BlockType.VARIABLE,
                                                name=name,
                                                content=content,
                                                start_line=start_line,
                                                end_line=end_line,
                                                start_col=start_col,
                                                end_col=end_col
                                            ))

        return blocks

    def _extract_top_level_enums(self, node: Any) -> List[CodeBlock]:
        """Extract only top-level enum declarations from Python module."""
        blocks = []

        # Look for direct children of the module that are class definitions inheriting from Enum
        if hasattr(node, 'children'):
            for child in node.children:
                if hasattr(child, 'type') and child.type == 'class_definition':
                    content = self._get_node_text(child)
                    if 'Enum' in content:  # Simple heuristic
                        name = self._get_identifier_name(child)
                        if name:
                            start_line, end_line, start_col, end_col = self._get_node_position(child)
                            blocks.append(CodeBlock(
                                type=BlockType.ENUM,
                                name=name,
                                content=content,
                                start_line=start_line,
                                end_line=end_line,
                                start_col=start_col,
                                end_col=end_col
                            ))

        return blocks

    def _extract_top_level_interfaces(self, node: Any) -> List[CodeBlock]:
        """Extract only top-level interface-like declarations from Python module."""
        blocks = []

        # Look for direct children of the module that are abstract classes or protocols
        if hasattr(node, 'children'):
            for child in node.children:
                if hasattr(child, 'type') and child.type == 'class_definition':
                    content = self._get_node_text(child)
                    # Simple heuristic: look for ABC, Protocol, or abstract methods
                    if any(keyword in content for keyword in ['ABC', 'Protocol', 'abstractmethod']):
                        name = self._get_identifier_name(child)
                        if name:
                            start_line, end_line, start_col, end_col = self._get_node_position(child)
                            blocks.append(CodeBlock(
                                type=BlockType.INTERFACE,
                                name=name,
                                content=content,
                                start_line=start_line,
                                end_line=end_line,
                                start_col=start_col,
                                end_col=end_col
                            ))

        return blocks
