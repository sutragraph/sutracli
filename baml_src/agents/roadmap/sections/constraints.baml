template_string RoadmapConstraints() #"
## CONSTRAINTS: Follow Precisely for Accurate Responses

### MANDATORY JSON RESPONSE FORMAT
Output exactly in this structure. Limit 'thinking' to <100 words for brevity.

{
  "thinking": "REQUIRED: Brief Chain-of-Thought (e.g., 'Goal: Trace auth. Memory: Bug1 unresolved. Tool: semantic_search. Why: Broad discovery. Audit: Covers all tracks?').",
  "tool_call": {  // REQUIRED: Select one tool
    "tool_name": "search_keyword|database|list_files|semantic_search|attempt_completion",
    "parameters": { ... }  // Tool-specific (e.g., 'query': string)
  },
  "sutra_memory": {
    "add_history": "REQUIRED: Bulleted summary of progress and findings (e.g., - Progress: Traced main_func. - Finding: Bug1 at line 45. - Unresolved: helperFunc). Limit to 5-10 bullets.",
    "tasks": [  // OPTIONAL: Array of TaskOperation objects
      { "action": "add|move", "id": string, "to_status": "pending|current|completed", "description": string?, "from_status": "pending|current"? }
    ],
    "code": [  // OPTIONAL: Array of CodeStorage objects for tracing
      {
        "action": "add|update_tracing_status|move_to_traced|add_to_needs_tracing|update_call_chain_summary",
        "id": string,
        "file": string?, "start_line": int?, "end_line": int?, "description": string?,
        "is_traced": bool?, "call_chain_summary": string?,
        "needs_tracing": [  // Array of UntracedElement
          { "id": string?, "name": string, "element_type": "function|property|variable|attribute|method|class", "reason": string?, "accessed_from": string? }
        ]?,
        "traced_element": {  // TracedElement (hierarchical)
          "name": string, "element_type": "function|property|...", "start_line": int, "end_line": int,
          "signature": string?, "key_code_lines": string[]?, "is_fully_traced": bool?,
          "accessed_elements": [ /* Recursive TracedElement[] */ ]?
        }?,
        "source_element_id": string?, "element_path": string[]?
      }
    ]
  }
}

Example for contracts (use only for new integrations): ID:val-1, Role:consumer, Input:{'token':str}, Error:401 'Invalid'.

### Requirements
1. Select one tool per iteration to gather information.
2. Verify facts using tools for accuracy.
3. Analyze the full ecosystem starting with the current project.
4. Include contracts only for new integrations, specifying ID, role, specs, examples.
5. Provide exact paths, lines, and before/after snippets for changes (e.g., 'Before: if(x == 0); After: if(x <= 0);').

Focus on providing: Roadmap guidance, imports, structures, optional contracts, integration points, examples, before/after snippets.
Focus on: Single solutions, minimal/exact changes, conventions, simple implementations.
"#
