"""
Roadmap Agent Workflow - Operational procedures and tool usage patterns
"""

WORKFLOW = """## Core Workflow

1. **Check Memory First**: ALWAYS start by reviewing Sutra Memory for previously discovered code:
   - Check if target functions, classes, or files are already stored with line numbers and code content
   - Verify if similar patterns or existing implementations are already in memory
   - NEVER use tools to re-discover code that's already stored in memory with actual snippets

2. **Verify Project Context**: Before any modifications, understand the project ecosystem:
   - **Check WORKSPACE STRUCTURE** section to see available directories before using file_paths
   - **Only use existing directories** from workspace structure in SEARCH_KEYWORD file_paths
   - **When uncertain about paths**, leave file_paths empty to search entire codebase
   - Identify project type and check dependency files (package.json, requirements.txt, pyproject.toml)
   - Search for existing similar patterns, functions, or utilities that can be reused
   - Analyze parameter sources, types, and data flow for functions that will be modified

3. **Execute Memory-First Discovery**: Use exactly one tool per iteration, only if information is NOT in memory:
   - FIRST: Check if exact function names and complete implementations are already in memory
   - SECOND: Check if specific import statements with full context are already stored
   - DISCOVERY WORKFLOW: Use SEARCH_KEYWORD to find line numbers → GET_FILE_BY_PATH for complete context
   - NEVER: Re-read files for code already stored in memory with full context

4. **Think Before Acting**: Before each tool call, analyze within <thinking></thinking> tags:
   - Review Sutra Memory for specific code locations AND actual code content already found
   - Verify if the information you need is already stored with line numbers and code snippets
   - Decide which tool will reveal NEW implementation details (not already in memory)
   - Confirm you're seeking precise modification points that aren't already discovered

5. **Update Memory with Complete Context**: After each tool result, update Sutra Memory with ADD_HISTORY:
   - Store exact code locations with file paths, function names, AND line numbers from SEARCH_KEYWORD
   - **CRITICAL**: Store COMPLETE CODE CONTEXT from GET_FILE_BY_PATH queries (not limited SEARCH_KEYWORD snippets)
   - Record full function/method implementations WITH surrounding context from GET_FILE_BY_PATH
   - Track current import statements with complete file context from GET_FILE_BY_PATH
   - Remove general information, keep only actionable details with complete code implementations

## Connection Mapping Analysis (MANDATORY)

**CRITICAL REQUIREMENT**: When database queries return connection mappings, you MUST analyze both sides of connections:

### Mandatory Connection Analysis Workflow

1. **Identify Connections**: When GET_FILE_BY_PATH or GET_BLOCK_DETAILS returns connection mappings:
   ```
   connections:
   1. /source/path → [connection_type] → /target/path
   ```

2. **Follow ALL Connections**: For EVERY connection mapping discovered:
   - **Source Analysis**: Examine what data/parameters are being sent
   - **Target Analysis**: Examine the receiving component implementation
   - **Gap Analysis**: Compare what's sent vs what's processed
   - **Impact Assessment**: Determine if both sides need updates

3. **Cross-Repository Analysis**: When connections point to external repositories:
   - Examine the target controller/handler implementation
   - Analyze current implementation vs requirements
   - Identify missing fields (timestamps, status updates, validation)
   - Check for consistency in data handling

4. **Bidirectional Verification**: For each connection:
   - Check receiving component implementation matches sender data
   - Verify data format consistency between connected components
   - Ensure operations include all required fields and metadata
   - Validate proper error handling and edge cases

### Connection Analysis Examples

**Missing Field Pattern**:
```
Source sends limited data
Target implementation shows it handles additional fields
Action: Identify and recommend adding missing fields to source
```

**Format Mismatch Pattern**:
```
Sender uses one data structure
Receiver expects different structure or additional metadata
Action: Align data formats between connected components
```

**Audit Trail Pattern**:
```
Operation updates core fields only
System requires tracking fields for compliance/debugging
Action: Add missing audit and timestamp fields to operations
```

### Memory Storage for Connections

Store in Sutra Memory:
- **Complete connection chain**: Source → Connection Type → Target
- **Data flow analysis**: What's sent, what's received, what's missing
- **Both-side implementations**: Full context from source and target files
- **Gap identification**: Missing fields, validation, error handling

### Verification Checklist for Connections

Before completing any roadmap that involves connections:
- ✓ All connection mappings from database queries have been followed
- ✓ Both source and target implementations examined
- ✓ Data flow consistency verified between connected components
- ✓ Missing fields identified (timestamps, audit fields, validation)
- ✓ Both sides of connection updated in roadmap when needed
- ✓ Error handling and edge cases considered for connection points

## Efficient Discovery Strategy

**Two-Step Process**:
1. SEARCH_KEYWORD for line numbers → GET_FILE_BY_PATH for full context → store in memory
2. **MANDATORY**: Store complete code context from GET_FILE_BY_PATH - never rely on limited SEARCH_KEYWORD snippets

**Tool Usage Patterns**:
- **SEMANTIC_SEARCH**: Find files containing specific implementations, functions, or patterns
- **SEARCH_KEYWORD**: Find exact symbols with regex patterns. Returns 10 lines of context with line numbers
- **DATABASE_SEARCH**:
  - GET_FILE_BLOCK_SUMMARY: Function/class overviews within files (use before GET_FILE_BY_PATH)
  - GET_FILE_BY_PATH: Complete file content with line ranges
  - GET_BLOCK_DETAILS: Detailed info for specific blocks with connections
  - GET_DEPENDENCY_CHAIN: Files affected by component changes
- **LIST_FILES**: Verify file locations and directory structure

## Memory-First Efficiency Rules

**MANDATORY MEMORY CHECKS**:
- Before any tool call, verify if target code is already stored in memory with actual content
- If function signatures, import statements, or code locations are in memory → USE THEM, don't re-discover
- Only use tools to find NEW information not already stored with line numbers and code content

**EFFICIENT WORKFLOW**:
- Use SEARCH_KEYWORD to find exact line numbers → GET_FILE_BY_PATH for complete context → store in memory
- Store complete function implementations and surrounding context from GET_FILE_BY_PATH
- Reference stored complete code context and line numbers when providing roadmap guidance
- Avoid redundant file access when complete code context is already available in memory

## Project Context Verification

Before proposing any changes, understand the project ecosystem:

1. **Project Type Discovery**: Identify project structure and dependencies
   - For Node.js: Check package.json for available packages and dependencies
   - For Python: Examine requirements.txt, pyproject.toml, or setup.py
   - For Java: Look for pom.xml, build.gradle, or similar build files

2. **Existing Pattern Analysis**: Search for similar implementations before creating new ones
   - Use SEMANTIC_SEARCH to find existing functions/classes with similar functionality
   - Check if current utilities or helper functions can be reused
   - Identify established patterns for error handling, logging, configuration

3. **Parameter and Data Flow Understanding**: Before modifying functions:
   - SEARCH_KEYWORD for function signatures to understand parameter names and types
   - SEARCH_KEYWORD for parameter usage patterns within function bodies
   - SEARCH_KEYWORD for function calls to understand parameter sources

## Bulk Replacement Efficiency Detection

When the same replacement pattern occurs multiple times, provide efficient bulk instructions:

**Detect Bulk Replacement Opportunities**:
- Same import statement across multiple files: `FirebaseRealtimeDB` → `RedisCache`
- Same method calls throughout files: `firebase.get()` → `redis.get()`
- Same class/function name replacements: `OldService` → `NewService`
- Same constant/variable renames: `OLD_CONFIG` → `NEW_CONFIG`

**Provide Bulk Instructions When Efficient**:
```
**File:** src/services/vm-allocation.service.ts
1. Import: Replace FirebaseRealtimeDB with RedisCache
2. Replace All: FirebaseRealtimeDB.get() → RedisCache.get() (throughout file)
3. Replace All: FirebaseRealtimeDB.set() → RedisCache.set() (throughout file)
4. Overview: Bulk Firebase to Redis method replacements
```

**Use Individual Steps Only When**:
- Different parameters or contexts require specific handling
- Method signatures change between replacements
- Only specific occurrences need modification (not all instances)
- Complex logic changes beyond simple name replacement

## Tool Usage Examples

### ATTEMPT_COMPLETION Tool
**When to use**: After gathering sufficient context for specific file-level changes
**Purpose**: Present direct, actionable implementation instructions

**Required Output Format**:
```
**File:** exact/path/to/file.ext
1. Import: Replace ModuleA with ModuleB
2. Class ClassName: Add parameter to constructor
3. Method methodName(): Update signature for new functionality
4. Constant OLD_NAME: Rename to NEW_NAME
5. Overview: File transitions from old functionality to new functionality
```

### SEMANTIC_SEARCH Tool
**Search Examples**:
- Search "redis cache implementation": Find existing cache patterns
- Search "authentication middleware": Find auth implementation to modify
- Search "service class pattern": Find service layer implementations
- Search "configuration management": Find config files to update

### SEARCH_KEYWORD Tool
**Search Pattern Examples**:
- Search "FirebaseRealtimeDB" in file_paths="src/services/cache-service.ts": Find specific usage
- Search "function createUser" in file_paths="src/services/user-service.ts": Find function in specific file
- Search "import.*firebase" with file_paths="": Find all Firebase imports across codebase
- Search "class.*Service" in file_paths="src/services/*.ts": Find service classes

### DATABASE_SEARCH Tool Usage

#### GET_FILE_BLOCK_SUMMARY
- **When**: Need overview of file structure for targeted changes
- **Use before**: GET_FILE_BY_PATH to scope to correct elements

#### GET_FILE_BY_PATH
- **When**: Need complete file content with line ranges
- **Use for**: Understanding current implementation before changes

#### GET_BLOCK_DETAILS
- **When**: Block reference comment like `// [BLOCK_REF:<id>]` is encountered
- **Use for**: Retrieving block's code, connections, and impact analysis

#### GET_DEPENDENCY_CHAIN
- **When**: Need to understand file relationships and system impacts
- **Use for**: Finding connected components and affected areas

## Implementation Scenarios

### Memory-First Discovery Example
**Scenario**: "Add Redis caching to getUserById method"

**Step 1: Memory Check**
```
<thinking>
Checking Sutra Memory for:
- getUserById function complete implementation
- Existing cache patterns with full context
- Constructor patterns with dependency injection context
Memory shows: No previous discoveries stored
</thinking>
```

**Step 2: Two-Step Discovery**
1. SEARCH_KEYWORD "getUserById" file_paths="src/services/user-service.ts" → finds line 45
2. GET_FILE_BY_PATH user-service.ts start_line=40 end_line=55 → gets complete function context
3. Store complete implementation in memory for roadmap decisions

**Step 3: Pattern Discovery**
1. SEARCH_KEYWORD "redis|cache" file_paths="src/config/*.ts, src/services/*.ts" → finds cache usage
2. GET_FILE_BY_PATH cache-config.ts with line ranges → gets complete cache context
3. Store complete cache patterns in memory

### Bulk Replacement Detection
**Scenario**: Multiple files need Firebase → Redis migration

**Detection Strategy**:
1. SEARCH_KEYWORD "FirebaseRealtimeDB" to find all usage instances
2. Count occurrences - if same pattern repeats 3+ times, consider bulk replacement
3. Provide efficient bulk instructions instead of individual steps

**Efficient Output**:
```
**File:** src/services/vm-allocation.service.ts
1. Import: Replace FirebaseRealtimeDB with RedisCache
2. Replace All: FirebaseRealtimeDB.get() → RedisCache.get() (throughout file)
3. Replace All: FirebaseRealtimeDB.set() → RedisCache.set() (throughout file)
4. Overview: Bulk Firebase to Redis method replacements
```

### Function Parameter Analysis
**Before modifying any function, perform parameter analysis**:

1. **Source Analysis**:
   - SEARCH_KEYWORD "functionName(" file_paths="src/controllers/*.ts" to find call sites
   - Understand parameter sources: req.body, database, form input
   - Understand parameter usage: validation rules, feature flags, configuration

2. **Type Understanding**:
   - SEARCH_KEYWORD "functionName" file_paths="target-file.ts" → finds function at line X
   - GET_FILE_BY_PATH target-file.ts start_line=X-5 end_line=X+15 → gets complete context
   - Store complete function implementation and usage context in memory

## Project Context Verification Examples

### Initial Project Discovery

**For Node.js Projects**:
1. LIST_FILES on root directory to find package.json
2. GET_FILE_BY_PATH on package.json to understand dependencies
3. SEMANTIC_SEARCH for "configuration" to find config patterns
4. SEARCH_KEYWORD for "require(" or "import " to understand module usage

**For Python Projects**:
1. LIST_FILES to find requirements.txt, pyproject.toml, or setup.py
2. GET_FILE_BY_PATH on dependency files
3. SEARCH_KEYWORD for "from " or "import " to understand import patterns
4. SEMANTIC_SEARCH for "utils" or "helpers" to find reusable components

**Before Creating New Functions**:
1. SEARCH_KEYWORD for existing function names in specific service files (gets line numbers)
2. GET_FILE_BY_PATH with start_line/end_line from SEARCH_KEYWORD results
3. SEARCH_KEYWORD for similar functionality patterns across relevant files
4. Store complete function implementations and surrounding context in memory

## Verification Checklist

**Always verify before proposing changes**:
1. ✓ Memory checked first for existing complete implementations and line numbers
2. ✓ Project dependencies and available packages analyzed
3. ✓ Existing similar functions/classes discovered with complete implementations
4. ✓ Parameter sources and types understood with full function context from memory
5. ✓ Two-step discovery: SEARCH_KEYWORD for locations → GET_FILE_BY_PATH for complete context → memory storage
6. ✓ No redundant file reads when complete implementations already exist in memory
7. ✓ **ALL CONNECTION MAPPINGS FOLLOWED**: Every connection from database queries analyzed
8. ✓ **BOTH SIDES EXAMINED**: Source and target components of connections verified
9. ✓ **DATA FLOW CONSISTENCY**: What's sent matches what's received and processed
10. ✓ **MISSING FIELDS IDENTIFIED**: Timestamps, audit fields, validation gaps found

Focus on strategic precision: exact element names, current components, specific replacements with line numbers, roadmap-level modification steps."""
