template_string RoadmapStrategy() #"
## Thinking Approach: Use Chain-of-Thought
Outline step-by-step in 'thinking': 'Goal? Memory check? Tool? Why? Verify: All problems covered?' Example: 'Parse: 2 issues → Track1: Valid fail (Bug1) → semantic_search auth; Track2: Invalid pass (Bug2) → search_keyword validator'. End with: 'Tracing Audit: All needs_tracing empty? All projects analyzed? All symptoms traced? If no, tool next. Hidden Connections Audit: Hypothesize related projects from list/descriptions; use semantic_search if no links.'

### Guidelines (Positive Audits)
Address all problems explicitly: List as Bug1/Bug2 in thinking/history.
Trace internals deeply: For func found, think 'What calls? Trace to DB/API.'
Ensure completeness before completion: Confirm all elements to finals, tracks done, needs_tracing=[], matches history.
Prioritize core (e.g., validation paths); limit needs <10; audit for full chains/symptoms.
Audit for subtle bugs: Simulate edges, flag off-by-one/inversions if diagnostic query. Refer to SutraMemoryPrompt's tracing section.
Audit for search breadth: If results narrow/single, expand with wider semantic_search across projects; store multiple findings before analysis.

### Systematic Approach
Follow tracing: Store incremental in memory; recurse to finals.
Flow: Pre-review memory/audit needs; select one tool; post-update trace; if relevant findings, store then expand searches to related projects; start analysis/tracing from stored memory.

### Feedback Handling
If feedback_received: Review feedback + priors; identify tasks for improvements; analyze; apply mods; generate new roadmap. Example: Feedback 'Missed contract' → Add to Phase4.
"#
