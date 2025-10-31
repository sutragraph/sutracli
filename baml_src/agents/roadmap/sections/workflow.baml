template_string RoadmapWorkflow() #"
## WORKFLOW

### Phase 1: Project Discovery & Architecture Mapping
- Perform wide semantic_search across hypothesized related projects (starting with the [CURRENT] one) to identify logic, capturing multiple relevant snippets. If any relevant findings (e.g., code, connections), store immediately in sutra_memory.
- Map complete communication flow: Search existing patterns (e.g., API calls, queues) via search_keyword, iterating on multiple hits across related projects. Identify paths like A → B → C. (`add_to_history` if needed)
- Tool Status often include mapped connections between projects, use them.

### Phase 2: Code Analysis
1. Discover patterns & reuse: Search existing before new (e.g., for API, search_keyword 'axios'). Process multiple results; store relevant snippets/connections in memory. Avoid fixation: If one snippet found, search wider for alternatives. Example Reuse: 'Exists: httpClient.js; Reusable: Yes, add auth param; Mod: Line 45: if(req.auth) {...}'.
2. Connection-driven hopping: Trace flows across projects (e.g., if call to Y.service, GET_FILE_BY_PATH Y/service.py:10-20 → trace internals). Analyze both sides fully, storing intermediates.
3. Dependencies: Check files/imports first; match existing.
4. Prefix rule: Search constants for domains (e.g., 'API_BASE'); use them in changes.

### Phase 3: Impact Assessment & Change Planning
Before changes, for each project, suggest the minimal necessary changes. Don't overcomplicate. Use existing code where possible.
```
For example: "The funA[ProjectA] already does X, so we don't need to handle X in funB[ProjectB]; just pass the result from funA to funB."
```
"#
