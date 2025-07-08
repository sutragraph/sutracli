"""Main file with imports and external library calls"""

# Standard library imports
import os
import sys
import json
import math
import time
import random
from datetime import datetime
from pathlib import Path

# Third-party imports (simulated)
import requests  # External HTTP library
import numpy as np  # External numerical library
import pandas as pd  # External data analysis library

# Local imports
from example import add, Calculator, fetch_data
from utils import logger, format_date
import math_utils


# Function calls using imported functions
def main():
    """Main function with external and internal calls"""
    # Internal function calls - should create edges
    result = add(10, 5)
    calc = Calculator()
    calc.increment()
    calc.add_to_value(5)
    product = Calculator.multiply(3, 4)
    squared = math_utils.square(5)
    formatted_time = format_date(datetime.now())

    # External library calls - should be filtered out
    print(f"Addition result: {result}")  # Built-in function
    len([1, 2, 3])  # Built-in function
    str(result)  # Built-in function
    int("42")  # Built-in function
    float("3.14")  # Built-in function

    # Standard library calls - should be filtered out
    os.path.join("path", "to", "file")  # os module
    sys.exit(0)  # sys module
    json.dumps({"key": "value"})  # json module
    math.sqrt(16)  # math module
    time.sleep(1)  # time module
    random.randint(1, 10)  # random module
    datetime.now()  # datetime module
    Path("/tmp").exists()  # pathlib module

    # Third-party library calls - should be filtered out
    requests.get("https://api.example.com")  # requests library
    np.array([1, 2, 3])  # numpy library
    pd.DataFrame({"col": [1, 2, 3]})  # pandas library

    # Internal utility calls - should create edges
    logger.info("Application started")

    return result


def process_data(data):
    """Function with mixed internal and external calls"""
    # Internal calls - should create edges
    processed = math_utils.square(data)
    calc = Calculator()
    final_result = calc.add_to_value(processed)

    # External calls - should be filtered out
    print(f"Processing: {data}")
    json_str = json.dumps({"result": final_result})
    math.pow(final_result, 2)

    return final_result


def external_api_simulation():
    """Function simulating external API calls"""
    # All these should be filtered out as external calls
    response = requests.get("https://api.example.com/data")
    data = response.json()

    # Numpy operations - should be filtered
    arr = np.array(data)
    mean_val = np.mean(arr)

    # Pandas operations - should be filtered
    df = pd.DataFrame(data)
    result = df.groupby("category").sum()

    # Built-in operations - should be filtered
    print(f"Mean: {mean_val}")
    len(result)

    return result


# Module-level calls
if __name__ == "__main__":
    main()
    process_data(42)
    external_api_simulation()
