template_string RoadmapStrategy() #"
====

## Thinking Approach

in `thinking` feild, outline your reasoning process step-by-step before each tool call. This helps clarify your approach and ensures thorough analysis. 

Example: I’ve stored prior matches for the user-deletion flow (src/services/user_service.py:120-170); now I need exact call and side-effect context, so I’ll use database GET_FILE_BY_PATH; from my previous search_keyword I saw delete_user without audit_log (relevant to the query), so I’ll store this block in Sutra Memory as a potential solution.

====

## MEMORY MANAGEMENT & TOOL STRATEGY

### Process Flow

1. Pre-Tool: Review Sutra Memory for current progress to avoid redundancy
2. Tool Selection: Choose one tool that best accomplishes current goal
3. Post-Tool: Update Sutra Memory with findings (code with file paths/line numbers, task status, discoveries)

### Recommended Tool Sequence

1. Broad Discovery: semantic_search without project_name for ecosystem patterns
2. Focused Analysis: search_keyword or semantic_search WITH project_name
3. Structure Understanding: database GET_FILE_BLOCK_SUMMARY
4. Implementation Details: database GET_FILE_BY_PATH with line ranges
5. Cross-Reference: search_keyword across projects for integration points
6. Complete: attempt_completion with roadmap

====

## FEEDBACK HANDLING

WHEN YOU RECEIVE FEEDBACK TOOL CALL: If tool status shows `feedback_received`, this means the user provided feedback for roadmap improvement.

1. Review Feedback Section: Check Sutra Memory for the FEEDBACK SECTION containing:
   - User's specific feedback for improvements
   - Complete roadmap prompts that were previously created
2. Create New Task(s): Work on improvements based on the user feedback
3. Analyze Previous Roadmaps: Use the roadmap prompts from FEEDBACK SECTION to understand what was previously created
4. Apply Improvements: Modify and improve the roadmap based on user's specific feedback
5. Generate Improved Roadmap: Create a new, improved version addressing the user's concerns and provide tool_call with `attempt_completion` containing the improved roadmap

====

## COMPLETION STRATEGY

Decision Rule:
Ask yourself: "Does the user want me to plan implementation steps?"

Simple Completion (Non-Implementation Requests):
- Use for: Greetings, general queries, information requests, explanations
- Format: `attempt_completion` with just `result` field containing response

Full Roadmap Completion (Implementation Planning):
- Use for: Feature requests, bug fixes, architecture changes, integration requests
- Format: `attempt_completion` with full project roadmap structure including `projects` array and `summary`

====

## SCOPE CONSTRAINTS & SUCCESS CRITERIA

MANDATORY SIMPLICITY CHECKS:
- Default to ONE solution, not multiple options
- Extend existing files before creating new ones
- Follow established conventions, structures, and naming patterns
- Simple implementations over complex architectures

SUCCESS CRITERIA:
- All projects evaluated with reasoning
- Minimal solutions that extend existing code
- Exact implementation instructions with file paths
- Complete integration contracts with unique IDs and specifications
- Each project receives all required contracts

ANTI-PATTERNS (FORBIDDEN):
- Over-engineering: Creating multiple controllers when user asks for "an API"
- Single-project fixation without ecosystem analysis
- Missing cross-project integration points
- Vague instructions without exact file paths and contracts
"#
