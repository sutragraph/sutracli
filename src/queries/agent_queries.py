"""
Roadmap Agent Database Queries
Exposed queries for agent direct access + Background queries for auto-conversion.
Architecture: Agent gets actionable data, never sees raw IDs or database complexity.
"""

# ============================================================================
# BACKGROUND QUERIES - Auto-Conversion (Never Exposed to Agent)
# ============================================================================

GET_CODE_BLOCK_BY_ID = """
SELECT
    cb.id, cb.type, cb.name, cb.content, cb.start_line, cb.end_line,
    cb.start_col, cb.end_col, cb.parent_block_id,
    f.file_path, f.language, f.id as file_id,
    p.name as project_name, p.id as project_id
FROM code_blocks cb
JOIN files f ON cb.file_id = f.id
JOIN projects p ON f.project_id = p.id
WHERE cb.id = ?
"""
# Returns: Single code block with full context
# Example: {
#   id: 123, type: "function", name: "uploadAvatar",
#   content: "def uploadAvatar(user_id, file):\n    ...",
#   start_line: 45, end_line: 67, parent_block_id: 89,
#   file_path: "src/services/user_service.py", language: "python",
#   project_name: "backend_api", file_id: 456, project_id: 1
# }

GET_FILE_BY_ID = """
SELECT
    f.id, f.file_path, f.language, f.content, f.content_hash,
    p.name as project_name, p.id as project_id,
    COUNT(cb.id) as block_count
FROM files f
JOIN projects p ON f.project_id = p.id
LEFT JOIN code_blocks cb ON f.id = cb.file_id
WHERE f.id = ?
GROUP BY f.id
"""
# Returns: Single file with metadata and block count
# Example: {
#   id: 456, file_path: "src/services/user_service.py", language: "python",
#   content: "import bcrypt\nfrom models import User\n\nclass UserService:\n    ...",
#   content_hash: "abc123def456", project_name: "backend_api",
#   project_id: 1, block_count: 8
# }

GET_IMPLEMENTATION_CONTEXT = """
SELECT
    cb.id, cb.type, cb.name, cb.start_line, cb.end_line,
    parent.name as parent_name, parent.type as parent_type,
    f.file_path, f.language
FROM code_blocks cb
LEFT JOIN code_blocks parent ON cb.parent_block_id = parent.id
JOIN files f ON cb.file_id = f.id
WHERE cb.file_id = ?
ORDER BY cb.start_line
LIMIT 25
"""
# Returns: All blocks in file with parent context (max 25)
# Example: [
#   {id: 89, type: "class", name: "UserService", start_line: 10, end_line: 120,
#    parent_name: null, parent_type: null, file_path: "src/services/user_service.py"},
#   {id: 123, type: "function", name: "uploadAvatar", start_line: 45, end_line: 67,
#    parent_name: "UserService", parent_type: "class", file_path: "src/services/user_service.py"}
# ]

# ============================================================================
# EXPOSED QUERIES - Discovery & Context Expansion
# ============================================================================

GET_FILE_BLOCK_SUMMARY = """
SELECT
    cb.id, cb.type, cb.name, cb.start_line, cb.end_line, cb.parent_block_id
FROM code_blocks cb
WHERE cb.file_id = ?
ORDER BY cb.start_line
LIMIT 20
"""
# Returns: Quick overview of all blocks in file (no content, max 20)
# Example: [
#   {id: 89, type: "class", name: "UserService", start_line: 10, end_line: 120, parent_block_id: null},
#   {id: 123, type: "function", name: "uploadAvatar", start_line: 45, end_line: 67, parent_block_id: 89},
#   {id: 124, type: "function", name: "deleteAvatar", start_line: 69, end_line: 85, parent_block_id: 89}
# ]

GET_CHILD_BLOCKS = """
SELECT
    cb.id, cb.type, cb.name, cb.start_line, cb.end_line
FROM code_blocks cb
WHERE cb.parent_block_id = ?
ORDER BY cb.start_line
LIMIT 15
"""
# Returns: Direct children of a parent block (max 15)
# Example for UserService class: [
#   {id: 123, type: "function", name: "uploadAvatar", start_line: 45, end_line: 67},
#   {id: 124, type: "function", name: "deleteAvatar", start_line: 69, end_line: 85},
#   {id: 125, type: "function", name: "validateUser", start_line: 87, end_line: 102}
# ]

GET_PARENT_BLOCK = """
SELECT
    cb.id, cb.type, cb.name, cb.start_line, cb.end_line,
    f.file_path
FROM code_blocks cb
JOIN files f ON cb.file_id = f.id
WHERE cb.id = (SELECT parent_block_id FROM code_blocks WHERE id = ?)
"""
# Returns: Parent block of given block (single result or null)
# Example for uploadAvatar function: {
#   id: 89, type: "class", name: "UserService", start_line: 10, end_line: 120,
#   file_path: "src/services/user_service.py"
# }

# ============================================================================
# EXPOSED QUERIES - Impact Analysis
# ============================================================================

GET_FILES_USING_SYMBOL = """
SELECT 'REQUIRES_RIPGREP' as tool,
       'Search for symbol usage across all files' as action,
       'Use: ripgrep to find where symbols are used' as suggestion
"""
# Returns: Ripgrep tool requirement message
# Use ripgrep instead: rg "uploadAvatar" --type py
# Would find: ["src/controllers/profile.py:23", "src/api/user.py:45", "tests/test_user.py:67"]

GET_FILE_IMPACT_SCOPE = """
SELECT
    'importer' as relationship_type,
    f.file_path, f.language, p.name as project_name,
    r.import_content
FROM relationships r
JOIN files f ON r.source_id = f.id
JOIN projects p ON f.project_id = p.id
WHERE r.target_id = ?
UNION ALL
SELECT
    'dependency' as relationship_type,
    f.file_path, f.language, p.name as project_name,
    r.import_content
FROM relationships r
JOIN files f ON r.target_id = f.id
JOIN projects p ON f.project_id = p.id
WHERE r.source_id = ?
ORDER BY relationship_type, file_path
LIMIT 25
"""
# Returns: Files that import this file + files this file imports (max 25)
# Example for user_service.py: [
#   {relationship_type: "importer", file_path: "src/controllers/profile.py",
#    language: "python", project_name: "backend_api", import_content: "from services.user_service import UserService"},
#   {relationship_type: "dependency", file_path: "src/models/user.py",
#    language: "python", project_name: "backend_api", import_content: "from models.user import User"}
# ]

GET_FILE_IMPORTS = """
SELECT
    r.import_content,
    f.file_path, f.language, p.name as project_name
FROM relationships r
JOIN files f ON r.target_id = f.id
JOIN projects p ON f.project_id = p.id
WHERE r.source_id = ?
ORDER BY f.file_path
LIMIT 15
"""
# Returns: Files that this file imports (max 15)
# Example for user_service.py: [
#   {import_content: "from models.user import User", file_path: "src/models/user.py",
#    language: "python", project_name: "backend_api"},
#   {import_content: "import bcrypt", file_path: "external/bcrypt",
#    language: "python", project_name: "backend_api"}
# ]

# ============================================================================
# EXPOSED QUERIES - Dependency Mapping
# ============================================================================

GET_DEPENDENCY_CHAIN = """
WITH RECURSIVE dep_chain(file_id, file_path, target_id, target_path, depth, path) AS (
    -- Base case: direct dependencies
    SELECT
        r.source_id, sf.file_path,
        r.target_id, tf.file_path,
        1, sf.file_path || ' → ' || tf.file_path
    FROM relationships r
    JOIN files sf ON r.source_id = sf.id
    JOIN files tf ON r.target_id = tf.id
    WHERE r.source_id = ?

    UNION ALL

    -- Recursive case: follow the chain
    SELECT
        dc.file_id, dc.file_path,
        r.target_id, tf.file_path,
        dc.depth + 1, dc.path || ' → ' || tf.file_path
    FROM dep_chain dc
    JOIN relationships r ON dc.target_id = r.source_id
    JOIN files tf ON r.target_id = tf.id
    WHERE dc.depth < 5 AND dc.path NOT LIKE '%' || tf.file_path || '%'
)
SELECT file_id, file_path, target_id, target_path, depth, path
FROM dep_chain
ORDER BY depth, file_path
LIMIT 25
"""
# Returns: Multi-level dependency chain (max 5 levels deep, max 25 results)
# Example for user_service.py: [
#   {file_id: 456, file_path: "src/services/user_service.py", target_id: 789,
#    target_path: "src/models/user.py", depth: 1, path: "user_service.py → user.py"},
#   {file_id: 456, file_path: "src/services/user_service.py", target_id: 101,
#    target_path: "src/database/connection.py", depth: 2, path: "user_service.py → user.py → connection.py"}
# ]

# ============================================================================
# EXPOSED QUERIES - Cross-Project Impact Analysis
# ============================================================================

GET_EXTERNAL_CONNECTIONS = """
SELECT
    'incoming' as direction, ic.description, ic.technology_name, ic.snippet_lines
FROM incoming_connections ic
WHERE ic.file_id = ?
UNION ALL
SELECT
    'outgoing' as direction, oc.description, oc.technology_name, oc.snippet_lines
FROM outgoing_connections oc
WHERE oc.file_id = ?
ORDER BY direction, technology_name
LIMIT 15
"""
# Returns: External integrations for specific file (max 15)
# Example for user_service.py: [
#   {direction: "incoming", description: "Frontend user profile API",
#    technology_name: "React", snippet_lines: "[45, 67]"},
#   {direction: "outgoing", description: "AWS S3 file upload",
#    technology_name: "AWS_S3", snippet_lines: "[52, 58]"}
# ]

GET_PROJECT_EXTERNAL_CONNECTIONS = """
SELECT
    f.file_path, f.language,
    COALESCE(ic.technology_name, oc.technology_name) as technology,
    COALESCE(ic.description, oc.description) as description,
    CASE WHEN ic.id IS NOT NULL THEN 'incoming' ELSE 'outgoing' END as direction
FROM files f
LEFT JOIN incoming_connections ic ON f.id = ic.file_id
LEFT JOIN outgoing_connections oc ON f.id = oc.file_id
WHERE f.project_id = ? AND (ic.id IS NOT NULL OR oc.id IS NOT NULL)
ORDER BY f.file_path, direction
LIMIT 25
"""
# Returns: All external connections for entire project (max 25)
# Example for backend_api project: [
#   {file_path: "src/services/user_service.py", language: "python",
#    technology: "AWS_S3", description: "File upload service", direction: "outgoing"},
#   {file_path: "src/api/user_api.py", language: "python",
#    technology: "React", description: "Frontend API calls", direction: "incoming"}
# ]

GET_CONNECTION_IMPACT = """
SELECT
    cm.connection_type, cm.description, cm.match_confidence,
    CASE
        WHEN ic.file_id = ? THEN 'receives_from'
        WHEN oc.file_id = ? THEN 'sends_to'
    END as impact_type,
    COALESCE(if2.file_path, of2.file_path) as other_file,
    COALESCE(ic2.technology_name, oc2.technology_name) as technology
FROM connection_mappings cm
LEFT JOIN incoming_connections ic ON cm.receiver_id = ic.id
LEFT JOIN outgoing_connections oc ON cm.sender_id = oc.id
LEFT JOIN incoming_connections ic2 ON cm.sender_id = ic2.id
LEFT JOIN outgoing_connections oc2 ON cm.receiver_id = oc2.id
LEFT JOIN files if2 ON ic2.file_id = if2.id
LEFT JOIN files of2 ON oc2.file_id = of2.id
WHERE (ic.file_id = ? OR oc.file_id = ?) AND cm.match_confidence > 0.5
ORDER BY cm.match_confidence DESC
LIMIT 15
"""
# Returns: High-confidence connection mappings for file (>0.5 confidence, max 15)
# Example for user_service.py: [
#   {connection_type: "API_CALL", description: "Profile update endpoint",
#    match_confidence: 0.85, impact_type: "receives_from",
#    other_file: "frontend/src/components/Profile.jsx", technology: "React"},
#   {connection_type: "FILE_UPLOAD", description: "Avatar storage",
#    match_confidence: 0.92, impact_type: "sends_to",
#    other_file: "aws_s3_bucket", technology: "AWS_S3"}
# ]

# ============================================================================
# EXPOSED QUERIES - Pattern Recognition
# ============================================================================

GET_SIMILAR_IMPLEMENTATIONS = """
SELECT 'REQUIRES_RIPGREP' as tool,
       'Search for similar function/class implementations' as action,
       'Use: ripgrep with pattern matching for similar names' as suggestion
"""
# Returns: Ripgrep tool requirement message
# Use ripgrep instead: rg "def.*upload.*|class.*upload.*" --type py
# Would find: ["src/services/file_service.py:23:def uploadDocument", "src/media/media_service.py:45:def uploadImage"]

GET_FILES_WITH_PATTERN = """
SELECT 'REQUIRES_RIPGREP' as tool,
       'Search for files containing specific patterns' as action,
       'Use: ripgrep to find pattern matches in file content' as suggestion
"""
# Returns: Ripgrep tool requirement message
# Use ripgrep instead: rg "upload.*avatar" --files-with-matches --type py
# Would find: ["src/services/user_service.py", "src/controllers/profile_controller.py", "tests/test_avatar.py"]

# ============================================================================
# BACKGROUND QUERIES - Auto-Enrichment
# ============================================================================

GET_FILE_COMPLEXITY_SCORE = """
SELECT
    f.file_path, f.language,
    COUNT(cb.id) as total_blocks,
    COUNT(CASE WHEN cb.type = 'function' THEN 1 END) as function_count,
    COUNT(CASE WHEN cb.type = 'class' THEN 1 END) as class_count,
    COUNT(r.id) as dependency_count
FROM files f
LEFT JOIN code_blocks cb ON f.id = cb.file_id
LEFT JOIN relationships r ON f.id = r.source_id
WHERE f.id = ?
GROUP BY f.id
"""
# Returns: Complexity metrics for roadmap planning (single result)
# Example for user_service.py: {
#   file_path: "src/services/user_service.py", language: "python",
#   total_blocks: 8, function_count: 6, class_count: 1, dependency_count: 4
# }

# ============================================================================
# LEGACY COMPATIBILITY - Map Old Query Names to New Architecture
# ============================================================================

# Map old query names to new exposed queries
GET_NODES_BY_EXACT_NAME = """
SELECT 'REQUIRES_RIPGREP' as tool,
       'Search for exact symbol names across codebase' as action,
       'Use: ripgrep with exact pattern matching' as suggestion
"""
# Legacy compatibility - use ripgrep: rg "^def uploadAvatar|^class uploadAvatar" --type py

GET_NODES_BY_NAME_LIKE = """
SELECT 'REQUIRES_RIPGREP' as tool,
       'Search for nodes with similar names' as action,
       'Use: ripgrep with fuzzy pattern matching' as suggestion
"""
# Legacy compatibility - use ripgrep: rg "upload.*avatar" --type py

GET_NODES_BY_KEYWORD_SEARCH = """
SELECT 'REQUIRES_RIPGREP' as tool,
       'Search for keyword patterns in code' as action,
       'Use: ripgrep for keyword search across files' as suggestion
"""
# Legacy compatibility - use ripgrep: rg "keyword1.*keyword2" --type py
GET_CODE_FROM_FILE = GET_FILE_BY_ID
GET_ALL_NODE_NAMES_FROM_FILE = GET_FILE_BLOCK_SUMMARY
GET_FILE_DEPENDENCIES = GET_FILE_IMPORTS

# External tool requirements - indicate what tools are needed
GET_FUNCTION_CALLERS = """
SELECT 'REQUIRES_RIPGREP' as tool, 'Search for function calls across codebase' as action,
       'Use: ripgrep pattern search for function invocations' as suggestion
"""
# Returns: Ripgrep tool requirement message
# Use ripgrep instead: rg "uploadAvatar\(" --type py
# Would find: ["src/controllers/profile.py:23:    user_service.uploadAvatar(user_id, file)"]

GET_FUNCTION_CALLEES = """
SELECT 'REQUIRES_RIPGREP' as tool, 'Search for function calls within implementation' as action,
       'Use: ripgrep pattern search within function body' as suggestion
"""
# Returns: Ripgrep tool requirement message
# Use ripgrep instead: rg "\..*\(" src/services/user_service.py -A 20 -B 5
# Would find function calls within the uploadAvatar implementation

# ============================================================================
# QUERY SUMMARY FOR ROADMAP AGENT
# ============================================================================

"""
EXPOSED QUERIES (Agent Direct Access):
- GET_FILE_BLOCK_SUMMARY: Context expansion around discovered files
- GET_CHILD_BLOCKS: Navigate into classes/functions
- GET_PARENT_BLOCK: Navigate up hierarchy
- GET_FILE_IMPACT_SCOPE: File-level dependency impact scope
- GET_FILE_IMPORTS: What this file depends on (import statements)
- GET_DEPENDENCY_CHAIN: Multi-level dependency tree
- GET_EXTERNAL_CONNECTIONS: Cross-project integrations
- GET_PROJECT_EXTERNAL_CONNECTIONS: All project external connections
- GET_CONNECTION_IMPACT: Mapped connections with confidence

RIPGREP QUERIES (External Tool Required):
- GET_FILES_USING_SYMBOL: Find where symbols are used
- GET_SYMBOL_SOURCES: Find where symbols are defined
- GET_SIMILAR_IMPLEMENTATIONS: Find similar function/class names
- GET_FILES_WITH_PATTERN: Find pattern matches in file content

BACKGROUND QUERIES (Auto-Conversion):
- GET_CODE_BLOCK_BY_ID: Convert semantic search "block_123" to actual code
- GET_FILE_BY_ID: Convert semantic search "file_456" to actual file
- GET_IMPLEMENTATION_CONTEXT: Add parent/child context to results
- GET_FILE_COMPLEXITY_SCORE: Add complexity metrics for roadmap planning

ARCHITECTURE PRINCIPLE:
Agent receives actionable, context-rich data. Never sees raw IDs or database complexity.
All results limited to 15-25 items max to prevent information overload.
"""


