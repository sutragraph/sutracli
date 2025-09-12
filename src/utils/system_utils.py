import fnmatch
import os
import platform
import pwd
from pathlib import Path


def get_operating_system():
    """Get the operating system name."""
    return platform.system()


def get_default_shell():
    """Get the default shell for the current user."""
    try:
        shell = os.environ.get("SHELL")
        if shell:
            return shell
        return pwd.getpwuid(os.getuid()).pw_shell
    except (ImportError, KeyError, OSError):
        raise Exception("Unable to determine the default shell.")


def get_home_directory():
    """Get the home directory of the current user."""
    return str(Path.home())


def get_current_directory():
    """Get the current working directory."""
    return os.getcwd()


def get_home_and_current_directories() -> dict:
    """Get both home and current working directories."""
    return {"home": get_home_directory(), "current_dir": get_current_directory()}


def get_workspace_structure() -> str:
    """
    Get a tree-like structure of folders in the current directory.
    Adaptive depth: starts at 4, reduces to 3, then 2, then 1 based on folder count.
    Only shows directories, not files. Respects .gitignore patterns.
    """

    def load_gitignore_patterns(base_path: Path) -> list[str]:
        """Load and parse .gitignore patterns."""
        gitignore_path = base_path / ".gitignore"
        patterns = []

        if gitignore_path.exists():
            try:
                with open(gitignore_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        # Skip empty lines and comments
                        if line and not line.startswith("#"):
                            # Handle directory patterns
                            if line.endswith("/"):
                                line = line[:-1]
                            patterns.append(line)
            except (OSError, UnicodeDecodeError):
                pass

        return patterns

    def is_ignored(path: Path, base_path: Path, patterns: list[str]) -> bool:
        """Check if a path should be ignored based on gitignore patterns."""
        # Get relative path from base
        try:
            rel_path = path.relative_to(base_path)
            path_str = str(rel_path)

            for pattern in patterns:
                # Handle different pattern types
                if pattern.startswith("**/"):
                    # Global pattern like **/__pycache__
                    if fnmatch.fnmatch(path.name, pattern[3:]):
                        return True
                    # Also check full path
                    if fnmatch.fnmatch(path_str, pattern):
                        return True
                elif "/" in pattern:
                    # Path-specific pattern
                    if fnmatch.fnmatch(path_str, pattern):
                        return True
                else:
                    # Simple name pattern
                    if fnmatch.fnmatch(path.name, pattern):
                        return True
                    # Also check if any parent directory matches
                    for parent in path.parents:
                        if parent != base_path and fnmatch.fnmatch(
                            parent.name, pattern
                        ):
                            return True
        except ValueError:
            # Path is not relative to base_path
            pass

        return False

    def count_folders_at_depth(
        path: Path,
        max_depth: int,
        current_depth: int = 0,
        base_path: Path = None,
        patterns: list[str] = None,
    ) -> int:
        """Count total folders up to max_depth."""
        if current_depth >= max_depth:
            return 0

        count = 0
        try:
            for item in path.iterdir():
                if item.is_dir() and not item.name.startswith("."):
                    # Skip if ignored by gitignore
                    if base_path and patterns and is_ignored(item, base_path, patterns):
                        continue
                    count += 1
                    if current_depth + 1 < max_depth:
                        count += count_folders_at_depth(
                            item, max_depth, current_depth + 1, base_path, patterns
                        )
        except PermissionError:
            pass
        return count

    def build_tree(
        path: Path,
        max_depth: int,
        current_depth: int = 0,
        prefix: str = "",
        base_path: Path = None,
        patterns: list[str] = None,
        threshold: int = 100,
    ) -> str:
        """Build the tree structure string."""
        if current_depth >= max_depth:
            return ""

        result = ""
        try:
            # Get all directories, sorted, excluding gitignore patterns
            dirs = [
                item
                for item in path.iterdir()
                if item.is_dir() and not item.name.startswith(".")
            ]

            # Filter out ignored directories
            if base_path and patterns:
                dirs = [
                    item for item in dirs if not is_ignored(item, base_path, patterns)
                ]

            dirs.sort(key=lambda x: x.name.lower())

            # Use the threshold for truncation instead of hardcoded 100
            truncated = False
            total_dirs = len(dirs)
            if len(dirs) > threshold:
                dirs = dirs[:threshold]
                truncated = True

            for i, dir_path in enumerate(dirs):
                # Add the current directory to the tree using dash format
                result += f"{prefix}- {dir_path.name}\n"

                # Set prefix for subdirectories (add two spaces for each level)
                tree_prefix = prefix + "  "

                # Recursively add subdirectories
                if current_depth + 1 < max_depth:
                    result += build_tree(
                        dir_path,
                        max_depth,
                        current_depth + 1,
                        tree_prefix,
                        base_path,
                        patterns,
                        threshold,
                    )

            # Add truncation indicator if needed
            if truncated:
                result += f"{prefix}- ... ({total_dirs - threshold} more folders)\n"

        except PermissionError:
            pass

        return result

    current_path = Path(get_current_directory())

    # Load gitignore patterns
    gitignore_patterns = load_gitignore_patterns(current_path)

    # Determine optimal depth based on folder count
    # Start with depth 4, if folders > 150, reduce depth step by step
    depths_to_try = [5, 4, 3, 2, 1]
    threshold = 100  # Single threshold for folder count

    optimal_depth = 1
    for depth in depths_to_try:
        folder_count = count_folders_at_depth(
            current_path, depth, base_path=current_path, patterns=gitignore_patterns
        )
        if folder_count <= threshold:
            optimal_depth = depth
            break

    # Build and return the tree structure
    tree = build_tree(
        current_path,
        optimal_depth,
        base_path=current_path,
        patterns=gitignore_patterns,
        threshold=threshold,
    )
    return tree.rstrip()  # Remove trailing newline
