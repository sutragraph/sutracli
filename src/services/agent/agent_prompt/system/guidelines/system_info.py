SYSTEM_INFO = """====

SYSTEM INFORMATION

Operating System: {os_name}
Default Shell: {shell}
Home Directory: {home_directory}
Current Workspace Directory: {current_dir}

The Current Workspace Directory is the active VS Code project directory, and is therefore the default directory for all tool operations. New terminals will be created in the current workspace directory, however if you change directories in a terminal it will then have a different working directory; changing directories in a terminal does not modify the workspace directory, because you do not have access to change the workspace directory. You receive a comprehensive overview of the project's directory structure in the WORKSPACE STRUCTURE section, which shows only folder names (not individual files). The structure shows directories up to a limited depth, so there may be additional subdirectories not visible in this overview. This provides key insights into the project from directory names and how developers conceptualize and organize their code. The WORKSPACE STRUCTURE represents the initial state of the project and remains static throughout your session. When you make changes like adding or removing folders, these modifications are tracked separately in sutra memory, which is provided with each user interaction to keep you informed of the current project state. This dual system ensures you always have both the original project layout for reference and current modifications for accurate decision-making. For exploring specific directories and viewing files, use the list_files tool instead of ls command, as it is optimized and faster than traditional shell commands.
"""
