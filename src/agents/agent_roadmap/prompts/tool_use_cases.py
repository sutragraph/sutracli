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
1. SEMANTIC_SEARCH for similar functionality: "user authentication", "data validation", "cache management"
2. SEARCH_KEYWORD for existing function names: "function validateUser", "class UserService"
3. DATABASE_SEARCH: GET_FILE_BLOCK_SUMMARY on relevant files to understand existing patterns
4. DATABASE_SEARCH: GET_CHILD_BLOCKS to examine method signatures and parameters

**Parameter Analysis Workflow**:
1. DATABASE_SEARCH: GET_FILE_BY_PATH on target file to see function signature
2. SEARCH_KEYWORD for function calls to understand how parameters are passed
3. DATABASE_SEARCH: GET_DEPENDENCY_CHAIN to find all callers of the function
4. SEMANTIC_SEARCH for "validation" or "input handling" to understand parameter processing patterns

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

#### GET_CHILD_BLOCKS
- **When**: Need details of methods within a class for modification
- **Use for**: Understanding method signatures and implementations
- **Focus**: Find specific methods to update or replace

#### GET_FILE_IMPORTS
- **When**: Need to understand import dependencies for updates
- **Use for**: Planning import statement changes
- **Focus**: Identify which imports need adding/removing/updating

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
- Search "FirebaseRealtimeDB": Find all Firebase usage to replace
- Search "function createUser": Find specific function implementations
- Search "import.*firebase": Find import statements to update
- Search "TODO.*migration": Find migration-related code
- Search "class.*Service": Find service classes to modify
- Search "export.*Config": Find configuration exports to update

## Agent Workflow

1. **Quick Discovery**: Use SEMANTIC_SEARCH to find relevant files and patterns
2. **Targeted Analysis**: Use DATABASE queries on specific files to understand current implementation
3. **Pattern Identification**: Use SEARCH_KEYWORD to find all instances of code that needs changes
4. **Dependency Check**: Use GET_FILE_IMPORTS to understand what needs updating
5. **Direct Instructions**: Use ATTEMPT_COMPLETION to provide specific file-by-file changes

## Implementation Scenarios

### Project Context Discovery Before Implementation

**New Feature Request**: "Add caching to user service"

**Step 1: Project Verification**
1. LIST_FILES src/ to understand project structure
2. DATABASE_SEARCH: GET_FILE_BY_PATH package.json to check for existing cache libraries
3. SEMANTIC_SEARCH "cache" to find existing caching implementations
4. SEARCH_KEYWORD "redis|memcached|cache" to find current cache usage

**Step 2: Pattern Discovery**
1. SEMANTIC_SEARCH "user service" to find the target service
2. DATABASE_SEARCH: GET_FILE_BLOCK_SUMMARY on user service to understand current structure
3. SEMANTIC_SEARCH "service pattern" to understand how services are structured
4. SEARCH_KEYWORD "constructor|dependency injection" to understand how dependencies are added

**Step 3: Parameter Analysis**
1. DATABASE_SEARCH: GET_CHILD_BLOCKS on getUserById method to understand current parameters
2. SEARCH_KEYWORD "getUserById(" to find all call sites
3. DATABASE_SEARCH: GET_DEPENDENCY_CHAIN to understand what calls this method
4. SEMANTIC_SEARCH "error handling" to understand how errors are managed

**Step 4: Integration Planning**
1. Check if Redis is in package.json dependencies
2. Find existing Redis configurations or connection patterns
3. Understand existing async/await patterns in the service
4. Verify error handling patterns for external dependencies

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
3. SEARCH_KEYWORD for all Firebase import/usage patterns
4. Find Redis patterns if they exist
5. Generate specific file modifications with exact function/import changes

### API Updates
1. SEMANTIC_SEARCH for existing API patterns: "API endpoint handler"
2. GET_FILE_BLOCK_SUMMARY of route/controller files
3. SEARCH_KEYWORD for specific endpoint implementations
4. Generate exact endpoint modifications and new additions

### Dependency Updates
1. SEMANTIC_SEARCH for current dependency usage patterns
2. GET_DEPENDENCY_CHAIN for affected files
3. SEARCH_KEYWORD for all usage instances of old dependency
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
   - SEARCH_KEYWORD "validateUserInput(" to find all call sites
   - Understand where `userData` comes from: req.body, database, form input
   - Understand `options` usage: validation rules, feature flags, configuration

2. **Type Understanding**:
   - SEARCH_KEYWORD "validateUserInput" to find the function definition and signature
   - SEARCH_KEYWORD "const.*=.*userData" to find destructuring patterns
   - SEARCH_KEYWORD "typeof.*userData.|userData..*!==" to find validation logic
   - SEARCH_KEYWORD "return.*error|throw.*Error" to understand error patterns

3. **Flow Analysis**:
   - SEMANTIC_SEARCH "user input validation" to find similar validation patterns
   - DATABASE_SEARCH: GET_DEPENDENCY_CHAIN to see what depends on this function
   - SEARCH_KEYWORD for error handling: "throw|return.*error|catch"

4. **Integration Requirements**:
   - Check existing validation libraries in package.json
   - Find validation schemas or rules in the codebase
   - Understand logging patterns for validation failures

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

**Detection Strategy**:
1. Use SEARCH_KEYWORD to count pattern occurrences
2. If 3+ identical replacements in a file → suggest bulk replacement
3. Focus on strategic guidance, not implementation details

## Verification Before Changes Checklist

**Always verify before proposing changes**:
1. ✓ Project dependencies and available packages analyzed
2. ✓ Existing similar functions/classes discovered
3. ✓ Parameter sources and types understood
4. ✓ Return value usage analyzed
5. ✓ Error handling patterns identified
6. ✓ Integration points mapped
7. ✓ Existing utilities that can be reused found
8. ✓ Repetitive patterns identified for bulk replacement efficiency

Focus on strategic precision: exact element names, current components, specific replacements, roadmap-level modification steps.
"""
