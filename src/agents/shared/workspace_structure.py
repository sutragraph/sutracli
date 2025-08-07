"""
Workspace structure information for agents
"""

import os
from pathlib import Path

def get_workspace_structure(max_depth: int = 3) -> str:
    """Get current workspace directory structure."""
    current_dir = os.getcwd()

    def _build_tree(path: Path, prefix: str = "", depth: int = 0) -> str:
        if depth >= max_depth:
            return ""

        items = []
        try:
            # Get directories only, sorted
            dirs = sorted([p for p in path.iterdir() if p.is_dir() and not p.name.startswith('.')])

            for i, item in enumerate(dirs):
                is_last = i == len(dirs) - 1
                current_prefix = "└── " if is_last else "├── "
                items.append(f"{prefix}{current_prefix}{item.name}/")

                # Recursively add subdirectories
                next_prefix = prefix + ("    " if is_last else "│   ")
                subtree = _build_tree(item, next_prefix, depth + 1)
                if subtree:
                    items.append(subtree)
        except PermissionError:
            pass

        return "\n".join(items)

    structure = _build_tree(Path(current_dir))

    return f"""====

WORKSPACE STRUCTURE

Current Workspace Directory: {current_dir}

Structure:
{structure}

This section provides a comprehensive overview of the project's directory structure, showing folders up to {max_depth} levels deep. This gives key insights into the project organization and how developers structure their code. The WORKSPACE STRUCTURE represents the initial state of the project and remains static throughout your session.

===="""

WORKSPACE_STRUCTURE = get_workspace_structure()
