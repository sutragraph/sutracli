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
"""

# ============================================================================
# EXPOSED QUERIES
# ============================================================================

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


GET_FILE_BLOCK_SUMMARY = """
SELECT
    cb.id, cb.type, cb.name, cb.start_line, cb.end_line, cb.parent_block_id,
    f.file_path, p.name as project_name, p.id as project_id
FROM code_blocks cb
JOIN files f ON cb.file_id = f.id
JOIN projects p ON f.project_id = p.id
WHERE cb.file_id = ?
ORDER BY cb.start_line
"""

GET_CHILD_BLOCKS = """
SELECT
    cb.id, cb.type, cb.name, cb.start_line, cb.end_line
FROM code_blocks cb
WHERE cb.parent_block_id = ?
ORDER BY cb.start_line
"""

GET_PARENT_BLOCK = """
SELECT
    cb.id, cb.type, cb.name, cb.start_line, cb.end_line,
    f.file_path
FROM code_blocks cb
JOIN files f ON cb.file_id = f.id
WHERE cb.id = (SELECT parent_block_id FROM code_blocks WHERE id = ?)
"""

GET_FILE_IMPORTS = """
SELECT
    r.import_content as import_content,
    f.file_path, f.language, p.name as project_name
FROM relationships r
JOIN files f ON r.target_id = f.id
JOIN projects p ON f.project_id = p.id
WHERE r.source_id = ?
"""

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
    WHERE dc.depth < ? AND dc.path NOT LIKE '%' || tf.file_path || '%'
)
SELECT file_id, file_path, target_id, target_path, depth, path
FROM dep_chain
ORDER BY depth, file_path
LIMIT 25
"""

# ============================================================================
# Others
# ============================================================================

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

GET_INCOMING_CONNECTIONS = """
SELECT
    ic.id, ic.description, ic.snippet_lines, ic.technology_name,
    ic.code_snippet, ic.created_at,
    f.file_path as target_file_path, f.language as target_language,
    p.name as target_project_name, p.id as target_project_id,
    oc.technology_name as source_technology_name, cm.match_confidence,
    oc.description as source_description,
    sf.file_path as source_file_path, sf.language as source_language,
    sp.name as source_project_name, sp.id as source_project_id,
    'incoming' as direction
FROM incoming_connections ic
JOIN files f ON ic.file_id = f.id
JOIN projects p ON f.project_id = p.id
LEFT JOIN connection_mappings cm ON ic.id = cm.receiver_id
LEFT JOIN outgoing_connections oc ON cm.sender_id = oc.id
LEFT JOIN files sf ON oc.file_id = sf.id
LEFT JOIN projects sp ON sf.project_id = sp.id
WHERE ic.file_id = ?
ORDER BY ic.created_at DESC, cm.match_confidence DESC
"""

GET_OUTGOING_CONNECTIONS = """
SELECT
    oc.id, oc.description, oc.snippet_lines, oc.technology_name,
    oc.code_snippet, oc.created_at,
    f.file_path as source_file_path, f.language as source_language,
    p.name as source_project_name, p.id as source_project_id,
    ic.technology_name as target_technology_name, cm.match_confidence,
    ic.description as target_description,
    tf.file_path as target_file_path, tf.language as target_language,
    tp.name as target_project_name, tp.id as target_project_id,
    'outgoing' as direction
FROM outgoing_connections oc
JOIN files f ON oc.file_id = f.id
JOIN projects p ON f.project_id = p.id
LEFT JOIN connection_mappings cm ON oc.id = cm.sender_id
LEFT JOIN incoming_connections ic ON cm.receiver_id = ic.id
LEFT JOIN files tf ON ic.file_id = tf.id
LEFT JOIN projects tp ON tf.project_id = tp.id
WHERE oc.file_id = ?
ORDER BY oc.created_at DESC, cm.match_confidence DESC
"""

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

GET_CONNECTION_IMPACT = """
SELECT
    COALESCE(oc.technology_name, ic.technology_name) as technology_name, cm.description, cm.match_confidence,
    CASE
        WHEN ic.file_id = ? THEN 'receives_from'
        WHEN oc.file_id = ? THEN 'sends_to'
    END as impact_type,
    COALESCE(if2.id, of2.id) as other_file_id,
    COALESCE(if2.file_path, of2.file_path) as other_file,
    COALESCE(ip2.name, op2.name) as other_project_name,
    COALESCE(ip2.id, op2.id) as other_project_id,
    COALESCE(ic2.technology_name, oc2.technology_name) as technology,
    COALESCE(ic.code_snippet, oc.code_snippet) as anchor_code_snippet,
    COALESCE(ic2.code_snippet, oc2.code_snippet) as other_code_snippet,
    COALESCE(ic.snippet_lines, oc.snippet_lines) as anchor_snippet_lines,
    COALESCE(ic2.snippet_lines, oc2.snippet_lines) as other_snippet_lines
FROM connection_mappings cm
LEFT JOIN incoming_connections ic ON cm.receiver_id = ic.id
LEFT JOIN outgoing_connections oc ON cm.sender_id = oc.id
LEFT JOIN incoming_connections ic2 ON cm.sender_id = ic2.id
LEFT JOIN outgoing_connections oc2 ON cm.receiver_id = oc2.id
LEFT JOIN files if2 ON ic2.file_id = if2.id
LEFT JOIN files of2 ON oc2.file_id = of2.id
LEFT JOIN projects ip2 ON if2.project_id = ip2.id
LEFT JOIN projects op2 ON of2.project_id = op2.id
WHERE (ic.file_id = ? OR oc.file_id = ?) AND cm.match_confidence > 0.5
ORDER BY cm.match_confidence DESC
LIMIT 15
"""
