"""
Database queries for code extraction data operations.
All queries work with the new schema (projects, files, code_blocks, relationships, connections).
"""

# ============================================================================
# TABLE CREATION QUERIES
# ============================================================================

CREATE_PROJECTS_TABLE = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    path TEXT NOT NULL,
    description TEXT DEFAULT '',
    cross_indexing_done BOOLEAN DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, path)
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
    type TEXT NOT NULL, -- import, function, class, variable, interface, enum, export
    name TEXT NOT NULL,
    content TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    start_col INTEGER NOT NULL,
    end_col INTEGER NOT NULL,
    file_id INTEGER NOT NULL, -- ID of the file this block belongs to
    parent_block_id INTEGER, -- ID of the parent block for nested blocks (NULL for top-level blocks)
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_block_id) REFERENCES code_blocks(id) ON DELETE CASCADE
)
"""

CREATE_RELATIONSHIPS_TABLE = """
CREATE TABLE IF NOT EXISTS relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL, -- ID of the source file
    target_id INTEGER NOT NULL, -- ID of the target file
    import_content TEXT NOT NULL, -- The original import statement
    symbols TEXT NOT NULL, -- JSON array of symbols imported
    type TEXT NOT NULL DEFAULT 'import', -- Type of relationship (default: import)
    UNIQUE(source_id, target_id, type)
)
"""

CREATE_INCOMING_CONNECTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS incoming_connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT NOT NULL,
    file_id INTEGER NOT NULL,
    snippet_lines TEXT,
    technology_name TEXT CHECK (technology_name IN ('HTTP/HTTPS','WebSockets','gRPC','GraphQL','MessageQueue','Unknown')),
    code_snippet TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
)
"""

CREATE_OUTGOING_CONNECTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS outgoing_connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT NOT NULL,
    file_id INTEGER NOT NULL,
    snippet_lines TEXT,
    technology_name TEXT CHECK (technology_name IN ('HTTP/HTTPS','WebSockets','gRPC','GraphQL','MessageQueue','Unknown')),
    code_snippet TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
)
"""

CREATE_CONNECTION_MAPPINGS_TABLE = """
CREATE TABLE IF NOT EXISTS connection_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    description TEXT,
    match_confidence REAL DEFAULT 0.0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES outgoing_connections(id) ON DELETE CASCADE,
    FOREIGN KEY (receiver_id) REFERENCES incoming_connections(id) ON DELETE CASCADE,
    UNIQUE(sender_id, receiver_id)
)
"""

CREATE_TABLES = [
    CREATE_PROJECTS_TABLE,
    CREATE_FILES_TABLE,
    CREATE_CODE_BLOCKS_TABLE,
    CREATE_RELATIONSHIPS_TABLE,
    CREATE_INCOMING_CONNECTIONS_TABLE,
    CREATE_OUTGOING_CONNECTIONS_TABLE,
    CREATE_CONNECTION_MAPPINGS_TABLE,
]

# ============================================================================
# INDEX CREATION QUERIES
# ============================================================================

CREATE_INDEXES = [
    # File indexes
    "CREATE INDEX IF NOT EXISTS idx_files_project_id ON files(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_files_language ON files(language)",
    "CREATE INDEX IF NOT EXISTS idx_files_path ON files(file_path)",
    "CREATE INDEX IF NOT EXISTS idx_files_hash ON files(content_hash)",
    # Code block indexes
    "CREATE INDEX IF NOT EXISTS idx_blocks_file_id ON code_blocks(file_id)",
    "CREATE INDEX IF NOT EXISTS idx_blocks_parent_id ON code_blocks(parent_block_id)",
    "CREATE INDEX IF NOT EXISTS idx_blocks_type ON code_blocks(type)",
    "CREATE INDEX IF NOT EXISTS idx_blocks_name ON code_blocks(name)",
    "CREATE INDEX IF NOT EXISTS idx_blocks_lines ON code_blocks(start_line, end_line)",
    # Relationship indexes
    "CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_id)",
    "CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target_id)",
    "CREATE INDEX IF NOT EXISTS idx_relationships_type ON relationships(type)",
    "CREATE INDEX IF NOT EXISTS idx_relationships_source_target ON relationships(source_id, target_id, type)",
    # Incoming connections indexes
    "CREATE INDEX IF NOT EXISTS idx_incoming_connections_file_id ON incoming_connections(file_id)",
    "CREATE INDEX IF NOT EXISTS idx_incoming_connections_technology ON incoming_connections(technology_name)",
    # Outgoing connections indexes
    "CREATE INDEX IF NOT EXISTS idx_outgoing_connections_file_id ON outgoing_connections(file_id)",
    "CREATE INDEX IF NOT EXISTS idx_outgoing_connections_technology ON outgoing_connections(technology_name)",
    # Connection mappings indexes
    "CREATE INDEX IF NOT EXISTS idx_connection_mappings_sender ON connection_mappings(sender_id)",
    "CREATE INDEX IF NOT EXISTS idx_connection_mappings_receiver ON connection_mappings(receiver_id)",
    "CREATE INDEX IF NOT EXISTS idx_connection_mappings_confidence ON connection_mappings(match_confidence)",
]
