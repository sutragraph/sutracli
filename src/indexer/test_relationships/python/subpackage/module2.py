"""Module 2 for testing Python relationship extraction."""

# Standard library import
import datetime

# Relative import (going up one level)
from .. import module1


def function2():
    """Test function in module2."""
    print("Function 2 from module2")
    print(f"Current time: {datetime.datetime.now()}")
