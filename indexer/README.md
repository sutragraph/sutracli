# Enhanced AST Parser with Code Block Extraction

A powerful AST parser built on tree-sitter that extracts specific code constructs from TypeScript and Python files. Features an extensible builder pattern architecture for adding new language support.

## Features

- 🌳 **Multi-Language AST Parsing**: Parse 159+ programming languages using tree-sitter
- 🔍 **Code Block Extraction**: Extract enums, variables, functions, classes, interfaces, imports, and exports
- 🏗️ **Builder Pattern**: Extensible architecture for adding new language extractors
- 📁 **Batch Processing**: Process entire directories recursively
- 🎯 **Selective Extraction**: Extract only specific types of code blocks
- 📊 **Rich Metadata**: Detailed position and context information
- 🚀 **High Performance**: Caches parsers and processes files efficiently

## Installation

```bash
pip install tree-sitter-language-pack
```

## Quick Start

```python
from enhanced_ast_parser import EnhancedASTParser
from extractors import BlockType

# Initialize parser
parser = EnhancedASTParser()

# Extract all code blocks from a file
result = parser.parse_and_extract("example.py")
blocks = result["blocks"]

# Extract only functions and classes
result = parser.parse_and_extract("example.ts", [BlockType.FUNCTION, BlockType.CLASS])

# Process entire directory
results = parser.extract_from_directory("src/")
```

## Supported Languages

### Currently Supported for Extraction
- **Python** (.py, .pyw, .pyi) - Classes, functions, variables, imports, enums, interfaces
- **TypeScript** (.ts, .tsx) - Interfaces, enums, classes, functions, imports, exports

### Extractable Code Blocks

| Block Type | Description | Python | TypeScript |
|------------|-------------|---------|------------|
| **Enum** | Enum declarations | ✅ | ✅ |
| **Variable** | Variable declarations/assignments | ✅ | ✅ |
| **Function** | Function definitions | ✅ | ✅ |
| **Class** | Class declarations | ✅ | ✅ |
| **Interface** | Interface declarations | ✅* | ✅ |
| **Import** | Import statements | ✅ | ✅ |
| **Export** | Export statements | ✅* | ✅ |

*Python: Interfaces detected via ABC/Protocol, Exports via `__all__`

## Usage Examples

### Basic Extraction

```python
from enhanced_ast_parser import EnhancedASTParser

parser = EnhancedASTParser()

# Parse and extract all blocks
result = parser.parse_and_extract("myfile.py")
if "error" not in result:
    blocks = result["blocks"]
    print(f"Found {len(blocks)} code blocks")
    
    for block in blocks:
        print(f"{block.type.value}: {block.name} (lines {block.start_line}-{block.end_line})")
```

### Specific Block Types

```python
# Extract only functions
functions = parser.extract_functions("script.py")
for func in functions:
    print(f"Function: {func.name} at line {func.start_line}")

# Extract only classes
classes = parser.extract_classes("module.ts")
for cls in classes:
    print(f"Class: {cls.name}")

# Extract only imports
imports = parser.extract_imports("app.py")
for imp in imports:
    print(f"Import: {imp.name}")
    print(f"Source: {imp.metadata.get('source', 'N/A')}")
```

### Directory Processing

```python
# Process entire directory
results = parser.extract_from_directory("src/")

for file_path, result in results.items():
    if "error" in result:
        print(f"Error in {file_path}: {result['error']}")
        continue
    
    blocks = result["blocks"]
    language = result["language"]
    
    print(f"{file_path} ({language}): {len(blocks)} blocks")
```

### Summary Reports

```python
# Get summary of code blocks
summary = parser.get_summary("myfile.py")
print("Code Block Summary:")
for block_type, count in summary.items():
    if count > 0:
        print(f"  {block_type.capitalize()}s: {count}")
```

## Code Block Structure

Each extracted code block is a `CodeBlock` object with:

```python
@dataclass
class CodeBlock:
    type: BlockType           # Type of block (enum, function, class, etc.)
    name: str                 # Name of the block
    content: str              # Full source code content
    start_line: int           # Starting line number (1-indexed)
    end_line: int             # Ending line number (1-indexed)
    start_col: int            # Starting column (0-indexed)
    end_col: int              # Ending column (0-indexed)
    metadata: Dict[str, Any]  # Additional metadata
```

## Advanced Usage

### Custom Block Type Filtering

```python
from extractors import BlockType

# Extract only specific types
result = parser.parse_and_extract(
    "myfile.ts", 
    [BlockType.CLASS, BlockType.INTERFACE, BlockType.FUNCTION]
)

# Filter existing blocks
all_blocks = parser.parse_and_extract("myfile.py")["blocks"]
functions_only = parser.get_blocks_by_type(all_blocks, BlockType.FUNCTION)
```

### Working with Metadata

```python
# Extract imports with metadata
imports = parser.extract_imports("myfile.py")
for imp in imports:
    print(f"Import: {imp.name}")
    print(f"Source: {imp.metadata.get('source', 'N/A')}")
    print(f"Names: {imp.metadata.get('imported_names', [])}")
```

## API Reference

### Main Parser Class

#### `EnhancedASTParser()`

**Methods:**

- `parse_and_extract(file_path, block_types=None)` - Parse file and extract blocks
- `extract_from_directory(dir_path, block_types=None)` - Process entire directory
- `extract_functions(file_path)` - Extract only functions
- `extract_classes(file_path)` - Extract only classes
- `extract_imports(file_path)` - Extract only imports
- `get_summary(file_path)` - Get block count summary
- `get_blocks_by_type(blocks, block_type)` - Filter blocks by type
- `get_supported_languages()` - Get all supported languages
- `get_supported_extraction_languages()` - Get extraction-supported languages
- `clear_cache()` - Clear parser cache

### Block Types

```python
from extractors import BlockType

BlockType.ENUM        # Enum declarations
BlockType.VARIABLE    # Variable declarations
BlockType.FUNCTION    # Function definitions
BlockType.CLASS       # Class declarations
BlockType.INTERFACE   # Interface declarations
BlockType.IMPORT      # Import statements
BlockType.EXPORT      # Export statements
```

## Error Handling

The parser provides comprehensive error handling:

```python
result = parser.parse_and_extract("myfile.py")

if "error" in result:
    print(f"Parsing failed: {result['error']}")
    # Handle error case
else:
    blocks = result["blocks"]
    language = result["language"]
    # Process successful result
```

Common error scenarios:
- File not found
- Unsupported file type
- No extractor available for language
- Parsing errors

## Architecture

### Project Structure

```
indexer/
├── enhanced_ast_parser.py     # Main parser with extraction
├── extractors/
│   ├── __init__.py           # Base classes and builder
│   ├── python_extractor.py   # Python extraction logic
│   └── typescript_extractor.py # TypeScript extraction logic
├── utils/
│   ├── __init__.py
│   ├── file_utils.py         # File handling utilities
│   ├── ignore_patterns.py    # File ignore patterns
│   └── supported_languages.py # Language definitions
├── requirements.txt          # Dependencies
├── README.md                 # This file
├── USAGE.md                  # Quick usage guide
└── PROJECT_SUMMARY.md        # Detailed project overview
```

### Builder Pattern

The system uses a builder pattern for extensibility:

```python
from extractors import builder, BaseExtractor

# Create custom extractor
class MyLanguageExtractor(BaseExtractor):
    def extract_functions(self, node):
        # Implementation
        pass
    
    def extract_classes(self, node):
        # Implementation
        pass
    
    # ... other methods

# Register with builder
builder.register_extractor("mylang", MyLanguageExtractor)

# Use it
parser = EnhancedASTParser()
result = parser.parse_and_extract("file.mylang")
```

## Language-Specific Notes

### TypeScript
- Supports interfaces, enums, arrow functions, method definitions
- Export statements include both named and default exports
- Import statements handle various import syntaxes
- Generics and type annotations are preserved in content

### Python
- Enums detected by inheritance from `Enum`, `IntEnum`, `Flag`
- Interfaces detected by inheritance from `ABC` or `Protocol`
- Exports handled through `__all__` assignments
- Supports both simple and from-import statements
- Decorators are included in function/class content

## Performance

- **Parser Caching**: Reuses tree-sitter parsers for better performance
- **Lazy Processing**: Only processes files when requested
- **Memory Efficient**: Streams through directories without loading all files
- **Scalable**: Can handle large codebases efficiently

## Contributing

To add support for a new language:

1. Create a new extractor class inheriting from `BaseExtractor`
2. Implement all abstract methods for your language's AST structure
3. Register the extractor with the builder
4. Update language support documentation
5. Add tests for your language

Example:

```python
from extractors import BaseExtractor, builder

class JavaExtractor(BaseExtractor):
    def extract_functions(self, node):
        # Implement Java method extraction
        pass
    
    def extract_classes(self, node):
        # Implement Java class extraction
        pass
    
    # ... implement other methods

# Register the extractor
builder.register_extractor("java", JavaExtractor)
```

## Dependencies

- `tree-sitter-language-pack`: Multi-language parsing support
- Python 3.8+: Modern Python features and type hints

## License

This project is part of the AST indexer system and follows the same licensing terms.

## Support

For issues, questions, or contributions, please refer to the project repository.