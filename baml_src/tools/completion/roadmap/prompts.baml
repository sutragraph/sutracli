// Roadmap Completion Tool Prompts

template_string RoadmapCompletionToolTemplate() #"
    ## roadmap_completion
    Description: Complete strategic roadmap analysis with comprehensive multi-project implementation guidance. Use when you have gathered sufficient information and can provide complete strategic guidance with exact file paths, line numbers, and implementation contracts.

    This tool generates structured roadmap output that follow-up agents can execute independently without requiring additional context or clarification.

    ## CONTENT REQUIREMENTS

    Your roadmap completion must include ALL of the following components:

    ### Executive Summary
    Provide a high-level strategic overview including:
    - **Scope**: Brief description of what needs to be implemented
    - **Strategy**: Chosen approach with reasoning (extend existing vs create new)
    - **Projects Affected**: List of all projects requiring changes
    - **Integration Points**: Cross-project dependencies and data flow points

    ### Per-Project Implementation Instructions

    For EACH project requiring changes, provide:

    #### Project Impact Assessment
    - **Project Name**: Exact project name as discovered in analysis
    - **Impact Level**: High/Medium/Low/None with detailed reasoning
    - **Changes Required**: Boolean indicating if modifications needed
    - **Reasoning**: Comprehensive explanation of impact and why changes are needed

    #### File Modifications (if changes required)
    For each file that needs changes:
    - **File Path**: Use EXACT paths as returned by tools - never construct or modify paths
    - **Lines**: Specific line ranges or numbers (e.g., "45-67" or "23,45,67")
    - **Current State**: Description of existing signature/structure
    - **Target State**: Description of new signature/requirements
    - **Implementation Steps**: Ordered list of exact modifications with line references
    - **Import Changes**: Specific imports to add/modify/remove

    #### API Contracts (if applicable)
    For each new or modified API endpoint:
    - **Route**: HTTP method and exact path (e.g., "POST /auth/validate")
    - **Request**: Field names and types for request payload
    - **Response**: Field names and types for successful response
    - **Errors**: HTTP status codes with descriptions of error conditions

    #### Cross-Project Integration
    Document how this project integrates with others:
    - **Calls To**: Other projects this project calls, with specific endpoints
    - **Called By**: Other projects that call this project, with integration methods
    - **Data Contracts**: Shared data structures and formats
    - **Authentication**: Auth requirements and token handling

    #### Deployment Requirements
    - **Deploy Order**: Sequence number indicating deployment priority
    - **Prerequisites**: What must be deployed/configured first
    - **Testing Requirements**: Integration tests and validation steps needed

    ### Ecosystem Coordination

    #### Deployment Sequence
    Provide ordered phases for deployment:
    - **Phase Number**: Sequential deployment phase
    - **Project Name**: Which project deploys in this phase
    - **Description**: Brief description and reasoning for this phase
    - **Dependencies**: Prerequisites from previous phases

    #### Integration Testing
    Specify testing requirements:
    - **Test Data Flow**: End-to-end testing scenarios across projects
    - **API Contract Validation**: Steps to validate API contracts work correctly
    - **Error Handling Tests**: Cross-project error propagation testing

    #### Risk Assessment
    Document potential issues and mitigation:
    - **Breaking Changes**: Potential compatibility issues to watch for
    - **Rollback Plan**: How to revert changes if issues arise
    - **Monitoring Requirements**: What to monitor during and after deployment

    ## QUALITY STANDARDS

    ### Precision Requirements
    - Use EXACT file paths as returned by tools - never construct or modify paths
    - Include specific line numbers for all modifications
    - Provide complete API contracts with all error codes
    - Document all cross-project dependencies explicitly
    - Reference exact tool results, not assumptions

    ### Strategic Focus
    - Provide WHAT to change and WHERE, not HOW to implement
    - Focus on roadmap-level guidance, not implementation details
    - Emphasize extending existing code over creating new
    - Choose minimal viable solutions that meet requirements
    - Document strategic decisions made (extend vs create new)

    ### Completeness Criteria
    - All projects in ecosystem must be evaluated (even if no changes needed)
    - Every integration point between projects must be documented
    - Deployment sequence must account for all dependencies
    - Risk mitigation strategies must be provided
    - All file modifications must have exact line references

    ## USAGE GUIDELINES

    ### When to Use roadmap_completion
    Use this tool only when you have:
    ✅ Completed comprehensive multi-project analysis
    ✅ Exact file paths and line numbers for all modifications
    ✅ Identified all cross-project integration points
    ✅ Strategic decisions documented (extend vs create new)
    ✅ Complete understanding of deployment dependencies

    ### Before Using roadmap_completion
    Ensure you have gathered:
    - Complete project inventory and impact assessment
    - Exact implementation locations with file paths and line numbers from tool results
    - API contracts and data flow specifications
    - Cross-project dependency mapping
    - Strategic decisions with reasoning (simplicity-first approach)

    ### Content Quality Requirements
    - **Independently Executable**: Follow-up agents can execute without additional context
    - **Strategically Sound**: Follows simplicity-first principles (extend > create new)
    - **Technically Precise**: Exact file paths, line numbers, API specifications
    - **Risk Aware**: Addresses potential issues and provides mitigation strategies
    - **Ecosystem Complete**: Covers all affected projects and their relationships

    Usage:
    {
      "result": "Request for comprehensive strategic roadmap completion"
    }

    The result parameter should trigger generation of the complete roadmap structure with all components listed above, populated with your specific analysis findings and strategic decisions.
"#


