class BasePromptParams {
  system_info SystemInfoParams
  project_context ProjectContext
}

template_string BaseSystemPrompt(agent_name: Agent, tools: ToolName[], params:BasePromptParams) #"
{{ AgentSystemPromptBase(agent_name) }}

{% if tools|length > 0 %}
{{ ToolsPrompt(agent_name, tools) }}
{% endif %}

{{ SystemInfo(params.system_info) }}

{% if params.project_context.projects|length > 0 %}
{{ ProjectContextTemplate(params.project_context) }}
{% endif %}

"#

template_string AgentSystemPromptBase(agent_name: Agent) #"
{% if agent_name == Agent.ROADMAP %}
{{ RoadmapSystemPromptBase() }}
{% endif %}
"#
