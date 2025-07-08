"""Mathematical utility functions"""

import math
from typing import Union, List

def square(x: Union[int, float]) -> Union[int, float]:
    """Calculate square of a number"""
    return x * x

def cube(x: Union[int, float]) -> Union[int, float]:
    """Calculate cube of a number"""
    # Call another function
    squared = square(x)
    return squared * x

def factorial(n: int) -> int:
    """Calculate factorial of a number"""
    if n <= 1:
        return 1
    # Recursive call
    return n * factorial(n - 1)

def fibonacci(n: int) -> int:
    """Calculate nth Fibonacci number"""
    if n <= 1:
        return n
    # Multiple recursive calls
    return fibonacci(n - 1) + fibonacci(n - 2)

def calculate_stats(numbers: List[Union[int, float]]) -> dict:
    """Calculate statistics for a list of numbers"""
    if not numbers:
        return {}
    
    # Use built-in functions
    total = sum(numbers)
    count = len(numbers)
    mean = total / count
    
    # Use math module functions
    variance = sum((x - mean) ** 2 for x in numbers) / count
    std_dev = math.sqrt(variance)
    
    # Call local functions
    squares = [square(x) for x in numbers]
    sum_of_squares = sum(squares)
    
    return {
        'count': count,
        'sum': total,
        'mean': mean,
        'variance': variance,
        'std_dev': std_dev,
        'sum_of_squares': sum_of_squares,
        'min': min(numbers),
        'max': max(numbers)
    }

class MathOperations:
    """Class for mathematical operations"""
    
    def __init__(self, precision: int = 2):
        """Initialize with precision"""
        self.precision = precision
    
    def round_result(self, value: float) -> float:
        """Round result to specified precision"""
        return round(value, self.precision)
    
    def safe_divide(self, a: float, b: float) -> float:
        """Safely divide two numbers"""
        if b == 0:
            raise ValueError("Division by zero")
        result = a / b
        # Call instance method
        return self.round_result(result)
    
    def power(self, base: float, exponent: float) -> float:
        """Calculate power using math.pow"""
        result = math.pow(base, exponent)
        return self.round_result(result)
    
    @staticmethod
    def gcd(a: int, b: int) -> int:
        """Calculate greatest common divisor"""
        return math.gcd(a, b)
    
    @classmethod
    def create_high_precision(cls):
        """Create instance with high precision"""
        return cls(precision=6)

# Module-level calculations
PI = math.pi
E = math.e

# Function calls at module level
default_ops = MathOperations()
high_precision_ops = MathOperations.create_high_precision()

# Test calculations
test_numbers = [1, 2, 3, 4, 5]
stats = calculate_stats(test_numbers)
cubed_five = cube(5)
fact_five = factorial(5)