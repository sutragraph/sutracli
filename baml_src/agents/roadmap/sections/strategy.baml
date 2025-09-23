template_string RoadmapStrategy() #"
### Thinking Approach: Use Chain-of-Thought
Outline step-by-step in 'thinking': 'Goal? Memory check? Tool? Why? Verify: All problems covered?' Example: 'Parse: 2 issues → Track1: Valid fail (Bug1) → semantic_search auth across projects; Track2: Invalid pass (Bug2) → search_keyword validator'. End with: 'Tracing Audit: For all code snippets → needs_tracing empty? All projects analyzed? All symptoms traced? If no, tool next. Hidden Connections Audit: Hypothesize related projects from list/descriptions/microservices; use semantic_search across them if no links.'

### Guidelines
- Address all problems explicitly: List as Bug1/Bug2 in thinking/history.
- Trace internals deeply: For func found, think 'What calls? Trace to DB/API.' Include persistence layers: audit for atomicity; flag issues if no safeguards. For each needs_tracing, enforce resolution: 'Process this need with a tool call and update to traced.'
- Ensure completeness before completion: Confirm all elements to finals, tracks done, needs_tracing=[]—if not, mandate tool calls to resolve. Matches history.
- Prioritize core (e.g., validation paths); limit needs <10; audit for full chains/symptoms.
- Audit for subtle bugs: Simulate edges, flag off-by-one/inversions. For tracing stalls, check 'All needs_tracing resolved? If no, tool next.'
- Audit for search breadth: If results narrow/single, expand with wider semantic_search across hypothesized related projects; store multiple findings before analysis. Example: For inter-project flow, hypothesize repos like ["projectA", "projectB"] and search 'API call patterns'.

### Systematic Approach
Follow tracing: Store incremental in memory; recurse to finals.
Flow: Pre-review memory/audit needs; select one tool; post-update trace with 'move_to_traced' or 'update_tracing_status'; if relevant findings, store then expand. If needs_tracing not empty, prioritize resolving one per step.

### Feedback Handling
If feedback_received: Review feedback + priors; identify tasks for improvements; analyze; apply mods; generate new roadmap. Example: Feedback 'Missed contract' → Add to Phase4.
"#
