"""Example Python file for testing"""

# Regular function
def add(a, b):
    """Add two numbers"""
    return a + b

# Async function
async def fetch_data(url):
    """Fetch data from URL"""
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# Class with methods
class Calculator:
    """A simple calculator class"""
    
    def __init__(self):
        """Initialize calculator"""
        self.value = 0
        self.history = []
    
    def increment(self):
        """Increment the value"""
        self.value += 1
        self.history.append(f"increment: {self.value}")
        return self.value
    
    def add_to_value(self, amount):
        """Add amount to current value"""
        self.value += amount
        self.history.append(f"add: {amount}")
        return self.value
    
    @staticmethod
    def multiply(a, b):
        """Static method to multiply two numbers"""
        return a * b
    
    @classmethod
    def create_with_value(cls, initial_value):
        """Class method to create calculator with initial value"""
        calc = cls()
        calc.value = initial_value
        return calc

# Function with decorators
def log_calls(func):
    """Decorator to log function calls"""
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

@log_calls
def decorated_function(x, y):
    """Function with decorator"""
    return x * y

# Global variables
PI = 3.14159
CONFIG = {
    'debug': True,
    'version': '1.0.0'
}

# Module-level function calls
result = add(5, 3)
calc_instance = Calculator()
multiplied = Calculator.multiply(10, 20)