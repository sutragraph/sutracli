"""
Database queries for code extraction data operations.
All queries work with the new schema (projects, files, code_blocks, relationships).
"""

# ============================================================================
# TABLE CREATION QUERIES
# ============================================================================

CREATE_PROJECTS_TABLE = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    version TEXT DEFAULT '1.0.0'
)
"""

CREATE_FILES_TABLE = """
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY, -- Use the CRC32 ID from JSON
    project_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    language TEXT NOT NULL,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(project_id, file_path)
)
"""

CREATE_CODE_BLOCKS_TABLE = """
CREATE TABLE IF NOT EXISTS code_blocks (
    id INTEGER PRIMARY KEY, -- Use the incremental ID from JSON
    file_id INTEGER NOT NULL,
    parent_block_id INTEGER NULL, -- For actual hierarchy (class->method)
    type TEXT NOT NULL, -- import, function, class, variable, interface, enum, export
    name TEXT NOT NULL,
    content TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    start_col INTEGER NOT NULL,
    end_col INTEGER NOT NULL,
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_block_id) REFERENCES code_blocks(id) ON DELETE CASCADE
)
"""

CREATE_RELATIONSHIPS_TABLE = """
CREATE TABLE IF NOT EXISTS relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL, -- Can be file_id or block_id
    target_id INTEGER NOT NULL, -- Can be file_id or block_id  
    type TEXT NOT NULL, -- 'import', 'calls', 'extends', 'implements', 'references', etc.
    metadata TEXT, -- JSON string for additional relationship data
    UNIQUE(source_id, target_id, type)
)
"""

# ============================================================================
# INDEX CREATION QUERIES
# ============================================================================

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_files_project_id ON files(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_files_language ON files(language)",
    "CREATE INDEX IF NOT EXISTS idx_files_path ON files(file_path)",
    "CREATE INDEX IF NOT EXISTS idx_files_hash ON files(content_hash)",
    "CREATE INDEX IF NOT EXISTS idx_blocks_file_id ON code_blocks(file_id)",
    "CREATE INDEX IF NOT EXISTS idx_blocks_parent_id ON code_blocks(parent_block_id)",
    "CREATE INDEX IF NOT EXISTS idx_blocks_type ON code_blocks(type)",
    "CREATE INDEX IF NOT EXISTS idx_blocks_name ON code_blocks(name)",
    "CREATE INDEX IF NOT EXISTS idx_blocks_lines ON code_blocks(start_line, end_line)",
    "CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_id)",
    "CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target_id)",
    "CREATE INDEX IF NOT EXISTS idx_relationships_type ON relationships(type)",
    "CREATE INDEX IF NOT EXISTS idx_relationships_source_target ON relationships(source_id, target_id, type)",
]

# ============================================================================
# INSERT QUERIES
# ============================================================================

INSERT_PROJECT = """
INSERT OR REPLACE INTO projects (name, version)
VALUES (?, ?)
"""

INSERT_FILE = """
INSERT OR REPLACE INTO files 
(id, project_id, file_path, language, content, content_hash)
VALUES (?, ?, ?, ?, ?, ?)
"""

INSERT_CODE_BLOCK = """
INSERT OR REPLACE INTO code_blocks 
(id, file_id, parent_block_id, type, name, content, start_line, end_line, start_col, end_col)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

INSERT_RELATIONSHIP = """
INSERT OR REPLACE INTO relationships 
(source_id, target_id, type, metadata)
VALUES (?, ?, ?, ?)
"""

# ============================================================================
# SELECT QUERIES
# ============================================================================

# Project queries
GET_ALL_PROJECTS = """
SELECT name, version
FROM projects
ORDER BY name
"""

# File queries
GET_FILE_BY_PATH = """
SELECT id, project_id, file_path, language, content, content_hash
FROM files
WHERE project_id = ? AND file_path = ?
"""

# Code block queries
GET_BLOCKS_BY_FILE = """
SELECT cb.id, cb.type, cb.name, cb.content, cb.start_line, cb.end_line,
       cb.start_col, cb.end_col, cb.parent_block_id, f.file_path, f.language
FROM code_blocks cb
JOIN files f ON cb.file_id = f.id
WHERE f.file_path = ? AND f.project_id = ?
ORDER BY cb.start_line
"""

# ============================================================================
# COUNT QUERIES
# ============================================================================

GET_PROJECT_BLOCK_COUNT = """
SELECT COUNT(*) as count
FROM code_blocks cb
JOIN files f ON cb.file_id = f.id
WHERE f.project_id = ?
"""

# ============================================================================
# DELETE QUERIES
# ============================================================================

DELETE_PROJECT_RELATIONSHIPS = """
DELETE FROM relationships
WHERE source_id IN (SELECT id FROM files WHERE project_id = ?)
   OR target_id IN (SELECT id FROM files WHERE project_id = ?)
"""

DELETE_PROJECT_BLOCKS = """
DELETE FROM code_blocks
WHERE file_id IN (SELECT id FROM files WHERE project_id = ?)
"""

DELETE_PROJECT_FILES = """
DELETE FROM files WHERE project_id = ?
"""

# ============================================================================
# STATISTICS QUERIES
# ============================================================================

GET_BLOCK_STATS_BY_TYPE = """
SELECT type, COUNT(*) as count
FROM code_blocks
GROUP BY type
ORDER BY count DESC
"""

GET_RELATIONSHIP_STATS_BY_TYPE = """
SELECT type, COUNT(*) as count
FROM relationships
GROUP BY type
ORDER BY count DESC
"""

GET_FILES_BY_LANGUAGE = """
SELECT language, COUNT(*) as count
FROM files
GROUP BY language
ORDER BY count DESC
"""

GET_FILES_BY_PROJECT = """
SELECT p.name as project_name, COUNT(f.id) as count
FROM projects p
LEFT JOIN files f ON p.id = f.project_id
GROUP BY p.id, p.name
ORDER BY count DESC
"""
