template_string SutraMemoryPrompt() #"
## SUTRA MEMORY SYSTEM
Use this persistent memory to store info for future iterations, including call chain tracing to finals. Prioritize useful data like task progress, code locations, findings, trace chains to operations (DB, file, net, mem, sys, logic). Store relevant search findings (e.g., code snippets, project connections) incrementally upon discovery to build context before analysis/tracing.

### Format Requirements
Include 'add_history' every response: key findings, but only new progress, findings, or unresolved items (e.g., bugs/symptoms traced, unresolved elements, progress)—do not repeat or restate points; reference them if needed. Structure as actionable log with deltas only.

Use 'tasks' for operations (one current only; move before new current):
- Add pending: { "action": "add", "id": "1", "to_status": "pending", "description": "Analyze auth architecture" }
- Add current: { "action": "add", "id": "2", "to_status": "current", "description": "Review user model" }
- Add completed: { "action": "add", "id": "3", "to_status": "completed", "description": "Project exploration done" }
- Move to complete: { "action": "move", "id": "1", "from_status": "current", "to_status": "completed" }
- Start pending: { "action": "move", "id": "2", "from_status": "pending", "to_status": "current" }
- Pause current: { "action": "move", "id": "1", "from_status": "current", "to_status": "pending" }; then add new current.

Use 'code' for tracing: Incremental actions like add mains, move to traced, add needs. Limit needs <20; trace to finals (e.g., database: cursor.execute(), logic: if/calc). Example from search: { "action": "add", "id": "search_hit_1", "file": "auth.py", "description": "Relevant auth snippet", "needs_tracing": [...] }

Store: Code signatures/locations, trace chains, file paths/lines, patterns/relationships, task dependencies, error patterns, configs, unresolved traces/bugs.
Example: { "action": "add", "id": "1", "needs_tracing": [{ "name": string, "element_type": "method", "reason": string }] }

Practical Guidelines:
Break complex work into specific tasks.
Update history with findings/actions (e.g., 'Bug1 traced to DB').
Clean obsolete tasks/code regularly.
Trace elements (functions, properties, variables, attributes, methods) to finals.

Focus on: Specific task descriptions, query-relevant storage, complete traces.
Prioritize: Exact references, avoiding redundancy.

## Call Chain Tracing Section
Integrate call chain tracing using the 'code' array in sutra_memory: Build exhaustive chains to finals, storing via actions below.

### Actions (Incremental)
Use 'add' for discovery + needs_tracing.
Use 'add_to_needs_tracing' for new during trace.
Use 'move_to_traced' from needs_tracing with source_element_id/element_path.
Use 'update_call_chain_summary' with [✓] progress.
Use 'update_tracing_status' is_traced=true when needs empty (audit all first).

### Hierarchy Rules
1. First traced: element_path = [] (root).
2. Subsequent: element_path = [parent_id] (accessed by parent).
3. Deep: element_path = [grandparent_id, parent_id].

### Usage Clarifications
'id': Code snippet ID (e.g., "1").
'source_element_id': From needs_tracing (e.g., "elem_001") to move. the id of each element will be shown like [ID:elem_001].
'element_path': Array for placement ([] root, ["elem_001"] child).

Remember: IDs for the elements are auto-generated strings not numbers unlike the code snippet IDs.

Correct Examples:
// Root
{ "action": "move_to_traced", "id": "1", "source_element_id": "elem_001", "traced_element": { ... }, "element_path": [] }

// Child
{ "action": "move_to_traced", "id": "1", "source_element_id": "elem_002", "traced_element": { ... }, "element_path": ["elem_001"] }

// Grandchild
{ "action": "move_to_traced", "id": "1", "source_element_id": "elem_003", "traced_element": { ... }, "element_path": ["elem_001", "elem_002"] }

### Workflow: Think 'Element? Internals? New? Update?'
1. Discovery: Add mains is_traced=false; summary '→ elements [NEEDS TRACING]'. Elements: functions (calls), properties (access), variables (assign/use), attributes (ref), methods (ops). Hypothesize related projects/microservices and expand traces across them.
2. Recurse: Per need, tools → trace. Think 'Relevance to query? If low, resolve as final. Process one/iter; cap 10/snippet.' Audit issues; add to needs if found. Mandate: If needs_tracing exists, select tool to resolve one and update status (e.g., 'move_to_traced').
3. Complete: Update status true. Pre-CoT: 'All needs_tracing empty? All at finals? Simulated edges?'

Finals: DB (execute), File (write), Net (post), Mem (set), Sys (now), Logic (if/calc).

Recursive Examples:
Iteration 1: Add 'processTask' function: needs_tracing [{ "name": "external.callA", "element_type": "method" }, { "name": "internal.updateB", "element_type": "function" }]. // Comment: Methods called but implementations not visible; hypothesize related projects like "external-service" and "internal-service".

Iteration 2: Trace payment.charge: Calls external API. Move payment.charge to traced; add_to_needs_tracing [...]. Update summary: 'processOrder → payment.charge[✓] → [EXTERNAL_API]'. Set is_traced=true if no needs_tracing left.

Iteration 3: Trace total: Direct attr [FINAL - Direct Logic]. Move total; no new.

Continue until empty; summary: 'processData → obj.value[✓] + service.getData[✓] + logger.info[✓] → [DIRECT_LOGIC + DATABASE + FILE_IO]'.
"#
