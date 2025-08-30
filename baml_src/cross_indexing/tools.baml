template_string CrossIndexingToolCalls(tools: ToolName[]) #"
{% if tools|length > 0 %}
{{ ToolsPrompt(Agent.CrossIndexing, tools) }}
{% endif %}
"#
