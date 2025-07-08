"""Static method and class method usage examples"""

from math_utils import MathOperations
from utils import DataProcessor
import math

class Helper:
    """Helper class with static methods"""
    
    PI = 3.14159
    VERSION = "1.0.0"
    
    def __init__(self, name: str):
        """Initialize helper"""
        self.name = name
    
    @staticmethod
    def format_number(num: float, precision: int = 2) -> str:
        """Static method to format numbers"""
        return f"{num:.{precision}f}"
    
    @staticmethod
    def validate_positive(value: float) -> bool:
        """Static method to validate positive numbers"""
        return value > 0
    
    @classmethod
    def create_default(cls):
        """Class method to create default instance"""
        return cls("default_helper")
    
    @classmethod
    def get_version(cls) -> str:
        """Class method to get version"""
        return cls.VERSION
    
    def process_data(self, data: list) -> list:
        """Instance method that uses static methods"""
        processed = []
        for item in data:
            if isinstance(item, (int, float)):
                # Use static method from same class
                if Helper.validate_positive(item):
                    # Use static method with formatting
                    formatted = Helper.format_number(item, 3)
                    processed.append(formatted)
                
                # Use class variable
                pi_multiple = item * Helper.PI
                processed.append(pi_multiple)
        
        return processed

def use_static_methods():
    """Function that uses various static methods"""
    # Use static method from Helper class
    formatted = Helper.format_number(42.12345, 2)
    
    # Use static method from imported class
    gcd_result = MathOperations.gcd(48, 18)
    
    # Use class method
    helper_instance = Helper.create_default()
    version = Helper.get_version()
    
    # Use static method from imported class
    processor = DataProcessor.create_default()
    
    # Use math module static functions
    sqrt_result = math.sqrt(16)
    sin_result = math.sin(Helper.PI / 2)
    
    return {
        'formatted': formatted,
        'gcd': gcd_result,
        'version': version,
        'sqrt': sqrt_result,
        'sin': sin_result
    }

class Calculator:
    """Calculator class with static methods"""
    
    @staticmethod
    def add(a: float, b: float) -> float:
        """Static add method"""
        return a + b
    
    @staticmethod
    def multiply(a: float, b: float) -> float:
        """Static multiply method"""
        return a * b
    
    @staticmethod
    def power(base: float, exponent: float) -> float:
        """Static power method"""
        return base ** exponent
    
    def calculate_compound(self, values: list) -> float:
        """Instance method using static methods"""
        if not values:
            return 0
        
        # Use static methods from same class
        result = values[0]
        for i in range(1, len(values)):
            # Chain static method calls
            result = Calculator.add(result, values[i])
            result = Calculator.multiply(result, 1.1)  # 10% increase
        
        # Use static method from Helper class
        if Helper.validate_positive(result):
            return result
        
        return 0

class MathConstants:
    """Class with mathematical constants and static methods"""
    
    PI = 3.141592653589793
    E = 2.718281828459045
    GOLDEN_RATIO = 1.618033988749895
    
    @staticmethod
    def get_circle_area(radius: float) -> float:
        """Calculate circle area using class constant"""
        # Use class constant in static method
        return MathConstants.PI * radius * radius
    
    @staticmethod
    def get_circle_circumference(radius: float) -> float:
        """Calculate circle circumference"""
        return 2 * MathConstants.PI * radius
    
    @classmethod
    def get_all_constants(cls) -> dict:
        """Get all mathematical constants"""
        return {
            'pi': cls.PI,
            'e': cls.E,
            'golden_ratio': cls.GOLDEN_RATIO
        }

# Module-level static usage
def main():
    """Main function with static method usage"""
    # Use static methods from different classes
    area = MathConstants.get_circle_area(5.0)
    circumference = MathConstants.get_circle_circumference(5.0)
    
    # Use static methods with chaining
    sum_result = Calculator.add(10, 20)
    product = Calculator.multiply(sum_result, 2)
    power_result = Calculator.power(product, 2)
    
    # Use class methods
    constants = MathConstants.get_all_constants()
    helper = Helper.create_default()
    
    # Use static validation
    is_positive = Helper.validate_positive(power_result)
    
    # Use imported static methods
    high_precision_ops = MathOperations.create_high_precision()
    gcd_value = MathOperations.gcd(100, 75)
    
    return {
        'area': area,
        'circumference': circumference,
        'power_result': power_result,
        'is_positive': is_positive,
        'constants': constants,
        'gcd': gcd_value
    }

# Module-level calls
results = use_static_methods()
main_results = main()

# Direct static method calls
pi_formatted = Helper.format_number(MathConstants.PI, 4)
e_formatted = Helper.format_number(MathConstants.E, 4)
golden_formatted = Helper.format_number(MathConstants.GOLDEN_RATIO, 4)

# Calculator instance using static methods
calc = Calculator()
test_values = [1.0, 2.0, 3.0, 4.0, 5.0]
compound_result = calc.calculate_compound(test_values)