"""
Simplified TypeScript/JavaScript Symbol Extractor

Extracts symbols from TypeScript/JavaScript AST nodes with minimal boilerplate.
"""

from typing import Any, List, Set
from . import BaseExtractor, Symbol, SymbolType


class TypeScriptExtractor(BaseExtractor):
    """Simplified TypeScript/JavaScript symbol extractor."""

    @property
    def language(self) -> str:
        """Return the language this extractor handles."""
        return "typescript"

    def _extract_definitions(self, ast_node: Any, symbols: List[Symbol]) -> None:
        """First pass: Extract only definitions and declarations."""
        self._extract_recursive(ast_node, symbols, extract_calls=False)

    def _extract_calls(self, ast_node: Any, symbols: List[Symbol], defined_names: Set[str]) -> None:
        """Second pass: Extract function/method calls for defined symbols only."""
        self._extract_recursive(ast_node, symbols, extract_calls=True, defined_names=defined_names)

    def _get_keywords(self) -> Set[str]:
        """TypeScript/JavaScript keywords and built-ins to filter out."""
        # Language keywords
        keywords = {
            'abstract', 'as', 'any', 'async', 'await', 'boolean', 'break', 'case',
            'catch', 'class', 'const', 'constructor', 'continue', 'debugger',
            'declare', 'default', 'delete', 'do', 'else', 'enum', 'export',
            'extends', 'false', 'finally', 'for', 'from', 'function', 'get', 'if',
            'implements', 'import', 'in', 'infer', 'instanceof', 'interface', 'is',
            'keyof', 'let', 'module', 'namespace', 'native', 'new', 'never', 'null',
            'of', 'package', 'private', 'protected', 'public', 'readonly', 'require',
            'return', 'set', 'static', 'super', 'switch', 'this', 'throw', 'true',
            'try', 'type', 'typeof', 'undefined', 'unknown', 'var', 'void', 'while',
            'with', 'yield'
        }

        # Built-in types
        types = {
            'any', 'bigint', 'boolean', 'never', 'null', 'number', 'object',
            'string', 'symbol', 'undefined', 'unknown', 'void'
        }

        # Common built-in objects and APIs
        builtins = {
            'Array', 'Boolean', 'Console', 'Date', 'Document', 'Error', 'Function',
            'JSON', 'Math', 'Number', 'Object', 'Promise', 'RegExp', 'String',
            'Symbol', 'Window', 'console', 'document', 'global', 'process',
            'window', 'setTimeout', 'setInterval', 'clearTimeout', 'clearInterval'
        }

        return keywords | types | builtins

    def _extract_recursive(self, node: Any, symbols: List[Symbol], extract_calls: bool = False, defined_names: Set[str] = None):
        """Recursively extract symbols."""
        if not hasattr(node, 'type'):
            return

        node_type = node.type

        if extract_calls and defined_names is not None:
            # Second pass: Extract calls to defined symbols
            if node_type == 'call_expression':
                name = self._extract_call_name(node)
                if name and name in defined_names and self._is_valid_symbol(name):
                    symbols.append(self._create_symbol(node, name, SymbolType.FUNCTION))

            elif node_type == 'member_expression':
                name = self._extract_member_name(node)
                if name and name in defined_names and self._is_valid_symbol(name):
                    symbols.append(self._create_symbol(node, name, SymbolType.METHOD))
        else:
            # First pass: Extract definitions only
            if node_type in ['function_declaration', 'function', 'method_definition']:
                name = self._find_identifier(node)
                if name and self._is_valid_symbol(name):
                    symbols.append(self._create_symbol(node, name, SymbolType.FUNCTION))

            elif node_type == 'arrow_function':
                # Arrow functions often don't have names, skip them
                pass

            elif node_type == 'class_declaration':
                name = self._find_identifier(node)
                if name and self._is_valid_symbol(name):
                    symbols.append(self._create_symbol(node, name, SymbolType.CLASS))

            elif node_type == 'interface_declaration':
                name = self._find_identifier(node)
                if name and self._is_valid_symbol(name):
                    symbols.append(self._create_symbol(node, name, SymbolType.INTERFACE))

            elif node_type in ['variable_declaration', 'lexical_declaration']:
                names = self._extract_variable_names(node)
                for name in names:
                    if self._is_valid_symbol(name):
                        symbol_type = SymbolType.CONSTANT if self._is_const_declaration(node) else SymbolType.VARIABLE
                        symbols.append(self._create_symbol(node, name, symbol_type))

            elif node_type == 'type_alias_declaration':
                name = self._find_identifier(node)
                if name and self._is_valid_symbol(name):
                    symbols.append(self._create_symbol(node, name, SymbolType.TYPE))

            elif node_type == 'enum_declaration':
                name = self._find_identifier(node)
                if name and self._is_valid_symbol(name):
                    symbols.append(self._create_symbol(node, name, SymbolType.ENUM))

            elif node_type == 'enum_body':
                # Extract enum members
                names = self._extract_enum_members(node)
                for name in names:
                    if self._is_valid_symbol(name):
                        symbols.append(self._create_symbol(node, name, SymbolType.ENUM_MEMBER))

            elif node_type in ['parameter', 'required_parameter', 'optional_parameter']:
                name = self._find_identifier(node)
                if name and self._is_valid_symbol(name):
                    symbols.append(self._create_symbol(node, name, SymbolType.PARAMETER))

            elif node_type in ['property_signature', 'method_signature', 'property_identifier']:
                name = self._get_text(node) if node_type == 'property_identifier' else self._find_identifier(node)
                if name and self._is_valid_symbol(name):
                    symbols.append(self._create_symbol(node, name, SymbolType.PROPERTY))

            elif node_type in ['import_statement', 'import_declaration']:
                names = self._extract_import_names(node)
                for name in names:
                    if self._is_valid_symbol(name):
                        symbols.append(self._create_symbol(node, name, SymbolType.ALIAS))

            elif node_type in ['export_statement', 'export_declaration']:
                # Export statements - let recursion handle nested elements
                pass

        # Recurse into children
        if hasattr(node, 'children'):
            for child in node.children:
                self._extract_recursive(child, symbols, extract_calls, defined_names)

    def _extract_variable_names(self, node: Any) -> List[str]:
        """Extract variable names from declarations."""
        names = []
        if hasattr(node, 'children'):
            for child in node.children:
                if hasattr(child, 'type'):
                    if child.type == 'variable_declarator':
                        name = self._find_identifier(child)
                        if name:
                            names.append(name)
                    elif child.type == 'identifier':
                        name = self._get_text(child)
                        if name:
                            names.append(name)
        return names

    def _extract_enum_members(self, node: Any) -> List[str]:
        """Extract enum member names."""
        names = []
        if hasattr(node, 'children'):
            for child in node.children:
                if hasattr(child, 'type') and child.type == 'property_identifier':
                    name = self._get_text(child)
                    if name:
                        names.append(name)
                elif hasattr(child, 'children'):
                    # Look deeper for identifiers
                    for grandchild in child.children:
                        if hasattr(grandchild, 'type') and grandchild.type == 'property_identifier':
                            name = self._get_text(grandchild)
                            if name:
                                names.append(name)
        return names

    def _extract_import_names(self, node: Any) -> List[str]:
        """Extract imported names and aliases."""
        names = []
        if hasattr(node, 'children'):
            for child in node.children:
                if hasattr(child, 'type'):
                    if child.type == 'import_clause':
                        names.extend(self._extract_import_clause_names(child))
                    elif child.type == 'identifier':
                        name = self._get_text(child)
                        if name:
                            names.append(name)
        return names

    def _extract_import_clause_names(self, node: Any) -> List[str]:
        """Extract names from import clause."""
        names = []
        if hasattr(node, 'children'):
            for child in node.children:
                if hasattr(child, 'type'):
                    if child.type == 'identifier':
                        name = self._get_text(child)
                        if name:
                            names.append(name)
                    elif child.type == 'named_imports':
                        names.extend(self._extract_named_imports(child))
        return names

    def _extract_named_imports(self, node: Any) -> List[str]:
        """Extract names from named imports."""
        names = []
        if hasattr(node, 'children'):
            for child in node.children:
                if hasattr(child, 'type'):
                    if child.type == 'import_specifier':
                        # Look for identifier or alias
                        name = self._find_identifier(child)
                        if name:
                            names.append(name)
        return names

    def _is_const_declaration(self, node: Any) -> bool:
        """Check if this is a const declaration."""
        if hasattr(node, 'children'):
            for child in node.children:
                if hasattr(child, 'text') and child.text == b'const':
                    return True
        return False

    def _find_identifier(self, node: Any) -> str:
        """Find the first identifier in a node."""
        if not hasattr(node, 'children'):
            return ""

        for child in node.children:
            if hasattr(child, 'type') and child.type == 'identifier':
                return self._get_text(child)
            # Recursively search in child nodes
            name = self._find_identifier(child)
            if name:
                return name
        return ""

    def _get_text(self, node: Any) -> str:
        """Get text content from a node."""
        if hasattr(node, 'text') and node.text:
            try:
                return node.text.decode('utf-8')
            except (UnicodeDecodeError, AttributeError):
                return ""
        return ""

    def _extract_call_name(self, node: Any) -> str:
        """Extract function name from a call expression."""
        if hasattr(node, 'children'):
            for child in node.children:
                if hasattr(child, 'type'):
                    if child.type == 'identifier':
                        return self._get_text(child)
                    elif child.type == 'member_expression':
                        # For method calls like obj.method()
                        return self._extract_member_name(child)
        return ""

    def _extract_member_name(self, node: Any) -> str:
        """Extract method name from member expression."""
        if hasattr(node, 'children'):
            # Look for property_identifier (method name)
            for child in node.children:
                if hasattr(child, 'type') and child.type == 'property_identifier':
                    return self._get_text(child)
        return ""

    