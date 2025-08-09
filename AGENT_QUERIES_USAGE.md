# GraphOperations Agent Query Methods - Developer Usage Guide

## Quick Start

### Import and Initialize
```python
from graph.sqlite_client import GraphOperations

# Initialize (uses singleton SQLite connection)
graph_ops = GraphOperations()
```

### Basic Usage Pattern
```python
# 1. Start with semantic search results (from other tools)
embedding_results = ["block_123", "file_456"]  # From semantic_search tool

# 2. Convert to concrete data
concrete_data = graph_ops.resolve_embedding_nodes(embedding_results)

# 3. Get detailed context for each item
for item in concrete_data:
    if item.get('type') != 'file':  # It's a block
        details = graph_ops.get_block_details(item['id'])
        print(f"Block: {details['name']} in {details['file_path']}")
    else:  # It's a file
        summary = graph_ops.get_file_block_summary(item['id'])
        print(f"File: {item['file_path']} has {len(summary)} blocks")
```

## Common Usage Patterns

### 1. Exploring Code Structure

```python
# Get file overview
file_id = 123
blocks = graph_ops.get_file_block_summary(file_id)

print(f"File contains {len(blocks)} code blocks:")
for block in blocks:
    print(f"  {block['type']}: {block['name']} (lines {block['start_line']}-{block['end_line']})")

# Get implementation context with parent relationships
context = graph_ops.get_implementation_context(file_id)
for item in context:
    parent_info = f" in {item['parent_name']}" if item['parent_name'] else ""
    print(f"  {item['type']}: {item['name']}{parent_info}")
```

### 2. Analyzing Dependencies

```python
# Check what a file imports
file_id = 123
imports = graph_ops.get_imports(file_id)
print(f"File imports {len(imports)} dependencies:")
for imp in imports:
    print(f"  {imp['import_content']} from {imp['file_path']}")

# See who imports this file
importers = graph_ops.get_importers(file_id)
print(f"File is imported by {len(importers)} other files")

# Get full impact scope
impact = graph_ops.get_file_impact_scope(file_id)
for rel in impact:
    print(f"  {rel['relationship_type']}: {rel['file_path']}")
```

### 3. Tracing Dependency Chains

```python
# Get multi-level dependency chain
file_id = 123
chain = graph_ops.get_dependency_chain(file_id, depth=3)

print("Dependency chain:")
for dep in chain:
    print(f"  Depth {dep['depth']}: {dep['path']}")
```

### 4. Finding Symbol Usage

```python
# First, get a focused search scope
file_id = 123
scope = graph_ops.get_search_scope_by_import_graph(
    anchor_file_id=file_id,
    direction="both",  # or "dependencies" or "importers"
    max_depth=2
)

print(f"Search scope: {len(scope['paths'])} files")

# Then search for symbol usage within that scope
symbol_usage = graph_ops.get_files_using_symbol(
    symbol_pattern="uploadAvatar",
    paths=scope['paths']  # Constrain search to relevant files
)

print(f"Symbol 'uploadAvatar' found in {len(symbol_usage)} locations:")
for usage in symbol_usage:
    print(f"  {usage['file_path']}:{usage['line']}: {usage['snippet']}")
```

### 5. Block Navigation and Hierarchy

```python
# Get block details with parent and connections
block_id = 456
details = graph_ops.get_block_details(block_id)

print(f"Block: {details['name']} ({details['type']})")
print(f"File: {details['file_path']}")
print(f"Lines: {details['start_line']}-{details['end_line']}")

if details['parent']:
    print(f"Parent: {details['parent']['name']} ({details['parent']['type']})")

print(f"External connections: {len(details['connections_in_range'])}")

# Get children of a block
children = graph_ops.get_block_children(block_id)
print(f"Children: {len(children)}")
for child in children:
    print(f"  {child['type']}: {child['name']}")

# Get full hierarchy path
hierarchy = graph_ops.get_block_hierarchy_path(block_id)
print("Hierarchy path:")
for level in hierarchy:
    print(f"  → {level['type']}: {level['name']}")
```

### 6. Pattern and Similarity Search

```python
# Find similar function implementations
similar = graph_ops.find_similar_implementations("upload", "function")
print(f"Found {len(similar)} similar implementations:")
for impl in similar:
    print(f"  {impl['file_path']}:{impl['line']} - {impl['preview']}")

# Find files with specific patterns
pattern_files = graph_ops.find_files_with_pattern("async.*upload")
print(f"Files matching pattern:")
for file in pattern_files:
    print(f"  {file['file_path']}: {file['match_count']} matches")
```

### 7. External Connections and Cross-Project Impact

```python
# Get external connections for a file
file_id = 123
connections = graph_ops.get_external_connections(file_id)
print(f"External connections: {len(connections)}")
for conn in connections:
    print(f"  {conn['direction']}: {conn['description']} ({conn['technology_name']})")

# Get connection impact analysis
impact = graph_ops.get_connection_impact(file_id)
print(f"High-confidence connections: {len(impact)}")
for imp in impact:
    print(f"  {imp['impact_type']}: {imp['description']} (confidence: {imp['match_confidence']})")
```

## Integration with Agent Tools

### With Semantic Search Results
```python
# Agent workflow: semantic_search → resolve → get_details
def process_semantic_results(semantic_results):
    # Convert semantic search node IDs to concrete data
    resolved = graph_ops.resolve_embedding_nodes(semantic_results)
    
    detailed_results = []
    for item in resolved:
        if 'content' in item:  # It's a block
            details = graph_ops.get_block_details(item['id'])
            detailed_results.append(details)
        else:  # It's a file
            summary = graph_ops.get_file_block_summary(item['id'])
            detailed_results.append({
                'type': 'file_summary',
                'file_path': item['file_path'],
                'blocks': summary
            })
    
    return detailed_results
```

### With Keyword Search Scoping
```python
# Agent workflow: get_scope → search_keyword
def scoped_keyword_search(anchor_file_id, keyword):
    # Get focused search scope
    scope = graph_ops.get_search_scope_by_import_graph(
        anchor_file_id=anchor_file_id,
        direction="both",
        max_depth=2
    )
    
    # Search within scope (would call search_keyword tool here)
    # This constrains the search to relevant files only
    return scope['paths']  # Use these paths in search_keyword tool
```

## Best Practices

### 1. Always Use Search Scoping
```python
# ❌ Don't search entire codebase
all_usage = graph_ops.get_files_using_symbol("function_name")

# ✅ Do scope your searches
scope = graph_ops.get_search_scope_by_import_graph(anchor_file_id)
scoped_usage = graph_ops.get_files_using_symbol("function_name", scope['paths'])
```

### 2. Handle None Results Gracefully
```python
# ❌ Don't assume results exist
block_details = graph_ops.get_block_details(block_id)
print(block_details['name'])  # Could crash if None

# ✅ Do check for None
block_details = graph_ops.get_block_details(block_id)
if block_details:
    print(f"Found block: {block_details['name']}")
else:
    print("Block not found")
```

### 3. Limit Result Processing
```python
# Results are already limited by the methods (15-25 items)
# But process them efficiently
results = graph_ops.get_file_block_summary(file_id)
for block in results[:10]:  # Process first 10 if you need fewer
    process_block(block)
```

### 4. Use Appropriate Methods for Your Needs
```python
# ❌ Don't get full details when you only need summary
for file_id in file_ids:
    file_data = graph_ops.resolve_file(file_id)  # Gets full content
    print(file_data['file_path'])

# ✅ Do use summary methods when appropriate
for file_id in file_ids:
    blocks = graph_ops.get_file_block_summary(file_id)  # Just structure
    print(f"File has {len(blocks)} blocks")
```

## Error Handling

```python
def safe_get_block_details(block_id):
    try:
        details = graph_ops.get_block_details(block_id)
        if details:
            return details
        else:
            print(f"Block {block_id} not found")
            return None
    except Exception as e:
        print(f"Error getting block details: {e}")
        return None

def safe_dependency_analysis(file_id):
    try:
        # Multiple related operations
        imports = graph_ops.get_imports(file_id)
        importers = graph_ops.get_importers(file_id)
        chain = graph_ops.get_dependency_chain(file_id, depth=3)
        
        return {
            'imports': imports,
            'importers': importers,
            'chain': chain
        }
    except Exception as e:
        print(f"Error in dependency analysis: {e}")
        return {
            'imports': [],
            'importers': [],
            'chain': []
        }
```

## Performance Tips

### 1. Batch Operations When Possible
```python
# ❌ Don't make multiple individual calls
for block_id in block_ids:
    details = graph_ops.get_block_details(block_id)
    process_details(details)

# ✅ Do get summary first, then details for selected items
file_blocks = graph_ops.get_file_block_summary(file_id)
interesting_blocks = [b for b in file_blocks if b['type'] == 'function']
for block in interesting_blocks[:5]:  # Limit to 5 most relevant
    details = graph_ops.get_block_details(block['id'])
    process_details(details)
```

### 2. Cache Search Scopes
```python
# Cache scope for multiple searches
scope = graph_ops.get_search_scope_by_import_graph(anchor_file_id)
scope_paths = scope['paths']

# Reuse for multiple searches
usage1 = graph_ops.get_files_using_symbol("pattern1", scope_paths)
usage2 = graph_ops.get_files_using_symbol("pattern2", scope_paths)
```

## Legacy Method Mapping

If you're migrating from old query names:

```python
# Old way
results = connection.execute_query(GET_NODES_BY_EXACT_NAME, {"name": "function_name"})

# New way
results = graph_ops.find_files_with_pattern(f"^{re.escape('function_name')}")

# Old way
file_content = connection.execute_query(GET_CODE_FROM_FILE, {"file_id": file_id})

# New way
file_content = graph_ops.resolve_file(file_id)
```

## Common Gotchas

1. **File vs Block IDs**: Make sure you're passing the right type of ID to each method
2. **Empty Results**: Many methods return empty lists rather than None - check `len(results)`
3. **Ripgrep Dependencies**: Pattern methods require `rg` command to be available
4. **Line Number Indexing**: Line numbers are 1-based, not 0-based
5. **Path Formats**: File paths are relative to project root

## Example: Complete Agent Workflow

```python
def analyze_code_change_impact(block_id):
    """Complete workflow for analyzing the impact of changing a code block."""
    
    # 1. Get block details and context
    block_details = graph_ops.get_block_details(block_id)
    if not block_details:
        return "Block not found"
    
    print(f"Analyzing: {block_details['name']} in {block_details['file_path']}")
    
    # 2. Get file-level impact scope
    file_id = block_details['file_id']
    impact_scope = graph_ops.get_file_impact_scope(file_id)
    
    print(f"File is connected to {len(impact_scope)} other files")
    
    # 3. Get focused search scope for symbol usage
    scope = graph_ops.get_search_scope_by_import_graph(file_id, direction="both")
    
    # 4. Find where this block's name is used
    symbol_usage = graph_ops.get_files_using_symbol(
        symbol_pattern=block_details['name'],
        paths=scope['paths']
    )
    
    print(f"Symbol '{block_details['name']}' used in {len(symbol_usage)} locations")
    
    # 5. Check for similar implementations for reference
    similar = graph_ops.find_similar_implementations(
        block_details['name'], 
        block_details['type']
    )
    
    print(f"Found {len(similar)} similar implementations")
    
    # 6. Get external connections that might be affected
    connections = graph_ops.get_external_connections(file_id)
    
    return {
        'block': block_details,
        'file_impact': impact_scope,
        'symbol_usage': symbol_usage,
        'similar_implementations': similar,
        'external_connections': connections
    }
```

This comprehensive analysis can guide roadmap planning by showing all the places that might be affected by a code change.