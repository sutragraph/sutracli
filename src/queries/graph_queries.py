"""
Graph Database Queries for Cross-Index Service
Contains all SQL queries used by the cross-indexing service for connection management.
"""

# ============================================================================
# CONNECTION RETRIEVAL QUERIES
# ============================================================================

GET_EXISTING_INCOMING_CONNECTIONS = """
SELECT ic.id,
       ic.description,
       files.id AS file_id,
       files.file_path,
       files.language,
       p.name AS project_name,
       p.id AS project_id
FROM incoming_connections ic
LEFT JOIN files ON ic.file_id = files.id
LEFT JOIN projects p ON files.project_id = p.id
ORDER BY ic.created_at DESC
"""

GET_EXISTING_OUTGOING_CONNECTIONS = """
SELECT oc.id,
       oc.description,
       files.id AS file_id,
       files.file_path,
       files.language,
       p.name AS project_name,
       p.id AS project_id
FROM outgoing_connections oc
LEFT JOIN files ON oc.file_id = files.id
LEFT JOIN projects p ON files.project_id = p.id
ORDER BY oc.created_at DESC
"""

GET_CONNECTIONS_BY_IDS = """
SELECT c.id, c.description, c.technology_name, c.code_snippet,
       files.file_path, files.language, p.name as project_name
FROM {table_name} c
LEFT JOIN files ON c.file_id = files.id
LEFT JOIN projects p ON files.project_id = p.id
WHERE c.id IN ({placeholders})
"""

# ============================================================================
# CONNECTION INSERTION QUERIES
# ============================================================================

INSERT_INCOMING_CONNECTION = """
INSERT INTO incoming_connections
(description, file_id, start_line, end_line, technology_name, code_snippet)
VALUES (?, ?, ?, ?, ?, ?)
"""

INSERT_OUTGOING_CONNECTION = """
INSERT INTO outgoing_connections
(description, file_id, start_line, end_line, technology_name, code_snippet)
VALUES (?, ?, ?, ?, ?, ?)
"""

INSERT_CONNECTION_MAPPING = """
INSERT OR IGNORE INTO connection_mappings (sender_id, receiver_id, description, match_confidence)
VALUES (?, ?, ?, ?)
"""

# ============================================================================
# PROJECT UPDATE QUERIES
# ============================================================================

UPDATE_PROJECT_DESCRIPTION = """
UPDATE projects SET description = ? WHERE id = ?
"""

GET_PROJECT_DESCRIPTION = """
SELECT description FROM projects WHERE id = ?
"""


# ============================================================================
# CROSS-INEDING QUERIES
# ============================================================================

GET_ALL_CHECKPOINTS = """
SELECT id, project_id, file_path, change_type, old_code, new_code, updated_at
FROM checkpoints
ORDER BY updated_at DESC
"""

INSERT_CHECKPOINT = """
INSERT OR REPLACE INTO checkpoints
(project_id, file_path, change_type, old_code, new_code, updated_at)
VALUES (?, ?, ?, ?, ?, ?)
"""

DELETE_ALL_CHECKPOINTS = """
DELETE FROM checkpoints
"""

DELETE_CHECKPOINTS_BY_IDS = """
DELETE FROM checkpoints WHERE id IN ({placeholders})
"""

GET_CONNECTIONS_BY_FILE_ID = """
SELECT c.id, c.description, c.start_line, c.end_line, c.technology_name, c.code_snippet, c.created_at,
       f.file_path
FROM {table_name} c
LEFT JOIN files f ON c.file_id = f.id
WHERE c.file_id = ?
ORDER BY c.start_line
"""

UPDATE_CONNECTION_LINES = """
UPDATE {table_name}
SET start_line = ?, end_line = ?
WHERE id = ?
"""

UPDATE_CONNECTION_CODE_AND_LINES = """
UPDATE {table_name}
SET code_snippet = ?, start_line = ?, end_line = ?
WHERE id = ?
"""
