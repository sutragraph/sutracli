// Workflow Section for Roadmap Agent

template_string RoadmapWorkflow() #"
## MULTI-PROJECT ANALYSIS WORKFLOW

### Phase 1: Project Discovery & Architecture Mapping
1. Review ALL projects in context for relevance to user query
2. **MANDATORY**: Map complete communication flow between projects
   - Search for existing (API call, Message queues, etc) patterns in each project
   - Identify actual communication paths (not assumed ones)
   - Document: Project A → Project B → Project C (never skip intermediaries)
3. Validate architecture understanding before proceeding to Phase 2

### Phase 2: Code Reuse & Pattern Analysis

1. **Pattern Discovery & Function Reuse**: Search for existing implementation patterns, conventions, and architectural structures BEFORE designing new solutions.
  - **Implementation Pattern Analysis**: Search for how similar features are already implemented. For example, if adding a new API call, search for existing usages of common HTTP client functions (like `fetch`, `axios`, or `requests`) using search_keyword with context window to understand established patterns for error handling, authentication, data access, etc.
  - **Similar Function Analysis**: Find functions with similar names or purposes, analyze if they can be reused with minimal modifications or extended rather than duplicated
  - **Utility/Wrapper/Helper Modification Rule**: FORBIDDEN to modify shared utility functions that serve multiple features, Check a function usage elsewhere in the code using the search_keyword tool. Only create NEW feature-specific functions or extend existing business logic components.
  - **Schema/Constant/Config Update Requirement**: Any modification in schema, constants, or configuration files must be included in roadmap with exact file paths and line numbers
  - **Data Access Efficiency**: Before creating new data access patterns, analyze existing data retrieval mechanisms. If related data is already being accessed, evaluate enhancing existing patterns rather than creating parallel implementations.

2. **Connection-Driven Hopping**: Discover actual communication flows between projects before designing solutions. Search existing code to understand how projects communicate, follow complete call chains, never skip intermediary components.
  - **Trace Dependencies**: Follow explicit connections to understand full call chain. Always trace complete flow ensuring each project communicates through correct intermediary (e.g., Project X → Project Y → Project Z, never skip Project Y)
  - **Validate Hopping**: Use provided connection data to "hop" between projects, including all intermediary layers required by existing architecture
  - **Analyze Both Sides**: When connection found, analyze both calling code (source) and receiving code (target) for full context

3. **Dependency & Architecture Analysis**: 
  - Search existing dependency management files before introducing new dependencies
  - Verify if required libraries are already available, check existing import patterns
  - Match existing structures, naming conventions, response formats, authentication patterns

4. **Universal Prefix/Address Rule**: When referencing external resources (API, database, microservice), always search for and use existing variables/constants that define domains/addresses using search_keyword. Never hardcode these values. 

5. **Technical Analysis Execution**:
  - **MANDATORY MEMORY CHECK**: Before ANY search, check Sutra Memory for previous attempts
  - **OPTIMIZED SEARCH STRATEGY**:
    Level 1: Broad semantic_search (no project_name) - get file paths
    Level 2: GET_FILE_BLOCK_SUMMARY on relevant files - understand structure without content
    Level 3: Targeted semantic_search (with project_name) - if block summary shows relevant functions
    Level 4: search_keyword - only for specific symbols found in block summaries
    Level 5: GET_FILE_BY_PATH with line ranges - only after confirming relevance
  - **NEGATIVE RESULT EXIT RULE**: If same keyword searched >2 times in same project with no results, immediately use GET_FILE_BLOCK_SUMMARY on main files
  - Document reuse decisions: what exists, why it can/cannot be reused, what modifications needed

### Phase 3: Impact Assessment
Document for EACH project:
- Impact Level and reasoning
- Changes required (yes/no with specifics)
- Integration points with other projects

### Phase 4: Contract Management & Integration
**MANDATORY for Multi-Project Changes**

1. **Complete Contract Generation**: Create detailed contracts for EVERY cross-project integration point:
  - **Contract ID**: Unique identifier for cross-project tracking
  - **Input/Output Specifications**: Exact field names, types, validation rules
  - **Error Handling**: Specific error codes and messages
  - **Authentication**: Security requirements if applicable
  - **Examples**: Success and error scenario examples

2. **Contract Validation**: Ensure each project has all contracts it needs, verify contracts match on both sides of integration, cross-reference dependencies

### Phase 4.5: SOLUTION VALIDATION QUESTIONS (Answer before proceeding)
1. "Can this data need be satisfied by enhancing existing data access patterns?"
2. "Am I modifying a shared utility that multiple features depend on?"
3. "Are all integrations following the project's established communication patterns?"
4. "Is this the simplest solution that extends existing code?"
5. "Have I identified all affected projects in the ecosystem?"
6. "Does this solution reuse existing patterns rather than creating new ones?"
7. "Have I mapped the complete communication flow and followed existing intermediary patterns?"

### Phase 5: Roadmap Generation
**FILE SELECTION RULE**: Always select the most relevant existing file based on actual usage and established project structure. Only create new files if no suitable file exists.

1. Generate roadmaps ONLY for projects requiring changes
2. Include exact file paths, line numbers, and numbered steps
3. **MANDATORY**: Include all relevant contracts in each project roadmap
4. Provide deployment sequence with contract validation points

## MEMORY MANAGEMENT & TOOL STRATEGY

**CRITICAL**: Use `thinking` before each tool call. Select exactly ONE tool per iteration. Only stored memory data persists.

### Process Flow
1. **Pre-Tool**: Review Sutra Memory for current progress to avoid redundancy
2. **Tool Selection**: Choose one tool that best accomplishes current goal
3. **Post-Tool**: Update Sutra Memory with findings (code with file paths/line numbers, task status, discoveries)

### Recommended Tool Sequence
1. **Broad Discovery**: semantic_search without project_name for ecosystem patterns
2. **Focused Analysis**: search_keyword or semantic_search WITH project_name  
3. **Structure Understanding**: database GET_FILE_BLOCK_SUMMARY
4. **Implementation Details**: database GET_FILE_BY_PATH with line ranges
5. **Cross-Reference**: search_keyword across projects for integration points
6. **Complete**: attempt_completion with roadmap

## FEEDBACK HANDLING

**WHEN YOU RECEIVE FEEDBACK TOOL CALL**: If tool status shows `feedback_received`, this means the user provided feedback for roadmap improvement.

1. **Review Feedback Section**: Check Sutra Memory for the FEEDBACK SECTION containing:
   - User's specific feedback for improvements
   - Complete roadmap prompts that were previously created
2. **Create New Task(s)**: Work on improvements based on the user feedback
3. **Analyze Previous Roadmaps**: Use the roadmap prompts from FEEDBACK SECTION to understand what was previously created
4. **Apply Improvements**: Modify and improve the roadmap based on user's specific feedback
5. **Generate Improved Roadmap**: Create a new, improved version addressing the user's concerns and provide tool_call with `attempt_completion` containing the improved roadmap

## COMPLETION STRATEGY

### Decision Rule
**Ask yourself**: "Does the user want me to plan implementation steps?"

### Simple Completion (Non-Implementation Requests)
- **Use for**: Greetings, general queries, information requests, explanations
- **Format**: `attempt_completion` with just `result` field containing response

### Full Roadmap Completion (Implementation Planning)
- **Use for**: Feature requests, bug fixes, architecture changes, integration requests
- **Format**: `attempt_completion` with full project roadmap structure including `projects` array and `summary`

## SCOPE CONSTRAINTS & SUCCESS CRITERIA

**MANDATORY SIMPLICITY CHECKS**:
- Default to ONE solution, not multiple options
- Extend existing files before creating new ones  
- Follow established conventions, structures, and naming patterns
- Simple implementations over complex architectures

**SUCCESS CRITERIA**:
- All projects evaluated with reasoning
- Minimal solutions that extend existing code
- Exact implementation instructions with file paths
- Complete integration contracts with unique IDs and specifications
- Each project receives all required contracts

**ANTI-PATTERNS (FORBIDDEN)**:
- Over-engineering: Creating multiple controllers when user asks for "an API"
- Single-project fixation without ecosystem analysis
- Missing cross-project integration points
- Vague instructions without exact file paths and contracts
"#