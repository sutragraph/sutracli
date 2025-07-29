"""
Simplified Java Symbol Extractor

Extracts symbols from Java AST nodes with minimal boilerplate.
"""
from typing import Any, List, Set
from . import BaseExtractor, Symbol, SymbolType

class JavaExtractor(BaseExtractor):
    """Simplified Java symbol extractor."""

    @property
    def language(self) -> str:
        """Return the language this extractor handles."""
        return "java"

    def _extract_definitions(self, ast_node: Any, symbols: List[Symbol]) -> None:
        """First pass: Extract only definitions and declarations."""
        self._extract_recursive(ast_node, symbols, extract_calls=False)

    def _extract_calls(self, ast_node: Any, symbols: List[Symbol], defined_names: Set[str]) -> None:
        """Second pass: Extract function/method calls for defined symbols only."""
        self._extract_recursive(ast_node, symbols, extract_calls=True, defined_names=defined_names)

    def _get_keywords(self) -> Set[str]:
        """Java keywords, built-ins, and common stdlib method names to filter out."""

        keywords = {
            'abstract','assert','boolean','break','byte','case','catch','char','class','const','continue',
            'default','do','double','else','enum','extends','final','finally','float','for','goto','if',
            'implements','import','instanceof','int','interface','long','native','new','package','private',
            'protected','public','return','short','static','strictfp','super','switch','synchronized',
            'this','throw','throws','transient','try','void','volatile','while','sealed', 'permits', 'record',
            'var','yield', 'module','requires','exports','opens','uses','provides','with','transitive'
        }

        builtins = {
            # Core types
            'Object','String','Integer','Long','Short','Byte','Double','Float','Character','Boolean','Number',
            'Void','Class','Enum','Thread','Runnable','Math','System','StringBuilder','StringBuffer',
            # Collections
            'List','ArrayList','LinkedList','Vector','Stack','Queue','Deque','PriorityQueue',
            'Set','HashSet','LinkedHashSet','TreeSet','EnumSet',
            'Map','HashMap','LinkedHashMap','TreeMap','Hashtable','Properties','WeakHashMap','IdentityHashMap',
            'Collections','Arrays','Objects',
            # Streams and I/O
            'InputStream','OutputStream','FileInputStream','FileOutputStream','BufferedInputStream',
            'BufferedOutputStream','DataInputStream','DataOutputStream','PrintStream','PrintWriter',
            'Reader','Writer','FileReader','FileWriter','BufferedReader','BufferedWriter',
            'File','Path','Paths','Files',
            # Time
            'Date','Calendar','TimeZone','LocalDate','LocalTime','LocalDateTime','ZonedDateTime','Instant',
            'Duration','Period','ZoneId','OffsetDateTime','OffsetTime',
            # Concurrency
            'Thread','Runnable','Callable','Executor','Executors','Future','CompletableFuture','CountDownLatch',
            'Semaphore','ReentrantLock','ReadWriteLock','AtomicInteger','AtomicLong','ConcurrentHashMap',
            # Exceptions
            'Exception','RuntimeException','Error','Throwable','NullPointerException','IndexOutOfBoundsException',
            'ClassCastException','IllegalArgumentException','IllegalStateException','IOException','FileNotFoundException',
            'InterruptedException','CloneNotSupportedException','AssertionError','ArithmeticException',
            'SecurityException','UnsupportedOperationException'
        }

        stdlib_methods = {
            # Object class
            'equals','hashCode','toString','getClass','clone','notify','notifyAll','wait','finalize',
            # String
            'charAt','codePointAt','compareTo','concat','contains','endsWith','equalsIgnoreCase','format',
            'getBytes','getChars','indexOf','isEmpty','join','lastIndexOf','length','matches','replace',
            'replaceAll','split','startsWith','strip','stripLeading','stripTrailing','substring','toCharArray',
            'toLowerCase','toUpperCase','trim','valueOf',
            # Collections/Lists
            'add','addAll','clear','contains','containsAll','get','indexOf','isEmpty','iterator','listIterator',
            'remove','removeAll','retainAll','set','size','sort','subList','toArray','replaceAll',
            # Maps
            'put','putAll','putIfAbsent','remove','getOrDefault','containsKey','containsValue','keySet',
            'values','entrySet','compute','computeIfAbsent','computeIfPresent','merge','forEach','replace',
            # Arrays/Collections utils
            'asList','binarySearch','copyOf','equals','fill','hashCode','parallelSort','sort','stream',
            # System/Math
            'currentTimeMillis','nanoTime','arraycopy','exit','gc','identityHashCode','lineSeparator','setOut',
            'abs','ceil','floor','max','min','random','round','signum','sqrt','pow','log','log10','exp',
            # Threads/Futures
            'run','start','join','sleep','yield','interrupt','isAlive','submit','invokeAll','invokeAny','cancel'
        }

        return keywords | builtins | stdlib_methods

    def _extract_recursive(self, node: Any, symbols: List[Symbol], extract_calls: bool = False, defined_names: Set[str] = None):
        """Recursively extract symbols."""
        if not hasattr(node, 'type'):
            return

        node_type = node.type

        if extract_calls and defined_names is not None:
            # Second pass: Extract calls to defined symbols
            if node_type == 'method_invocation':
                name = self._extract_call_name(node)
                if name and name in defined_names and self._is_valid_symbol(name):
                    symbols.append(self._create_symbol(node, name, SymbolType.METHOD))
            elif node_type == 'field_access':
                name = self._extract_attribute_name(node)
                if name and name in defined_names and self._is_valid_symbol(name):
                    symbols.append(self._create_symbol(node, name, SymbolType.FIELD))
        else:
            # First pass: definitions
            if node_type == 'class_declaration':
                name = self._find_identifier(node)
                if name and self._is_valid_symbol(name):
                    symbols.append(self._create_symbol(node, name, SymbolType.CLASS))

            elif node_type == 'method_declaration':
                name = self._find_identifier(node)
                if name and self._is_valid_symbol(name):
                    symbols.append(self._create_symbol(node, name, SymbolType.METHOD))

            elif node_type == 'constructor_declaration':
                name = self._find_identifier(node)
                if name and self._is_valid_symbol(name):
                    symbols.append(self._create_symbol(node, name, SymbolType.CONSTRUCTOR))

            elif node_type == 'field_declaration':
                names = self._extract_variable_declarators(node)
                for name in names:
                    if self._is_valid_symbol(name):
                        symbol_type = SymbolType.CONSTANT if name.isupper() else SymbolType.FIELD
                        symbols.append(self._create_symbol(node, name, symbol_type))

            elif node_type == 'variable_declarator':
                name = self._find_identifier(node)
                if name and self._is_valid_symbol(name):
                    symbol_type = SymbolType.VARIABLE if not name.isupper() else SymbolType.CONSTANT
                    symbols.append(self._create_symbol(node, name, symbol_type))

            elif node_type == 'formal_parameter':
                name = self._find_identifier(node)
                if name and self._is_valid_symbol(name):
                    symbols.append(self._create_symbol(node, name, SymbolType.PARAMETER))

            elif node_type == 'annotation':
                name = self._find_identifier(node)
                if name and self._is_valid_symbol(name):
                    symbols.append(self._create_symbol(node, name, SymbolType.ANNOTATION))

            elif node_type in ['import_declaration','package_declaration']:
                names = self._extract_import_names(node)
                for name in names:
                    if self._is_valid_symbol(name):
                        symbols.append(self._create_symbol(node, name, SymbolType.ALIAS))

        if hasattr(node, 'children'):
            for child in node.children:
                self._extract_recursive(child, symbols, extract_calls, defined_names)

    def _extract_variable_declarators(self, node: Any) -> List[str]:
        """Extract variable names from a field or local variable declaration."""
        names = []
        if hasattr(node, 'children'):
            for child in node.children:
                if hasattr(child, 'type') and child.type == 'variable_declarator':
                    ident = self._find_identifier(child)
                    if ident:
                        names.append(ident)
        return names

    def _extract_import_names(self, node: Any) -> List[str]:
        """Extract imported class or package names."""
        names = []
        if hasattr(node, 'children'):
            for child in node.children:
                if hasattr(child, 'type'):
                    if child.type == 'scoped_identifier' or child.type == 'identifier':
                        text = self._get_text(child)
                        if text:
                            names.append(text.split('.')[-1])
        return names

    def _extract_call_name(self, node: Any) -> str:
        """Extract method name from a method_invocation node."""
        if hasattr(node, 'children'):
            for child in node.children:
                if hasattr(child, 'type') and child.type == 'identifier':
                    return self._get_text(child)
        return ""

    def _extract_attribute_name(self, node: Any) -> str:
        """Extract field or method name from field_access node."""
        if hasattr(node, 'children'):
            for child in reversed(node.children):
                if hasattr(child, 'type') and child.type == 'identifier':
                    return self._get_text(child)
        return ""

    def _find_identifier(self, node: Any) -> str:
        """Find the first identifier in a node."""
        if not hasattr(node, 'children'):
            return ""
        for child in node.children:
            if hasattr(child, 'type') and child.type == 'identifier':
                return self._get_text(child)
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
