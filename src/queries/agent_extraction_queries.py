"""
Agent queries for the new extraction schema (files, code_blocks, relationships).
These queries replace the old tree-sitter node-based queries.
"""

# Find code blocks by exact name (functions, classes, variables, etc.)
GET_BLOCKS_BY_NAME = """
    SELECT
        cb.id,
        cb.type,
        cb.name,
        cb.content,
        cb.start_line,
        cb.end_line,
        cb.start_col,
        cb.end_col,
        cb.parent_block_id,
        f.file_path,
        f.language,
        p.name as project_name,
        p.id as project_id
    FROM code_blocks cb
    JOIN files f ON cb.file_id = f.id
    JOIN projects p ON f.project_id = p.id
    WHERE LOWER(cb.name) = LOWER(:name)
    AND (:project_id IS NULL OR f.project_id = :project_id)
    ORDER BY f.file_path, cb.start_line
    LIMIT 100
"""

# Fallback query for GET_BLOCKS_BY_NAME when no exact matches found (prefix matching)
GET_BLOCKS_BY_NAME_LIKE = """
    SELECT
        cb.id,
        cb.type,
        cb.name,
        cb.content,
        cb.start_line,
        cb.end_line,
        cb.start_col,
        cb.end_col,
        cb.parent_block_id,
        f.file_path,
        f.language,
        p.name as project_name,
        p.id as project_id
    FROM code_blocks cb
    JOIN files f ON cb.file_id = f.id
    JOIN projects p ON f.project_id = p.id
    WHERE LOWER(cb.name) LIKE LOWER(:name) || '%'
    AND (:project_id IS NULL OR f.project_id = :project_id)
    ORDER BY
        CASE
            WHEN LOWER(cb.name) = LOWER(:name) THEN 1
            WHEN LOWER(cb.name) LIKE LOWER(:name) || '.' || '%' THEN 2
            ELSE 3
        END,
        f.file_path, cb.start_line
    LIMIT 100
"""

# Search code blocks by keyword in name or content
GET_BLOCKS_BY_KEYWORD_SEARCH = """
    SELECT
        cb.id,
        cb.type,
        cb.name,
        cb.content,
        cb.start_line,
        cb.end_line,
        cb.start_col,
        cb.end_col,
        cb.parent_block_id,
        f.file_path,
        f.language,
        p.name as project_name,
        p.id as project_id
    FROM code_blocks cb
    JOIN files f ON cb.file_id = f.id
    JOIN projects p ON f.project_id = p.id
    WHERE (LOWER(cb.name) LIKE '%' || LOWER(:keyword) || '%'
           OR LOWER(cb.content) LIKE '%' || LOWER(:keyword) || '%')
    AND (:project_id IS NULL OR f.project_id = :project_id)
    ORDER BY
        CASE
            WHEN LOWER(cb.name) LIKE '%' || LOWER(:keyword) || '%' THEN 1
            ELSE 2
        END,
        f.file_path, cb.start_line
    LIMIT 100
"""

# Get file content directly
GET_FILE_CONTENT = """
    SELECT
        f.content,
        f.language,
        f.file_path,
        f.content_hash,
        p.name as project_name,
        p.id as project_id
    FROM files f
    JOIN projects p ON f.project_id = p.id
    WHERE f.file_path = :file_path
    AND (:project_id IS NULL OR f.project_id = :project_id)
"""

# Get all code block names from a specific file
GET_BLOCK_NAMES_FROM_FILE = """
    SELECT
        cb.name,
        cb.type,
        cb.start_line,
        cb.end_line,
        cb.start_col,
        cb.end_col,
        cb.parent_block_id,
        f.file_path,
        f.language,
        p.name as project_name
    FROM code_blocks cb
    JOIN files f ON cb.file_id = f.id
    JOIN projects p ON f.project_id = p.id
    WHERE f.file_path = :file_path
    AND (:project_id IS NULL OR f.project_id = :project_id)
    ORDER BY cb.start_line
"""

# Get all code blocks from a specific file (with content)
GET_BLOCKS_IN_FILE = """
    SELECT
        cb.id,
        cb.type,
        cb.name,
        cb.content,
        cb.start_line,
        cb.end_line,
        cb.start_col,
        cb.end_col,
        cb.parent_block_id,
        f.file_path,
        f.language,
        p.name as project_name,
        p.id as project_id
    FROM code_blocks cb
    JOIN files f ON cb.file_id = f.id
    JOIN projects p ON f.project_id = p.id
    WHERE f.file_path = :file_path
    AND (:project_id IS NULL OR f.project_id = :project_id)
    ORDER BY cb.start_line
"""

# Get code blocks by type (function, class, variable, etc.)
GET_BLOCKS_BY_TYPE = """
    SELECT
        cb.id,
        cb.type,
        cb.name,
        cb.content,
        cb.start_line,
        cb.end_line,
        cb.start_col,
        cb.end_col,
        cb.parent_block_id,
        f.file_path,
        f.language,
        p.name as project_name,
        p.id as project_id
    FROM code_blocks cb
    JOIN files f ON cb.file_id = f.id
    JOIN projects p ON f.project_id = p.id
    WHERE cb.type = :type
    AND (:project_id IS NULL OR f.project_id = :project_id)
    ORDER BY f.file_path, cb.start_line
    LIMIT 100
"""

# Get detailed information about a specific code block
GET_BLOCK_DETAILS = """
    SELECT
        cb.id,
        cb.type,
        cb.name,
        cb.content,
        cb.start_line,
        cb.end_line,
        cb.start_col,
        cb.end_col,
        cb.parent_block_id,
        f.file_path,
        f.language,
        f.content_hash,
        p.name as project_name,
        p.id as project_id
    FROM code_blocks cb
    JOIN files f ON cb.file_id = f.id
    JOIN projects p ON f.project_id = p.id
    WHERE cb.id = :block_id
    AND (:project_id IS NULL OR f.project_id = :project_id)
"""

# Get file imports (what files this file imports)
GET_FILE_IMPORTS = """
    SELECT DISTINCT 
        tf.file_path as imported_file,
        tf.language as imported_language,
        r.metadata as import_metadata
    FROM relationships r
    JOIN files sf ON r.source_id = sf.id
    JOIN files tf ON r.target_id = tf.id
    WHERE r.type = 'import'
    AND sf.file_path = :file_path
    AND (:project_id IS NULL OR sf.project_id = :project_id)
    ORDER BY tf.file_path
"""
