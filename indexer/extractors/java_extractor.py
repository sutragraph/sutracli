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
        if node and hasattr(node, 'children'):
            print("node.children", node.children)
            for child in node.children:
                if hasattr(child, 'type') and child.type == 'identifier':
                    return self._get_node_text(child)
        return ""

    def extract_imports(self, node: Any) -> List[CodeBlock]:
        """Extract import statements."""
        try:
            blocks = []
            import_nodes = self._traverse_nodes(node, ['import_declaration'])
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
        except Exception as e:
            print(f"[extract_imports] Exception: {e}")
            raise
    
    def extract_exports(self, node: Any) -> List[CodeBlock]:
        """Java does not have export statements; return empty list."""
        try:
            return []
        except Exception as e:
            print(f"[extract_exports] Exception: {e}")
            raise


    def _extract_import_name(self, import_node: Any) -> str:
        """Extract the imported package or class name from an import statement (Java)."""
        if import_node and hasattr(import_node, 'children'):
            for child in import_node.children:
                if hasattr(child, 'type') and child.type == 'scoped_identifier':
                    return self._get_node_text(child)
                elif hasattr(child, 'type') and child.type == 'identifier':
                    return self._get_node_text(child)
        return 'unknown'


    def extract_interfaces(self, node: Any) -> List[CodeBlock]:
        """Extract interface declarations from Java AST."""
        try:
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
        except Exception as e:
            print(f"[extract_interfaces] Exception: {e}")
            raise

    def extract_enums(self, node: Any) -> List[CodeBlock]:
        """Extract enum declarations from Java AST."""
        try:
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
        except Exception as e:
            print(f"[extract_enums] Exception: {e}")
            raise

    def extract_methods(self, node: Any) -> List[CodeBlock]:
        """Extract method declarations from Java AST."""
        try:
            blocks = []
            method_nodes = self._traverse_nodes(node, ['method_declaration', 'constructor_declaration'])
            for method_node in method_nodes:
                name = self._get_identifier_name(method_node)
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
            return blocks
        except Exception as e:
            print(f"[extract_methods] Exception: {e}")
            raise

    def extract_fields(self, node: Any) -> List[CodeBlock]:
        """Extract field (variable) declarations from Java AST."""
        try:
            blocks = []
            field_nodes = self._traverse_nodes(node, ['field_declaration'])
            for field_node in field_nodes:
                # Java fields can have multiple variable_declarators
                if field_node and hasattr(field_node, 'children'):
                    for child in field_node.children:
                        if hasattr(child, 'type') and child.type == 'variable_declarator':
                            name = self._get_identifier_name(child)
                            if name:
                                start_line, end_line, start_col, end_col = self._get_node_position(child)
                                content = self._get_node_text(child)
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
        except Exception as e:
            print(f"[extract_fields] Exception: {e}")
            raise

    def _extract_nested_functions(self, parent_node: Any) -> List[CodeBlock]:
        """Extract method and constructor declarations nested within a Java parent node (not top-level)."""
        nested_methods = []

        def traverse(node, depth=0):
            if hasattr(node, 'type') and node.type in ['method_declaration', 'constructor_declaration'] and depth > 0:
                name = self._get_identifier_name(node)
                if name:
                    start_line, end_line, start_col, end_col = self._get_node_position(node)
                    content = self._get_node_text(node)
                    nested_methods.append(CodeBlock(
                        type=BlockType.FUNCTION,
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

        return nested_methods

    def _extract_nested_variables(self, parent_node: Any) -> List[CodeBlock]:
        """Extract field (variable) declarations nested within a Java parent node (not top-level)."""
        nested_variables = []

        def traverse(node, depth=0):
            if hasattr(node, 'type') and node.type == 'field_declaration' and depth > 0:
                # Java fields can have multiple variable_declarators
                if hasattr(node, 'children'):
                    for child in node.children:
                        if hasattr(child, 'type') and child.type == 'variable_declarator':
                            name = self._get_identifier_name(child)
                            if name:
                                start_line, end_line, start_col, end_col = self._get_node_position(child)
                                content = self._get_node_text(child)
                                nested_variables.append(CodeBlock(
                                    type=BlockType.VARIABLE,
                                    name=name,
                                    content=content,
                                    start_line=start_line,
                                    end_line=end_line,
                                    start_col=start_col,
                                    end_col=end_col
                                ))
            if hasattr(node, 'children'):
                for child in node.children:
                    traverse(child, depth + 1)

        if hasattr(parent_node, 'children'):
            for child in parent_node.children:
                traverse(child, 0)

        return nested_variables

    def _extract_nested_classes(self, parent_node: Any) -> List[CodeBlock]:
        """Extract class declarations nested within a Java parent node (not top-level)."""
        nested_classes = []

        def traverse(node, depth=0):
            if hasattr(node, 'type') and node.type == 'class_declaration' and depth > 0:
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
                    return  # Do not traverse deeper from this class
            if hasattr(node, 'children'):
                for child in node.children:
                    traverse(child, depth + 1)

        if hasattr(parent_node, 'children'):
            for child in parent_node.children:
                traverse(child, 0)

        return nested_classes

    def _extract_nested_interfaces(self, parent_node: Any) -> List[CodeBlock]:
        """Extract interface declarations nested within a Java parent node (not top-level)."""
        nested_interfaces = []

        def traverse(node, depth=0):
            if hasattr(node, 'type') and node.type == 'interface_declaration' and depth > 0:
                name = self._get_identifier_name(node)
                if name:
                    start_line, end_line, start_col, end_col = self._get_node_position(node)
                    content = self._get_node_text(node)
                    nested_interfaces.append(CodeBlock(
                        type=BlockType.INTERFACE,
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

        return nested_interfaces

    def _extract_nested_enums(self, parent_node: Any) -> List[CodeBlock]:
        """Extract enum declarations nested within a Java parent node (not top-level)."""
        nested_enums = []

        def traverse(node, depth=0):
            if hasattr(node, 'type') and node.type == 'enum_declaration' and depth > 0:
                name = self._get_identifier_name(node)
                if name:
                    start_line, end_line, start_col, end_col = self._get_node_position(node)
                    content = self._get_node_text(node)
                    nested_enums.append(CodeBlock(
                        type=BlockType.ENUM,
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

        return nested_enums

