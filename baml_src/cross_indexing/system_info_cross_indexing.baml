template_string CrossIndexingSystemInfoTemplate(home_dir: string, current_dir: string) #"
    ## SYSTEM INFORMATION

    Home Directory: {{ home_dir }}
    Current Directory: {{ current_dir }}

    This system information provides context about the environment where code execution and file operations will occur. Use this information to:
    - Understand path resolution and file system conventions
    - Make platform-specific decisions when needed
    - Set proper file permissions and executable formats
"#

