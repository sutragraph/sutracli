"""
System information for agents
"""

import os
import platform

def get_system_info() -> str:
    """Get current system information."""
    return f"""====

SYSTEM INFORMATION

Operating System: {platform.system()}
Default Shell: {os.environ.get('SHELL', 'unknown')}
Home Directory: {os.path.expanduser('~')}
Current Directory: {os.getcwd()}

===="""

SYSTEM_INFO = get_system_info()
