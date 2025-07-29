"""
Java AST Extractor

Extracts Java code constructs from AST trees.
"""

from typing import Any, List
from . import BaseExtractor, BlockType, CodeBlock


class JavaExtractor(BaseExtractor):
    """Extractor for Java code blocks."""

    def __init__(self, language: str = "java", symbol_extractor=None):
        super().__init__(language, symbol_extractor)

    def _get_identifier_name(self, node: Any) -> str:
        """Get identifier name from a node."""
        if node and hasattr(node, 'children'):
            for child in node.children:
                if hasattr(child, "type") and child.type == "identifier":
                    return self._get_node_text(child)
        return ""

    def extract_imports(self, node: Any) -> List[CodeBlock]:
        """Extract import statements."""
        try:
            blocks = []
            import_nodes = self._traverse_nodes(node, ["import_declaration"])
            for import_node in import_nodes:
                start_line, end_line, start_col, end_col = self._get_node_position(import_node)
                content = self._get_node_text(import_node)
                # Extract the module name or first imported name as the identifier
                name = self._extract_import_name(import_node)
                blocks.append(
                    self._create_code_block(
                        BlockType.IMPORT,
                        name,
                        content,
                        start_line,
                        end_line,
                        start_col,
                        end_col,
                        import_node,
                    )
                )

            return blocks
        except Exception as e:
            print(f"[extract_imports] Exception: {e}")
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
                    blocks.append(
                        self._create_code_block(
                            BlockType.INTERFACE,
                            name,
                            content,
                            start_line,
                            end_line,
                            start_col,
                            end_col,
                            interface_node
                        )
                    )
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
                    blocks.append(
                        self._create_code_block(
                            BlockType.ENUM,
                            name,
                            content,
                            start_line,
                            end_line,
                            start_col,
                            end_col
                        )
                    )
            return blocks
        except Exception as e:
            print(f"[extract_enums] Exception: {e}")
            raise


    def extract_functions(self, node: Any) -> List[CodeBlock]:
        """Extract method declarations with nested elements as children."""
        functions = self._extract_top_level_functions(node)
        for function in functions:
            function.children = self._extract_nested_elements(node, function)
        return functions

    def extract_classes(self, node: Any) -> List[CodeBlock]:
        """Extract class declarations with nested elements as children."""
        classes = self._extract_top_level_classes(node)
        for class_block in classes:
            class_block.children = self._extract_nested_elements(node, class_block)
        return classes

    def extract_variables(self, node: Any) -> List[CodeBlock]:
        """Extract field declarations."""
        return self._extract_top_level_variables(node)

    def extract_all(self, root_node: Any) -> List[CodeBlock]:
        """Java-specific implementation of extract_all."""
        self._blocks = []
        self._extract_all_symbols(root_node)

        # Java-specific order
        self._blocks.extend(self.extract_imports(root_node))
        self._blocks.extend(self.extract_variables(root_node))
        self._blocks.extend(self.extract_classes(root_node))
        self._blocks.extend(self.extract_functions(root_node))

        return self._blocks

    def _extract_top_level_functions(self, node: Any) -> List[CodeBlock]:
        """Extract only top-level method declarations."""
        blocks = []
        if hasattr(node, "children"):
            for child in node.children:
                if hasattr(child, "type") and child.type == "method_declaration":
                    name = self._get_identifier_name(child)
                    if name:
                        start_line, end_line, start_col, end_col = self._get_node_position(
                            child
                        )
                        content = self._get_node_text(child)
                        blocks.append(
                            self._create_code_block(
                                BlockType.FUNCTION,
                                name,
                                content,
                                start_line,
                                end_line,
                                start_col,
                                end_col,
                                child,
                            )
                        )
        return blocks

    def _extract_nested_functions(self, parent_node: Any) -> List[CodeBlock]:
        """Extract method and constructor declarations nested within a Java parent node (not top-level)."""
        nested_methods = []

        def traverse(node, depth=0):
            if hasattr(node, 'type') and node.type in ['method_declaration', 'constructor_declaration'] and depth > 0:
                name = self._get_identifier_name(node)
                if name:
                    start_line, end_line, start_col, end_col = self._get_node_position(node)
                    content = self._get_node_text(node)
                    nested_methods.append(
                        self._create_code_block(
                            BlockType.FUNCTION,
                            name,
                            content,
                            start_line,
                            end_line,
                            start_col,
                            end_col,
                            node
                        )
                    )
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
                                nested_variables.append(
                                    self._create_code_block(
                                        BlockType.VARIABLE,
                                        name,
                                        content,
                                        start_line,
                                        end_line,
                                        start_col,
                                        end_col,
                                        node
                                    )
                                )
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
                    nested_classes.append(
                        self._create_code_block(
                            BlockType.CLASS,
                            name,
                            content,
                            start_line,
                            end_line,
                            start_col,
                            end_col,
                            node
                        )
                    )
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
                    nested_interfaces.append(
                        self._create_code_block(
                            BlockType.INTERFACE,
                            name,
                            content,
                            start_line,
                            end_line,
                            start_col,
                            end_col,
                            node
                        )
                    )
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
                    nested_enums.append(
                        self._create_code_block(
                            BlockType.ENUM,
                            name,
                            content,
                            start_line,
                            end_line,
                            start_col,
                            end_col,
                            node
                        )
                    )
                    return
            if hasattr(node, 'children'):
                for child in node.children:
                    traverse(child, depth + 1)

        if hasattr(parent_node, 'children'):
            for child in parent_node.children:
                traverse(child, 0)

        return nested_enums


    def _extract_top_level_classes(self, node: Any) -> List[CodeBlock]:
        """Extract only top-level class declarations."""
        blocks = []
        if hasattr(node, "children"):
            for child in node.children:
                if hasattr(child, "type") and child.type == "class_declaration":
                    name = self._get_identifier_name(child)
                    if name:
                        start_line, end_line, start_col, end_col = self._get_node_position(
                            child
                        )
                        content = self._get_node_text(child)
                        blocks.append(
                            self._create_code_block(
                                BlockType.CLASS,
                                name,
                                content,
                                start_line,
                                end_line,
                                start_col,
                                end_col,
                                child,
                            )
                        )
        return blocks

    def _extract_top_level_variables(self, node: Any) -> List[CodeBlock]:
        """Extract only top-level field declarations."""
        blocks = []
        if hasattr(node, "children"):
            for child in node.children:
                if hasattr(child, "type") and child.type == "field_declaration":
                    names = self._extract_field_names(child)
                    if names:
                        start_line, end_line, start_col, end_col = self._get_node_position(
                            child
                        )
                        content = self._get_node_text(child)
                        for name in names:
                            blocks.append(
                                self._create_code_block(
                                    BlockType.VARIABLE,
                                    name,
                                    content,
                                    start_line,
                                    end_line,
                                    start_col,
                                    end_col,
                                    child,
                                )
                            )
        return blocks

    def _extract_field_names(self, field_node: Any) -> List[str]:
        """Extract variable names from field declaration."""
        names = []
        if hasattr(field_node, "children"):
            for child in field_node.children:
                if hasattr(child, "type") and child.type == "variable_declarator":
                    name = self._get_identifier_name(child)
                    if name:
                        names.append(name)
        return names

