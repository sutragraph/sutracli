# AI Agent Navigation Plan: Database Queries for Code Understanding

## How AI Agents Actually Work

### **Agent Navigation Patterns:**
1. **Semantic Discovery** → Find relevant code through embeddings
2. **Precise Lookup** → Get exact details of discovered items  
3. **Context Expansion** → Understand surrounding code structure
4. **Relationship Mapping** → Follow dependencies and connections
5. **Focused Analysis** → Drill down into specific implementations

### **Current Agent Workflow:**
```
User Query → Semantic Search → Get node_id results → ??? → Database lookup → Code analysis
                                                    ↑
                                            MISSING BRIDGE
```

## Critical Missing Bridge: Semantic Search → Database

### **Problem:**
- Semantic search returns `node_id` like "block_123" or "file_456"
- No way to convert these to actual database records
- Agent can't get from semantic results to structured data

### **Solution Needed:**
```sql
-- Parse node_id format and route to appropriate query
GET_NODE_DETAILS_BY_EMBEDDING_ID(node_id) → 
  if starts_with("block_") → GET_CODE_BLOCK_BY_ID(extract_id)
  if starts_with("file_") → GET_FILE_BY_ID(extract_id)
```

## Agent-Centric Query Design

### **1. Discovery Queries (Post-Semantic Search)**
```sql
-- CRITICAL: Bridge semantic search to database
GET_CODE_BLOCK_BY_ID(block_id) → Full block details + file context
GET_FILE_BY_ID(file_id) → File details + block summary

-- Quick context for discovered items
GET_BLOCK_CONTEXT(block_id) → Parent class/function + file info
GET_FILE_BLOCK_SUMMARY(file_id) → All block names/types (no content)
```

### **2. Context Expansion Queries**
```sql
-- Understand what's around the discovered code
GET_SIBLING_BLOCKS(block_id) → Other blocks at same level
GET_CHILD_BLOCKS(block_id) → Methods in class, nested functions
GET_PARENT_BLOCK(block_id) → Containing class/function

-- File-level context
GET_FILE_IMPORTS(file_id) → What this file depends on
GET_FILE_IMPORTERS(file_id) → What depends on this file
```

### **3. Focused Navigation Queries**
```sql
-- Find specific things by name (when agent knows what to look for)
GET_BLOCKS_BY_NAME_IN_FILE(file_id, name) → Find specific function/class in file
GET_BLOCKS_BY_TYPE_IN_FILE(file_id, type) → All functions/classes in file
GET_BLOCKS_BY_NAME_PATTERN(pattern) → Fuzzy search across all blocks

-- Line-based navigation (when agent has line numbers)
GET_BLOCKS_AT_LINE(file_id, line_number) → What block contains this line
GET_BLOCKS_IN_RANGE(file_id, start_line, end_line) → All blocks in range
```

### **4. Relationship Mapping**
```sql
-- Follow dependencies
GET_IMPORTED_SYMBOLS(file_id) → What symbols this file imports
GET_SYMBOL_SOURCES(symbol_name) → Where a symbol is defined
GET_DEPENDENCY_CHAIN(file_id, depth) → Multi-level dependency tree

-- Cross-project connections
GET_EXTERNAL_CONNECTIONS(file_id) → APIs, databases, services this file uses
GET_CONNECTION_DETAILS(connection_id) → Full details of external connection
```

## What Agents DON'T Need

### **Avoid These Query Types:**
- `GET_ALL_FILES` → Too much data, agent can't process
- `GET_PROJECT_STATISTICS` → Agent doesn't care about counts
- `GET_FILES_BY_LANGUAGE` → Agent searches semantically, not by language
- `GET_CIRCULAR_DEPENDENCIES` → Too complex, agent won't use

### **Why These Are Bad:**
- **Information Overload** → Agents need focused, relevant data
- **No Clear Action** → Agent can't decide what to do with 100 files
- **Performance Issues** → Large result sets slow down agent reasoning

## Optimized Query Set for AI Agents

### **Tier 1: Critical (Must Implement First)**
1. `GET_CODE_BLOCK_BY_ID` - Bridge from semantic search
2. `GET_FILE_BY_ID` - Bridge from semantic search  
3. `GET_NODE_DETAILS_BY_EMBEDDING_ID` - Parse and route function
4. `GET_FILE_BLOCK_SUMMARY` - Quick overview without content
5. `GET_BLOCKS_BY_NAME_IN_FILE` - Find specific items in discovered files

### **Tier 2: Important (Context Expansion)**
1. `GET_CHILD_BLOCKS` - Navigate into discovered classes/functions
2. `GET_PARENT_BLOCK` - Navigate up hierarchy
3. `GET_FILE_IMPORTS` - Understand dependencies
4. `GET_IMPORTED_SYMBOLS` - What symbols are available

### **Tier 3: Advanced (Relationship Mapping)**
1. `GET_SYMBOL_SOURCES` - Where symbols come from
2. `GET_BLOCKS_AT_LINE` - Line-based navigation
3. `GET_EXTERNAL_CONNECTIONS` - Cross-project analysis

## Query Design Principles

### **1. Focused Results**
- Return 5-20 items max, not hundreds
- Include only essential fields
- Provide content only when explicitly needed

### **2. Context-Rich**
- Always include file path and project name
- Include line numbers for navigation
- Show relationships (parent/child)

### **3. Action-Oriented**
- Results should suggest next steps
- Include enough info for agent to decide
- Support common navigation patterns

### **4. Performance-First**
- Use indexes effectively
- Avoid expensive JOINs when possible
- Support pagination for large results

## Implementation Strategy

### **Phase 1: Bridge the Gap**
Implement the semantic search bridge immediately:
- `GET_CODE_BLOCK_BY_ID`
- `GET_FILE_BY_ID` 
- `GET_NODE_DETAILS_BY_EMBEDDING_ID`

### **Phase 2: Context Navigation**
Add queries for exploring discovered code:
- `GET_FILE_BLOCK_SUMMARY`
- `GET_CHILD_BLOCKS`
- `GET_PARENT_BLOCK`

### **Phase 3: Relationship Mapping**
Enable dependency analysis:
- `GET_FILE_IMPORTS`
- `GET_IMPORTED_SYMBOLS`
- `GET_SYMBOL_SOURCES`

This approach focuses on how agents actually think and navigate, rather than providing database-centric queries that agents won't effectively use.
