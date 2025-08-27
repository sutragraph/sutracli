
template_string AgentSystemPromptBase(agent_name: AgentName) #"
{% if agent_name == "ROADMAP" %}
{{ RoadmapSystemPromptBase() }}
{% endif %}
"#

template_string BaseSystemPrompt(agent_name: AgentName, project_context: ProjectContext?, tools: ToolName[]) #"
{{ AgentSystemPromptBase(agent_name) }}

{% if project_context %}
## PROJECT CONTEXT
{{ ProjectContextTemplate(project_context) }}
{% endif %}

{% if tools|length > 0 %}
{{ ToolsPrompt(agent_name, tools) }}
{% endif %}

{{ SutraMemoryPrompt() }}

{{ SystemInfo() }}

## CRITICAL RULES
1. **One Tool Per Iteration**: Execute exactly one tool per response
2. **Mandatory Memory**: Always include sutra_memory with add_history
3. **Structured Response**: Always return properly formatted JSON
4. **Complete Analysis**: Process all relevant information thoroughly
"#
