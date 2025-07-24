"""
Comprehensive Python test file for AST parser testing.
Contains examples of all extractable code constructs.
"""

import os
import sys
from typing import Protocol, List, Dict, Any
from abc import ABC, abstractmethod
from enum import Enum, IntEnum
from dataclasses import dataclass
import asyncio
from pathlib import Path

# ============================================================================
# ENUMS - Should be extracted as BlockType.ENUM
# ============================================================================

class Status(Enum):
    """Basic enum example."""
    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"

class Priority(IntEnum):
    """Integer enum example."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3

class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3

# ============================================================================
# VARIABLES - Should be extracted as BlockType.VARIABLE
# ============================================================================

# Simple variable assignments
DATABASE_URL = "postgresql://localhost/mydb"
API_VERSION = "v1.0"
MAX_RETRIES = 3
IS_DEBUG = True

# Tuple unpacking
name, age, city = "John", 30, "NYC"

# List unpacking
first, second, *rest = [1, 2, 3, 4, 5]

# Dictionary
CONFIG = {
    "host": "localhost",
    "port": 5432,
    "debug": True
}

# List comprehension
NUMBERS = [x for x in range(10)]

# Complex assignment
user_data = {
    "name": "Alice",
    "settings": {
        "theme": "dark",
        "notifications": True
    }
}

# ============================================================================
# FUNCTIONS - Should be extracted as BlockType.FUNCTION
# ============================================================================

def simple_function():
    """A simple function."""
    return "Hello, World!"

def function_with_params(name: str, age: int = 25) -> str:
    """Function with parameters and type hints."""
    return f"Name: {name}, Age: {age}"

def function_with_args(*args, **kwargs):
    """Function with variable arguments."""
    return args, kwargs

async def async_function():
    """Async function example."""
    await asyncio.sleep(1)
    return "Async result"

async def async_function_with_params(url: str, timeout: int = 30) -> Dict[str, Any]:
    """Async function with parameters."""
    # Simulate async operation
    await asyncio.sleep(0.1)
    return {"url": url, "timeout": timeout}

def generator_function():
    """Generator function."""
    for i in range(5):
        yield i

def decorator_function(func):
    """Decorator function."""
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

@decorator_function
def decorated_function():
    """Function with decorator."""
    return "Decorated!"

def nested_function_example():
    """Function with nested function."""
    def inner_function():
        return "Inner"

    return inner_function()

# Lambda functions (assigned to variables)
lambda_func = lambda x: x * 2
complex_lambda = lambda x, y=10: x + y if x > 0 else y

# ============================================================================
# CLASSES - Should be extracted as BlockType.CLASS
# ============================================================================

class SimpleClass:
    """A simple class."""

    def __init__(self):
        self.value = 42

    def get_value(self):
        return self.value

class ClassWithMethods:
    """Class with various methods."""

    def __init__(self, name: str):
        self.name = name
        self._private_value = 100

    def public_method(self):
        """Public method."""
        return f"Hello from {self.name}"

    def _private_method(self):
        """Private method."""
        return self._private_value

    @property
    def name_property(self):
        """Property method."""
        return self.name

    @staticmethod
    def static_method():
        """Static method."""
        return "Static result"

    @classmethod
    def class_method(cls):
        """Class method."""
        return cls.__name__

    async def async_method(self):
        """Async method."""
        await asyncio.sleep(0.1)
        return "Async method result"

class InheritedClass(ClassWithMethods):
    """Class with inheritance."""

    def __init__(self, name: str, value: int):
        super().__init__(name)
        self.value = value

    def get_info(self):
        return f"{self.name}: {self.value}"

class MultipleInheritanceClass(SimpleClass, ClassWithMethods):
    """Class with multiple inheritance."""

    def __init__(self, name: str):
        SimpleClass.__init__(self)
        ClassWithMethods.__init__(self, name)

@dataclass
class DataClass:
    """Dataclass example."""
    name: str
    age: int
    email: str = ""

class GenericClass:
    """Generic class example."""

    def __init__(self, items: List[Any]):
        self.items = items

    def add_item(self, item: Any):
        self.items.append(item)

# ============================================================================
# INTERFACES - Should be extracted as BlockType.INTERFACE
# ============================================================================

class AbstractBaseClass(ABC):
    """Abstract base class example."""

    @abstractmethod
    def abstract_method(self):
        """Abstract method that must be implemented."""
        pass

    @abstractmethod
    async def abstract_async_method(self):
        """Abstract async method."""
        pass

    def concrete_method(self):
        """Concrete method in ABC."""
        return "Concrete implementation"

class ShapeProtocol(Protocol):
    """Protocol example."""

    def area(self) -> float:
        """Calculate area."""
        ...

    def perimeter(self) -> float:
        """Calculate perimeter."""
        ...

class ProcessorProtocol(Protocol):
    """Another protocol example."""

    async def process(self, data: Any) -> Any:
        """Process data asynchronously."""
        ...

    def validate(self, data: Any) -> bool:
        """Validate input data."""
        ...

# Implementation of abstract class
class ConcreteImplementation(AbstractBaseClass):
    """Concrete implementation of abstract class."""

    def abstract_method(self):
        return "Implemented!"

    async def abstract_async_method(self):
        await asyncio.sleep(0.1)
        return "Async implemented!"

# ============================================================================
# EXPORTS - Should be extracted as BlockType.EXPORT
# ============================================================================

# __all__ definition for explicit exports
__all__ = [
    "Status",
    "Priority",
    "SimpleClass",
    "ClassWithMethods",
    "AbstractBaseClass",
    "ShapeProtocol",
    "simple_function",
    "async_function",
    "DATABASE_URL",
    "API_VERSION"
]

# ============================================================================
# ADDITIONAL COMPLEX EXAMPLES
# ============================================================================

class ComplexClass:
    """Complex class with nested classes and various constructs."""

    class NestedClass:
        """Nested class example."""

        def __init__(self, value):
            self.value = value

        def nested_method(self):
            return self.value * 2

    class AnotherNestedClass:
        """Another nested class."""

        async def async_nested_method(self):
            await asyncio.sleep(0.1)
            return "Nested async result"

    def __init__(self):
        self.nested = self.NestedClass(10)

    def method_with_nested_function(self):
        """Method containing nested function."""
        def inner():
            return "Inner function in method"

        return inner()

# Context manager class
class ContextManager:
    """Context manager example."""

    def __enter__(self):
        print("Entering context")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("Exiting context")
        return False

# Exception class
class CustomException(Exception):
    """Custom exception class."""

    def __init__(self, message: str, code: int = 500):
        super().__init__(message)
        self.code = code

# Metaclass example
class MetaClass(type):
    """Metaclass example."""

    def __new__(cls, name, bases, attrs):
        return super().__new__(cls, name, bases, attrs)

class ClassWithMetaclass(metaclass=MetaClass):
    """Class using metaclass."""

    def method(self):
        return "Metaclass method"

# ============================================================================
# FUNCTIONS WITH VARIOUS DECORATORS
# ============================================================================

def timing_decorator(func):
    """Timing decorator."""
    def wrapper(*args, **kwargs):
        import time
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} took {end - start:.4f} seconds")
        return result
    return wrapper

@timing_decorator
def timed_function():
    """Function with timing decorator."""
    import time
    time.sleep(0.1)
    return "Timed result"

@property
def standalone_property():
    """Standalone property (unusual but valid)."""
    return "Property value"

# ============================================================================
# EDGE CASES AND SPECIAL CONSTRUCTS
# ============================================================================

# Function with complex default arguments
def complex_defaults(
    name: str = "default",
    items: List[str] = None,
    config: Dict[str, Any] = None
):
    """Function with complex default arguments."""
    if items is None:
        items = []
    if config is None:
        config = {}
    return {"name": name, "items": items, "config": config}

# Function with type annotations
def typed_function(
    input_data: List[Dict[str, Any]],
    processor: ProcessorProtocol,
    timeout: float = 30.0
) -> List[Any]:
    """Function with complex type annotations."""
    return [processor.process(item) for item in input_data]

# Async generator
async def async_generator():
    """Async generator function."""
    for i in range(3):
        await asyncio.sleep(0.1)
        yield i

# Class with slots
class SlottedClass:
    """Class with __slots__."""
    __slots__ = ['x', 'y']

    def __init__(self, x, y):
        self.x = x
        self.y = y

# Final test constructs
if __name__ == "__main__":
    # This should not be extracted as it's not a top-level construct
    def main():
        """Main function."""
        print("Running tests...")

    main()
