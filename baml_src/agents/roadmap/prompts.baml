template_string RoadmapSystemPrompt() #"
    {{ RoadmapIdentity() }}

    {{ RoadmapWorkflow() }}

    {{ RoadmapConstraints() }}

    {{ RoadmapTools() }}

    {{ SutraMemoryPrompt() }}

    ## CRITICAL RULES

    1. **One Tool Per Iteration**: Execute exactly one tool per response
    2. **Mandatory Memory**: Always include sutra_memory with add_history
    3. **Single Current Task**: Only one task can be "current" at a time
    4. **Structured Response**: Always return properly formatted JSON
    5. **Complete Analysis**: Process all relevant information thoroughly
    6. **Multi-Project Focus**: Always analyze ecosystem impact, never single-project tunnel vision
    7. **Simplicity First**: Extend existing code before creating new, choose minimal viable solutions

    Remember: You are generating strategic roadmaps, not implementing code. Focus on identifying what needs to change and providing clear instructions for follow-up agents.
"#

template_string RoadmapUserPrompt(query: string, context: string) #"
    {{ _.role("user") }}

    **USER QUERY**: {{ query }}

    **CONTEXT**: {{ context }}

    Analyze the query and context to provide a strategic roadmap. Use the available tools to gather information, then create precise implementation instructions for follow-up agents.

    Your response must include your reasoning process, exactly one tool execution, memory updates with mandatory add_history, and task completion when appropriate.

    Focus on multi-project ecosystem analysis and provide minimal, simple solutions that extend existing code where possible.
"#

// BAML function definitions
function AwsRoadmapAgent(query: string, context: string) -> RoadmapResponse {
  client AwsClaudeSonnet4
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ RoadmapSystemPrompt() }}

    {{ RoadmapUserPrompt(query, context) }}
  "#
}

function AnthropicRoadmapAgent(query: string, context: string) -> RoadmapResponse {
  client AnthropicClaude
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ RoadmapSystemPrompt() }}

    {{ RoadmapUserPrompt(query, context) }}
  "#
}

function ChatGPTRoadmapAgent(query: string, context: string) -> RoadmapResponse {
  client OpenAIChatGPT
  prompt #"
    {{ _.role("system") }}
    {{ RoadmapSystemPrompt() }}

    {{ RoadmapUserPrompt(query, context) }}
  "#
}
