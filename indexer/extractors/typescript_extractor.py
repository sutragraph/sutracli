"""
TypeScript AST Extractor

Extracts TypeScript/JavaScript code constructs from AST trees.
"""

from typing import Any, List
from . import BaseExtractor, BlockType, CodeBlock


class TypeScriptExtractor(BaseExtractor):
    """Extractor for TypeScript/JavaScript code blocks."""

    def __init__(self, language: str = "typescript"):
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

    def extract_enums(self, node: Any) -> List[CodeBlock]:
        """Extract enum declarations."""
        blocks = []
        enum_nodes = self._traverse_nodes(node, ['enum_declaration'])

        for enum_node in enum_nodes:
            name = self._get_identifier_name(enum_node)
            if name:
                start_line, end_line, start_col, end_col = self._get_node_position(enum_node)
                content = self._get_node_text(enum_node)

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

    def extract_variables(self, node: Any) -> List[CodeBlock]:
        """Extract variable declarations."""
        blocks = []

        # Extract variable declarations
        var_nodes = self._traverse_nodes(node, [
            'variable_declaration',
            'lexical_declaration'
        ])

        for var_node in var_nodes:
            names = self._extract_variable_names(var_node)
            if names:
                start_line, end_line, start_col, end_col = self._get_node_position(var_node)
                content = self._get_node_text(var_node)

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

    def extract_functions(self, node: Any) -> List[CodeBlock]:
        """Extract function declarations."""
        blocks = []

        # Extract function declarations
        func_nodes = self._traverse_nodes(node, ['function_declaration'])
        for func_node in func_nodes:
            name = self._get_identifier_name(func_node)
            if name:
                start_line, end_line, start_col, end_col = self._get_node_position(func_node)
                content = self._get_node_text(func_node)

                blocks.append(CodeBlock(
                    type=BlockType.FUNCTION,
                    name=name,
                    content=content,
                    start_line=start_line,
                    end_line=end_line,
                    start_col=start_col,
                    end_col=end_col
                ))

        # Extract method definitions
        method_nodes = self._traverse_nodes(node, ['method_definition'])
        for method_node in method_nodes:
            name = self._get_method_name(method_node)
            if name:
                start_line, end_line, start_col, end_col = self._get_node_position(method_node)
                content = self._get_node_text(method_node)

                blocks.append(CodeBlock(
                    type=BlockType.FUNCTION,
                    name=name,
                    content=content,
                    start_line=start_line,
                    end_line=end_line,
                    start_col=start_col,
                    end_col=end_col
                ))

        # Extract function expressions assigned to variables
        var_nodes = self._traverse_nodes(node, [
            'variable_declaration',
            'lexical_declaration'
        ])

        for var_node in var_nodes:
            if hasattr(var_node, 'children'):
                for child in var_node.children:
                    if hasattr(child, 'type') and child.type == 'variable_declarator':
                        name = self._get_identifier_name(child)
                        if name and self._is_function_assignment(child):
                            start_line, end_line, start_col, end_col = self._get_node_position(var_node)
                            content = self._get_node_text(var_node)

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

    def extract_classes(self, node: Any) -> List[CodeBlock]:
        """Extract class declarations."""
        blocks = []
        class_nodes = self._traverse_nodes(node, ['class_declaration'])

        for class_node in class_nodes:
            name = self._get_identifier_name(class_node)
            if name:
                start_line, end_line, start_col, end_col = self._get_node_position(class_node)
                content = self._get_node_text(class_node)

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

    def extract_interfaces(self, node: Any) -> List[CodeBlock]:
        """Extract interface declarations."""
        blocks = []
        interface_nodes = self._traverse_nodes(node, ['interface_declaration'])

        for interface_node in interface_nodes:
            name = self._get_identifier_name(interface_node)
            if name:
                start_line, end_line, start_col, end_col = self._get_node_position(interface_node)
                content = self._get_node_text(interface_node)

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

    def extract_imports(self, node: Any) -> List[CodeBlock]:
        """Extract import statements."""
        blocks = []
        import_nodes = self._traverse_nodes(node, ['import_statement'])

        for import_node in import_nodes:
            name = self._extract_import_name(import_node)
            if name:
                start_line, end_line, start_col, end_col = self._get_node_position(import_node)
                content = self._get_node_text(import_node)

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
        """Extract export statements."""
        blocks = []
        export_nodes = self._traverse_nodes(node, [
            'export_statement',
            'export_declaration'
        ])

        for export_node in export_nodes:
            name = self._extract_export_name(export_node)
            if name:
                start_line, end_line, start_col, end_col = self._get_node_position(export_node)
                content = self._get_node_text(export_node)

                blocks.append(CodeBlock(
                    type=BlockType.EXPORT,
                    name=name,
                    content=content,
                    start_line=start_line,
                    end_line=end_line,
                    start_col=start_col,
                    end_col=end_col
                ))

        return blocks

    def _extract_import_name(self, import_node: Any) -> str:
        """Extract the primary name from an import statement."""
        if hasattr(import_node, 'children'):
            for child in import_node.children:
                if hasattr(child, 'type'):
                    if child.type == 'import_clause':
                        # Look for default import or named imports
                        if hasattr(child, 'children'):
                            for grandchild in child.children:
                                if hasattr(grandchild, 'type'):
                                    if grandchild.type == 'identifier':
                                        return self._get_node_text(grandchild)
                                    elif grandchild.type == 'named_imports':
                                        # Get first named import
                                        names = self._extract_named_imports(grandchild)
                                        return names[0] if names else 'unknown'
                    elif child.type == 'string':
                        # Import without names, use module path
                        return self._get_node_text(child).strip('"\'')

        return 'unknown'

    def _extract_named_imports(self, named_imports_node: Any) -> List[str]:
        """Extract names from named imports."""
        names = []
        if hasattr(named_imports_node, 'children'):
            for child in named_imports_node.children:
                if hasattr(child, 'type') and child.type == 'import_specifier':
                    if hasattr(child, 'children'):
                        for grandchild in child.children:
                            if hasattr(grandchild, 'type') and grandchild.type == 'identifier':
                                names.append(self._get_node_text(grandchild))
                                break
        return names

    def _extract_export_name(self, export_node: Any) -> str:
        """Extract the primary name from an export statement."""
        if hasattr(export_node, 'children'):
            for child in export_node.children:
                if hasattr(child, 'type'):
                    if child.type in ['function_declaration', 'class_declaration', 'interface_declaration']:
                        return self._get_identifier_name(child)
                    elif child.type == 'variable_declaration':
                        names = self._extract_variable_names(child)
                        return names[0] if names else 'unknown'
                    elif child.type == 'export_clause':
                        names = self._extract_export_names(child)
                        return names[0] if names else 'unknown'

        return 'default'

    def _extract_export_names(self, export_clause: Any) -> List[str]:
        """Extract names from export clause."""
        names = []
        if hasattr(export_clause, 'children'):
            for child in export_clause.children:
                if hasattr(child, 'type') and child.type == 'export_specifier':
                    if hasattr(child, 'children'):
                        for grandchild in child.children:
                            if hasattr(grandchild, 'type') and grandchild.type == 'identifier':
                                names.append(self._get_node_text(grandchild))
                                break
        return names

    def _is_function_assignment(self, declarator_node: Any) -> bool:
        """Check if a variable declarator is a function assignment."""
        if hasattr(declarator_node, 'children'):
            for child in declarator_node.children:
                if hasattr(child, 'type') and child.type in [
                    'function_expression',
                    'arrow_function',
                    'async_function_expression'
                ]:
                    return True
        return False

    def _extract_variable_names(self, var_node: Any) -> List[str]:
        """Extract variable names from variable declaration."""
        names = []
        if hasattr(var_node, 'children'):
            for child in var_node.children:
                if hasattr(child, 'type') and child.type == 'variable_declarator':
                    name = self._get_identifier_name(child)
                    if name:
                        names.append(name)
                    else:
                        # Handle destructuring
                        names.extend(self._extract_destructuring_names(child))
        return names

    def _extract_destructuring_names(self, declarator_node: Any) -> List[str]:
        """Extract names from destructuring patterns."""
        names = []
        if hasattr(declarator_node, 'children'):
            for child in declarator_node.children:
                if hasattr(child, 'type'):
                    if child.type == 'object_pattern':
                        names.extend(self._extract_object_pattern_names(child))
                    elif child.type == 'array_pattern':
                        names.extend(self._extract_array_pattern_names(child))
        return names

    def _extract_object_pattern_names(self, pattern_node: Any) -> List[str]:
        """Extract names from object destructuring pattern."""
        names = []
        if hasattr(pattern_node, 'children'):
            for child in pattern_node.children:
                if hasattr(child, 'type') and child.type == 'pair_pattern':
                    if hasattr(child, 'children'):
                        for grandchild in child.children:
                            if hasattr(grandchild, 'type') and grandchild.type == 'identifier':
                                names.append(self._get_node_text(grandchild))
        return names

    def _extract_array_pattern_names(self, pattern_node: Any) -> List[str]:
        """Extract names from array destructuring pattern."""
        names = []
        if hasattr(pattern_node, 'children'):
            for child in pattern_node.children:
                if hasattr(child, 'type') and child.type == 'identifier':
                    names.append(self._get_node_text(child))
        return names

    def _get_method_name(self, method_node: Any) -> str:
        """Get the name of a method node."""
        if hasattr(method_node, 'children'):
            for child in method_node.children:
                if hasattr(child, 'type') and child.type == 'property_identifier':
                    return self._get_node_text(child)
        return ""
