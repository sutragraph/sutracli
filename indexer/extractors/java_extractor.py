"""
Java AST Extractor

Extracts Java code constructs from AST trees.
"""

from typing import Any, List
from . import BaseExtractor, BlockType, CodeBlock


class JavaExtractor(BaseExtractor):
    """Java-specific extractor for code blocks (new convention)."""

    FUNCTION_TYPES = {"method_declaration", "constructor_declaration"}
    CLASS_TYPES = {"class_declaration"}
    INTERFACE_TYPES = {"interface_declaration"}
    ENUM_TYPES = {"enum_declaration"}
    VARIABLE_TYPES = {"field_declaration"}
    IMPORT_TYPES = {"import_declaration"}

    def __init__(self, language: str = "java", file_id: int = 0, symbol_extractor=None):
        super().__init__(language, file_id, symbol_extractor)

    def _get_identifier_name(self, node: Any) -> str:
        """Get identifier name from a node."""
        if hasattr(node, "children"):
            for child in node.children:
                if hasattr(child, "type") and child.type == "identifier":
                    return self._get_node_text(child)
        return ""

    def _extract_import_name(self, node: Any) -> str:
        """Extract the imported package or class name from an import statement (Java)."""
        if hasattr(node, "children"):
            for child in node.children:
                if hasattr(child, "type") and child.type == "scoped_identifier":
                    return self._get_node_text(child)
                elif hasattr(child, "type") and child.type == "identifier":
                    return self._get_node_text(child)
        return "unknown"

    def extract_imports(self, root_node: Any) -> List[CodeBlock]:
        """Extract import statements."""
        def process_import(node):
            name = self._extract_import_name(node)
            names = [name] if name else []
            return self._create_code_block(node, BlockType.IMPORT, names)
        return self._generic_traversal(root_node, self.IMPORT_TYPES, process_import)

    def extract_interfaces(self, root_node: Any) -> List[CodeBlock]:
        """Extract interface declarations from Java AST."""
        def process_interface(node):
            name = self._get_identifier_name(node)
            names = [name] if name else []
            return self._create_code_block(node, BlockType.INTERFACE, names)
        return self._generic_traversal(root_node, self.INTERFACE_TYPES, process_interface)

    def extract_enums(self, root_node: Any) -> List[CodeBlock]:
        """Extract enum declarations from Java AST."""
        def process_enum(node):
            name = self._get_identifier_name(node)
            names = [name] if name else []
            return self._create_code_block(node, BlockType.ENUM, names)
        return self._generic_traversal(root_node, self.ENUM_TYPES, process_enum)

    def extract_functions(self, root_node: Any) -> List[CodeBlock]:
        """Extract method declarations with nested elements as children."""
        def process_function(node):
            name = self._get_identifier_name(node)
            names = [name] if name else []
            return self._create_function_block_with_nested_extraction(
                node, BlockType.FUNCTION, names, self.FUNCTION_TYPES
            )
        return self._generic_traversal(root_node, self.FUNCTION_TYPES, process_function)

    def extract_classes(self, root_node: Any) -> List[CodeBlock]:
        """Extract class declarations with nested elements as children."""
        def process_class(node):
            name = self._get_identifier_name(node)
            names = [name] if name else []
            start_line, end_line, start_col, end_col = self._get_node_position(node)
            symbols = self._get_symbols_for_block(start_line, end_line, start_col, end_col)
            class_block = CodeBlock(
                type=BlockType.CLASS,
                name=names[0] if names else "anonymous",
                content="",
                symbols=symbols,
                start_line=start_line,
                end_line=end_line,
                start_col=start_col,
                end_col=end_col,
                id=self._hash_generator.next_id(),
            )
            # Nested: methods, variables, interfaces, enums, classes
            nested_blocks = []
            nested_blocks.extend(self._generic_traversal(node, self.FUNCTION_TYPES, process_function))
            nested_blocks.extend(self._extract_class_level_variables(node))
            nested_blocks.extend(self._generic_traversal(node, self.INTERFACE_TYPES, process_interface))
            nested_blocks.extend(self._generic_traversal(node, self.ENUM_TYPES, process_enum))
            nested_blocks.extend(self._generic_traversal(node, self.CLASS_TYPES, process_class))
            class_block.children = nested_blocks
            return class_block
        def process_function(node):
            name = self._get_identifier_name(node)
            names = [name] if name else []
            return self._create_function_block_with_nested_extraction(
                node, BlockType.FUNCTION, names, self.FUNCTION_TYPES
            )
        def process_interface(node):
            name = self._get_identifier_name(node)
            names = [name] if name else []
            return self._create_code_block(node, BlockType.INTERFACE, names)
        def process_enum(node):
            name = self._get_identifier_name(node)
            names = [name] if name else []
            return self._create_code_block(node, BlockType.ENUM, names)
        return self._generic_traversal(root_node, self.CLASS_TYPES, process_class)

    def extract_variables(self, root_node: Any) -> List[CodeBlock]:
        """Extract field declarations."""
        def process_variable(node):
            names = self._extract_field_names(node)
            return self._create_code_block(node, BlockType.VARIABLE, names) if names else None
        return self._generic_traversal(root_node, self.VARIABLE_TYPES, process_variable)

    def extract_all(self, root_node: Any) -> List[CodeBlock]:
        """Java-specific implementation of extract_all."""
        self._extract_all_symbols(root_node)
        all_blocks = []
        all_blocks.extend(self.extract_imports(root_node))
        all_blocks.extend(self.extract_exports(root_node))
        all_blocks.extend(self.extract_enums(root_node))
        all_blocks.extend(self.extract_variables(root_node))
        all_blocks.extend(self.extract_functions(root_node))
        all_blocks.extend(self.extract_classes(root_node))
        return all_blocks

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

    def _extract_class_level_variables(self, class_node: Any) -> List[CodeBlock]:
        """Extract field declarations that are direct children of a class (not nested)."""
        variables = []
        for child in class_node.children:
            if hasattr(child, "type") and child.type == "field_declaration":
                names = self._extract_field_names(child)
                if names:
                    variable_block = self._create_code_block(child, BlockType.VARIABLE, names)
                    variables.append(variable_block)
        return variables

    def _extract_names_from_node(self, node: Any) -> List[str]:
        """Extract all identifier names from a Java node (handles various patterns)."""
        names = []
        if hasattr(node, "type"):
            if node.type == "identifier":
                names.append(self._get_node_text(node))
            elif node.type == "variable_declarator":
                # Extract identifier from variable declarator
                name = self._get_identifier_name(node)
                if name:
                    names.append(name)
            elif node.type == "field_declaration":
                # Extract field names from field declaration
                names.extend(self._extract_field_names(node))
            elif node.type in ["method_declaration", "constructor_declaration"]:
                # Extract method name
                name = self._get_identifier_name(node)
                if name:
                    names.append(name)
            elif node.type in ["class_declaration", "interface_declaration", "enum_declaration"]:
                # Extract class/interface/enum name
                name = self._get_identifier_name(node)
                if name:
                    names.append(name)
            else:
                # Generic fallback: find all identifiers in the node
                def find_identifiers(n):
                    if hasattr(n, "type") and n.type == "identifier":
                        names.append(self._get_node_text(n))
                    if hasattr(n, "children"):
                        for child in n.children:
                            find_identifiers(child)
                find_identifiers(node)
        return list(set(names))  # Remove duplicates

    def _replace_nested_functions_with_references(self, original_content: str, nested_functions: List[CodeBlock]) -> str:
        """Replace nested method content with block references for Java."""
        if not nested_functions:
            return original_content
        # Sort nested functions by start position (descending) to avoid offset issues
        sorted_functions = sorted(nested_functions, key=lambda f: f.start_line, reverse=True)
        for func in sorted_functions:
            func_content = func.content
            func_lines = func_content.split("\n")
            reference = f"// [BLOCK_REF:{func.id}]"
            signature_lines = []
            brace_found = False
            for line in func_lines:
                signature_lines.append(line)
                stripped_line = line.strip()
                if stripped_line.endswith("{"):
                    signature_lines.append(f"    {reference}")
                    brace_found = True
                    break
                elif stripped_line.endswith(";"):
                    signature_lines.append(f"    {reference}")
                    brace_found = True
                    break
            if not brace_found and signature_lines:
                signature_lines.append(f"    {reference}")
            replacement = "\n".join(signature_lines)
            original_content = original_content.replace(func_content, replacement)
        return original_content

    def extract_exports(self, root_node: Any) -> List[CodeBlock]:
        """Extract export statements (Java public classes, interfaces, and methods)."""
        blocks = []
        def has_public_modifier(node: Any) -> bool:
            """Check if a node has public modifier."""
            if hasattr(node, "children"):
                for child in node.children:
                    if hasattr(child, "type") and child.type == "modifiers":
                        modifiers_text = self._get_node_text(child)
                        return "public" in modifiers_text
            return False
        def process_export(node: Any, block_type: BlockType) -> CodeBlock:
            """Process a node as an export block."""
            name = self._get_identifier_name(node)
            if name:
                start_line, end_line, start_col, end_col = self._get_node_position(node)
                content = self._get_node_text(node)
                symbols = self._get_symbols_for_block(start_line, end_line, start_col, end_col)
                return CodeBlock(
                    type=block_type,
                    name=name,
                    content=content,
                    symbols=symbols,
                    start_line=start_line,
                    end_line=end_line,
                    start_col=start_col,
                    end_col=end_col,
                    id=self._hash_generator.next_id(),
                )
            return None
        # Find public classes
        for child in root_node.children:
            if hasattr(child, "type") and child.type == "class_declaration":
                if has_public_modifier(child):
                    export_block = process_export(child, BlockType.EXPORT)
                    if export_block:
                        blocks.append(export_block)
        # Find public interfaces
        for child in root_node.children:
            if hasattr(child, "type") and child.type == "interface_declaration":
                if has_public_modifier(child):
                    export_block = process_export(child, BlockType.EXPORT)
                    if export_block:
                        blocks.append(export_block)
        # Find public enums
        for child in root_node.children:
            if hasattr(child, "type") and child.type == "enum_declaration":
                if has_public_modifier(child):
                    export_block = process_export(child, BlockType.EXPORT)
                    if export_block:
                        blocks.append(export_block)
        # Find public methods (static methods in classes can be considered exports)
        def find_public_methods(node: Any, depth: int = 0):
            if hasattr(node, "children"):
                for child in node.children:
                    if hasattr(child, "type") and child.type == "method_declaration":
                        if has_public_modifier(child):
                            # Check if it's also static (common for utility methods)
                            modifiers_text = ""
                            for grandchild in child.children:
                                if hasattr(grandchild, "type") and grandchild.type == "modifiers":
                                    modifiers_text = self._get_node_text(grandchild)
                                    break
                            if "static" in modifiers_text:
                                export_block = process_export(child, BlockType.EXPORT)
                                if export_block:
                                    blocks.append(export_block)
                    # Recursively search in nested structures
                    if depth < 2:  # Limit depth to avoid deep nesting
                        find_public_methods(child, depth + 1)
        find_public_methods(root_node)
        return blocks
