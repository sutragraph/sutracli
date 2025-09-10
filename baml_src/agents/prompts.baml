class BasePromptParams {
  system_info SystemInfoParams
  project_context ProjectContext
}

template_string BaseSystemPrompt(agent_name: Agent, tools: ToolName[], params:BasePromptParams) #"
{{ AgentSystemPromptBase(agent_name) }}

{% if params.project_context.projects|length > 0 %}
{{ ProjectContextTemplate(params.project_context) }}
{% endif %}

{% if tools|length > 0 %}
{{ ToolsPrompt(agent_name, tools) }}
{% endif %}

{{ SutraMemoryPrompt() }}

{{ SystemInfo(params.system_info) }}

====

## CRITICAL RULES
1. One Tool Per Iteration: Execute exactly one tool per response
2. Mandatory Memory: Always include sutra_memory with add_history
3. Structured Response: Always return properly formatted JSON
4. Complete Analysis: Process all relevant information thoroughly
"#

template_string AgentSystemPromptBase(agent_name: Agent) #"
{% if agent_name == Agent.ROADMAP %}
{{ RoadmapSystemPromptBase() }}
{% endif %}
"#
