template_string SystemInfo(os: string, shell: string, home: string, current_dir: string) #"
    ## SYSTEM INFORMATION

    **Operating System:** {{ os }}
    **Default Shell:** {{ shell }}
    **Home Directory:** {{ home }}
    **Current Directory:** {{ current_dir }}

    This system information provides context about the environment where code execution and file operations will occur. Use this information to:
    - Choose appropriate shell commands and syntax
    - Understand path resolution and file system conventions
    - Make platform-specific decisions when needed
    - Set proper file permissions and executable formats
"#

