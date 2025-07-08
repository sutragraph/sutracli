# Find any node by exact name (functions, classes, API endpoints, etc.)
GET_NODES_BY_EXACT_NAME = """
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
        p.name as project_name,
        p.id as project_id
    FROM nodes n
    LEFT JOIN file_hashes fh ON n.file_hash_id = fh.id
    LEFT JOIN projects p ON n.project_id = p.id
    WHERE n.name_lower = LOWER(:name)
    AND (:project_id IS NULL OR n.project_id = :project_id)
    ORDER BY n.node_id
    LIMIT 100
"""

# Fallback query for GET_NODES_BY_EXACT_NAME when no exact matches found (prefix matching for file extensions)
GET_NODES_BY_NAME_LIKE = """
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
        p.name as project_name,
        p.id as project_id
    FROM nodes n
    LEFT JOIN file_hashes fh ON n.file_hash_id = fh.id
    LEFT JOIN projects p ON n.project_id = p.id
    WHERE n.name_lower LIKE LOWER(:name) || '%'
    AND (:project_id IS NULL OR n.project_id = :project_id)
    ORDER BY
        CASE
            WHEN n.name_lower = LOWER(:name) THEN 1
            WHEN n.name_lower LIKE LOWER(:name) || '.' || '%' THEN 2
            ELSE 3
        END,
        n.node_id
    LIMIT 100
"""

# Global keyword search in code content and node names
GET_NODES_BY_KEYWORD_SEARCH = """
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
        p.name as project_name,
        p.id as project_id
    FROM nodes n
    LEFT JOIN file_hashes fh ON n.file_hash_id = fh.id
    LEFT JOIN projects p ON n.project_id = p.id
    WHERE (
        n.code_snippet LIKE '%' || :keyword || '%'
        OR n.name_lower LIKE '%' || LOWER(:keyword) || '%'
    )
    AND (:project_id IS NULL OR n.project_id = :project_id)
    ORDER BY
        CASE
            WHEN n.name_lower = LOWER(:keyword) THEN 1
            WHEN n.name_lower LIKE LOWER(:keyword) || '%' THEN 2
            WHEN n.name_lower LIKE '%' || LOWER(:keyword) || '%' THEN 3
            ELSE 4
        END,
        n.node_id
    LIMIT 100
"""

# Find code snippet from a specific file
GET_CODE_FROM_FILE = """
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
        p.name as project_name,
        p.id as project_id
    FROM nodes n
    INNER JOIN file_hashes fh ON n.file_hash_id = fh.id
    LEFT JOIN projects p ON n.project_id = p.id
    WHERE fh.file_path = :file_path
    AND n.node_type = 'File'
    AND (:project_id IS NULL OR n.project_id = :project_id)
    ORDER BY JSON_EXTRACT(n.lines, '$[0]')
"""

# Get all node names from a specific file
GET_ALL_NODE_NAMES_FROM_FILE = """
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
        p.name as project_name,
        p.id as project_id
    FROM nodes n
    INNER JOIN file_hashes fh ON n.file_hash_id = fh.id
    LEFT JOIN projects p ON n.project_id = p.id
    WHERE fh.file_path = :file_path
    AND (:project_id IS NULL OR n.project_id = :project_id)
    ORDER BY JSON_EXTRACT(n.lines, '$[0]')
"""

# Get all nodes from a specific file
GET_ALL_NODES_FROM_FILE = """
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
        p.name as project_name,
        p.id as project_id
    FROM nodes n
    INNER JOIN file_hashes fh ON n.file_hash_id = fh.id
    LEFT JOIN projects p ON n.project_id = p.id
    WHERE fh.file_path = :file_path
    AND (:project_id IS NULL OR n.project_id = :project_id)
    ORDER BY JSON_EXTRACT(n.lines, '$[0]')
"""

# Get detailed information about a specific node
GET_NODE_DETAILS = """
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
        p.name as project_name,
        p.id as project_id
    FROM nodes n
    LEFT JOIN file_hashes fh ON n.file_hash_id = fh.id
    LEFT JOIN projects p ON n.project_id = p.id
    WHERE n.node_id = :node_id
    AND (:project_id IS NULL OR n.project_id = :project_id)
"""

# Get functions that call a specific function (callers)
GET_FUNCTION_CALLERS = """
    SELECT DISTINCT 
        n1.name as caller_function,
        n1.node_type as caller_type,
        fh1.file_path as caller_file,
        n1.code_snippet,
        r.properties as call_properties,
        JSON_EXTRACT(r.properties, '$.line_number') as line_number
    FROM relationships r
    JOIN nodes n1 ON r.from_node_id = n1.node_id
    JOIN nodes n2 ON r.to_node_id = n2.node_id
    LEFT JOIN file_hashes fh1 ON n1.file_hash_id = fh1.id
    LEFT JOIN file_hashes fh2 ON n2.file_hash_id = fh2.id
    WHERE r.relationship_type = 'CALLS'
    AND n2.name_lower = LOWER(:function_name)
    AND (:project_id IS NULL OR n1.project_id = :project_id)
    ORDER BY fh1.file_path, line_number
"""

# Get functions called by a specific function (callees)
GET_FUNCTION_CALLEES = """
    SELECT DISTINCT 
        n2.name as callee_function,
        n2.node_type as callee_type,
        fh2.file_path as callee_file,
        n2.code_snippet,
        r.properties as call_properties,
        JSON_EXTRACT(r.properties, '$.line_number') as line_number
    FROM relationships r
    JOIN nodes n1 ON r.from_node_id = n1.node_id
    JOIN nodes n2 ON r.to_node_id = n2.node_id
    LEFT JOIN file_hashes fh1 ON n1.file_hash_id = fh1.id
    LEFT JOIN file_hashes fh2 ON n2.file_hash_id = fh2.id
    WHERE r.relationship_type = 'CALLS'
    AND n1.name_lower = LOWER(:function_name)
    AND (:project_id IS NULL OR n1.project_id = :project_id)
    ORDER BY fh2.file_path, line_number
"""

# Get file dependencies (what files this file imports)
GET_FILE_DEPENDENCIES = """
    SELECT DISTINCT 
        fh2.file_path as dependency_file,
        fh2.language as dependency_language,
        r.properties as import_properties
    FROM relationships r
    JOIN file_hashes fh1 ON r.from_node_id = fh1.id
    JOIN file_hashes fh2 ON r.to_node_id = fh2.id
    WHERE r.relationship_type = 'IMPORTS'
    AND fh1.file_path = :file_path
    AND (:project_id IS NULL OR fh1.project_id = :project_id)
    ORDER BY fh2.file_path
"""
