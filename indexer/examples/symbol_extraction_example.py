#!/usr/bin/env python3
"""
Symbol Extraction Example

This example demonstrates how to use the symbol extraction system
to extract both code blocks and their contained symbols.
"""

import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ast_parser import ASTParser
from extractors import Extractor, BlockType
from symbol_extractors import SymbolExtractorBuilder
from symbol_extractors.python_symbol_extractor import PythonSymbolExtractor
from symbol_extractors.typescript_symbol_extractor import TypeScriptSymbolExtractor


def create_symbol_extractor():
    """Create and configure a symbol extractor for multiple languages."""
    builder = SymbolExtractorBuilder()

    # Register symbol extractors for different languages
    builder.register_extractor("python", PythonSymbolExtractor)
    builder.register_extractor("typescript", TypeScriptSymbolExtractor)
    builder.register_extractor("javascript", TypeScriptSymbolExtractor)  # JS uses TS extractor

    return builder.build()


def demonstrate_python_extraction():
    """Demonstrate symbol extraction from Python code."""
    print("=== Python Symbol Extraction Example ===\n")

    # Sample Python code
    python_code = '''
class DataProcessor:
    """A class for processing data."""

    DEFAULT_CHUNK_SIZE = 1000

    def __init__(self, chunk_size=None):
        self.chunk_size = chunk_size or self.DEFAULT_CHUNK_SIZE
        self._buffer = []

    async def process_data(self, data_source, transform_func=None):
        """Process data from a source with optional transformation."""
        processed_items = []

        for item in data_source:
            if transform_func:
                transformed_item = transform_func(item)
                processed_items.append(transformed_item)
            else:
                processed_items.append(item)

        return processed_items

    @staticmethod
    def validate_input(data):
        """Validate input data."""
        return data is not None and len(data) > 0

def main():
    processor = DataProcessor(chunk_size=500)
    return processor

if __name__ == "__main__":
    main()
'''

    # Create symbol extractor
    symbol_extractor = create_symbol_extractor()

    # Create main extractor with symbol extraction capability
    extractor = Extractor(symbol_extractor=symbol_extractor)

    # Parse the code
    parser = ASTParser()
    ast_tree = parser.parse(python_code, "python")

    if not ast_tree:
        print("Failed to parse Python code")
        return

    # Extract code blocks with symbols
    blocks = extractor.extract_from_ast(ast_tree, "python")

    # Display results
    print(f"Found {len(blocks)} code blocks:\n")

    for i, block in enumerate(blocks, 1):
        print(f"{i}. {block.type.value.upper()}: {block.name}")
        print(f"   Lines: {block.start_line}-{block.end_line}")
        print(f"   Symbols: {', '.join(block.symbols) if block.symbols else 'None'}")
        print(f"   Content preview: {block.content[:80]}...")
        print()


def demonstrate_typescript_extraction():
    """Demonstrate symbol extraction from TypeScript code."""
    print("=== TypeScript Symbol Extraction Example ===\n")

    # Sample TypeScript code
    typescript_code = '''
interface UserData {
    id: number;
    name: string;
    email: string;
    isActive: boolean;
}

enum UserRole {
    ADMIN = 'admin',
    USER = 'user',
    MODERATOR = 'moderator'
}

class UserManager {
    private users: UserData[] = [];
    private static instance: UserManager;

    constructor() {
        if (UserManager.instance) {
            return UserManager.instance;
        }
        UserManager.instance = this;
    }

    public addUser(userData: UserData): void {
        const existingUser = this.findUserById(userData.id);
        if (!existingUser) {
            this.users.push(userData);
        }
    }

    private findUserById(userId: number): UserData | null {
        return this.users.find(user => user.id === userId) || null;
    }

    public async fetchUserData(apiEndpoint: string): Promise<UserData[]> {
        const response = await fetch(apiEndpoint);
        const jsonData = await response.json();
        return jsonData as UserData[];
    }
}

type UserFilter = (user: UserData) => boolean;

const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;
    return emailRegex.test(email);
};

export { UserManager, UserRole, UserData };
'''

    # Create symbol extractor
    symbol_extractor = create_symbol_extractor()

    # Create main extractor with symbol extraction capability
    extractor = Extractor(symbol_extractor=symbol_extractor)

    # Parse the code
    parser = ASTParser()
    ast_tree = parser.parse(typescript_code, "typescript")

    if not ast_tree:
        print("Failed to parse TypeScript code")
        return

    # Extract code blocks with symbols
    blocks = extractor.extract_from_ast(ast_tree, "typescript")

    # Display results
    print(f"Found {len(blocks)} code blocks:\n")

    for i, block in enumerate(blocks, 1):
        print(f"{i}. {block.type.value.upper()}: {block.name}")
        print(f"   Lines: {block.start_line}-{block.end_line}")
        print(f"   Symbols: {', '.join(block.symbols) if block.symbols else 'None'}")
        print(f"   Content preview: {block.content[:80]}...")
        print()


def demonstrate_specific_block_extraction():
    """Demonstrate extracting only specific types of blocks."""
    print("=== Extracting Only Functions ===\n")

    python_code = '''
def calculate_area(radius):
    """Calculate the area of a circle."""
    pi = 3.14159
    area = pi * radius * radius
    return area

def calculate_perimeter(radius):
    """Calculate the perimeter of a circle."""
    pi = 3.14159
    perimeter = 2 * pi * radius
    return perimeter

class Circle:
    def __init__(self, radius):
        self.radius = radius

    def get_area(self):
        return calculate_area(self.radius)
'''

    # Create symbol extractor and main extractor
    symbol_extractor = create_symbol_extractor()
    extractor = Extractor(symbol_extractor=symbol_extractor)

    # Parse the code
    parser = ASTParser()
    ast_tree = parser.parse(python_code, "python")

    if not ast_tree:
        print("Failed to parse Python code")
        return

    # Extract only function blocks
    function_blocks = extractor.extract_from_ast(
        ast_tree,
        "python",
        block_types=[BlockType.FUNCTION]
    )

    # Display results
    print(f"Found {len(function_blocks)} function blocks:\n")

    for i, block in enumerate(function_blocks, 1):
        print(f"{i}. Function: {block.name}")
        print(f"   Lines: {block.start_line}-{block.end_line}")
        print(f"   Symbols: {', '.join(block.symbols) if block.symbols else 'None'}")
        print()


def demonstrate_symbol_analysis():
    """Demonstrate analyzing extracted symbols."""
    print("=== Symbol Analysis Example ===\n")

    python_code = '''
import os
from typing import List, Dict

class FileProcessor:
    def __init__(self, base_directory: str):
        self.base_directory = base_directory
        self.processed_files = []
        self.file_count = 0

    def process_file(self, filename: str, options: Dict = None) -> bool:
        full_path = os.path.join(self.base_directory, filename)
        success = False

        try:
            with open(full_path, 'r') as file_handle:
                content = file_handle.read()
                processed_content = self._transform_content(content, options)
                success = True
        except FileNotFoundError as error:
            print(f"File not found: {error}")

        return success

    def _transform_content(self, content: str, options: Dict) -> str:
        if options and 'uppercase' in options:
            return content.upper()
        return content
'''

    # Create extractors
    symbol_extractor = create_symbol_extractor()
    extractor = Extractor(symbol_extractor=symbol_extractor)

    # Parse and extract
    parser = ASTParser()
    ast_tree = parser.parse(python_code, "python")

    if not ast_tree:
        print("Failed to parse Python code")
        return

    blocks = extractor.extract_from_ast(ast_tree, "python")

    # Analyze symbols
    all_symbols = set()
    symbol_counts = {}
    symbols_by_block_type = {}

    for block in blocks:
        block_type_name = block.type.value
        if block_type_name not in symbols_by_block_type:
            symbols_by_block_type[block_type_name] = []

        for symbol in block.symbols:
            all_symbols.add(symbol)
            symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
            symbols_by_block_type[block_type_name].extend([symbol])

    # Display analysis
    print(f"Total unique symbols found: {len(all_symbols)}")
    print(f"All symbols: {', '.join(sorted(all_symbols))}\n")

    print("Symbol frequency:")
    for symbol, count in sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {symbol}: {count} occurrences")

    print("\nSymbols by block type:")
    for block_type, symbols in symbols_by_block_type.items():
        unique_symbols = list(set(symbols))
        print(f"  {block_type}: {', '.join(unique_symbols)}")


def main():
    """Run all demonstration examples."""
    print("Symbol Extraction System Demonstration")
    print("=" * 50)
    print()

    try:
        demonstrate_python_extraction()
        print("\n" + "=" * 50 + "\n")

        demonstrate_typescript_extraction()
        print("\n" + "=" * 50 + "\n")

        demonstrate_specific_block_extraction()
        print("\n" + "=" * 50 + "\n")

        demonstrate_symbol_analysis()

    except Exception as e:
        print(f"Error during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
