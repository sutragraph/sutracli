// Project Context Templates for BAML
// Dynamic project context injection for agents

template_string ProjectContextHeader() #"
    ## RELEVANT PROJECT CONTEXT

    Here is a list of projects that are relevant to the current task. Use their descriptions to understand their purpose and how they might be interconnected.
"#

template_string ProjectContextInstruction() #"
    **Project Context Usage:**
    - Analyze ALL projects listed below for relevance to the user query
    - Categorize each project: High/Medium/Low/Not Applicable with reasoning
    - Identify integration points between projects
    - Default to MINIMAL solutions that extend existing projects rather than creating new ones
    - Consider cross-project impacts and coordination requirements

    **Multi-Project Analysis Priority:**
    1. Review project descriptions and identify primary candidates
    2. Look for shared technologies, dependencies, or related functionality
    3. Consider deployment and integration complexity
    4. Choose the simplest solution that spans the fewest projects

    When no specific projects are identified as relevant, work in general context but always consider the broader ecosystem.
"#

template_string DefaultProjectContext() #"
    {{ ProjectContextHeader() }}

    No specific projects identified as relevant to this query. Working in general context.

    {{ ProjectContextInstruction() }}
"#

template_string ProjectContextTemplate(projects: string) #"
    {{ ProjectContextHeader() }}

    {{ projects }}

    {{ ProjectContextInstruction() }}
"#

template_string ProjectEntry(name: string, path: string, description: string) #"
    **project:** {{ name }}
    **path:** {{ path }}
    **description:** {{ description }}
"#

template_string ProjectContextGuidance() #"
    **Context Analysis Guidelines:**

    When analyzing project context:
    - **Ecosystem First**: Consider how projects interact and depend on each other
    - **Minimal Complexity**: Choose solutions that require changes to the fewest projects
    - **Existing Patterns**: Extend current architectures rather than introducing new ones
    - **Integration Points**: Document where projects need to coordinate
    - **Deployment Order**: Consider which projects must be updated first

    **Project Relevance Scoring:**
    - **High**: Direct functionality match, explicitly mentioned, or core dependency
    - **Medium**: Related functionality, shared technology stack, or potential integration
    - **Low**: Tangential relationship, shared infrastructure, or distant dependency
    - **Not Applicable**: No relationship to the query or requirements

    Remember: The goal is to provide strategic roadmap guidance across the entire project ecosystem, not just individual project implementations.
"#
