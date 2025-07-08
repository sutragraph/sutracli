"""
YAML Analyzer.

A clean, standalone analyzer that uses YAML configuration for easy language support.
Focused on clarity and maintainability with comprehensive edge resolution.
"""

import yaml
import os
from typing import Dict, List, Optional, Any
from tree_sitter import Node as TSNode, Language, Parser
from .models import ASTNode, ASTEdge, AnalysisResult
from .utils import NodeFactory, FileUtils, LanguageUtils
from loguru import logger

class UnsupportedFileAnalyzer:
    """Analyzer for unsupported file types that creates basic file nodes."""

    def __init__(self, repo_id: str, node_id_generator=None):
        """Initialize the unsupported file analyzer."""
        self.repo_id = repo_id
        self.node_factory = NodeFactory(repo_id)
        self.node_id_generator = node_id_generator

    def analyze_file(self, file_path: str) -> Dict:
        """Analyze an unsupported file and return a basic file node."""
        try:
            # Read file content
            content = FileUtils.read_file_content(file_path)

            # Detect language from extension (even if unsupported)
            language = LanguageUtils.get_language_from_file_path(file_path) or "unknown"

            # Create basic file node with unsupported flag
            file_node = self.node_factory.create_file_node(
                file_path,
                content,
                language,
                lambda: self.node_id_generator.generate_node_id(file_path),
            )

            # Add unsupported flag to metadata
            file_node.metadata["unsupported"] = True
            file_node.metadata["reason"] = "No YAML configuration or parser available"

            # Create basic result
            result = AnalysisResult(
                language=language,
                nodes=[file_node],
                edges=[],
                imports={},
                function_count=0,
            )
            return result.to_dict()

        except Exception as e:
            logger.debug(f"Error analyzing unsupported file {file_path}: {e}")
            # Return minimal error result
            error_result = AnalysisResult(
                language="unknown",
                nodes=[],
                edges=[],
                error=str(e),
            )
            return error_result.to_dict()


class YamlAnalyzer:
    """Clean, standalone YAML-driven analyzer."""

    def __init__(
        self,
        repo_id: str,
        language_path: str,
        language_name: str,
        config_path: Optional[str] = None,
        node_id_generator=None,
    ):
        """Initialize the analyzer."""
        self.repo_id = repo_id
        self.language_name = language_name

        # Initialize tree-sitter components
        self.parser = Parser()
        self.language = Language(language_path, language_name)
        self.parser.set_language(self.language)

        # Initialize components
        self.node_factory = NodeFactory(repo_id)
        self.config = self._load_config(config_path or self._get_default_config_path())
        self._query_cache = {}
        self.node_id_generator = node_id_generator

        # Analysis state
        self.nodes = []
        self.edges = []
        self.imports = {}

    def analyze_file(self, file_path: str) -> Dict:
        """Analyze a file and return its AST representation."""
        # Reset state for new file analysis
        self.nodes = []
        self.edges = []
        self.imports = {}

        try:
            # Read and parse file
            source_code = self._read_file_content(file_path)
            root_node = self._parse_source_code(source_code)

            # Create file node with deterministic ID
            file_node = self.node_factory.create_file_node(
                file_path,
                source_code,
                self.language_name,
                lambda: self.node_id_generator.generate_node_id(file_path),
            )
            self.nodes.append(file_node)

            # Process file components
            self._process_file_components(root_node, source_code, file_path, file_node)

            # Resolve edges using the analysis services
            self._resolve_all_edges()

            # Create and return result
            function_count = len([n for n in self.nodes if n.type == "function"])

            result = AnalysisResult(
                language=self.language_name,
                nodes=self.nodes,
                edges=self.edges,
                imports=self.imports.get(file_path, {}),
                function_count=function_count,
            )
            return result.to_dict()

        except Exception as e:
            logger.debug(f"Error analyzing {file_path}: {e}")
            import traceback

            traceback.logger.debug_exc()

            # Return minimal result with error
            error_result = AnalysisResult(
                language=self.language_name,
                nodes=self.nodes,
                edges=[],
                error=str(e),
            )
            return error_result.to_dict()

    def _read_file_content(self, file_path: str) -> str:
        """Read and return file content."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            raise IOError(f"Error reading file {file_path}: {e}")

    def _parse_source_code(self, source_code: str):
        """Parse source code and return AST."""
        try:
            tree = self.parser.parse(bytes(source_code, "utf-8"))
            return tree.root_node
        except Exception as e:
            raise ValueError(f"Error parsing source code: {e}")

    def _get_default_config_path(self) -> str:
        """Get default config path for language."""
        config_path = os.path.join(
            os.path.dirname(__file__), "yaml_configs", f"{self.language_name}.yaml"
        )
        return config_path

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load language configuration from YAML file."""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except (FileNotFoundError, yaml.YAMLError) as e:
            logger.debug(f"Warning: Config error for {config_path}: {e}")
            return {}

    def _process_file_components(
        self, root_node: TSNode, source_code: str, file_path: str, file_node: ASTNode
    ):
        """Process file components using YAML configuration."""
        source_bytes = source_code.encode("utf-8")

        # Process structural elements (functions, classes, etc.)
        for name, config in self.config.get("elements", {}).items():
            self._process_elements(
                name, config, root_node, source_bytes, file_path, file_node
            )

        # Process relationships (calls, imports, etc.)
        for name, config in self.config.get("relationships", {}).items():
            self._process_relationships(
                name, config, root_node, source_bytes, file_path, file_node
            )

    def _process_elements(
        self,
        element_type: str,
        config: Dict[str, Any],
        root_node: TSNode,
        source_bytes: bytes,
        file_path: str,
        file_node: ASTNode,
    ):
        """Process structural elements like functions and classes."""
        query_text = config.get("query", "")
        if not query_text:
            return

        captures = self._execute_query(query_text, root_node, element_type)
        for capture in captures:
            node = capture.get("element") or capture.get(element_type)
            if not node:
                continue

            # Extract element information
            name = self._get_node_text(
                node.child_by_field_name("name") or node, source_bytes
            )
            if not name:
                continue

            # Apply element-specific filtering
            if self._should_skip_element(element_type, name):
                continue

            # Create AST node with deterministic ID
            element_node = ASTNode(
                id=self.node_id_generator.generate_node_id(file_path),
                repo_id=self.repo_id,
                type=element_type,
                path=file_path,
                name=name,
                content=self._get_node_text(node, source_bytes),
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                metadata=self._extract_element_metadata(
                    capture, config, node, source_bytes
                ),
            )

            self.nodes.append(element_node)

            # Create contains edge
            self.edges.append(
                ASTEdge(
                    from_id=file_node.id,
                    to_id=element_node.id,
                    type="contains",
                    metadata={"relationship": f"{element_type}_definition"},
                )
            )

    def _process_relationships(
        self,
        relationship_type: str,
        config: Dict[str, Any],
        root_node: TSNode,
        source_bytes: bytes,
        file_path: str,
        file_node: ASTNode,
    ):
        """Process relationships like imports and function calls."""
        query_text = config.get("query", "")
        if not query_text:
            return

        captures = self._execute_query(query_text, root_node, relationship_type)
        for capture in captures:
            # Extract target information
            target_info = self._extract_target_info(capture, config)
            if not target_info:
                continue

            # Filter out external/system calls for 'calls' relationship type
            if relationship_type == "calls" and not self._should_create_call_edge(
                target_info
            ):
                continue

            # Create relationship edge (will be resolved later)
            edge = ASTEdge(
                from_id=file_node.id,
                to_id=None,  # Will be resolved later
                type=relationship_type,
                metadata=target_info,
            )
            self.edges.append(edge)

    def _execute_query(
        self, query_text: str, root_node: TSNode, query_name: str
    ) -> List[Dict[str, TSNode]]:
        """Execute tree-sitter query and return captures."""
        if query_name not in self._query_cache:
            try:
                self._query_cache[query_name] = self.language.query(query_text)
            except Exception as e:
                logger.debug(f"Error compiling query {query_name}: {e}")
                return []

        query = self._query_cache[query_name]
        try:
            captures = query.captures(root_node)

            # Group captures properly - each call should be a separate match
            # The issue was that we were incorrectly grouping captures from different calls
            grouped_captures = []

            # Process captures in order and create separate matches for each complete call
            i = 0
            while i < len(captures):
                node, capture_name = captures[i]
                current_match = {capture_name: node}

                # If this is a 'target' capture (direct call), it's a complete match
                if capture_name == "target":
                    grouped_captures.append(current_match)
                    i += 1
                # If this is an 'object' capture, look for the corresponding 'method'
                elif capture_name == "object":
                    # Look for the next 'method' capture
                    if i + 1 < len(captures):
                        next_node, next_capture_name = captures[i + 1]
                        if next_capture_name == "method":
                            current_match[next_capture_name] = next_node
                            grouped_captures.append(current_match)
                            i += 2  # Skip both captures
                        else:
                            # Orphaned object capture, skip it
                            i += 1
                    else:
                        # Orphaned object capture at end, skip it
                        i += 1
                else:
                    # Other capture types, treat as individual matches
                    grouped_captures.append(current_match)
                    i += 1

            return grouped_captures
        except Exception as e:
            logger.debug(f"Error executing query {query_name}: {e}")
            return []

    def _get_node_text(self, node: TSNode, source_bytes: bytes) -> str:
        """Get text content of a tree-sitter node."""
        if not node:
            return ""
        return node.text.decode("utf-8", errors="ignore")

    def _extract_element_metadata(
        self,
        capture: Dict[str, TSNode],
        config: Dict[str, Any],
        node: TSNode,
        source_bytes: bytes,
    ) -> Dict[str, Any]:
        """Extract metadata for structural elements."""
        metadata = {}

        # Extract parameters for functions
        if "parameters" in capture:
            metadata["parameters"] = self._extract_parameters_from_node(
                capture["parameters"], source_bytes
            )

        # Check for async/decorators/etc based on config
        for key, check_config in config.get("metadata_checks", {}).items():
            metadata[key] = self._check_metadata_condition(
                capture, check_config, source_bytes
            )

        return metadata

    def _extract_parameters_from_node(
        self, params_node: TSNode, source_bytes: bytes
    ) -> List[str]:
        """Extract parameter names from a parameters node."""
        if not params_node:
            return []

        parameters = []
        for child in params_node.children:
            if child.type in ["identifier", "parameter"]:
                param_name = self._get_node_text(child, source_bytes)
                if param_name:
                    parameters.append(param_name)

        return parameters

    def _check_metadata_condition(
        self,
        capture: Dict[str, TSNode],
        check_config: Dict[str, Any],
        source_bytes: bytes,
    ) -> bool:
        """Check a metadata condition based on configuration."""
        check_type = check_config.get("type", "")

        if check_type == "has_decorator":
            decorator_name = check_config.get("name", "")
            # Simple check for decorator presence
            return decorator_name in self._get_node_text(
                capture.get("element", TSNode()), source_bytes
            )

        return False

    def _extract_target_info(
        self, capture: Dict[str, TSNode], config: Dict[str, Any]
    ) -> Optional[Dict[str, str]]:
        """Extract target information for relationships."""
        target_capture = config.get("target_capture", "target")
        target_node = capture.get(target_capture)

        # Handle member/attribute calls (object.method or Class.method) - prioritize these
        object_node = capture.get("object")
        method_node = capture.get("method")

        if object_node and method_node:
            object_name = self._get_node_text(object_node, b"")
            method_name = self._get_node_text(method_node, b"")

            if object_name and method_name:
                # Determine if this is likely a static call (Class.method) or instance call (obj.method)
                call_type = self._determine_call_type(object_name)

                return {
                    "target_name": method_name,
                    "object_name": object_name,
                    "qualified_name": f"{object_name}.{method_name}",
                    "target_type": config.get("target_type", "unknown"),
                    "call_type": call_type,
                }

        # Handle simple function calls (direct target) - only if no object/method found
        if target_node:
            target_name = target_node.text.decode("utf-8", errors="ignore")
            return {
                "target_name": target_name,
                "target_type": config.get("target_type", "unknown"),
                "call_type": "direct",
            }

        return None

    def _determine_call_type(self, object_name: str) -> str:
        """Determine if this is likely a static call (Class.method) or instance call (obj.method)."""
        if not object_name:
            return "unknown"

        # Simple heuristic: if it starts with uppercase, likely a class (static call)
        if object_name[0].isupper():
            return "static"
        else:
            return "instance"

    def _should_skip_element(self, element_type: str, name: str) -> bool:
        """Determine if an element should be skipped based on configuration."""
        # Check if there are skip rules in the configuration
        skip_rules = self.config.get("skip_rules", {}).get(element_type, [])

        for rule in skip_rules:
            if rule.get("type") == "name_equals" and rule.get("value") == name:
                return True
            elif rule.get("type") == "name_not_equals" and rule.get("value") != name:
                return True

        return False

    def _should_create_call_edge(self, target_info: Dict[str, str]) -> bool:
        """Determine if a call edge should be created based on whether target is internal."""
        call_type = target_info.get("call_type", "")
        target_name = target_info.get("target_name", "")
        object_name = target_info.get("object_name", "")

        # For direct calls, check if the function exists in our nodes
        if call_type == "direct":
            return self._has_internal_function(target_name)

        # For static/instance calls, check if the object exists in our nodes
        elif call_type in ["static", "instance"] and object_name:
            return self._has_internal_object(object_name)

        return False

    def _has_internal_function(self, function_name: str) -> bool:
        """Check if a function is defined in our current nodes."""
        for node in self.nodes:
            if node.type == "function" and node.name == function_name:
                return True
        return False

    def _has_internal_object(self, object_name: str) -> bool:
        """Check if an object/class is defined in our current nodes."""
        # Check if it's a class name (for static calls)
        for node in self.nodes:
            if node.type == "class" and node.name == object_name:
                return True

        # For instance calls, use evidence-based filtering
        # Strategy: Be conservative - only allow objects we're confident are internal

        # Check if this appears to be an external object
        if self._appears_external(object_name):
            return False

        # Check if we have evidence this object is defined internally
        if self._has_internal_evidence(object_name):
            return True

        # Default: be conservative and assume external
        return False

    def _appears_external(self, name: str) -> bool:
        """Check if name appears to be external based on evidence."""
        # No hardcoded patterns - use evidence-based approach

        # If we have this object defined in our current analysis, it's internal
        for node in self.nodes:
            if node.type in ["class", "variable", "function"] and node.name == name:
                return False  # It's internal, not external

        # If it's a single letter or very short name, likely external (parameter, built-in)
        if len(name) <= 2:
            return True

        # If it's all uppercase, likely a constant or built-in
        if name.isupper() and len(name) > 2:
            return True

        # Default: assume external (conservative approach)
        return True

    def _has_internal_evidence(self, name: str) -> bool:
        """Check if we have evidence this object is defined internally."""
        # Check if we have a class, variable, or function with this name in our nodes
        for node in self.nodes:
            if node.type in ["class", "variable", "function"] and node.name == name:
                return True

        # Check if it looks like a user-defined variable (longer descriptive names)
        if len(name) > 6 and name.islower() and "_" in name:
            # Likely a user-defined variable like "user_manager", "data_processor"
            return True

        # Check if it's camelCase or PascalCase (common for user-defined objects)
        if len(name) > 4 and any(c.isupper() for c in name[1:]) and name[0].islower():
            # Likely camelCase user variable like "userManager", "dataProcessor"
            return True

        # Default: no evidence of being internal
        return False

    def _resolve_all_edges(self):
        """Resolve all edges in the current analysis."""
        # Build lookup maps for efficient resolution
        file_nodes = {}
        all_nodes = {}

        for node in self.nodes:
            all_nodes[node.id] = node
            if node.type == "file":
                file_nodes[node.path] = node

        # Resolve each edge
        for edge in self.edges:
            if edge.to_id is not None:
                continue  # Already resolved

            edge_type = edge.type
            metadata = edge.metadata

            if edge_type == "imports":
                self._resolve_import_edge(edge, metadata, file_nodes, all_nodes)
            elif edge_type == "calls":
                self._resolve_call_edge(edge, metadata, all_nodes)
            elif edge_type == "extends":
                self._resolve_inheritance_edge(edge, metadata, all_nodes)
            elif edge_type == "instantiates":
                self._resolve_instantiation_edge(edge, metadata, all_nodes)

    def _resolve_import_edge(
        self, edge: ASTEdge, metadata: Dict[str, Any], file_nodes: Dict, all_nodes: Dict
    ) -> bool:
        """Resolve import edge by finding target file."""
        target_name = metadata.get("target_name", "")
        if not target_name:
            return False

        # Try to find target file by resolving import path
        from_node = all_nodes.get(edge.from_id)
        if not from_node:
            return False

        # Clean the target name - remove quotes and normalize
        import_path = target_name.strip('"').strip("'")

        # Handle different import patterns
        for file_path, file_node in file_nodes.items():
            if self._matches_import_path(import_path, file_path, file_node, from_node):
                edge.to_id = file_node.id
                return True

        return False

    def _matches_import_path(
        self, import_path: str, file_path: str, file_node: ASTNode, from_node: ASTNode
    ) -> bool:
        """Check if an import path matches a file."""
        import os

        # Handle relative imports (./file.js, ../file.js)
        if import_path.startswith("./") or import_path.startswith("../"):
            # Get the directory of the importing file
            from_dir = os.path.dirname(from_node.path)

            # Resolve the relative path
            resolved_path = os.path.normpath(os.path.join(from_dir, import_path))

            # Check if this matches the target file (with or without extension)
            if file_path == resolved_path:
                return True

            # Try adding common extensions if not present
            if not import_path.endswith((".js", ".ts", ".jsx", ".tsx")):
                for ext in [".js", ".ts", ".jsx", ".tsx"]:
                    if file_path == resolved_path + ext:
                        return True

        # Handle module imports (just filename)
        else:
            # Check if the file name matches
            if file_node.name == import_path:
                return True

            # Check if the file name without extension matches
            import_name_no_ext = (
                import_path.rsplit(".", 1)[0] if "." in import_path else import_path
            )
            file_name_no_ext = (
                file_node.name.rsplit(".", 1)[0]
                if "." in file_node.name
                else file_node.name
            )

            if file_name_no_ext == import_name_no_ext:
                return True

        return False

    def _resolve_call_edge(
        self, edge: ASTEdge, metadata: Dict[str, Any], all_nodes: Dict
    ) -> bool:
        """Resolve function call edge with enhanced context handling."""
        target_name = metadata.get("target_name", "")
        if not target_name:
            return False

        call_type = metadata.get("call_type", "direct")
        object_name = metadata.get("object_name", "")

        # Handle qualified calls (static/instance)
        if call_type in ["static", "instance"] and object_name:
            # Only try to resolve if the object is defined in our codebase
            if self._is_internal_object(object_name, all_nodes):
                resolved_id = self._resolve_qualified_call(
                    target_name, object_name, call_type, all_nodes
                )
                if resolved_id:
                    edge.to_id = resolved_id
                    return True
            # If object is not internal, skip this call (don't create edge)
            return False

        # Handle direct function calls - only resolve if function exists in codebase
        if call_type == "direct":
            for node in all_nodes.values():
                if node.type == "function" and node.name == target_name:
                    edge.to_id = node.id
                    return True
            # If function not found in codebase, skip (don't create edge for system functions)
            return False

        return False

    def _is_internal_object(self, object_name: str, all_nodes: Dict) -> bool:
        """Check if an object is defined in the internal codebase."""
        if not object_name:
            return False

        # Check if we have a class or variable with this name in our codebase
        for node in all_nodes.values():
            if node.type in ["class", "variable"] and node.name == object_name:
                return True

        return False

    def _resolve_qualified_call(
        self, method_name: str, object_name: str, call_type: str, all_nodes: Dict
    ) -> Optional[int]:
        """Resolve a qualified method call (Class.method or obj.method)."""

        if call_type == "static":
            # For static calls, look for the method in the specified class
            target_class = self._find_class_by_name(object_name, all_nodes)
            if target_class:
                return self._find_method_in_class(method_name, target_class, all_nodes)

        elif call_type == "instance":
            # For instance calls, try multiple resolution strategies

            # Strategy 1: Direct class name match (for cases like Calculator.method)
            target_class = self._find_class_by_name(object_name, all_nodes)
            if target_class:
                method_id = self._find_method_in_class(
                    method_name, target_class, all_nodes
                )
                if method_id:
                    return method_id

            # Strategy 2: Infer class from variable naming patterns
            inferred_class = self._infer_class_from_variable_name(
                object_name, all_nodes
            )
            if inferred_class:
                target_class = self._find_class_by_name(inferred_class, all_nodes)
                if target_class:
                    method_id = self._find_method_in_class(
                        method_name, target_class, all_nodes
                    )
                    if method_id:
                        return method_id

            # Strategy 3: Look for any method with the name (fallback)
            for node in all_nodes.values():
                if node.type in ["function", "method"] and node.name == method_name:
                    return node.id

        return None

    def _find_class_by_name(
        self, class_name: str, all_nodes: Dict
    ) -> Optional[ASTNode]:
        """Find a class node by name."""
        for node in all_nodes.values():
            if node.type == "class" and node.name == class_name:
                return node
        return None

    def _find_method_in_class(
        self, method_name: str, class_node: ASTNode, all_nodes: Dict
    ) -> Optional[int]:
        """Find a method within a specific class."""
        # Look for methods that are contained within this class
        for node in all_nodes.values():
            if (
                node.type
                in ["function", "method"]  # Support both function and method types
                and node.name == method_name
                and node.path == class_node.path
                and node.start_line > class_node.start_line
                and node.end_line < class_node.end_line
            ):
                return node.id
        return None

    def _infer_class_from_variable_name(
        self, variable_name: str, all_nodes: Dict
    ) -> Optional[str]:
        """Infer the likely class name from a variable name using simple heuristics."""
        if not variable_name:
            return None

        # Try to capitalize the variable name (simple heuristic)
        if variable_name.islower() and len(variable_name) > 2:
            capitalized = variable_name.capitalize()
            # Check if this capitalized version exists as a class
            if self._find_class_by_name(capitalized, all_nodes):
                return capitalized

        # Handle underscore_case to PascalCase conversion
        if "_" in variable_name:
            parts = variable_name.split("_")
            pascal_case = "".join(part.capitalize() for part in parts)
            if self._find_class_by_name(pascal_case, all_nodes):
                return pascal_case

        return None

    def _resolve_inheritance_edge(
        self, edge: ASTEdge, metadata: Dict[str, Any], all_nodes: Dict
    ) -> bool:
        """Resolve inheritance edge."""
        target_name = metadata.get("target_name", "")
        if not target_name:
            return False

        # Look for class with matching name
        for node in all_nodes.values():
            if node.type == "class" and node.name == target_name:
                edge.to_id = node.id
                return True

        return False

    def _resolve_instantiation_edge(
        self, edge: ASTEdge, metadata: Dict[str, Any], all_nodes: Dict
    ) -> bool:
        """Resolve instantiation edge."""
        target_name = metadata.get("target_name", "")
        if not target_name:
            return False

        # Look for class with matching name
        for node in all_nodes.values():
            if node.type == "class" and node.name == target_name:
                edge.to_id = node.id
                return True

        return False
