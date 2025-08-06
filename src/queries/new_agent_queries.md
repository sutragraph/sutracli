# Database Queries for AI Agent Code Navigation

Based on our actual database schema and extraction capabilities. These queries provide raw data for the agent to make intelligent decisions about code navigation, dependencies, and change impact.

## Core Block & File Retrieval

### `GET_CODE_BLOCK_DETAILS` ✅ **Database Query**
**Purpose**: Get complete block info with file/project context
**Returns**: block content, type, name, lines, file_path, project_name, language
**SQL**: `code_blocks JOIN files JOIN projects WHERE code_blocks.id = ?`

### `GET_FILE_DETAILS` ✅ **Database Query**
**Purpose**: Get file metadata with project context and block count
**Returns**: file info + project name + total blocks in file
**SQL**: `files JOIN projects LEFT JOIN code_blocks WHERE files.id = ?`

### `GET_NODE_DETAILS_BY_EMBEDDING_ID` ✅ **Database Query**
**Purpose**: Bridge semantic search results to actual code
**Returns**: Unified format for both block and file results from embeddings
**Logic**: Parse node_id ("block_123" or "file_456") → query appropriate table

## Block Hierarchy Navigation

### `GET_FILE_BLOCK_OVERVIEW` ✅ **Database Query**
**Purpose**: Get all top-level blocks in a file with basic info
**Returns**: block names, types, line ranges (no content for performance)
**SQL**: `code_blocks WHERE file_id = ? AND parent_block_id IS NULL`

### `GET_CHILD_BLOCKS` ✅ **Database Query**
**Purpose**: Get direct children of a parent block
**Returns**: Child block details (methods in class, nested functions)
**SQL**: `code_blocks WHERE parent_block_id = ?`

### `GET_PARENT_BLOCK` ✅ **Database Query**
**Purpose**: Get the immediate parent of a block
**Returns**: Parent block details
**SQL**: `code_blocks WHERE id = (SELECT parent_block_id FROM code_blocks WHERE id = ?)`

### `GET_BLOCK_HIERARCHY_PATH` ✅ **Database Function**
**Purpose**: Get full nesting path from root to specific block
**Returns**: Ordered list of parent blocks (root → target)
**Logic**: Recursive traversal up parent_block_id chain

## File Dependencies & Relationships

### `GET_FILE_IMPORTS` ✅ **Database Query**
**Purpose**: Get all files this file imports (outgoing dependencies)
**Returns**: Target files with import statements and symbols
**SQL**: `relationships JOIN files WHERE source_id = ?`

### `GET_FILE_IMPORTERS` ✅ **Database Query**
**Purpose**: Get all files that import this file (incoming dependencies)
**Returns**: Source files that depend on this file
**SQL**: `relationships JOIN files WHERE target_id = ?`

### `TRACE_DEPENDENCY_CHAIN` ✅ **Database Function**
**Purpose**: Follow import chain through multiple hops
**Returns**: Multi-level dependency tree
**Logic**: Recursive traversal through relationships table

## Cross-Project Connections

### `GET_FILE_INCOMING_CONNECTIONS` ✅ **Database Query**
**Purpose**: Get external systems/APIs that connect to this file
**Returns**: Incoming connection details with technology info
**SQL**: `incoming_connections WHERE file_id = ?`

### `GET_FILE_OUTGOING_CONNECTIONS` ✅ **Database Query**
**Purpose**: Get external systems this file connects to
**Returns**: Outgoing connection details with technology info
**SQL**: `outgoing_connections WHERE file_id = ?`

### `GET_CONNECTION_MAPPINGS_FOR_FILE` ✅ **Database Function**
**Purpose**: Get all connection mappings involving a file
**Returns**: Both incoming and outgoing mappings with confidence scores
**Logic**: Join through incoming/outgoing connections to connection_mappings

### `GET_PROJECT_CONNECTION_OVERVIEW` ✅ **Database Function**
**Purpose**: Get all external connections for entire project
**Returns**: Summary of all project's external integrations
**Logic**: Aggregate connections across all project files

## Major Limitations & Missing Capabilities

### ❌ **What We DON'T Extract/Store:**
1. **Function calls within blocks** - We don't parse internal function calls
2. **Variable references** - We don't track variable usage across blocks
3. **Interface implementations** - We don't extract interface/inheritance relationships
4. **Data flow** - We don't track how data moves through functions
5. **Call chains** - We can't trace function execution paths
6. **Coupling analysis** - We don't measure code coupling
7. **Architectural layers** - We don't classify code into architectural layers

### ⚠️ **Queries That Need External Tools:**
- **FIND_FUNCTION_CALLS** → Use ripgrep/AST parsing
- **TRACE_CALL_CHAIN** → Use static analysis tools
- **GET_VARIABLE_REFERENCES** → Use language servers
- **FIND_INTERFACE_IMPLEMENTATIONS** → Use ripgrep + pattern matching
- **ANALYZE_DATA_FLOW** → Use specialized analysis tools

### ✅ **What We CAN Provide:**
- File-level dependency mapping
- Block hierarchy within files
- Cross-project connection points
- Import/export relationships
- External system integrations
- Project structure overview

## Implementation Priority

1. **GET_CODE_BLOCK_DETAILS** - Critical for semantic search
2. **GET_NODE_DETAILS_BY_EMBEDDING_ID** - Critical bridge query
3. **GET_FILE_IMPORTS/IMPORTERS** - Essential for dependency analysis
4. **GET_CHILD_BLOCKS** - Important for code exploration
5. **GET_FILE_INCOMING/OUTGOING_CONNECTIONS** - Important for integration analysis
