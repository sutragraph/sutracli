"""
Hash utilities for file content and directory hashing.

This module provides functions for computing SHA256 hashes of files and directories,
used primarily for change detection in incremental indexing.
"""

import hashlib
from pathlib import Path
from typing import Dict, Optional, Union

from utils.file_utils import is_text_file, should_ignore_directory, should_ignore_file


def compute_file_hash(file_path: Union[str, Path]) -> Optional[str]:
    """
    Compute SHA256 hash of file content for change detection.

    Args:
        file_path: Path to the file

    Returns:
        SHA256 hash of file content or None if file cannot be read
    """
    try:
        file_path = Path(file_path)
        if not file_path.exists() or not file_path.is_file():
            return None

        with open(file_path, "rb") as f:
            content = f.read()
            return hashlib.sha256(content).hexdigest()
    except (OSError, IOError, PermissionError):
        return None


def compute_directory_hashes(dir_path: Union[str, Path]) -> Dict[Path, str]:
    """
    Compute SHA256 hashes for all relevant files in a directory.

    Args:
        dir_path: Path to the directory

    Returns:
        Dictionary mapping absolute file Path objects to their content hashes
    """
    import os

    dir_path = Path(dir_path)
    file_hashes = {}

    if not dir_path.exists() or not dir_path.is_dir():
        print(f"Directory not found: {dir_path}")
        return file_hashes

    try:
        # Walk through directory using the same logic as ASTParser.extract_from_directory
        for root, dirs, files in os.walk(dir_path):
            root_path = Path(root)

            # Filter out ignored directories (modifies dirs in-place to skip them)
            dirs[:] = [d for d in dirs if not should_ignore_directory(root_path / d)]

            # Process files in current directory
            for file in files:
                file_path = root_path / file

                # Skip ignored files
                if should_ignore_file(file_path):
                    continue

                # Skip non-text files
                if not is_text_file(file_path):
                    continue

                # Compute hash for this file
                file_hash = compute_file_hash(file_path)
                if file_hash:
                    # Store absolute Path object
                    absolute_path = file_path.resolve()
                    file_hashes[absolute_path] = file_hash

        print(
            f"📊 Computed hashes for {len(file_hashes)} files in directory: {dir_path}"
        )
        return file_hashes

    except Exception as e:
        print(f"Error computing directory hashes: {e}")
        return {}
