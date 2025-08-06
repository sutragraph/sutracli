# Roadmap Agent Implementation Guide

## Roadmap Agent Query Strategy

### **The Roadmap Agent's Job:**
**Input:** "Add user profile picture upload"
**Output:** 
```
IMPLEMENTATION ROADMAP:
1. Update UserService.uploadAvatar() method (src/services/user.py:45-67)
2. Modify ProfileController.updateProfile() (src/controllers/profile.py:23-45)  
3. Update UserAPI.post_profile() endpoint (src/api/user.py:89-102)
4. Configure CDN settings for profile pictures (config/cdn.yaml)
5. Update database schema: users.profile_picture_url (migrations/)
6. Test mobile app compatibility (external project impact)
```

## Query Tiers for Roadmap Generation

### **Tier 1: Discovery (What Exists)**
```sql
-- After semantic search finds relevant code
GET_CODE_BLOCK_BY_ID(block_id) → Implementation details
GET_FILE_BY_ID(file_id) → File context  
GET_FILE_BLOCK_SUMMARY(file_id) → What else is in file
GET_BLOCKS_BY_NAME_IN_FILE(file_id, name) → Find specific functions
```

**Roadmap Use:** "Found existing upload logic in UserService.uploadAvatar()"

### **Tier 2: Impact Analysis (What Will Break)**
```sql
GET_FILES_USING_SYMBOL(symbol_pattern) → Who uses this function
GET_SYMBOL_IMPACT_SCOPE(file_id) → All files that import/depend on this
```

**Roadmap Use:** "Changes will affect ProfileController, UserAPI, MobileSync"

### **Tier 3: Dependency Mapping (Implementation Order)**
```sql
GET_DEPENDENCY_CHAIN(file_id) → Multi-level dependency tree
GET_IMPLEMENTATION_CONTEXT(file_id) → Code structure in file
```

**Roadmap Use:** "Must update UserService first, then ProfileController, then API"

### **Tier 4: Cross-Project Impact (External Changes)**
```sql
GET_PROJECT_EXTERNAL_CONNECTIONS(project_id) → All external integrations
GET_EXTERNAL_CONNECTIONS(file_id) → APIs/databases this file touches
GET_CONNECTION_IMPACT(file_id) → Mapped connections with confidence
```

**Roadmap Use:** "Will affect Frontend API, Mobile app, Image CDN"

### **Tier 5: Pattern Recognition (How to Implement)**
```sql
GET_FILES_WITH_PATTERN(pattern) → Similar implementations
GET_SIMILAR_IMPLEMENTATIONS(type, pattern) → Related functions/classes
GET_FILE_COMPLEXITY_SCORE(file_id) → Estimate implementation difficulty
```

**Roadmap Use:** "Follow pattern from DocumentUpload.py for file handling"

## Roadmap Agent Workflow

### **Phase 1: Discovery & Analysis**
```python
# 1. Semantic search finds relevant code
semantic_results = semantic_search("user profile picture upload")

# 2. Get details of discovered implementations  
for result in semantic_results:
    if result.node_id.startswith("block_"):
        block_details = GET_CODE_BLOCK_BY_ID(extract_id(result.node_id))
        file_context = GET_FILE_BLOCK_SUMMARY(block_details.file_id)
    
# 3. Analyze impact scope
impact_files = GET_FILES_USING_SYMBOL("uploadAvatar")
dependencies = GET_DEPENDENCY_CHAIN(user_service_file_id)
```

### **Phase 2: Cross-Project Impact**
```python
# 4. Check external connections
external_impacts = GET_EXTERNAL_CONNECTIONS(user_service_file_id)
project_integrations = GET_PROJECT_EXTERNAL_CONNECTIONS(project_id)
connection_mappings = GET_CONNECTION_IMPACT(user_service_file_id)
```

### **Phase 3: Implementation Planning**
```python
# 5. Find similar patterns
similar_patterns = GET_FILES_WITH_PATTERN("upload%")
complexity_score = GET_FILE_COMPLEXITY_SCORE(user_service_file_id)

# 6. Generate ordered roadmap
roadmap = generate_implementation_order(
    current_implementation=block_details,
    impact_files=impact_files,
    dependencies=dependencies,
    external_impacts=external_impacts,
    patterns=similar_patterns
)
```

## Tool Integration Strategy

### **Database Queries + External Tools:**

1. **Semantic Search** → Find existing implementations
2. **Database Queries** → Analyze structure and dependencies
3. **Ripgrep** → Find actual usage patterns and function calls
4. **List Files** → Understand project structure  
5. **Terminal** → Verify assumptions, check configurations

### **Example: Complete Roadmap Generation**

**User Query:** "Add user profile picture upload"

**Step 1: Discovery**
```
semantic_search("user profile picture upload avatar")
→ block_1234: UserService.uploadAvatar()
→ file_5678: ProfileController.py
```

**Step 2: Analyze Current Implementation**
```sql
GET_CODE_BLOCK_BY_ID(1234)
→ Function: uploadAvatar(user_id, file)
→ File: /src/services/user_service.py
→ Lines: 45-67
→ Uses: FileStorage, ImageProcessor
```

**Step 3: Impact Analysis**
```sql
GET_FILES_USING_SYMBOL("uploadAvatar")
→ ProfileController.py (calls uploadAvatar)
→ UserAPI.py (exposes upload endpoint)
→ MobileSync.py (syncs profile data)
```

**Step 4: Dependency Mapping**
```sql
GET_DEPENDENCY_CHAIN(user_service_file_id)
→ UserService → FileStorage → AWS_S3
→ UserService → ImageProcessor → PIL
→ UserService → Database → PostgreSQL
```

**Step 5: External Impact**
```sql
GET_EXTERNAL_CONNECTIONS(user_service_file_id)
→ Outgoing: AWS S3 (file storage)
→ Outgoing: Image CDN (serving)
→ Incoming: Frontend API
→ Incoming: Mobile App
```

**Step 6: Pattern Recognition**
```sql
GET_FILES_WITH_PATTERN("upload%")
→ DocumentUpload.py (similar file handling)
→ MediaService.py (image processing patterns)
```

**Step 7: Generate Roadmap**
```
IMPLEMENTATION ROADMAP:
1. [CORE] Update UserService.uploadAvatar() for profile pictures
   - File: src/services/user_service.py:45-67
   - Dependencies: FileStorage, ImageProcessor
   - Complexity: Medium (existing upload logic)

2. [API] Update ProfileController.updateProfile()
   - File: src/controllers/profile_controller.py:23-45
   - Depends on: Step 1
   - Impact: Frontend API changes needed

3. [INTEGRATION] Update UserAPI endpoints
   - File: src/api/user_api.py:89-102
   - Depends on: Step 2
   - Impact: Mobile app compatibility

4. [EXTERNAL] Configure CDN for profile pictures
   - File: config/cdn_settings.yaml
   - Impact: Image serving infrastructure

5. [DATABASE] Add profile_picture_url column
   - File: migrations/add_profile_picture.sql
   - Impact: Database schema change

6. [TESTING] Verify mobile app compatibility
   - External project impact detected
   - Technology: React Native mobile app
```

## Key Advantages of This Approach

### **1. Impact-Aware Planning**
- Shows what will break before you start
- Identifies external project dependencies
- Estimates implementation complexity

### **2. Dependency-Driven Ordering**
- Implements dependencies first
- Avoids circular dependency issues
- Clear implementation sequence

### **3. Cross-Project Visibility**
- Flags external API changes needed
- Identifies mobile app impacts
- Shows database/infrastructure changes

### **4. Pattern-Based Guidance**
- Suggests similar implementations to follow
- Reduces implementation guesswork
- Leverages existing code patterns

This roadmap agent transforms vague user requests into concrete, ordered implementation plans with full impact analysis.
