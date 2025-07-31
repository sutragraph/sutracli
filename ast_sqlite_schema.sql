-- SQLite Schema for AST Extraction Results with Vector Embeddings
-- Supports sqlite-vec extension for vector operations

-- Enable foreign key constraints
PRAGMA foreign_keys = ON;

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Projects/Repositories table
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    version TEXT DEFAULT '1.0.0'
);

-- Files table
CREATE TABLE files (
    id INTEGER PRIMARY KEY, -- Use the CRC32 ID from JSON
    project_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    language TEXT NOT NULL,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(project_id, file_path)
);

-- Code blocks table
CREATE TABLE code_blocks (
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
);

-- Generic relationships table for extensibility
CREATE TABLE relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL, -- Can be file_id or block_id
    target_id INTEGER NOT NULL, -- Can be file_id or block_id
    type TEXT NOT NULL, -- 'import', 'calls', 'extends', 'implements', 'references', etc.
    UNIQUE(source_id, target_id, type)
);

-- ============================================================================
-- VECTOR EMBEDDINGS TABLES (using sqlite-vec)
-- ============================================================================

-- Code block embeddings (no file embeddings since everything is in blocks)
CREATE TABLE code_block_embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    block_id INTEGER NOT NULL,
    embedding_model TEXT NOT NULL, -- e.g., 'text-embedding-3-small', 'code-embedding-ada-002'
    embedding BLOB NOT NULL, -- Vector stored as BLOB
    FOREIGN KEY (block_id) REFERENCES code_blocks(id) ON DELETE CASCADE,
    UNIQUE(block_id, embedding_model)
);

-- ============================================================================
-- VECTOR SEARCH TABLES (sqlite-vec virtual tables)
-- ============================================================================

-- Virtual table for code block similarity search
CREATE VIRTUAL TABLE block_vectors USING vec0(
    block_id INTEGER PRIMARY KEY,
    embedding FLOAT[1536] -- Adjust dimension based on your embedding model
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- File indexes
CREATE INDEX idx_files_project_id ON files(project_id);
CREATE INDEX idx_files_language ON files(language);
CREATE INDEX idx_files_path ON files(file_path);
CREATE INDEX idx_files_hash ON files(content_hash);

-- Code block indexes
CREATE INDEX idx_blocks_file_id ON code_blocks(file_id);
CREATE INDEX idx_blocks_parent_id ON code_blocks(parent_block_id);
CREATE INDEX idx_blocks_type ON code_blocks(type);
CREATE INDEX idx_blocks_name ON code_blocks(name);
CREATE INDEX idx_blocks_lines ON code_blocks(start_line, end_line);

-- Relationship indexes
CREATE INDEX idx_relationships_source ON relationships(source_id);
CREATE INDEX idx_relationships_target ON relationships(target_id);
CREATE INDEX idx_relationships_type ON relationships(type);
CREATE INDEX idx_relationships_source_target ON relationships(source_id, target_id, type);

-- ============================================================================
-- NOTE: Vector embeddings are handled separately in vector_db.py
-- ============================================================================

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Complete file information with block counts
CREATE VIEW file_summary AS
SELECT
    f.id,
    f.file_path,
    f.language,
    f.content_hash,
    COUNT(cb.id) as total_blocks,
    COUNT(CASE WHEN cb.type = 'function' THEN 1 END) as function_count,
    COUNT(CASE WHEN cb.type = 'class' THEN 1 END) as class_count,
    COUNT(CASE WHEN cb.type = 'import' THEN 1 END) as import_count,
    p.name as project_name,
    p.version as project_version
FROM files f
LEFT JOIN code_blocks cb ON f.id = cb.file_id
JOIN projects p ON f.project_id = p.id
GROUP BY f.id;

-- Hierarchical code blocks view
CREATE VIEW block_hierarchy AS
WITH RECURSIVE block_tree AS (
    -- Root blocks (no parent)
    SELECT
        id, file_id, parent_block_id, type, name, content,
        start_line, end_line, 0 as depth, CAST(name AS TEXT) as path
    FROM code_blocks
    WHERE parent_block_id IS NULL

    UNION ALL

    -- Child blocks
    SELECT
        cb.id, cb.file_id, cb.parent_block_id, cb.type, cb.name, cb.content,
        cb.start_line, cb.end_line, bt.depth + 1, bt.path || ' > ' || cb.name
    FROM code_blocks cb
    JOIN block_tree bt ON cb.parent_block_id = bt.id
)
SELECT * FROM block_tree;

-- Import relationships view
CREATE VIEW import_dependencies AS
SELECT
    sf.file_path as source_file,
    tf.file_path as target_file,
    sf.language as source_language,
    tf.language as target_language,
    r.metadata,
    p.name as project_name
FROM relationships r
JOIN files sf ON r.source_id = sf.id
JOIN files tf ON r.target_id = tf.id
JOIN projects p ON sf.project_id = p.id
WHERE r.type = 'import';
