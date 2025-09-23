class Project {
  name string
  path string
  description string
}

class ProjectContext {
  projects Project[]
}

template_string ProjectEntry(project: Project) #"
Project: {{ project.name }}
Path: {{ project.path }}
Description: {{ project.description }}
"#

template_string ProjectContextTemplate(project_context: ProjectContext) #"
## PROJECTS CONTEXT:
{% for project in project_context.projects %}
{{ ProjectEntry(project) }}
{% endfor %}
"#
