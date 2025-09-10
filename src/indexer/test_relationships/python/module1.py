"""Module 1 for testing Python relationship extraction."""

# Standard library import
import os

# Import from subpackage
from .subpackage.module2 import function2


def function1():
    """Test function in module1."""
    print("Function 1 from module1")
    print(f"Current directory: {os.getcwd()}")
    function2()
