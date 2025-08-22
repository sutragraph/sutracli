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
(description, file_id, snippet_lines, technology_name, code_snippet)
VALUES (?, ?, ?, ?, ?)
"""

INSERT_OUTGOING_CONNECTION = """
INSERT INTO outgoing_connections
(description, file_id, snippet_lines, technology_name, code_snippet)
VALUES (?, ?, ?, ?, ?)
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
