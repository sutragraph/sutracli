class SystemInfoParams {
  os string
  shell string
  home string
  current_dir string
}

template_string SystemInfo(params:SystemInfoParams) #"
====

## SYSTEM INFORMATION

Operating System: {{ params.os }}
Default Shell: {{ params.shell }}
Home Directory: {{ params.home }}
Current Directory: {{ params.current_dir }}

This system information provides context about the environment where code execution and file operations will occur. Use this information to:
- Choose appropriate shell commands and syntax
- Understand path resolution and file system conventions
- Make platform-specific decisions when needed
- Set proper file permissions and executable formats
"#
