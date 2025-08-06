# Agent Query Architecture: Exposed vs Background Queries

## Overview
The roadmap agent needs two types of queries:
1. **Exposed Queries** - Direct agent access via database tool
2. **Background Queries** - Automatic conversions and data enrichment

## Step-by-Step Agent Workflow

### **Step 1: Initial Discovery**
**Agent Action:** Semantic search for relevant code
```
<semantic_search><query>user profile picture upload</query></semantic_search>
```

**Background Processing:**
- Semantic search returns: `[{node_id: "block_1234", similarity: 0.85}, {node_id: "block_5678", similarity: 0.78}]`
- **Auto-convert each `node_id` to actual code details**
- Background query: `GET_CODE_BLOCK_BY_ID(1234)` → Full function details
- Background query: `GET_CODE_BLOCK_BY_ID(5678)` → Full function details

**Agent Receives:** Formatted code blocks with file context, not just IDs

---

### **Step 2: Context Expansion**
**Agent Action:** Understand what's around discovered code
```
<database>
<query_name>GET_FILE_BLOCK_SUMMARY</query_name>
<file_id>456</file_id>
</database>
```

**Exposed Query:** `GET_FILE_BLOCK_SUMMARY(file_id)`
**Background Processing:** None needed - direct query result

**Agent Receives:** List of all functions/classes in the file (no content, just names/types)

---

### **Step 3: Impact Analysis**
**Agent Action:** Find what will be affected by changes
```
<database>
<query_name>GET_FILES_USING_SYMBOL</query_name>
<symbol>uploadAvatar</symbol>
</database>
```

**Exposed Query:** `GET_FILES_USING_SYMBOL(symbol_pattern)`
**Background Processing:** 
- Query returns file IDs and import statements
- **Auto-enrich with file paths and project names**
- Background query: Join with files and projects tables

**Agent Receives:** List of files that import/use the symbol with full context

---

### **Step 4: Dependency Mapping**
**Agent Action:** Understand implementation order
```
<database>
<query_name>GET_DEPENDENCY_CHAIN</query_name>
<file_id>456</file_id>
</database>
```

**Exposed Query:** `GET_DEPENDENCY_CHAIN(file_id)`
**Background Processing:**
- Recursive CTE query traces dependency chain
- **Auto-limit to 5 levels deep** to prevent infinite loops
- **Auto-format dependency paths** for readability

**Agent Receives:** Ordered dependency chain with file paths

---

### **Step 5: Cross-Project Impact**
**Agent Action:** Check external system effects
```
<database>
<query_name>GET_EXTERNAL_CONNECTIONS</query_name>
<file_id>456</file_id>
</database>
```

**Exposed Query:** `GET_EXTERNAL_CONNECTIONS(file_id)`
**Background Processing:**
- Query both incoming and outgoing connections
- **Auto-merge results** into single response
- **Auto-filter by confidence** (only show > 0.5 confidence)

**Agent Receives:** Combined list of external integrations

---

### **Step 6: Pattern Recognition**
**Agent Action:** Find similar implementations
```
<database>
<query_name>GET_SIMILAR_IMPLEMENTATIONS</query_name>
<type>function</type>
<pattern>upload%</pattern>
</database>
```

**Exposed Query:** `GET_SIMILAR_IMPLEMENTATIONS(type, pattern)`
**Background Processing:**
- **Auto-add file context** to each result
- **Auto-sort by relevance** (name similarity)
- **Auto-limit to 15 results** to prevent overload

**Agent Receives:** Relevant similar functions with file context

## Query Categories

### **EXPOSED QUERIES (Agent Direct Access)**
```sql
-- Discovery & Context
GET_FILE_BLOCK_SUMMARY(file_id)
GET_CHILD_BLOCKS(block_id)
GET_PARENT_BLOCK(block_id)

-- Impact Analysis  
GET_FILES_USING_SYMBOL(symbol_pattern)
GET_SYMBOL_IMPACT_SCOPE(file_id)
GET_DEPENDENCY_CHAIN(file_id)

-- Cross-Project Analysis
GET_EXTERNAL_CONNECTIONS(file_id)
GET_PROJECT_EXTERNAL_CONNECTIONS(project_id)
GET_CONNECTION_IMPACT(file_id)

-- Pattern Recognition
GET_SIMILAR_IMPLEMENTATIONS(type, pattern)
GET_FILES_WITH_PATTERN(pattern)

-- Utility Queries
GET_SYMBOL_SOURCES(symbol_name)
GET_FILE_IMPORTS(file_id)
```

### **BACKGROUND QUERIES (Auto-Conversion)**
```sql
-- Semantic Search Bridge (CRITICAL)
GET_CODE_BLOCK_BY_ID(block_id) -- Convert "block_123" to actual code
GET_FILE_BY_ID(file_id) -- Convert "file_456" to actual file

-- Data Enrichment
GET_IMPLEMENTATION_CONTEXT(file_id) -- Add parent/child context
GET_FILE_COMPLEXITY_SCORE(file_id) -- Add complexity metrics

-- Auto-Formatting
FORMAT_DEPENDENCY_PATH(chain) -- Make dependency chains readable
MERGE_CONNECTION_RESULTS(incoming, outgoing) -- Combine connection types
FILTER_BY_CONFIDENCE(connections, threshold) -- Remove low-confidence matches
```

## Critical Background Processing

### **1. Semantic Search Bridge (MOST IMPORTANT)**
```python
# When semantic search returns results
for result in semantic_results:
    if result.node_id.startswith("block_"):
        # BACKGROUND: Auto-convert to actual code
        block_details = GET_CODE_BLOCK_BY_ID(extract_id(result.node_id))
        # Agent receives formatted code, not just ID
```

### **2. Auto-Enrichment**
```python
# When agent queries for impact analysis
raw_results = GET_FILES_USING_SYMBOL("uploadAvatar")
# BACKGROUND: Auto-add file paths, project names, line numbers
enriched_results = enrich_with_file_context(raw_results)
# Agent receives rich context, not just raw data
```

### **3. Auto-Limiting**
```python
# Prevent agent overload
results = query_database(sql)
# BACKGROUND: Auto-apply limits
limited_results = results[:15]  # Max 15 items
# Agent receives manageable result sets
```

### **4. Auto-Formatting**
```python
# Make results agent-friendly
dependency_chain = GET_DEPENDENCY_CHAIN(file_id)
# BACKGROUND: Format for readability
formatted_chain = format_as_readable_path(dependency_chain)
# Agent receives "A → B → C" not raw SQL results
```

## Implementation Priority

### **Phase 1: Critical Bridge**
1. **GET_CODE_BLOCK_BY_ID** (background) - Convert semantic search results
2. **GET_FILE_BY_ID** (background) - Convert semantic search results
3. **GET_FILE_BLOCK_SUMMARY** (exposed) - Context expansion

### **Phase 2: Impact Analysis**
1. **GET_FILES_USING_SYMBOL** (exposed) - Find affected files
2. **GET_DEPENDENCY_CHAIN** (exposed) - Implementation order
3. **Auto-enrichment** (background) - Add file context

### **Phase 3: Cross-Project**
1. **GET_EXTERNAL_CONNECTIONS** (exposed) - External impacts
2. **GET_CONNECTION_IMPACT** (exposed) - Mapped connections
3. **Auto-filtering** (background) - Remove low-confidence results

## Key Principles

### **Exposed Queries Should:**
- Return 5-20 items max
- Include rich context (file paths, line numbers)
- Be action-oriented (suggest next steps)
- Have clear parameters

### **Background Processing Should:**
- Convert IDs to actual data automatically
- Enrich results with context
- Apply sensible limits
- Format for agent consumption
- Never expose raw database complexity

This architecture ensures the agent gets **actionable, context-rich data** without being overwhelmed by database complexity or raw IDs.
