"""
Database queries for graph operations and project management.
All queries support optional project_id parameter for filtering.
"""

# Get project statistics
GET_PROJECT_STATS = """
    SELECT 
        p.id,
        p.name,
        p.language,
        COUNT(DISTINCT n.node_id) as node_count,
        COUNT(DISTINCT fh.id) as file_count,
        COUNT(DISTINCT r.id) as relationship_count
    FROM projects p
    LEFT JOIN nodes n ON p.id = n.project_id
    LEFT JOIN file_hashes fh ON p.id = fh.project_id
    LEFT JOIN relationships r ON p.id = r.project_id
    WHERE p.id = :project_id
    GROUP BY p.id, p.name, p.language
"""

# Get all project statistics
GET_ALL_PROJECT_STATS = """
    SELECT 
        p.id,
        p.name,
        p.language,
        COUNT(DISTINCT n.node_id) as node_count,
        COUNT(DISTINCT fh.id) as file_count,
        COUNT(DISTINCT r.id) as relationship_count
    FROM projects p
    LEFT JOIN nodes n ON p.id = n.project_id
    LEFT JOIN file_hashes fh ON p.id = fh.project_id
    LEFT JOIN relationships r ON p.id = r.project_id
    GROUP BY p.id, p.name, p.language
    ORDER BY node_count DESC
"""

# Get files in a project
GET_PROJECT_FILES = """
    SELECT 
        fh.id,
        fh.file_path,
        fh.content_hash,
        fh.file_size,
        fh.language,
        fh.name,
        COUNT(n.node_id) as node_count
    FROM file_hashes fh
    LEFT JOIN nodes n ON fh.id = n.file_hash_id
    WHERE (:project_id IS NULL OR fh.project_id = :project_id)
    GROUP BY fh.id, fh.file_path, fh.content_hash, fh.file_size, fh.language, fh.name
    ORDER BY fh.file_path
"""

# Get related functions in the same file
GET_RELATED_FUNCTIONS_IN_FILE = """
    SELECT DISTINCT 
        n.name, 
        n.node_type, 
        n.lines,
        n.code_snippet
    FROM nodes n
    LEFT JOIN file_hashes fh ON n.file_hash_id = fh.id
    WHERE LOWER(fh.file_path) = LOWER(:file_path) 
    AND n.name != :function_name
    AND (:project_id IS NULL OR n.project_id = :project_id)
    ORDER BY JSON_EXTRACT(n.lines, '$[0]')
    LIMIT 5
"""

# Get nodes by function name pattern (fuzzy search)
GET_NODES_BY_FUNCTION_NAME_PATTERN = """
    SELECT 
        n.node_id,
        n.node_type,
        n.name,
        n.lines,
        n.code_snippet,
        n.properties,
        fh.file_path,
        fh.language,
        fh.file_size,
        p.name as project_name
    FROM nodes n
    LEFT JOIN file_hashes fh ON n.file_hash_id = fh.id
    LEFT JOIN projects p ON n.project_id = p.id
    WHERE n.name LIKE :name_pattern
    AND n.node_type IN ('function', 'method', 'function_definition')
    AND (:project_id IS NULL OR n.project_id = :project_id)
    ORDER BY n.name
    LIMIT 20
"""

# Get multi-level function callers (recursive)
GET_DEEP_CALLERS = """
    WITH RECURSIVE caller_chain(
        node_id, name, file_path, depth, path
    ) AS (
        -- Base case: direct callers
        SELECT DISTINCT 
            n1.node_id,
            n1.name,
            fh1.file_path,
            1 as depth,
            n1.name as path
        FROM relationships r
        JOIN nodes n1 ON r.from_node_id = n1.node_id
        JOIN nodes n2 ON r.to_node_id = n2.node_id
        LEFT JOIN file_hashes fh1 ON n1.file_hash_id = fh1.id
        LEFT JOIN file_hashes fh2 ON n2.file_hash_id = fh2.id
        WHERE r.relationship_type = 'CALLS'
        AND fh2.file_path = :file_path
        AND n2.name = :function_name
        AND (:project_id IS NULL OR n1.project_id = :project_id)
        
        UNION ALL
        
        -- Recursive case: callers of callers
        SELECT DISTINCT
            n1.node_id,
            n1.name,
            fh1.file_path,
            cc.depth + 1,
            cc.path || ' -> ' || n1.name
        FROM relationships r
        JOIN nodes n1 ON r.from_node_id = n1.node_id
        JOIN nodes n2 ON r.to_node_id = n2.node_id
        LEFT JOIN file_hashes fh1 ON n1.file_hash_id = fh1.id
        LEFT JOIN file_hashes fh2 ON n2.file_hash_id = fh2.id
        JOIN caller_chain cc ON cc.node_id = n2.node_id
        WHERE r.relationship_type = 'CALLS'
        AND cc.depth < 5
        AND (:project_id IS NULL OR n1.project_id = :project_id)
    )
    SELECT * FROM caller_chain ORDER BY depth, file_path
"""

# Get multi-level function callees (recursive)
GET_DEEP_CALLEES = """
    WITH RECURSIVE callee_chain(
        node_id, name, file_path, depth, path
    ) AS (
        -- Base case: direct callees
        SELECT DISTINCT 
            n2.node_id,
            n2.name,
            fh2.file_path,
            1 as depth,
            n2.name as path
        FROM relationships r
        JOIN nodes n1 ON r.from_node_id = n1.node_id
        JOIN nodes n2 ON r.to_node_id = n2.node_id
        LEFT JOIN file_hashes fh1 ON n1.file_hash_id = fh1.id
        LEFT JOIN file_hashes fh2 ON n2.file_hash_id = fh2.id
        WHERE r.relationship_type = 'CALLS'
        AND fh1.file_path = :file_path
        AND n1.name = :function_name
        AND (:project_id IS NULL OR n2.project_id = :project_id)
        
        UNION ALL
        
        -- Recursive case: callees of callees
        SELECT DISTINCT
            n2.node_id,
            n2.name,
            fh2.file_path,
            cc.depth + 1,
            cc.path || ' -> ' || n2.name
        FROM relationships r
        JOIN nodes n1 ON r.from_node_id = n1.node_id
        JOIN nodes n2 ON r.to_node_id = n2.node_id
        LEFT JOIN file_hashes fh1 ON n1.file_hash_id = fh1.id
        LEFT JOIN file_hashes fh2 ON n2.file_hash_id = fh2.id
        JOIN callee_chain cc ON cc.node_id = n1.node_id
        WHERE r.relationship_type = 'CALLS'
        AND cc.depth < 5
        AND (:project_id IS NULL OR n2.project_id = :project_id)
    )
    SELECT * FROM callee_chain ORDER BY depth, file_path
"""

# Get only functions from a specific file
GET_FILE_FUNCTIONS = """
    SELECT 
        n.node_id,
        n.name,
        n.lines,
        n.code_snippet,
        n.properties,
        COUNT(DISTINCT CASE WHEN r.from_node_id = n.node_id THEN r.id END) as outgoing_calls,
        COUNT(DISTINCT CASE WHEN r.to_node_id = n.node_id THEN r.id END) as incoming_calls
    FROM nodes n
    JOIN file_hashes fh ON n.file_hash_id = fh.id
    LEFT JOIN relationships r ON n.node_id = r.from_node_id OR n.node_id = r.to_node_id
    WHERE fh.file_path = :file_path
    AND n.node_type IN ('function', 'method', 'function_definition')
    AND (:project_id IS NULL OR n.project_id = :project_id)
    GROUP BY n.node_id, n.name, n.lines, n.code_snippet, n.properties
    ORDER BY n.lines
"""

# Get only classes from a specific file
GET_FILE_CLASSES = """
    SELECT 
        n.node_id,
        n.name,
        n.lines,
        n.code_snippet,
        n.properties,
        COUNT(DISTINCT CASE WHEN r.from_node_id = n.node_id THEN r.id END) as outgoing_relationships,
        COUNT(DISTINCT CASE WHEN r.to_node_id = n.node_id THEN r.id END) as incoming_relationships
    FROM nodes n
    JOIN file_hashes fh ON n.file_hash_id = fh.id
    LEFT JOIN relationships r ON n.node_id = r.from_node_id OR n.node_id = r.to_node_id
    WHERE fh.file_path = :file_path
    AND n.node_type = 'class'
    AND (:project_id IS NULL OR n.project_id = :project_id)
    GROUP BY n.node_id, n.name, n.lines, n.code_snippet, n.properties
    ORDER BY n.lines
"""

# Analyze usage patterns
GET_USAGE_PATTERNS = """
    SELECT 
        n.name,
        n.node_type,
        fh.file_path,
        COUNT(DISTINCT r_in.id) as times_called,
        COUNT(DISTINCT r_out.id) as calls_others,
        COUNT(DISTINCT fh_callers.file_path) as used_in_files
    FROM nodes n
    LEFT JOIN file_hashes fh ON n.file_hash_id = fh.id
    LEFT JOIN relationships r_in ON n.node_id = r_in.to_node_id AND r_in.relationship_type = 'CALLS'
    LEFT JOIN relationships r_out ON n.node_id = r_out.from_node_id AND r_out.relationship_type = 'CALLS'
    LEFT JOIN nodes n_callers ON r_in.from_node_id = n_callers.node_id
    LEFT JOIN file_hashes fh_callers ON n_callers.file_hash_id = fh_callers.id
    WHERE n.name = :name 
    AND n.node_type = :node_type
    AND (:project_id IS NULL OR n.project_id = :project_id)
    GROUP BY n.node_id, n.name, n.node_type, fh.file_path
    ORDER BY times_called DESC
"""
