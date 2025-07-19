# Enhanced AST Parser - Usage Guide

## Quick Start

### Installation

```bash
pip install tree-sitter-language-pack
```

### Basic Usage

```python
from enhanced_ast_parser import ASTParser
from extractors import BlockType

# Initialize parser
parser = ASTParser()

# Extract all code blocks
result = parser.parse_and_extract("my_file.py")
blocks = result["blocks"]

# Extract specific block types
result = parser.parse_and_extract("my_file.ts", [BlockType.FUNCTION, BlockType.CLASS])
```

## Common Operations

### Extract Functions Only

```python
functions = parser.extract_functions("script.py")
for func in functions:
    print(f"Function: {func.name} at line {func.start_line}")
```

### Extract Classes Only

```python
classes = parser.extract_classes("module.ts")
for cls in classes:
    print(f"Class: {cls.name}")
```

### Process Directory

```python
results = parser.extract_from_directory("src/")
for file_path, result in results.items():
    if "error" not in result:
        print(f"{file_path}: {len(result['blocks'])} blocks")
```

### Get Summary

```python
summary = parser.get_summary("file.py")
for block_type, count in summary.items():
    if count > 0:
        print(f"{block_type}: {count}")
```

### Filter Blocks by Type

```python
# Get all blocks
all_blocks = parser.parse_and_extract("file.py")["blocks"]

# Filter by specific type
functions = parser.get_blocks_by_type(all_blocks, BlockType.FUNCTION)
classes = parser.get_blocks_by_type(all_blocks, BlockType.CLASS)
imports = parser.get_blocks_by_type(all_blocks, BlockType.IMPORT)

print(f"Functions: {[f.name for f in functions]}")
print(f"Classes: {[c.name for c in classes]}")
print(f"Imports: {[i.name for i in imports]}")
```

## Block Types

| Type                  | Description            | Notes                                      |
| --------------------- | ---------------------- | ------------------------------------------ |
| `BlockType.ENUM`      | Enum declarations      | TypeScript enums, Python Enum classes      |
| `BlockType.VARIABLE`  | Variable declarations  | Supports destructuring, excludes lambdas   |
| `BlockType.FUNCTION`  | Function definitions   | All function declarations and methods      |
| `BlockType.CLASS`     | Class declarations     | Complete class definitions                 |
| `BlockType.INTERFACE` | Interface declarations | TypeScript interfaces, Python ABC/Protocol |
| `BlockType.IMPORT`    | Import statements      | All import variations with metadata        |
| `BlockType.EXPORT`    | Export statements      | TypeScript exports, Python **all**         |

## Supported Languages

- **Python** (.py, .pyw, .pyi) - Classes, functions, async functions, lambdas, methods, variables, destructuring
- **TypeScript** (.ts, .tsx) - Interfaces, enums, classes, functions, async functions, arrow functions, methods, constructors, variables, destructuring

## Error Handling

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

## Code Block Properties

Each `CodeBlock` contains:

- `type`: Block type (enum)
- `name`: Block name
- `content`: Full source code
- `start_line` / `end_line`: Line numbers
- `start_col` / `end_col`: Column positions
- `metadata`: Additional info (language, function type, etc.)

## Advanced Usage

### Custom Extraction

```python
# Extract only imports and exports
result = parser.parse_and_extract("file.ts", [BlockType.IMPORT, BlockType.EXPORT])

# Filter by block type
all_blocks = parser.parse_and_extract("file.py")["blocks"]
functions = parser.get_blocks_by_type(all_blocks, BlockType.FUNCTION)
```

### Working with Metadata

```python
# Import metadata
imports = parser.extract_imports("file.py")
for imp in imports:
    source = imp.metadata.get("source", "")
    names = imp.metadata.get("imported_names", [])
    print(f"From {source}: {', '.join(names)}")

# Function metadata
functions = parser.extract_functions("file.py")
for func in functions:
    metadata = func.metadata
    print(f"Function: {func.name}")
    print(f"  Async: {metadata.get('is_async', False)}")
    print(f"  Method: {metadata.get('is_method', False)}")
    print(f"  Constructor: {metadata.get('is_constructor', False)}")
    print(f"  Lambda: {metadata.get('is_lambda', False)}")
    print(f"  Arrow: {metadata.get('is_arrow', False)}")
```

## Function Classification

The parser properly classifies different types of functions:

### Python

```python
# Lambda functions - classified as FUNCTION
my_lambda = lambda x: x * 2

# Class methods - marked with is_method=True
class MyClass:
    def method(self):  # is_method=True
        pass

# Async functions - marked with is_async=True
async def async_func():  # is_async=True
    pass

# Standalone functions - is_method=False
def standalone():  # is_method=False
    pass
```

### TypeScript

```typescript
// Arrow functions - classified as FUNCTION with is_arrow=True
const arrow = () => {}; // is_arrow=True

// Class methods - marked with is_method=True
class MyClass {
  constructor() {} // is_method=True, is_constructor=True
  method() {} // is_method=True
}

// Async functions - marked with is_async=True
async function asyncFunc() {} // is_async=True
```

## Variable Handling

### Destructuring Support

```python
# Python tuple unpacking
a, b, c = 1, 2, 3  # Creates 3 variables: a, b, c
```

```typescript
// TypeScript destructuring
const { name, age } = person; // Creates 2 variables: name, age
const [first, second] = array; // Creates 2 variables: first, second
```

### Builder Pattern Extension

Add support for new languages:

```python
from extractors import builder, BaseExtractor

# Create custom extractor
class MyExtractor(BaseExtractor):
    def extract_functions(self, node):
        # Implementation
        pass

    def extract_classes(self, node):
        # Implementation
        pass

    # ... other methods

# Register the extractor
builder.register_extractor("mylang", MyExtractor)

# Use with the enhanced parser
parser = ASTParser()
result = parser.parse_and_extract("file.mylang")
```

## Performance Tips

1. **Use specific block types**: Extract only what you need
2. **Cache parser instance**: Reuse the same parser for multiple files
3. **Process directories in batches**: Use `extract_from_directory()`
4. **Clear cache periodically**: Use `parser.clear_cache()` for long-running processes

## Common Patterns

### Code Analysis

```python
# Analyze code structure
result = parser.parse_and_extract("complex_file.py")
blocks = result["blocks"]
summary = parser.get_summary("complex_file.py")

print(f"Total blocks: {len(blocks)}")
print(f"Functions: {summary.get('function', 0)}")
print(f"Classes: {summary.get('class', 0)}")
```

### Documentation Generation

```python
# Extract public API
classes = parser.extract_classes("api.py")
all_blocks = parser.parse_and_extract("api.py")["blocks"]
functions = parser.get_blocks_by_type(all_blocks, BlockType.FUNCTION)

for cls in classes:
    print(f"Class: {cls.name}")

for func in functions:
    print(f"Function: {func.name}")
```

### Migration Analysis

```python
# Find async functions for migration
all_blocks = parser.parse_and_extract("legacy.py")["blocks"]
functions = parser.get_blocks_by_type(all_blocks, BlockType.FUNCTION)
# Note: Async detection would need to be implemented based on content analysis

print(f"Found {len(functions)} functions to analyze for async migration")
```
