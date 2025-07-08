"""
Utility functions and classes for the tree-sitter analyzer.

This module provides utility classes for file operations, path handling,
content processing, AST node creation, and analysis services.
"""

import os
import hashlib
from typing import Optional, Set, List, Dict, Any, Tuple

from .models import ASTNode


class FileUtils:
    """Utility class for file operations."""

    @staticmethod
    def read_file_content(file_path: str) -> str:
        """
        Read and return file content safely.

        Args:
            file_path: Path to the file to read

        Returns:
            File content as string

        Raises:
            IOError: If file cannot be read
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            raise IOError(f"Error reading file {file_path}: {e}")

    @staticmethod
    def get_file_extension(file_path: str) -> str:
        """Get file extension (lowercase)."""
        return os.path.splitext(file_path.lower())[1]

    @staticmethod
    def get_file_name(file_path: str) -> str:
        """Get file name without path."""
        return os.path.basename(file_path)

    @staticmethod
    def get_file_size(file_path: str) -> int:
        """Get file size in bytes."""
        try:
            return os.path.getsize(file_path)
        except OSError:
            return 0

    @staticmethod
    def should_skip_file(file_path: str, exclude_patterns: Set[str]) -> bool:
        """
        Check if file should be skipped based on patterns.

        Args:
            file_path: Path to check
            exclude_patterns: Set of patterns to exclude

        Returns:
            True if file should be skipped
        """
        import fnmatch

        file_name = FileUtils.get_file_name(file_path)

        for pattern in exclude_patterns:
            # Handle glob patterns (like *.so, *.pyc)
            if "*" in pattern or "?" in pattern:
                if fnmatch.fnmatch(file_name, pattern) or fnmatch.fnmatch(
                    file_path, pattern
                ):
                    return True
            # Handle simple substring patterns (like venv, __pycache__)
            else:
                if pattern in file_path or pattern in file_name:
                    return True

        return False


class LanguageUtils:
    """Utility class for language detection and mapping."""

    @staticmethod
    def get_language_from_file_path(file_path: str) -> Optional[str]:
        """
        Get language name from file path based on extension.

        Args:
            file_path: Path to the file

        Returns:
            Language name or None if not supported
        """
        from .config import get_parser_config_loader

        extension = FileUtils.get_file_extension(file_path)
        parser_config = get_parser_config_loader()
        return parser_config.get_language_from_extension(extension)

    @staticmethod
    def is_language_supported(language: str) -> bool:
        """Check if language is supported."""
        from .config import get_parser_config_loader

        parser_config = get_parser_config_loader()
        return language in parser_config.get_supported_languages()


class ContentUtils:
    """Utility class for content processing."""

    @staticmethod
    def hash_content(content: str) -> str:
        """
        Generate SHA256 hash of content.

        Args:
            content: Content to hash

        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def hash_string(text: str) -> int:
        """
        Generate a stable integer hash from a string.

        Uses a smaller hash to ensure compatibility with SQLite INTEGER limits.

        Args:
            text: String to hash

        Returns:
            Integer hash value (within SQLite INTEGER range)
        """
        # Use first 8 hex characters instead of 12 to stay within SQLite limits
        # This gives us 32-bit values (up to 4,294,967,295)
        return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)


class PathUtils:
    """Utility class for path operations."""

    @staticmethod
    def normalize_path(path: str) -> str:
        """
        Normalize path to use forward slashes and resolve relative paths.

        Args:
            path: Path to normalize

        Returns:
            Normalized path
        """
        return os.path.normpath(os.path.abspath(path)).replace("\\", "/")

    @staticmethod
    def join_paths(*paths: str) -> str:
        """Join multiple paths together."""
        return os.path.join(*paths).replace("\\", "/")


class DirectoryUtils:
    """Utility class for directory operations."""

    @staticmethod
    def collect_files_with_extensions(
        directory: str, extensions: Set[str], exclude_patterns: Set[str] = None
    ) -> List[str]:
        """
        Collect all files with specified extensions from directory recursively.

        Args:
            directory: Directory to scan
            extensions: Set of file extensions to include
            exclude_patterns: Patterns to exclude

        Returns:
            List of file paths
        """
        exclude_patterns = exclude_patterns or set()
        collected_files = []

        for root, dirs, files in os.walk(directory):
            # Skip excluded directories
            dirs[:] = [
                d
                for d in dirs
                if not DirectoryUtils._should_skip_directory(
                    os.path.join(root, d), exclude_patterns
                )
            ]

            for file in files:
                file_path = os.path.join(root, file)

                # Check extension
                if FileUtils.get_file_extension(file_path) not in extensions:
                    continue

                # Check exclusion patterns
                if FileUtils.should_skip_file(file_path, exclude_patterns):
                    continue

                collected_files.append(PathUtils.normalize_path(file_path))

        return sorted(collected_files)

    @staticmethod
    def _should_skip_directory(directory_path: str, exclude_patterns: Set[str]) -> bool:
        """Check if directory should be skipped."""
        dir_name = os.path.basename(directory_path)
        return any(
            pattern in directory_path or pattern in dir_name
            for pattern in exclude_patterns
        )


class ValidationUtils:
    """Utility class for validation operations."""

    @staticmethod
    def is_valid_file_path(file_path: str) -> bool:
        """Check if file path is valid and exists."""
        return file_path and os.path.isfile(file_path)

    @staticmethod
    def is_valid_directory_path(directory_path: str) -> bool:
        """Check if directory path is valid and exists."""
        return directory_path and os.path.isdir(directory_path)


class NodeIdGenerator:
    """
    Generator for deterministic node IDs that fit within SQLite INTEGER limits.

    Creates IDs that ensure unchanged files get the same node IDs during incremental
    indexing, preventing duplicate nodes and maintaining cross-file references.
    """

    def __init__(self):
        """Initialize the generator with empty file counters."""
        self._file_counters = {}

    def reset_counters(self):
        """Reset the file counters to ensure deterministic IDs across analysis runs."""
        self._file_counters.clear()

    def generate_node_id(self, file_path: str) -> int:
        """
        Generate a deterministic node ID for the given file path.

        Creates IDs that fit within SQLite INTEGER limits (2^63-1).
        Each file gets a unique base ID, and nodes within the file increment sequentially.

        This ensures that unchanged files get the same node IDs during incremental
        indexing, preventing duplicate nodes and maintaining cross-file references.

        Args:
            file_path: Path to the file

        Returns:
            Deterministic node ID (within SQLite INTEGER range)
        """
        # Normalize the path using existing utility
        normalized_path = PathUtils.normalize_path(file_path)

        # Get or initialize counter for this file
        if normalized_path not in self._file_counters:
            self._file_counters[normalized_path] = 0

        # Generate base ID from file path hash (using existing utility)
        file_hash = ContentUtils.hash_string(normalized_path)
        # Use smaller bit shift (12 bits instead of 16) to stay within SQLite limits
        # This reserves 12 bits for sequence (up to 4095 nodes per file)
        base_id = file_hash << 12

        # Add sequence number
        sequence = self._file_counters[normalized_path]
        node_id = base_id + sequence

        # Increment counter for next node in this file
        self._file_counters[normalized_path] += 1

        return node_id


class NodeFactory:
    """Factory for creating AST nodes."""

    def __init__(self, repo_id: str):
        """Initialize the node factory."""
        self.repo_id = repo_id

    def create_file_node(
        self, file_path: str, content: str, language: str, node_id_generator
    ) -> ASTNode:
        """
        Create a file node.

        Args:
            file_path: Path to the file
            content: File content
            language: Programming language of the file
            node_id_generator: Function to generate unique node IDs

        Returns:
            Created ASTNode representing the file
        """
        node_id = node_id_generator()
        path = PathUtils.normalize_path(file_path)
        file_name = FileUtils.get_file_name(path)

        return ASTNode(
            id=node_id,
            repo_id=self.repo_id,
            type="file",
            path=path,
            name=file_name,
            content=content,
            start_line=1,
            end_line=len(content.splitlines()),
            content_hash=ContentUtils.hash_content(content),
            metadata={
                "language": language,
                "line_count": len(content.splitlines()),
                "size": len(content.encode("utf-8")),
            },
        )


class AnalysisOrchestrator:
    """Orchestrator that coordinates analysis services."""

    def __init__(self, config_manager=None):
        """Initialize with services."""
        from .config import get_config_manager

        self.config = config_manager or get_config_manager()

    def scan_and_filter_directory(
        self, directory_path: str
    ) -> Tuple[List[str], Set[str]]:
        """Scan directory and return filtered files with detected languages."""
        if not ValidationUtils.is_valid_directory_path(directory_path):
            return [], set()

        files = []
        languages = set()
        file_exclude_patterns = self.config.get_file_exclusion_patterns()
        dir_exclude_patterns = self.config.get_directory_exclusion_patterns()

        for root, dirs, filenames in os.walk(directory_path):
            # Skip excluded directories
            dirs[:] = [
                d
                for d in dirs
                if not DirectoryUtils._should_skip_directory(
                    os.path.join(root, d), dir_exclude_patterns
                )
            ]

            for filename in filenames:
                file_path = os.path.join(root, filename)

                # Skip excluded files
                if FileUtils.should_skip_file(file_path, file_exclude_patterns):
                    continue

                # Skip files that are too large
                if FileUtils.get_file_size(file_path) > self.config.get_max_file_size():
                    continue

                # Detect language
                language = LanguageUtils.get_language_from_file_path(file_path)
                if language:
                    languages.add(language)

                files.append(PathUtils.normalize_path(file_path))

        return sorted(files), languages

    def scan_directory(self, directory_path: str) -> List[str]:
        """Scan directory and return all files."""
        files, _ = self.scan_and_filter_directory(directory_path)
        return files

    def resolve_analysis_edges(self, analysis_results: Dict[str, Any]) -> None:
        """Resolve edges across all files in the analysis results."""
        if "edges" not in analysis_results or "nodes" not in analysis_results:
            return

        # Build comprehensive node lookups for cross-file resolution
        nodes_by_id = {}
        nodes_by_name = {}
        file_nodes = {}

        for node_data in analysis_results["nodes"]:
            node_id = node_data.get("id")
            node_name = node_data.get("name", "")
            node_type = node_data.get("type", "")
            node_path = node_data.get("path", "")

            nodes_by_id[node_id] = node_data

            if node_name:
                if node_name not in nodes_by_name:
                    nodes_by_name[node_name] = []
                nodes_by_name[node_name].append(node_data)

            if node_type == "file":
                file_nodes[node_path] = node_data

        # Resolve each edge using simplified cross-file logic
        for edge in analysis_results["edges"]:
            if edge.get("to_id") is None:  # Only resolve unresolved edges
                self._resolve_cross_file_edge(
                    edge, nodes_by_id, nodes_by_name, file_nodes
                )

    def _resolve_cross_file_edge(
        self,
        edge: Dict[str, Any],
        nodes_by_id: Dict,
        nodes_by_name: Dict,
        file_nodes: Dict,
    ) -> None:
        """Resolve edges that span across multiple files."""
        edge_type = edge.get("type", "")
        metadata = edge.get("metadata", {})
        target_name = metadata.get("target_name", "")

        if not target_name:
            return

        # Simple cross-file resolution - only handle the most common cases
        if edge_type == "calls":
            # Look for function calls across files
            if target_name in nodes_by_name:
                for node in nodes_by_name[target_name]:
                    if node.get("type") == "function":
                        edge["to_id"] = node.get("id")
                        return

        elif edge_type == "imports":
            # Handle import resolution
            import_path = target_name.strip('"').strip("'")
            from_node = nodes_by_id.get(edge.get("from_id"))

            if from_node:
                for file_path, file_node in file_nodes.items():
                    if self._simple_import_match(import_path, file_node):
                        edge["to_id"] = file_node.get("id")
                        return

        elif edge_type in ["extends", "instantiates"]:
            # Handle class relationships
            if target_name in nodes_by_name:
                for node in nodes_by_name[target_name]:
                    if node.get("type") == "class":
                        edge["to_id"] = node.get("id")
                        return

    def _simple_import_match(self, import_path: str, file_node: Dict) -> bool:
        """Simple import path matching for cross-file resolution."""
        file_name = file_node.get("name", "")

        # Direct name match
        if file_name == import_path:
            return True

        # Name without extension match
        import_name_no_ext = (
            import_path.rsplit(".", 1)[0] if "." in import_path else import_path
        )
        file_name_no_ext = (
            file_name.rsplit(".", 1)[0] if "." in file_name else file_name
        )

        return file_name_no_ext == import_name_no_ext

    def cleanup_unresolved_edges(self, analysis_results: Dict[str, Any]) -> int:
        """Remove unresolved edges from analysis results."""
        if "edges" not in analysis_results:
            return 0

        original_count = len(analysis_results["edges"])
        resolved_edges = []

        for edge in analysis_results["edges"]:
            if edge.get("to_id") is not None:
                resolved_edges.append(edge)

        analysis_results["edges"] = resolved_edges
        removed_count = original_count - len(resolved_edges)

        return removed_count
