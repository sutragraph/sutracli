## Roadmap Agent Database API (Agent-Exposed Wrappers)

This document defines the wrapper functions exposed to the Roadmap Agent and the underlying queries/tools they compose. The goal is to provide small, context-rich, and action-oriented results. Where multiple data sources are required, wrappers combine them and return a unified schema.

### Design principles

- Agent-first: return 5–25 results, include `file_path`, `project_name`, `language`, and line ranges; hide raw internal IDs.
- Bridge discovery→data: background wrappers convert embedding IDs to concrete blocks/files.
- Unified shapes: consistent fields across related endpoints; add computed `path` for dependency chains.
- Clear boundaries: callers/callees/symbol usage come from the search tool; structural/dependency/context data comes from the database tool.

---

### Background (auto-conversion)

These are not directly exposed to the agent UI, but are always used to transform discovery results and enrich responses.

1. resolve_block(block_id)

- Purpose: Convert an embedding-derived block reference to full details
- Uses: GET_CODE_BLOCK_BY_ID
- Returns: { id, type, name, content, start_line, end_line, parent_block_id, file_id, file_path, language, project_name, project_id }

2. resolve_file(file_id)

- Purpose: Convert a file reference to file metadata and block count
- Uses: GET_FILE_BY_ID
- Returns: { id, file_path, language, content, content_hash, project_name, project_id, block_count }

3. get_implementation_context(file_id)

- Purpose: Lightweight structure view for a file (ordered by lines)
- Uses: GET_IMPLEMENTATION_CONTEXT
- Returns: [ { id, type, name, start_line, end_line, parent_name, parent_type, file_path, language } ]

4. get_file_complexity(file_id)

- Purpose: Complexity metrics that inform effort estimates
- Uses: GET_FILE_COMPLEXITY_SCORE
- Returns: { file_path, language, total_blocks, function_count, class_count, dependency_count }

5. get_connections_overlapping_range(file_id, start_line, end_line)

- Purpose: Fetch incoming/outgoing connections whose snippet_lines overlap the given line range
- Uses: GET_EXTERNAL_CONNECTIONS + range filtering
- Returns: [ { direction: "incoming"|"outgoing", description, technology_name, snippet_lines } ]

---

### Discovery & Context (Agent-facing, minimal)

Agent-facing wrappers for immediate context expansion around discovered code.

5. get_file_block_summary(file_id)

- Purpose: Overview of classes/functions in a file (no content)
- Uses: GET_FILE_BLOCK_SUMMARY
- Returns: [ { id, type, name, start_line, end_line, parent_block_id } ]

6. get_block_children(block_id)

- Purpose: Methods/nested blocks of a parent
- Uses: GET_CHILD_BLOCKS
- Returns: [ { id, type, name, start_line, end_line } ]

7. get_block_details(block_id)

- Purpose: Single-call enrichment for discovered blocks
- Uses: resolve_block + GET_PARENT_BLOCK (internal) + get_connections_overlapping_range
- Returns: {
  id, type, name,
  file_path, language,
  start_line, end_line, start_col, end_col,
  parent: { id, type, name, start_line, end_line, file_path } | null,
  connections_in_range: [ { direction, description, technology_name, snippet_lines } ]
  }

8. get_block_hierarchy_path(block_id) [optional]

- Purpose: Full nesting path (root → target)
- Uses: composed from repeated GET_PARENT_BLOCK
- Returns: [ { id, type, name, start_line, end_line } ] (ordered root→leaf)

9. get_blocks_by_type_in_file(file_id, type) [optional]

- Purpose: Retrieve all blocks of a given type in a file
- Uses: filtered GET_FILE_BLOCK_SUMMARY
- Returns: [ { id, name, start_line, end_line, parent_block_id } ]

Deprecated/Removed (covered by get_block_details or low value):

- get_block_parent(block_id) — covered by get_block_details
- get_blocks_at_line(file_id, line_number) — removed

11. get_block_details(block_id)

- Purpose: Single-call enrichment for discovered blocks
- Uses: resolve_block + get_block_parent + get_connections_overlapping_range
- Returns: {
  id, type, name,
  file_path, language,
  start_line, end_line, start_col, end_col,
  parent: { id, type, name, start_line, end_line } | null,
  connections_in_range: [ { direction, description, technology_name, snippet_lines } ]
  }

---

### Dependency & Impact (background by default)

11. get_imports(file_id)

- Purpose: What this file imports
- Uses: GET_FILE_IMPORTS
- Returns: [ { import_content, file_path, language, project_name } ]

12. get_importers(file_id)

- Purpose: Who imports this file
- Uses: GET_FILE_IMPACT_SCOPE (filtered where relationship_type = importer)
- Returns: [ { file_path, language, project_name, import_content } ]

13. get_file_impact_scope(file_id)

- Purpose: Importers + dependencies in one view
- Uses: GET_FILE_IMPACT_SCOPE
- Returns: [ { relationship_type: "importer"|"dependency", file_path, language, project_name, import_content } ]

14. get_dependency_chain(file_id, depth=5)

- Purpose: Multi-hop dependency path
- Uses: GET_DEPENDENCY_CHAIN
- Post-processing: add human-readable `path` ("A → B → C")
- Returns: [ { file_id, file_path, target_id, target_path, depth, path } ]

15. get_files_using_symbol(symbol_pattern, paths=None)

- Purpose: Usage sites across the codebase
- Uses: search tool (search_keyword). If `paths` provided, search only those; otherwise caller should compute a scope first.
- Returns: [ { file_path, line, snippet } ]

16. get_search_scope_by_import_graph(anchor_file_id, direction="both", max_depth=2)

- Purpose: Compute a small set of file paths likely impacted based on imports/importers
- Uses: GET_FILE_IMPACT_SCOPE + consolidation
- Returns: { anchor_file_path, paths: [file_path, ...] }

---

### Cross-Project Connections

Surfacing external systems effects for impact-aware planning.

16. get_external_connections(file_id)

- Purpose: Incoming/outgoing integrations for a file
- Uses: GET_EXTERNAL_CONNECTIONS
- Returns: [ { direction: "incoming"|"outgoing", description, technology_name, snippet_lines } ]

17. get_project_external_connections(project_id)

- Purpose: All external integrations in a project
- Uses: GET_PROJECT_EXTERNAL_CONNECTIONS
- Returns: [ { file_path, language, technology, description, direction } ]

18. get_connection_impact(file_id) [background]

- Purpose: High-confidence mapped connections to/from this file
- Uses: GET_CONNECTION_IMPACT
- Returns: [ { connection_type, description, match_confidence, impact_type: "receives_from"|"sends_to", other_file, technology } ]

---

### Pattern Guidance

Find related implementations and patterns to guide changes.

19. find_similar_implementations(name_pattern, kind)

- Purpose: Similar function/class names for reference
- Uses: search tool (search_keyword)
- Returns: [ { file_path, line, preview, match_score } ]

20. find_files_with_pattern(pattern)

- Purpose: Content pattern matches across files
- Uses: search tool (search_keyword)
- Returns: [ { file_path, match_count } ]

---

### Bridge for Discovery → Data

Used immediately after semantic discovery results.

21. resolve_embedding_nodes(embedding_results)

- Purpose: Convert discovered `block_#` / `file_#` to concrete records
- Uses: resolve_block / resolve_file per ID prefix
- Returns: unified list of blocks/files with full context

---

### Legacy Compatibility Mapping (to be removed over time)

These wrappers keep old names working while delegating to the new API.

- get_nodes_by_exact_name(name) → find_files_with_pattern / search by exact symbol
- get_nodes_by_name_like(pattern) → find_similar_implementations
- get_nodes_by_keyword_search(pattern) → find_files_with_pattern
- get_function_callers(name) → get_files_using_symbol(f"{name}(")
- get_function_callees(block_id) → search within resolved block/file context using search tool
- get_file_dependencies(file_id) → get_imports(file_id)

---

### Result shape conventions

- Always include `file_path`, `project_name` (when applicable), `language`, and line ranges for navigation.
- Cap results to 15–25 items by default.
- Hide raw internal IDs in agent-facing responses (may be present during background resolution).

---

### Roadmap generation flow (wrappers used)

1. resolve_embedding_nodes → get_file_block_summary / get_block_parent / get_block_children
2. get_imports / get_importers / get_dependency_chain
3. get_external_connections / get_project_external_connections / get_connection_impact
4. find_similar_implementations / find_files_with_pattern / get_file_complexity
5. Produce ordered plan with files, line ranges, dependencies, and external impacts
