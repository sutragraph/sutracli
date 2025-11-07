"""Helper functions for tree-sitter processing."""

import json
import re
from pathlib import Path
from typing import Any, Dict, Generator, List


def load_json_file(file_path: Path) -> Dict[str, Any]:
    """Load and parse a JSON file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
