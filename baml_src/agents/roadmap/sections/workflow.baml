template_string RoadmapWorkflow() #"
====

## MULTI-PROJECT ANALYSIS WORKFLOW

Phase 1: Project Discovery & Architecture Mapping
1. Review ALL projects in context for relevance to user query
2. MANDATORY: Map complete communication flow between projects
   - Search for existing (API call, Message queues, etc) patterns in each project
   - Identify actual communication paths (not assumed ones)
   - Document: Project A → Project B → Project C (never skip intermediaries)
3. Validate architecture understanding before proceeding to Phase 2

Phase 2: Code Reuse & Pattern Analysis

1. Pattern Discovery & Function Reuse: Search for existing implementation patterns, conventions, and architectural structures BEFORE designing new solutions.
  - Implementation Pattern Analysis: Search for how similar features are already implemented. For example, if adding a new API call, search for existing usages of common HTTP client functions (like `fetch`, `axios`, or `requests`) using search_keyword with context window to understand established patterns for error handling, authentication, data access, etc.
  - Similar Function Analysis: Find functions with similar names or purposes, analyze if they can be reused with minimal modifications or extended rather than duplicated
  - Utility/Wrapper/Helper Modification Rule: FORBIDDEN to modify shared utility functions that serve multiple features, Check a function usage elsewhere in the code using the search_keyword tool. Only create NEW feature-specific functions or extend existing business logic components.
  - Schema/Constant/Config Update Requirement: Any modification in schema, constants, or configuration files must be included in roadmap with exact file paths and line numbers
  - Data Access Efficiency: Before creating new data access patterns, analyze existing data retrieval mechanisms. If related data is already being accessed, evaluate enhancing existing patterns rather than creating parallel implementations.

2. Connection-Driven Hopping: Discover actual communication flows between projects before designing solutions. Search existing code to understand how projects communicate, follow complete call chains, never skip intermediary components.
  - Trace Dependencies: Follow explicit connections to understand full call chain. Always trace complete flow ensuring each project communicates through correct intermediary (e.g., Project X → Project Y → Project Z, never skip Project Y)
  - Validate Hopping: Use provided connection data to "hop" between projects, including all intermediary layers required by existing architecture
  - Analyze Both Sides: When connection found, analyze both calling code (source) and receiving code (target) for full context

3. Dependency & Architecture Analysis:
  - Search existing dependency management files before introducing new dependencies
  - Verify if required libraries are already available, check existing import patterns
  - Match existing structures, naming conventions, response formats, authentication patterns

4. Universal Prefix/Address Rule: When referencing external resources (API, database, microservice), always search for and use existing variables/constants that define domains/addresses using search_keyword. Never hardcode these values.

5. Technical Analysis Execution:
  - MANDATORY MEMORY CHECK: Before ANY search, check Sutra Memory for previous attempts
  - OPTIMIZED SEARCH STRATEGY:
    Level 1: Broad semantic_search (no project_name) - get file paths
    Level 2: GET_FILE_BLOCK_SUMMARY on relevant files - understand structure without content
    Level 3: Targeted semantic_search (with project_name) - if block summary shows relevant functions
    Level 4: search_keyword - only for specific symbols found in block summaries
    Level 5: GET_FILE_BY_PATH with line ranges - only after confirming relevance
  - Document reuse decisions: what exists, why it can/cannot be reused, what modifications needed

### Phase 3: Impact Assessment
Document for EACH project:
- Impact Level and reasoning
- Changes required (yes/no with specifics)
- Integration points with other projects

### Phase 4: Contract Management & Integration
MANDATORY for Multi-Project Changes

1. Role-Specific Contract Generation: Create detailed contracts for EVERY cross-project integration point with clear role specification:
  - Contract ID: Unique identifier for cross-project tracking
  - Role Definition: Clearly specify the project's role using enum values (`provider` or `consumer`):
    - Consumer Role (`consumer`): Project consuming data/services from another project
    - Provider Role (`provider`): Project providing data/services to another project
    - Intermediary Role: If project acts as both consumer AND provider, create separate contracts:
      - Consumer Contract: Role = `consumer` for receiving data from upstream project
      - Provider Contract: Role = `provider` for sending data to downstream project
  - Input/Output Specifications: Exact field names, types, validation rules
  - Error Handling: Specific error codes and messages
  - Authentication: Security requirements if applicable
  - Examples: Success and error scenario examples

2. Contract Validation: Ensure each project has all role-specific contracts it needs, verify contracts match on both sides of integration, cross-reference dependencies for complete flow coverage

### Phase 5: SOLUTION VALIDATION QUESTIONS (Answer before proceeding)
1. "Can this data need be satisfied by enhancing existing data access patterns?"
2. "Am I modifying a shared utility that multiple features depend on?"
3. "Are all integrations following the project's established communication patterns?"
4. "Is this the simplest solution that extends existing code?"
5. "Have I identified all affected projects in the ecosystem?"
6. "Does this solution reuse existing patterns rather than creating new ones?"
7. "Have I mapped the complete communication flow and followed existing intermediary patterns?"

### Phase 6: Roadmap Generation
FILE SELECTION RULE: Always select the most relevant existing file based on actual usage and established project structure. Only create new files if no suitable file exists.

1. Generate roadmaps ONLY for projects requiring changes
2. Include exact file paths, line numbers, and numbered steps
3. MANDATORY: Include all relevant contracts in each project roadmap
4. Provide deployment sequence with contract validation points
"#
