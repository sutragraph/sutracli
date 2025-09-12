"""Main module for testing Python relationship extraction."""

# Standard library import
# Dynamic import (using importlib)
import importlib
import os
import sys
from pathlib import Path

# Absolute imports (assuming this is part of a package)
import test_relationships.python.module1 as mod1

# Relative imports
from .module1 import function1
from .subpackage import module2

dynamic_module = importlib.import_module(
    ".module1", package="test_relationships.python"
)


def main():
    """Main function."""
    print("Main module")
    function1()
    module2.function2()
    mod1.function1()
    dynamic_module.function1()


if __name__ == "__main__":
    main()
