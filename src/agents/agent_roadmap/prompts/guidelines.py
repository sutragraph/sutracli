"""
Roadmap Agent Guidelines

Operational procedures for producing precise implementation specifications
"""

GUIDELINES = """
## Project Context Verification

Before proposing any changes, understand the project ecosystem:

1. **Project Type Discovery**: Identify project structure and dependencies
   - For Node.js: Check package.json for available packages and dependencies
   - For Python: Examine requirements.txt, pyproject.toml, or setup.py
   - For Java: Look for pom.xml, build.gradle, or similar build files
   - For other languages: Find relevant configuration and dependency files

2. **Existing Pattern Analysis**: Search for similar implementations before creating new ones
   - Use SEMANTIC_SEARCH to find existing functions/classes with similar functionality
   - Check if current utilities or helper functions can be reused
   - Identify established patterns for error handling, logging, configuration
   - Look for existing service patterns, data access patterns, validation patterns

3. **Parameter and Data Flow Understanding**: Before modifying functions, use targeted searches:
   - SEARCH_KEYWORD for function signatures to understand parameter names and types
   - SEARCH_KEYWORD for parameter usage patterns within function bodies
   - SEARCH_KEYWORD for destructuring patterns: "const.*=.*paramName"
   - SEARCH_KEYWORD for type checks: "typeof.*paramName|paramName instanceof"
   - SEARCH_KEYWORD for return patterns: "return.*functionName"
   - SEARCH_KEYWORD for function calls to understand parameter sources

## Operational Workflow

1. **Think Before Acting**: Include a <thinking> section before each tool call:
   - Review Sutra Memory for specific code locations already found
   - Decide which tool will reveal exact implementation details
   - Confirm you're seeking precise modification points

2. **Efficient Discovery Pattern**: Execute exactly ONE tool per iteration:
   - SEARCH_KEYWORD → find exact symbols with 10-line context (preferred first step)
   - DATABASE with line ranges → get targeted file sections based on SEARCH_KEYWORD results
   - SEMANTIC_SEARCH → find files containing specific implementations (when broad discovery needed)
   - LIST_FILES → verify exact file locations when needed

3. **Memory Management**: After each tool result, update Sutra Memory with ADD_HISTORY:
   - Store precise code locations with file paths, function names, LINE NUMBERS from SEARCH_KEYWORD
   - **CRITICAL**: Store FULL CODE CONTEXT from GET_FILE_BY_PATH queries (not limited SEARCH_KEYWORD snippets)
   - Record complete function implementations with surrounding context from GET_FILE_BY_PATH
   - Store meaningful code blocks that provide sufficient context for roadmap decisions
   - Remove vague information, keep actionable details with complete code context
   - Maximum focus: 5-10 targeted results per discovery WITH full function/class context

**Required Workflow for Memory Storage**:
1. SEARCH_KEYWORD to find exact line numbers
2. GET_FILE_BY_PATH with start_line/end_line to get full context
3. Store complete code context in memory

**Example Memory Storage**:
```
SEARCH_KEYWORD found getUserById at line 45 in user-service.ts
GET_FILE_BY_PATH user-service.ts start_line=40 end_line=55 retrieved:

class UserService {
  async getUserById(id: string): Promise<User> {
    const user = await this.database.get(`user:${id}`);
    if (!user) {
      throw new Error('User not found');
    }
    return user;
  }

  async updateUser(id: string, data: Partial<User>): Promise<User> {
    // ... rest of context
  }
}
```

4. **Completion Criteria**: Use ATTEMPT_COMPLETION when you have:
   - Exact file paths with specific function/class/method names AND line numbers
   - Current implementation details (what exists now) from targeted searches
   - Specific replacement instructions (what it should become)
   - Complete modification specifications for all affected files

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
4. Replace All: FirebaseRealtimeDB.keys() → RedisCache.keys() (throughout file)
5. Overview: Bulk Firebase to Redis method replacements
```

**Use Individual Steps Only When**:
- Different parameters or contexts require specific handling
- Method signatures change between replacements
- Only specific occurrences need modification (not all instances)
- Complex logic changes beyond simple name replacement

## Efficient Discovery Strategy

**Locate Precisely** → Use SEARCH_KEYWORD to find exact line numbers (gets limited 10-line context)
**Get Full Context** → Use GET_FILE_BY_PATH with start_line/end_line from SEARCH_KEYWORD to get complete code context
**Store Complete Context** → Store full function/class implementations from GET_FILE_BY_PATH in memory
**Find Broader Patterns** → Use SEMANTIC_SEARCH only when broader file discovery is needed
**Map Dependencies** → Use GET_FILE_IMPORTS and GET_DEPENDENCY_CHAIN for impact analysis
**Specify Changes** → For each location found, specify current element and exact replacement
**Optimize Instructions** → When same pattern repeats, suggest bulk replacements instead of individual steps

**Two-Step Process**: SEARCH_KEYWORD for line numbers → GET_FILE_BY_PATH for full context → store in memory
**MANDATORY**: Store complete code context from GET_FILE_BY_PATH - never rely on limited SEARCH_KEYWORD snippets

## Roadmap Focus Anti-Patterns

**ABSOLUTELY FORBIDDEN - Do NOT provide**:
- Complete function implementations or method bodies
- Full class definitions with implementation details
- Detailed code snippets beyond method signatures
- Step-by-step coding instructions ("add this line, then add this line")
- Complete file content or large code blocks
- Implementation logic for new methods

**ROADMAP GUIDANCE ONLY - DO provide**:
- Strategic modification points: "Method getUserById(): Add caching layer"
- Import changes: "Import: Replace FirebaseDB with RedisCache"
- Structural changes: "Class UserService: Add cache dependency to constructor"
- Interface changes: "Method authenticate(): Change signature to include token type"
- Strategic decisions: "Use existing ValidationUtils instead of creating new validator"

**Examples of FORBIDDEN vs CORRECT**:

❌ FORBIDDEN:
```
Method getUserById(): Implement caching logic
```typescript
async getUserById(id: string) {
  const cached = await cache.get(`user:${id}`);
  if (cached) return cached;
  const user = await db.get(id);
  await cache.set(`user:${id}`, user);
  return user;
}
```

✅ CORRECT:
```
Method getUserById(): Add cache check before database query, store result in cache after retrieval
```

## Verification Process

Before completion, confirm you have discovered:
- Project context and available dependencies/packages
- Existing similar patterns or reusable components
- Function parameter sources, types, and usage patterns WITH line numbers
- Exact import statements that need changing WITH line locations
- Specific function signatures and their current parameters WITH line ranges
- Actual method calls with current argument patterns WITH line numbers
- Precise constant/variable declarations and their current values WITH locations
- Current code implementations that need replacement WITH line ranges
- Dependencies and files that import modified components

**Key**: All discoveries should include line numbers AND actual code snippets from SEARCH_KEYWORD for efficient targeted access

## Memory Storage Examples

**GOOD Memory Entry (Two-Step Process)**:
```
Step 1: SEARCH_KEYWORD "getUserById" in user-service.ts → Found at line 45
Step 2: GET_FILE_BY_PATH user-service.ts start_line=40 end_line=60 → Full context:

export class UserService {
  constructor(private database: DatabaseService) {}

  async getUserById(id: string): Promise<User> {
    const user = await this.database.get(`user:${id}`);
    if (!user) {
      throw new Error('User not found');
    }
    return user;
  }

  async updateUser(id: string, data: Partial<User>): Promise<User> {
    // ... context continues
  }
}
```

**BAD Memory Entry**:
```
Tool: SEARCH_KEYWORD "getUserById"
Result: Found getUserById function in user-service.ts at line 45
(Limited 10-line snippet without sufficient context)
```

**MANDATORY WORKFLOW**: SEARCH_KEYWORD for location → GET_FILE_BY_PATH for full context → store complete implementation

## Discovery Checklist

For each modification request, verify:

**Project Dependencies**:
- What packages/libraries are already available?
- Are there existing dependencies that solve the problem?
- What version constraints exist?

**Existing Solutions**:
- Do similar functions/classes already exist?
- Can existing utilities be extended rather than creating new ones?
- What patterns does the codebase already follow?

**Integration Points**:
- How do existing functions handle similar parameters?
- What validation patterns are already established?
- How does error handling work in similar contexts?
- What logging/monitoring patterns exist?

**Data Flow Analysis**:
- Where does the data come from that feeds into this function?
- What transformations happen to the data?
- Where does the output go and in what format?
- What are the side effects and external dependencies?"""
