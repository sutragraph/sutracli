template_string CrossIndexingToolCalls(tools: Tools_CrossIndexing[]) #"
{% if tools|length > 0 %}
{{ ToolsPrompt(AgentName.CrossIndexing, tools) }}
{% endif %}
"#
