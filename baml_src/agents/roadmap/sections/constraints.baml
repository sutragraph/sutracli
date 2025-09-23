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
    "add_history": "REQUIRED: summary of only new progress and findings (e.g., - New Progress: Traced main_func. - New Finding: Bug1 at line 45. - Unresolved: helperFunc)—avoid repetition from prior history. Limit to 3-5 findings.",
    "tasks": [  // OPTIONAL: Array of TaskOperation objects
      { "action": "add|move", "id": string, "to_status": "pending|current|completed", "description": string?, "from_status": "pending|current"? }
    ],
    "code": [  // OPTIONAL: Array of CodeStorage objects for tracing invisible/external elements
      {
        "action": "add|update_tracing_status|move_to_traced|add_to_needs_tracing|update_call_chain_summary",
        "id": string, // eg. "1",
        "file": string?, "start_line": int?, "end_line": int?, "description": string?,
        "is_traced": bool?, "call_chain_summary": string?,
        "needs_tracing": [  // Elements called/accessed but not visible in snippet that might need tracing
          {
            "name": string,
            "element_type": "function|property|variable|attribute|method|class",
            "reason": string?,
            "accessed_from": string?
          }
        ]?,
        "traced_element": {  // element you want to add to traced (hierarchical)
          "name": string,
          "element_type": "function|property|...",
          "start_line": int,
          "end_line": int,
          "signature": string?,
          "content": string, // Relevant code snippet
          "is_fully_traced": bool?,
          "accessed_elements": [ /* Recursive traced_element[] */ ]?
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
