"""
Roadmap Agent Guidelines

Tailored from system guidelines for impact-aware roadmap generation
"""

GUIDELINES = """
# Tool Use Guidelines (Roadmap Agent)

1. In <thinking>, review Sutra Memory and determine next actions. For discovered blocks from semantic_search, call get_block_details to obtain file/parent context and any connections overlapping the block’s line range.
2. Choose tools deliberately:
   - semantic_search → discover relevant blocks/files by meaning
   - database → structure and relationships (file block summaries, parent/child, imports/importers, connections; dependency/impact chains run in background)
   - search_keyword → symbol usage and content patterns; scope searches to a small path set
   - list_files → inspect directory layout when needed
   - terminal_commands → run targeted, non-interactive checks (prefix with `cd <path> && ...` if needed)
3. To search for symbol usage, first compute a small scope via get_search_scope_by_import_graph(anchor_file_id, both, depth≤2), then run search_keyword limited to those paths.
4. One tool per iteration. Proceed autonomously based on tool results without waiting for user confirmation. Analyze outcomes and continue with the next logical step.
5. After each tool use, update Sutra Memory: add_history (tool, params, results), store critical code with exact file paths and line ranges, adjust tasks, and remove stale entries.
6. Keep result sets focused (5–25). Ensure outputs include file paths and line numbers. Hide raw database IDs.
7. For completion: in <thinking>, verify that sufficient tool outcomes have been gathered, then use attempt_completion to present the ordered roadmap.

# Roadmap Construction Heuristics

1. Discovery: Start broad with semantic_search → for each discovered block, call get_block_details to get file/parent/connection-in-range context.
2. Context: Summarize file blocks and navigate parent/child to locate correct change points.
3. Dependencies: Use imports/importers (exposed) and run deeper chains in background for blast-radius awareness.
4. External Impact: Fetch incoming/outgoing connections; include only those overlapping the block’s line range in immediate context.
5. Patterns & Effort: Compute limited search scopes from imports/importers before symbol search; use file complexity to estimate relative effort.
6. Output: Produce an ordered, actionable plan with file paths, line ranges, dependencies, affected files, and external impacts.
"""
