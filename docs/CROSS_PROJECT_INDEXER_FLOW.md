# Cross Project Indexer - Flow & Logic Overview

## Document Purpose
This document provides a comprehensive overview of how the `CrossProjectIndexer` class works, including its architecture, data flow, and key decision-making logic.

---

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Core Flow Diagram](#core-flow-diagram)
3. [Key Components](#key-components)
4. [Detailed Process Flows](#detailed-process-flows)
5. [Data Structures](#data-structures)
6. [Error Handling](#error-handling)
7. [Performance Considerations](#performance-considerations)

---

## Architecture Overview

### Purpose
The `CrossProjectIndexer` is designed to handle **incremental cross-indexing** of code projects. Instead of re-indexing everything from scratch, it:
- Tracks changes to files since the last indexing run
- Updates only affected code connections
- Maintains database consistency
- Processes changes in batches to handle large codebases efficiently

### Key Design Principles

1. **Lazy Initialization**: Components are initialized only when needed
2. **Checkpoint-Based Tracking**: Maintains state between runs to identify incremental changes
3. **Phase 4 Focus**: Skips phases 1-3 (package discovery, import discovery, implementation discovery) and focuses on Phase 4 (Data Splitting) and Phase 5 (Connection Matching)
4. **Batching**: Processes large files/changes in configurable batch sizes
5. **Database-First**: All state is persisted in SQLite for reliability

---

## Core Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   run_incremental_cross_indexing()                      │
│                         [Entry Point]                                    │
└────────────┬──────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  1. LOAD CHECKPOINT                                                     │
│  └─ Retrieve all pending file changes from SQLite database              │
└────────────┬──────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  2. CREATE DIFF                                                         │
│  └─ Transform checkpoint into normalized diff structure                 │
│     (added, modified, deleted files)                                    │
└────────────┬──────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  3. DISPLAY SUMMARY                                                     │
│  └─ Show user: files affected, lines added/removed/modified             │
└────────────┬──────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  4. PROCESS INCREMENTAL CHANGES                                         │
│  └─ Group files by project_id                                           │
│  └─ For each project:                                                   │
│     ├─ Process modified files (update connections, collect snippets)    │
│     ├─ Process added files (collect for Phase 4)                        │
│     ├─ Handle deleted files                                             │
│     └─ Run Phase 4 in batches                                           │
└────────────┬──────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  5. RUN PHASE 5 (Connection Matching)                                   │
│  └─ Match connections across all modified projects                      │
└────────────┬──────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  6. RESET CHECKPOINT                                                    │
│  └─ Delete processed checkpoint entries from database                   │
└────────────┬──────────────────────────────────────────────────────────────┘
             │
             ▼
         SUCCESS ✓
```

---

## Key Components

### 1. **CrossProjectIndexer Class**
Main orchestrator class managing the entire incremental indexing workflow.

**Dependencies:**
- `SQLiteConnection`: Database access
- `CrossIndexing`: Phase 4 and Phase 5 execution
- `CrossIndexingTaskManager`: Manages code snippet batches
- `SessionManager`: Session state management
- `GraphOperations`: File and connection database operations

### 2. **Checkpoint System**
Stores pending file changes between indexing runs.

**Checkpoint Structure:**
```python
{
    "version": "1.0",
    "timestamp": "ISO-8601 timestamp",
    "changes": {
        "project_id:file_path": {
            "change_type": "added|modified|deleted",
            "old_code": "string (if applicable)",
            "new_code": "string (if applicable)"
        },
        ...
    },
    "checkpoint_ids": [1, 2, 3, ...],  # DB row IDs for selective deletion
    "metadata": {
        "total_changes": int,
        "created_by": "sutra_cli_incremental_cross_indexing",
        "last_updated": "ISO-8601 timestamp"
    }
}
```

### 3. **Diff Structure**
Normalized representation of changes, organized by type.

```python
{
    "added": {
        "project_id:file_path": {
            "change_type": "added",
            "current_content": "new file content"
        },
        ...
    },
    "modified": {
        "project_id:file_path": {
            "change_type": "modified",
            "baseline_content": "old content",
            "current_content": "new content"
        },
        ...
    },
    "deleted": {
        "project_id:file_path": {
            "change_type": "deleted",
            "baseline_content": "old content"
        },
        ...
    },
    "accumulated_changes": {...}  # Raw checkpoint changes
}
```

---

## Detailed Process Flows

### Flow 1: Loading Checkpoint
**Method:** `_load_cross_indexing_checkpoint()`

```
Load all checkpoint records from database
    ↓
For each checkpoint record:
    ├─ Extract project_id and file_path
    ├─ Build file_key as "project_id:file_path"
    ├─ Track change type and code snippets
    ├─ Track latest timestamp
    └─ Collect checkpoint row IDs for later deletion
    ↓
Build checkpoint data structure
    ├─ Set version, timestamp, metadata
    ├─ Include all changes and checkpoint_ids
    └─ Return checkpoint data
```

**Why Checkpoint IDs Matter:** The `checkpoint_ids` list allows selective deletion—only processed checkpoints are removed, so if indexing fails mid-process, unprocessed changes remain for the next run.

---

### Flow 2: Processing Modified Files
**Method:** `_process_modified_files(modified_files)`

This is the most complex flow, handling existing connections that may be affected by file changes.

```
For each modified file:
    │
    ├─1. Retrieve existing connections from database
    │   (incoming_connections + outgoing_connections)
    │
    ├─2. Parse diff using line mapping
    │   └─ Create: line_mapping (old_line → new_line or None)
    │   └─ Track: added_lines, removed_lines, replaced_ranges
    │
    ├─3. UPDATE CONNECTIONS (using _update_connections_after_file_changes)
    │   │
    │   └─ For each connection:
    │       │
    │       ├─A. Check for REPLACEMENT OVERLAPS
    │       │   (uses ADJACENCY_THRESHOLD = 3 lines)
    │       │
    │       ├─ CASE 1: Replacement completely covers connection
    │       │   └─ Mark for deletion with splitting_range
    │       │   └─ Will be re-analyzed in Phase 4
    │       │
    │       ├─ CASE 2: Replacement extends beyond connection
    │       │   └─ Mark for deletion with extended range
    │       │   └─ Include adjacent added lines
    │       │   └─ Will be re-analyzed in Phase 4
    │       │
    │       ├─ CASE 3: Connection contains replacement
    │       │   └─ Mark for resplitting (internal code change)
    │       │   └─ Delete and re-analyze in Phase 4
    │       │
    │       └─B. NO OVERLAPS: Use line mapping
    │           ├─ Find first valid mapped line (new_start)
    │           ├─ Find last valid mapped line (new_end)
    │           ├─ If both found:
    │           │   ├─ Update line numbers
    │           │   ├─ Update code snippet
    │           │   └─ Check if code content changed
    │           │   └─ If changed: mark for resplitting
    │           └─ If not found: connection was deleted
    │
    ├─4. DATABASE UPDATES
    │   ├─ Update connections with code + line changes
    │   ├─ Update connections with line-only changes
    │   └─ Delete completely removed connections
    │
    ├─5. PREPARE FOR PHASE 4
    │   ├─ Connections marked for resplitting
    │   └─ New lines added outside existing connections
    │
    └─6. Return list of snippets for Phase 4 processing
```

**Key Decision Points:**
- **Replacement Detection**: Uses `difflib.SequenceMatcher` to identify "replace" operations
- **Adjacency Threshold**: 3 lines—replacements within 3 lines are considered part of same change
- **Code Content vs Line Numbers**: Only resplit if code actually changed, not just line numbers

---

### Flow 3: Line Mapping in Detail
**Method:** `_parse_diff_lines(old_content, new_content)`

This creates the crucial mapping between old and new line numbers.

```
Use difflib.SequenceMatcher to compare old vs new lines
    ↓
For each opcode (tag, i1, i2, j1, j2):
    │
    ├─ "equal": Lines unchanged
    │   └─ Create 1:1 mapping: old_line[n] → new_line[n]
    │
    ├─ "delete": Lines only in old
    │   └─ Map to None: old_line[n] → None (deleted)
    │   └─ Track in removed_lines
    │
    ├─ "insert": Lines only in new
    │   └─ Track in added_lines (for Phase 4)
    │
    └─ "replace": Complete replacement
        ├─ Map old lines to None
        ├─ Track removed_lines
        ├─ Record replacement ranges (old_start, old_end, new_start, new_end)
        └─ DO NOT add replacement lines to added_lines
           (they're handled by resplitting logic)
    ↓
Return:
{
    "line_mapping": {old_line: new_line | None, ...},
    "added": [line_numbers in new file],
    "removed": [line_numbers in old file],
    "replaced_ranges": [(old_start, old_end, new_start, new_end), ...]
}
```

**Example:**
```
Old: Line 1: def foo():
     Line 2:     return x
     Line 3: def bar():

New: Line 1: def foo():
     Line 2:     return x + 1    # Modified
     Line 3:     return y
     Line 4: def bar():

Diff Result:
- "equal": Lines 1-1 map 1→1 (line 1 unchanged)
- "replace": Lines 2-2 replace 2→3 (line 2 is replaced with lines 2-3)
- "equal": Lines 3-3 map 4→4 (line 3 moves to line 4)
```

---

### Flow 4: Batch Processing & Phase 4
**Method:** `_run_phase_4_in_batches(project_id, modified_snippet_infos, new_file_infos)`

Respects configuration limits on lines per batch.

```
Get max_lines from CROSS_INDEXING_CONFIG (phase4_max_lines_per_batch)
    ↓
Combine modified snippets + new file snippets
    ↓
Create batches respecting line limit:
    │
    ├─ current_batch = []
    ├─ current_batch_lines = 0
    │
    └─ For each snippet:
        ├─ If (current_batch_lines + snippet.line_count) > max_lines:
        │   ├─ Save current_batch to batches
        │   └─ Start new batch
        └─ Add snippet to current_batch
    ↓
For each batch:
    ├─ Add all batch items to task_manager
    │   └─ _task_manager.add_code_snippet(...)
    │
    └─ Execute Phase 4:
        ├─ Get formatted code snippets context
        ├─ Include project description for context
        ├─ Run connection_splitting (BAML analysis)
        ├─ Store resulting connections in database
        └─ Clear task_manager for next batch
```

---

### Flow 5: Connection Resplitting
**Key Concept:** When code changes significantly, connections must be re-analyzed.

```
OLD CONNECTION:
┌─ File: auth.py
├─ Lines: 50-65
├─ Description: "Validates user credentials"
└─ Code: [old implementation]

CODE MODIFICATION at lines 52-54:
└─ Adds error handling logic
└─ Code now spans lines 50-72

RESPLITTING PROCESS:
├─ Delete old connection (lines 50-65)
├─ Prepare snippet with:
│  ├─ New line range: 50-72
│  ├─ Old description: "Validates user credentials"
│  └─ New code: [modified implementation]
└─ Submit to Phase 4 (BAML analysis)
    └─ BAML re-analyzes and provides:
       ├─ Updated description
       ├─ New connection boundaries if split
       └─ Stores in database
```

---

## Data Structures

### Connection Structure (from database)
```python
{
    "id": int,                    # Unique connection ID
    "direction": "incoming|outgoing",
    "start_line": int,
    "end_line": int,
    "code_snippet": str,
    "description": str,
    "needs_db_update": bool,      # Flag for database update
    "needs_code_update": bool,    # Flag if code snippet changed
    "is_deleted": bool,           # Flag for deletion
    "needs_resplitting": bool,    # Flag for Phase 4 re-analysis
    "old_description": str        # Previous description for context
}
```

### Snippet Info (for Phase 4 batching)
```python
{
    "file_path": str,
    "start_line": int,
    "end_line": int,
    "line_count": int,            # For batch calculation
    "description": str            # Old description for context (if resplitting)
}
```

### Diff Data from Line Parsing
```python
{
    "line_mapping": dict,         # old_line → new_line | None
    "added": list,                # New line numbers
    "removed": list,              # Deleted line numbers
    "replaced_ranges": list       # [(old_start, old_end, new_start, new_end), ...]
}
```

---

## Error Handling

### Strategy: Fail-Safe with Persistence

1. **Checkpoint Preservation**: Failed runs don't clear checkpoints
   - Only processed checkpoint IDs are deleted on success
   - Failed runs leave data for retry

2. **Database Rollback**: Transaction rollback on error
   ```python
   try:
       # Database operations
   except Exception:
       self.connection.connection.rollback()
       raise
   ```

3. **Logging**: Comprehensive debug logging
   - Line-by-line connection updates tracked
   - Diff analysis details logged
   - Phase 4 execution logged

4. **Graceful Degradation**:
   - Missing files logged but don't stop processing
   - Missing connections don't block entire project
   - Failed Phase 4 batches logged but continue

---

## Performance Considerations

### 1. **Batch Size Configuration**
```python
CROSS_INDEXING_CONFIG["phase4_max_lines_per_batch"]
```
- Default: Configurable (typically 5000-10000 lines)
- Larger batches: Fewer Phase 4 calls but more LLM tokens
- Smaller batches: More calls but lower cost per call

### 2. **Line Mapping Efficiency**
- Uses `difflib.SequenceMatcher` (Python standard library)
- Linear time complexity O(n) for diff analysis
- Minimal memory overhead

### 3. **Database Optimization**
- Batch commits instead of individual commits
- Selective checkpoint deletion (not all-or-nothing)
- Indexed queries on file_id and connection_id

### 4. **Scaling for Large Projects**
- Files split into chunks if > max_lines
- Batching prevents overwhelming Phase 4 (BAML analysis)
- Supports multiple projects in single run

### 5. **Memory Management**
- Lazy initialization of components
- Code snippets cleared after Phase 4 batch processed
- No loading of entire project into memory

---

## Summary Workflow

### Successful Run:
```
1. Load checkpoint from DB
2. Create normalized diff
3. Display summary to user
4. For each project:
   a. Process modified files (update connections)
   b. Process new files (collect for Phase 4)
   c. Run Phase 4 in batches (analyze code)
5. Run Phase 5 (match connections across projects)
6. Delete processed checkpoints from DB
7. Report success
```

### On Error:
```
1. Catch exception
2. Rollback any in-flight database transaction
3. Log error details
4. Leave checkpoint data untouched (for retry)
5. Report failure to user
```

---

## Key Methods Reference

| Method | Purpose | Input | Output |
|--------|---------|-------|--------|
| `run_incremental_cross_indexing()` | Main entry point | None | None (side effects) |
| `_load_cross_indexing_checkpoint()` | Fetch pending changes | None | Checkpoint dict |
| `_create_diff_from_checkpoint()` | Normalize checkpoint | Checkpoint | Diff structure |
| `_process_incremental_cross_indexing()` | Main processing | Diff | Success bool |
| `_group_files_by_project()` | Organize changes | Diff | Dict[project_id] |
| `_process_modified_files()` | Handle modified files | File dict | Snippet infos list |
| `_parse_diff_lines()` | Create line mapping | Old/new content | Diff data dict |
| `_update_connections_after_file_changes()` | Update connections | Connections + diff | Updated connections + resplit list |
| `_run_phase_4_in_batches()` | Execute analysis | Snippets + file infos | None (stores in DB) |
| `_save_cross_indexing_checkpoint_reset_baseline()` | Clean up | Checkpoint IDs | Success bool |

---

## Conclusion

The `CrossProjectIndexer` implements a sophisticated incremental indexing system that:
- ✅ Tracks changes between runs via checkpoints
- ✅ Intelligently updates affected connections
- ✅ Detects when connections need re-analysis (resplitting)
- ✅ Processes large codebases efficiently via batching
- ✅ Maintains database consistency with proper transaction handling
- ✅ Provides comprehensive logging for debugging

This enables efficient, scalable cross-project indexing for large codebases without re-processing unchanged code.
