"""
Tool Usage Examples and Instructions for Roadmap Agent

This file contains detailed usage instructions and examples for all tools available
to the roadmap agent. Focus on finding specific code changes and implementation details.
"""

TOOL_USAGE_CASES = """
## Tool Usage Guide

## Project Context Verification Examples

### Initial Project Discovery Workflow

**For Node.js Projects**:
1. LIST_FILES on root directory to find package.json
2. DATABASE_SEARCH: GET_FILE_BY_PATH on package.json to understand available dependencies
3. SEMANTIC_SEARCH for "configuration" or "config" to find config patterns
4. SEARCH_KEYWORD for "require(" or "import " to understand module usage patterns

**For Python Projects**:
1. LIST_FILES to find requirements.txt, pyproject.toml, or setup.py
2. DATABASE_SEARCH: GET_FILE_BY_PATH on dependency files
3. SEARCH_KEYWORD for "from " or "import " to understand import patterns
4. SEMANTIC_SEARCH for "utils" or "helpers" to find reusable components

**Before Creating New Functions**:
1. SEARCH_KEYWORD for existing function names: "function validateUser", "class UserService" in specific service files (gets line numbers)
2. DATABASE_SEARCH: GET_FILE_BY_PATH with start_line/end_line from SEARCH_KEYWORD results
3. SEARCH_KEYWORD for similar functionality patterns: "validation.*function", "auth.*method" across relevant files
4. DATABASE_SEARCH: GET_CHILD_BLOCKS to examine method signatures and parameters

**Efficient Parameter Analysis Workflow**:
1. SEARCH_KEYWORD for function definition: "function functionName" in target file (gets line numbers)
2. GET_FILE_BY_PATH with start_line/end_line around the function (gets complete context)
3. SEARCH_KEYWORD for function calls: "functionName(" across multiple caller files (gets call site line numbers)
4. GET_FILE_BY_PATH on caller files with line ranges around call sites (gets full usage context)
5. Store complete function implementations and call contexts in memory

### 1. ATTEMPT_COMPLETION Tool
**When to use**: After gathering sufficient context for specific file-level changes
**Purpose**: Present direct, actionable implementation instructions

**Usage Instructions**:
- Only use after finding specific files that need modification
- Provide file-by-file instructions with exact paths and numbered steps
- NEVER include timelines, phases, or executive summaries
- Each step must specify exact element names and modifications

**Required Output Format**:
```
**File:** exact/path/to/file.ext
1. Import: Replace ModuleA with ModuleB
2. Class ClassName: Add parameter to constructor
3. Method methodName(): Update signature for new functionality
4. Constant OLD_NAME: Rename to NEW_NAME
5. Function oldFunction(): Remove deprecated implementation
6. Overview: File transitions from old functionality to new functionality
```

**ROADMAP FOCUS**: Provide strategic guidance on WHAT to change, not HOW to implement it.

### 2. SEMANTIC_SEARCH Tool
**When to use**: Find existing code patterns and files related to the user's request
**Purpose**: Discover specific implementation patterns to follow or modify

**Usage Instructions**:
- Search for relevant existing implementations
- Focus on finding files that need modification
- Look for patterns to maintain consistency
- Always follow up with DATABASE queries on relevant results

**Search Examples**:
- Search "redis cache implementation": Find existing cache patterns
- Search "database migration script": Find migration file patterns
- Search "API endpoint definition": Find endpoint implementation patterns
- Search "authentication middleware": Find auth implementation to modify
- Search "service class pattern": Find service layer implementations
- Search "configuration management": Find config files to update

### 3. LIST_FILES Tool
**When to use**: Understand directory structure for file organization
**Purpose**: Find where to create new files or locate existing ones

**Usage Instructions**:
- Check directory structure when creating new files
- Verify file locations before modification
- Understand project organization patterns
- Keep exploration focused and minimal

**Directory Examples**:
- List src/services/: Find where to add new service files
- List src/utils/: Check utility file organization
- List src/config/: Locate configuration files
- List tests/: Find test file structure for new tests

### 4. DATABASE_SEARCH Tool
**When to use**: Get specific file content and dependency information
**Purpose**: Find exact code locations and understand modification requirements

**Query Types and Usage**:

#### GET_FILE_BY_PATH
- **When**: Need to examine specific files for modification
- **Use for**: Understanding current implementation before changes
- **Focus**: Identify specific functions/classes that need updates

#### GET_FILE_BLOCK_SUMMARY
- **When**: Need overview of file structure for targeted changes
- **Use for**: Finding specific methods/functions to modify
- **Focus**: Locate exact code blocks that need changes

#### GET_BLOCK_DETAILS
- **When**: A block reference is present in code comments (e.g., `// [BLOCK_REF:123]`) or when you need the precise block and its relationships
- **Use for**: Retrieving the block’s code, start/end lines, parent/children, and all incoming/outgoing connections for impact analysis
- **Focus**: Use the block’s start/end lines to bound subsequent GET_FILE_BY_PATH requests; leverage connections to understand affected files/components

#### GET_CHILD_BLOCKS
- **When**: Need details of methods within a class for modification
- **Use for**: Understanding method signatures and implementations
- **Focus**: Find specific methods to update or replace

#### GET_DEPENDENCY_CHAIN
- **When**: Need to understand which files will be affected by changes
- **Use for**: Finding all files that import a modified component
- **Focus**: Locate files that need import/usage updates

**Database Usage Guidelines**:
- Always use CODE_CONTENT=TRUE when you need implementation details
- Store specific file paths and line ranges in memory
- Focus on immediate modification needs, not comprehensive analysis

### 5. SEARCH_KEYWORD Tool
**When to use**: Find specific symbols, function names, or patterns to modify
**Purpose**: Locate exact code elements that need changes

**Usage Instructions**:
- Search for specific function names, class names, constants
- Use to find all usages of deprecated code
- Locate specific patterns that need updating
- Scope searches to relevant directories only

**Search Pattern Examples**:
- Search "FirebaseRealtimeDB" in file_paths="src/services/cache-service.ts, src/utils/firebase-db.ts": Find specific Firebase usage
- Search "function createUser" in file_paths="src/services/user-service.ts": Find function in specific file
- Search "import.*firebase" with file_paths="": Find all Firebase imports across entire codebase
- Search "TODO.*migration" in file_paths="src/migrations/*.ts": Find migration-related code in specific directory
- Search "class.*Service" in file_paths="src/services/*.ts": Find service classes in services directory
- Search "export.*Config" with file_paths="": Find all configuration exports across project

## Agent Workflow

1. **Quick Discovery**: Use SEMANTIC_SEARCH to find relevant files and patterns
2. **Targeted Analysis**: Prefer GET_FILE_BLOCK_SUMMARY first to scope elements; then use GET_FILE_BY_PATH for the relevant line range
3. **Pattern Identification**: Use SEARCH_KEYWORD to find all instances of code that needs changes
4. **Dependency Check**: Use GET_DEPENDENCY_CHAIN or GET_BLOCK_DETAILS respectively to understand what needs updating
5. **Direct Instructions**: Use ATTEMPT_COMPLETION to provide specific file-by-file changes

## Implementation Scenarios

### Efficient Discovery: "Add caching to user service"

**Step 1: Targeted Discovery**
1. SEARCH_KEYWORD "getUserById" file_paths="src/services/user-service.ts" → finds line 45
2. GET_FILE_BY_PATH user-service.ts start_line=40 end_line=60 → gets complete function context
3. SEARCH_KEYWORD "constructor.*UserService" file_paths="src/services/user-service.ts" → finds line 12
4. GET_FILE_BY_PATH user-service.ts start_line=10 end_line=20 → gets complete constructor context
5. Store complete implementations in memory for roadmap decisions

**Step 2: Pattern Discovery**
1. SEARCH_KEYWORD "redis|cache" file_paths="src/config/*.ts, src/services/*.ts" → finds cache usage line numbers
2. GET_FILE_BY_PATH cache-config.ts with line ranges → gets complete cache implementation context
3. SEARCH_KEYWORD "import.*redis" file_paths="" → finds import line numbers across codebase
4. GET_FILE_BY_PATH on files with redis imports → gets complete import and usage context
5. Store complete cache patterns and import contexts in memory

**Step 3: Efficient Verification**
### Handling Block Reference Markers
1. If a provided code snippet contains a comment like `// [BLOCK_REF:<id>]`, directly run GET_BLOCK_DETAILS with that `block_id` if you think the code inside it might be helpful.
2. Use incoming/outgoing connections from the block details to plan impact and dependencies

### Summary-First File Scoping
1. When a file path is known but the target element is not: run GET_FILE_BLOCK_SUMMARY first
2. Choose the relevant block by name/type → then run GET_FILE_BY_PATH with that block’s line range
3. Use GET_DEPENDENCY_CHAIN for file-level dependency mapping

### Cross-Repo API/Controller Discovery (when indexed)
1. If an API call or client fetch is observed in the current block, run GET_BLOCK_DETAILS on that block to retrieve outgoing connections
2. Inspect outgoing connections for connected file paths and project names; when the index includes external repos, the connection may provide the controller’s `file_path` and `connected_project_name`

### Connection-Aware Impact Analysis
1. For a given file or block: run GET_DEPENDENCY_CHAIN or GET_BLOCK_DETAILS respectively to get incoming/outgoing runtime connections and mapped relationships
2. Combine both to identify files/projects linked to the change and affected areas
3. LIST_FILES to check package.json exists
4. SEARCH_KEYWORD "redis" file_paths="package.json" → finds dependency line
5. GET_FILE_BY_PATH package.json with line range → gets dependency context
6. SEARCH_KEYWORD "async.*await" file_paths="src/services/user-service.ts" → finds async patterns
7. All complete contexts stored in memory - no redundant file reads needed

### Bulk Replacement Detection Workflow

**Scenario**: Multiple files need same Firebase → Redis migration

**Step 1: Pattern Discovery**
1. SEARCH_KEYWORD "FirebaseRealtimeDB" to find all usage instances
2. SEARCH_KEYWORD "import.*FirebaseRealtimeDB" to find all import statements
3. Count occurrences - if same pattern repeats 3+ times, consider bulk replacement

**Step 2: Efficiency Analysis**
```
// Inefficient - 15 individual steps for simple replacements:
**File:** src/services/vm-allocation.service.ts
1. Method getAllocation(): Replace FirebaseRealtimeDB.get() line 45
2. Method getAllocation(): Replace FirebaseRealtimeDB.set() line 52
3. Method getAllocation(): Replace FirebaseRealtimeDB.get() line 67
...15 more individual replacements

// Efficient - 4 bulk replacement steps:
**File:** src/services/vm-allocation.service.ts
1. Import: Replace FirebaseRealtimeDB with RedisCache
2. Replace All: FirebaseRealtimeDB.get() → RedisCache.get() (throughout file)
3. Replace All: FirebaseRealtimeDB.set() → RedisCache.set() (throughout file)
4. Replace All: FirebaseRealtimeDB.keys() → RedisCache.keys() (throughout file)
```

**Step 3: Bulk vs Individual Decision**
- **Use Bulk When**: Same method signature, same parameters, same context
- **Use Individual When**: Different parameters, logic changes, conditional modifications

### Code Migration (e.g., Firebase to Redis)
1. SEMANTIC_SEARCH for current implementation: "firebase database operations"
2. DATABASE queries for main implementation files
3. SEARCH_KEYWORD for all Firebase import/usage patterns file_paths="" (entire codebase)
4. SEARCH_KEYWORD for Redis patterns file_paths="src/config/*.ts, src/utils/*.ts" if they exist
5. Generate specific file modifications with exact function/import changes

### API Updates
1. SEMANTIC_SEARCH for existing API patterns: "API endpoint handler"
2. GET_FILE_BLOCK_SUMMARY of route/controller files
3. SEARCH_KEYWORD for specific endpoint implementations file_paths="src/routes/*.ts, src/controllers/*.ts"
4. Generate exact endpoint modifications and new additions

### Dependency Updates
1. SEMANTIC_SEARCH for current dependency usage patterns
2. GET_DEPENDENCY_CHAIN for affected files
3. SEARCH_KEYWORD for all usage instances of old dependency file_paths="" (entire codebase)
4. Generate specific import statement changes and usage updates

### New Feature Implementation
1. SEMANTIC_SEARCH for similar existing features
2. GET_FILE_BLOCK_SUMMARY of related components
3. Find patterns for new file organization
4. Generate specific new files and integration points

## Key Principles

- **Specificity**: Always provide exact file paths and function/class names
- **Actionability**: Focus on what to change, not why or when
- **Brevity**: Minimal context, maximum implementation detail
- **Patterns**: Follow existing code patterns for consistency
- **Dependencies**: Only mention direct import/usage dependencies
- **Numbered Steps**: Each file must use numbered modification steps
- **Element Precision**: Specify exactly what element exists now and what it should become

## Success Metrics

Your tool usage is successful when you can provide:
- Exact file paths with specific function/class/method names
- Current implementation details (what exists now)
- Specific replacement instructions (what it should become)
- Numbered steps for each file modification
- Complete dependency impact analysis
- Actionable, executable change specifications

### Function Parameter Deep Analysis

**Before modifying any function, perform parameter analysis**:

**Example: Modifying `validateUserInput(userData, options)` function**

1. **Source Analysis**:
   - SEARCH_KEYWORD "validateUserInput(" file_paths="src/controllers/*.ts, src/middleware/*.ts" to find all call sites
   - Understand where `userData` comes from: req.body, database, form input
   - Understand `options` usage: validation rules, feature flags, configuration

2. **Efficient Type Understanding**:
   - SEARCH_KEYWORD "validateUserInput" file_paths="src/utils/helpers.ts" → finds function at line 23
   - GET_FILE_BY_PATH helpers.ts start_line=20 end_line=35 → gets complete function implementation
   - SEARCH_KEYWORD "const.*=.*userData" file_paths="src/utils/helpers.ts" → finds destructuring at line 25
   - GET_FILE_BY_PATH helpers.ts with expanded range → gets complete validation context
   - Store complete function implementation and validation logic in memory

3. **Flow Analysis**:
   - SEMANTIC_SEARCH "user input validation" to find similar validation patterns
   - DATABASE_SEARCH: GET_DEPENDENCY_CHAIN to see what depends on this function
   - SEARCH_KEYWORD for error handling: "throw|return.*error|catch"

4. **Integration Requirements**:
   - Check existing validation libraries in package.json
   - Find validation schemas or rules in the codebase
   - Understand logging patterns for validation failures

## Memory-First Workflow Example

**Scenario**: "Add Redis caching to getUserById method"

**Step 1: Memory Check First**
```
<thinking>
Checking Sutra Memory for:
- getUserById function complete implementation
- Existing cache patterns with full context
- Constructor patterns with dependency injection context
Memory shows: No previous discoveries stored
</thinking>
```

**Step 2: Two-Step Discovery Process**
```
SEARCH_KEYWORD "getUserById" file_paths="src/services/user-service.ts"
Result: Found at line 45

GET_FILE_BY_PATH user-service.ts start_line=40 end_line=55
Result: Complete function context retrieved

Store in Memory:
Discovery: getUserById function
File: src/services/user-service.ts
Lines: 40-55 (complete context)
Code:
```
export class UserService {
  async getUserById(id: string): Promise<User> {
    const user = await this.database.get(`user:${id}`);
    if (!user) {
      throw new Error('User not found');
    }
    return user;
  }

  async updateUser(id: string, data: Partial<User>): Promise<User> {
    // ... surrounding context for better understanding
  }
}
```
```

**Step 3: Memory-First Next Discovery**
```
<thinking>
Need constructor info for dependency injection.
Checking Memory: getUserById complete implementation stored ✓
Memory shows: Need constructor context
</thinking>

SEARCH_KEYWORD "constructor.*UserService" file_paths="src/services/user-service.ts"
Result: Found at line 12

GET_FILE_BY_PATH user-service.ts start_line=8 end_line=18
Result: Complete constructor context retrieved

Store in Memory:
Discovery: UserService constructor
File: src/services/user-service.ts
Lines: 8-18 (complete context)
Code:
```
export class UserService {
  constructor(
    private database: DatabaseService,
    private logger: Logger
  ) {
    this.logger.info('UserService initialized');
  }
```
```

**Step 4: Using Memory for Roadmap**
```
<thinking>
Memory contains complete contexts:
- getUserById at line 40-55 with full function implementation and surrounding methods
- Constructor at line 8-18 with complete dependency injection pattern and initialization
- Sufficient complete code context available - no additional file reads needed
</thinking>

ATTEMPT_COMPLETION using complete implementations stored in memory
```

**Memory-Based Roadmap Output:**
```
**File:** src/services/user-service.ts
1. Constructor (line 12): Add cache dependency parameter after logger
2. Method getUserById (line 45): Add cache check before database query
3. Method getUserById (line 47): Add cache storage after successful database retrieval
4. Overview: Transform getUserById from database-only to cache-first pattern
```

## Bulk Replacement Efficiency Guidelines

**When Pattern Detection Suggests Bulk Operations**:

Use SEARCH_KEYWORD to identify repetitive patterns. When the same replacement occurs 3+ times, provide efficient bulk instructions.

### Strategic Bulk Instructions
**Library Migration Pattern**:
```
**File:** src/services/user-service.ts
1. Import: Replace OldLibrary with NewLibrary
2. Replace All: OldLibrary method calls → NewLibrary equivalents (throughout file)
3. Overview: Complete library migration strategy
```

**Method Renaming Pattern**:
```
**File:** src/utils/helpers.ts
1. Replace All: oldMethodName() → newMethodName() (throughout file)
2. Overview: Bulk method renaming for consistency
```

**Efficient Detection Strategy**:
1. SEARCH_KEYWORD to find pattern occurrences with line numbers (e.g., "firebase.get" file_paths="src/services/*.ts" finds lines 15, 23, 31)
2. If 3+ identical patterns with similar context → suggest bulk replacement
3. Store line numbers in memory for targeted modifications
4. Focus on strategic guidance, not implementation details

## Verification Before Changes Checklist

**Always verify before proposing changes**:
1. ✓ Memory checked first for existing complete implementations and line numbers
2. ✓ Project dependencies and available packages analyzed
3. ✓ Existing similar functions/classes discovered WITH complete implementations from GET_FILE_BY_PATH
4. ✓ Parameter sources and types understood WITH full function context from memory
5. ✓ Function parameter sources, types, and usage patterns WITH complete implementations stored
6. ✓ Return value usage analyzed WITH call site complete contexts AND surrounding code stored
7. ✓ Error handling patterns identified WITH complete function contexts AND surrounding implementations
8. ✓ Integration points mapped WITH complete code contexts AND full implementation details
9. ✓ Existing utilities that can be reused found WITH complete import contexts AND surrounding code
10. ✓ Repetitive patterns identified for bulk replacement WITH complete implementation contexts
11. ✓ Two-step discovery: SEARCH_KEYWORD for locations → GET_FILE_BY_PATH for complete context → memory storage
12. ✓ No redundant file reads when complete implementations already exist in memory

Focus on strategic precision: exact element names, current components, specific replacements with line numbers, roadmap-level modification steps. Always use two-step discovery: SEARCH_KEYWORD with targeted file_paths to get line numbers, then GET_FILE_BY_PATH with line ranges to get complete context, then store full implementations in memory.

## SEARCH_KEYWORD File Targeting Examples

**Multiple Specific Files**:
```
SEARCH_KEYWORD "getUserById" file_paths="src/services/user-service.ts, src/controllers/user-controller.ts"
```

**Entire Codebase Search**:
```
SEARCH_KEYWORD "FirebaseRealtimeDB" file_paths=""
```

**Directory Pattern Targeting**:
```
SEARCH_KEYWORD "class.*Service" file_paths="src/services/*.ts, src/utils/*.ts"
```

**Single File Precision**:
```
SEARCH_KEYWORD "constructor" file_paths="src/services/user-service.ts"
```
"""
