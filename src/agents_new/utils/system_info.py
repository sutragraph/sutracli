"""
System information for agents
"""

import os
import platform

from baml_client.types import SystemInfoParams


def get_system_info() -> SystemInfoParams:
    """Get current system information."""
    return SystemInfoParams(
        os=platform.system(),
        shell=os.environ.get("SHELL", "unknown"),
        home=os.path.expanduser("~"),
        current_dir=os.getcwd(),
    )
