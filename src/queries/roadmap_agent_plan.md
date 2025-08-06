# Roadmap Agent: Database Query Strategy

## Roadmap Agent Purpose
**Input:** User query like "Add user profile picture upload"
**Output:** Step-by-step roadmap with:
- Files that need changes
- Order of implementation
- Cross-project impact analysis
- External dependencies

## Roadmap Agent Workflow

### **Phase 1: Discovery & Impact Analysis**
1. **Find relevant code** (semantic search)
2. **Analyze current implementation** (database queries)
3. **Map dependencies** (relationships + connections)
4. **Identify impact scope** (what else needs changes)

### **Phase 2: Roadmap Generation**
1. **Prioritize changes** (dependencies first)
2. **Sequence steps** (logical order)
3. **Flag cross-project impacts** (external connections)
4. **Estimate complexity** (based on code analysis)

## Database Queries for Roadmap Agent

### **Tier 1: Discovery Queries (Find What Exists)**
```sql
-- After semantic search finds relevant blocks
GET_CODE_BLOCK_BY_ID(block_id) → Get implementation details
GET_FILE_BY_ID(file_id) → Get file context
GET_FILE_BLOCK_SUMMARY(file_id) → See what else is in the file
```

**Roadmap Use:** "Found existing user upload logic in UserService.uploadAvatar()"

### **Tier 2: Dependency Analysis (What Depends on What)**
```sql
GET_FILE_IMPORTS(file_id) → What this file needs
GET_FILE_IMPORTERS(file_id) → What depends on this file  
GET_SYMBOL_SOURCES(symbol_name) → Where functions/classes come from
GET_IMPORTED_SYMBOLS(file_id) → What symbols are available
```

**Roadmap Use:** "UserService depends on FileStorage, ImageProcessor, Database models"

### **Tier 3: Cross-Project Impact (External Changes Needed)**
```sql
GET_EXTERNAL_CONNECTIONS(file_id) → APIs, databases, services this touches
GET_FILE_INCOMING_CONNECTIONS(file_id) → External systems that call this
GET_FILE_OUTGOING_CONNECTIONS(file_id) → External systems this calls
```

**Roadmap Use:** "Changes will affect: Frontend API, Mobile app, Image CDN"

### **Tier 4: Implementation Context (How to Make Changes)**
```sql
GET_PARENT_BLOCK(block_id) → What class/module contains this
GET_CHILD_BLOCKS(block_id) → What methods are in this class
GET_SIBLING_BLOCKS(block_id) → What other methods exist at same level
GET_BLOCKS_BY_TYPE_IN_FILE(file_id, 'function') → All functions in file
```

**Roadmap Use:** "Add new method to UserService class alongside existing uploadAvatar()"

## Roadmap-Specific Query Additions

### **New Queries Needed for Roadmap Agent:**

```sql
-- Find all files that import a specific symbol (impact analysis)
GET_FILES_USING_SYMBOL = """
SELECT DISTINCT f.file_path, f.language, p.name as project_name
FROM relationships r
JOIN files f ON r.source_id = f.id  
JOIN projects p ON f.project_id = p.id
WHERE r.symbols LIKE ?
ORDER BY f.file_path
LIMIT 20
"""

-- Get all external connections for a project (cross-project impact)
GET_PROJECT_EXTERNAL_CONNECTIONS = """
SELECT 
    f.file_path,
    ic.technology_name, ic.description as incoming_desc,
    oc.technology_name, oc.description as outgoing_desc
FROM files f
LEFT JOIN incoming_connections ic ON f.id = ic.file_id
LEFT JOIN outgoing_connections oc ON f.id = oc.file_id
WHERE f.project_id = ? AND (ic.id IS NOT NULL OR oc.id IS NOT NULL)
ORDER BY f.file_path
LIMIT 30
"""

-- Find files by functionality pattern (for similar implementations)
GET_FILES_WITH_PATTERN = """
SELECT f.file_path, f.language, COUNT(cb.id) as matching_blocks
FROM files f
JOIN code_blocks cb ON f.id = cb.file_id
WHERE cb.name LIKE ? OR cb.content LIKE ?
GROUP BY f.id
ORDER BY matching_blocks DESC
LIMIT 15
"""
```

## Roadmap Agent Tool Integration

### **Tool Usage Strategy:**

1. **Semantic Search** → Find existing implementations
2. **Database Queries** → Analyze dependencies and structure  
3. **Ripgrep** → Find usage patterns and references
4. **List Files** → Understand project structure
5. **Terminal** → Verify assumptions, run tests

### **Example Roadmap Generation Flow:**

**User Query:** "Add user profile picture upload"

**Step 1: Discovery**
```
semantic_search("user profile picture upload avatar")
→ Finds: UserService.uploadAvatar(), ProfileController.updateProfile()
```

**Step 2: Analyze Current Implementation**
```
GET_CODE_BLOCK_BY_ID(avatar_function_id)
→ See how current avatar upload works

GET_FILE_IMPORTS(user_service_file_id)  
→ Uses: FileStorage, ImageProcessor, ValidationService
```

**Step 3: Impact Analysis**
```
GET_FILES_USING_SYMBOL("uploadAvatar")
→ ProfileController, UserAPI, MobileSync all use this

GET_EXTERNAL_CONNECTIONS(user_service_file_id)
→ Connects to: AWS S3, Image CDN, Database
```

**Step 4: Generate Roadmap**
```
ROADMAP:
1. Update UserService.uploadAvatar() to handle profile pictures
2. Modify ProfileController to call new upload method
3. Update UserAPI endpoints for frontend
4. Update MobileSync for mobile app compatibility  
5. Configure CDN for profile picture serving
6. Update database schema for profile picture URLs
```

## Roadmap-Optimized Query Characteristics

### **What Makes Queries Good for Roadmap Generation:**

1. **Impact-Focused** → Show what else will be affected
2. **Dependency-Aware** → Reveal implementation order
3. **Cross-Project Visibility** → Flag external changes needed
4. **Pattern-Based** → Find similar implementations for guidance

### **Query Result Format for Roadmap Agent:**
```json
{
  "current_implementation": "UserService.uploadAvatar()",
  "dependencies": ["FileStorage", "ImageProcessor"],
  "affected_files": ["ProfileController.py", "UserAPI.py"],
  "external_impacts": ["Frontend API", "Mobile App", "CDN"],
  "similar_patterns": ["DocumentUpload.py", "MediaService.py"]
}
```

## Implementation Priority for Roadmap Agent

### **Phase 1: Core Discovery (Implement First)**
1. `GET_CODE_BLOCK_BY_ID` - Understand existing implementations
2. `GET_FILE_IMPORTS` - Map dependencies
3. `GET_FILES_USING_SYMBOL` - Find impact scope
4. `GET_EXTERNAL_CONNECTIONS` - Cross-project analysis

### **Phase 2: Context Analysis**
1. `GET_PARENT_BLOCK` - Understand code structure
2. `GET_CHILD_BLOCKS` - See related methods
3. `GET_PROJECT_EXTERNAL_CONNECTIONS` - Full project impact

### **Phase 3: Pattern Recognition**
1. `GET_FILES_WITH_PATTERN` - Find similar implementations
2. `GET_SYMBOL_SOURCES` - Trace origins
3. Advanced ripgrep integration for usage patterns

## Key Insight: Roadmap Agent Needs Different Data

**Traditional Agent:** "Show me this specific code"
**Roadmap Agent:** "Show me what will be affected if I change this"

The queries need to be **impact-oriented** rather than **detail-oriented**, focusing on relationships and dependencies rather than just code content.
