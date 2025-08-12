"""
Tool Usage Examples and Instructions for Roadmap Agent

This file contains detailed usage instructions and examples for all tools available
to the roadmap agent. Focus on finding specific code changes and implementation details.
"""

TOOL_USAGE_CASES = """
# ROADMAP AGENT TOOL USAGE GUIDE (CONCISE INSTRUCTIONS FOCUS)

## 1. COMPLETION TOOL
**When to use**: After gathering sufficient context for specific file-level changes
**Purpose**: Present direct, actionable implementation instructions

**Usage Instructions**:
- Only use after finding specific files that need modification
- Provide file-by-file instructions with exact paths and changes
- Include essential code snippets only when needed for clarity
- NEVER include timelines, phases, or executive summaries

**Output Format**:
```
**File:** exact/path/to/file.ext
**Action:** Create/Modify/Delete
**Changes:**
- Add function X with signature Y
- Update import statements
- Remove deprecated class Z

**File:** another/path/file.ext
**Action:** Modify
**Changes:**
- Replace method implementation in lines 45-67
- Add new parameter to constructor
```

## 2. SEMANTIC SEARCH TOOL
**When to use**: Find existing code patterns and files related to the user's request
**Purpose**: Discover specific implementation patterns to follow or modify

**Usage Instructions**:
- Search for relevant existing implementations
- Focus on finding files that need modification
- Look for patterns to maintain consistency
- Always call GET_BLOCK_DETAILS on relevant results

**Examples**:
- Search for "redis cache implementation": Find existing cache patterns
- Search for "database migration script": Find migration file patterns
- Search for "API endpoint definition": Find endpoint implementation patterns
- Search for "authentication middleware": Find auth implementation to modify
- Search for "service class pattern": Find service layer implementations
- Search for "configuration management": Find config files to update

## 3. LIST FILES TOOL
**When to use**: Understand directory structure for file organization
**Purpose**: Find where to create new files or locate existing ones

**Usage Instructions**:
- Check directory structure when creating new files
- Verify file locations before modification
- Understand project organization patterns
- Keep exploration focused and minimal

**Examples**:
- List src/services/: Find where to add new service files
- List src/utils/: Check utility file organization
- List src/config/: Locate configuration files
- List tests/: Find test file structure for new tests

## 4. DATABASE SEARCH TOOL
**When to use**: Get specific file content and dependency information
**Purpose**: Find exact code locations and understand modification requirements

**Usage Instructions for each query type**:

### GET_FILE_BY_PATH
- **When**: Need to examine specific files for modification
- **Use for**: Understanding current implementation before changes
- **Focus**: Identify specific functions/classes that need updates

### GET_FILE_BLOCK_SUMMARY
- **When**: Need overview of file structure for targeted changes
- **Use for**: Finding specific methods/functions to modify
- **Focus**: Locate exact code blocks that need changes

### GET_CHILD_BLOCKS
- **When**: Need details of methods within a class for modification
- **Use for**: Understanding method signatures and implementations
- **Focus**: Find specific methods to update or replace

### GET_FILE_IMPORTS
- **When**: Need to understand import dependencies for updates
- **Use for**: Planning import statement changes
- **Focus**: Identify which imports need adding/removing/updating

### GET_DEPENDENCY_CHAIN
- **When**: Need to understand which files will be affected by changes
- **Use for**: Finding all files that import a modified component
- **Focus**: Locate files that need import/usage updates

**Database Usage Notes**:
- Always use CODE_CONTENT=TRUE when you need implementation details
- Store specific file paths and line ranges in memory
- Focus on immediate modification needs, not comprehensive analysis

## 5. SEARCH KEYWORD TOOL
**When to use**: Find specific symbols, function names, or patterns to modify
**Purpose**: Locate exact code elements that need changes

**Usage Instructions**:
- Search for specific function names, class names, constants
- Use to find all usages of deprecated code
- Locate specific patterns that need updating
- Scope searches to relevant directories only

**Examples**:
- Search "FirebaseRealtimeDB": Find all Firebase usage to replace
- Search "function createUser": Find specific function implementations
- Search "import.*firebase": Find import statements to update
- Search "TODO.*migration": Find migration-related code
- Search "class.*Service": Find service classes to modify
- Search "export.*Config": Find configuration exports to update

## AGENT WORKFLOW FOR CONCISE INSTRUCTIONS

1. **Quick Discovery**: Use SEMANTIC_SEARCH to find relevant files and patterns
2. **Targeted Analysis**: Use DATABASE queries on specific files to understand current implementation
3. **Pattern Identification**: Use SEARCH_KEYWORD to find all instances of code that needs changes
4. **Dependency Check**: Use GET_FILE_IMPORTS to understand what needs updating
5. **Direct Instructions**: Use COMPLETION to provide specific file-by-file changes

## INSTRUCTION GENERATION SCENARIOS

### Code Migration (e.g., Firebase to Redis)
1. SEARCH for current implementation: "firebase database operations"
2. GET file details for main implementation files
3. SEARCH for all Firebase import/usage patterns
4. Find Redis patterns if they exist
5. Generate specific file modifications with exact function/import changes

### API Updates
1. SEARCH for existing API patterns: "API endpoint handler"
2. GET file structure of route/controller files
3. SEARCH for specific endpoint implementations
4. Generate exact endpoint modifications and new additions

### Dependency Updates
1. SEARCH for current dependency usage patterns
2. GET import chains for affected files
3. SEARCH for all usage instances of old dependency
4. Generate specific import statement changes and usage updates

### New Feature Implementation
1. SEARCH for similar existing features
2. GET file structure of related components
3. Find patterns for new file organization
4. Generate specific new files and integration points

## KEY PRINCIPLES

- **Specificity**: Always provide exact file paths and function/class names
- **Actionability**: Focus on what to change, not why or when
- **Brevity**: Minimal context, maximum implementation detail
- **Patterns**: Follow existing code patterns for consistency
- **Dependencies**: Only mention direct import/usage dependencies
- **Code Snippets**: Include only when essential for clarity (signatures, key logic)
"""
