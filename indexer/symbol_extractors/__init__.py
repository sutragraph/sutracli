"""
Simple Symbol Extraction System

Extracts user-defined identifiers from code using language-specific extractors.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, List, Set, Optional
from dataclasses import dataclass


class SymbolType(Enum):
    """Symbol types supported across languages."""
    VARIABLE = "variable"
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    PARAMETER = "parameter"
    PROPERTY = "property"
    CONSTANT = "constant"
    ALIAS = "alias"
    MODULE = "module"
    NAMESPACE = "namespace"
    INTERFACE = "interface"
    TYPE = "type"
    ENUM = "enum"
    ENUM_MEMBER = "enum_member"
    DECORATOR = "decorator"
    UNKNOWN = "unknown"


@dataclass
class Symbol:
    """Represents a symbol found in code."""
    name: str
    symbol_type: SymbolType
    start_line: int
    end_line: int
    start_col: int
    end_col: int


class BaseExtractor(ABC):
    def __init__(self):
        self.keywords = self._get_keywords()

    @property
    @abstractmethod
    def language(self) -> str:
        """Return the language this extractor handles."""
        pass

    def extract_symbols(self, ast_node: Any, code_content: str) -> List[Symbol]:
        """Two-pass symbol extraction to avoid third-party library symbols."""
        # First pass: Extract definitions and declarations only
        definitions = []
        self._extract_definitions(ast_node, definitions)

        # Create a set of defined symbol names for quick lookup
        defined_names = {symbol.name for symbol in definitions}

        # Second pass: Extract function calls, but only for symbols we defined
        calls = []
        self._extract_calls(ast_node, calls, defined_names)

        # Combine and return all symbols
        return definitions + calls

    @abstractmethod
    def _extract_definitions(self, ast_node: Any, symbols: List[Symbol]) -> None:
        """First pass: Extract only definitions and declarations."""
        pass

    @abstractmethod
    def _extract_calls(self, ast_node: Any, symbols: List[Symbol], defined_names: Set[str]) -> None:
        """Second pass: Extract function/method calls for defined symbols only."""
        pass

    @abstractmethod
    def _get_keywords(self) -> Set[str]:
        pass

    def _is_valid_symbol(self, name: str) -> bool:
        if not name or not name.isidentifier():
            return False
        return name not in self.keywords

    def _create_symbol(self, node: Any, name: str, symbol_type: SymbolType) -> Symbol:
        start_line = getattr(node, 'start_point', [0])[0] + 1
        end_line = getattr(node, 'end_point', [0])[0] + 1
        start_col = getattr(node, 'start_point', [0, 0])[1]
        end_col = getattr(node, 'end_point', [0, 0])[1]
        return Symbol(name, symbol_type, start_line, end_line, start_col, end_col)

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

    def _extract_recursive(self, node: Any, symbols: List[Symbol], extract_calls: bool = False, defined_names: Optional[Set[str]] = None):
        """Helper method for recursive extraction that can be used by subclasses."""
        if not hasattr(node, 'type'):
            return

        if extract_calls and defined_names is not None:
            self._extract_call_symbols(node, symbols, defined_names)
        else:
            self._extract_definition_symbols(node, symbols)

        # Recurse into children
        if hasattr(node, 'children'):
            for child in node.children:
                self._extract_recursive(child, symbols, extract_calls, defined_names)

    def _extract_definition_symbols(self, node: Any, symbols: List[Symbol]):
        """Extract definition symbols from a node. To be overridden by subclasses."""
        pass

    def _extract_call_symbols(self, node: Any, symbols: List[Symbol], defined_names: Set[str]):
        """Extract call symbols from a node. To be overridden by subclasses."""
        pass


class Extractor:
    """Main extractor that uses language-specific extractors."""

    def __init__(self):
        self._extractors = {}
        self._register_extractors()

    def register_extractor(self, language: str, extractor: BaseExtractor):
        """Register an extractor for a specific language."""
        self._extractors[language] = extractor

    def _register_extractors(self):
        """Register available language extractors."""
        from .typescript_extractor import TypeScriptExtractor
        from .python_extractor import PythonExtractor

        self.register_extractor("typescript", TypeScriptExtractor())
        self.register_extractor("python", PythonExtractor())

    def extract_symbols(self, ast_node: Any, code_content: str, language: str) -> List[Symbol]:
        """Extract symbols using the appropriate language extractor."""
        extractor = self._extractors.get(language)
        if not extractor:
            return []

        try:
            return extractor.extract_symbols(ast_node, code_content)
        except Exception:
            return []

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        return list(self._extractors.keys())
