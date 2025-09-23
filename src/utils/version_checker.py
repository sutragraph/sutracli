"""
Version checker utility for SutraKit CLI.
Checks for package updates and notifies users about new versions.
"""

import importlib.metadata
from typing import Dict, Optional, Tuple

import requests
from rich.panel import Panel
from rich.text import Text

from src.utils.console import console


class VersionChecker:
    """Utility class for checking package versions and updates."""

    PACKAGE_NAME = "sutrakit"
    PYPI_API_URL = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"

    @staticmethod
    def get_current_version() -> Optional[str]:
        """Get the currently installed version of SutraKit."""
        try:
            return importlib.metadata.version(VersionChecker.PACKAGE_NAME)
        except importlib.metadata.PackageNotFoundError:
            return None

    @staticmethod
    def get_latest_version() -> Optional[str]:
        """Get the latest version from PyPI."""
        try:
            response = requests.get(VersionChecker.PYPI_API_URL, timeout=30)
            if response.status_code == 200:
                data = response.json()
                return data["info"]["version"]
        except Exception:
            # Silently fail if we can't check for updates
            pass
        return None

    @staticmethod
    def compare_versions(current: str, latest: str) -> str:
        """
        Compare two version strings.
        Returns: 'outdated', 'latest', or 'newer'
        """
        try:
            if current < latest:
                return "outdated"
            elif current == latest:
                return "latest"
            else:
                return "newer"
        except Exception:
            return "unknown"

    @classmethod
    def check_for_updates(cls, silent: bool = False) -> Dict:
        """
        Check for package updates.

        Args:
            silent: If True, don't show any output for up-to-date packages

        Returns:
            Dict with version info and update status
        """
        current = cls.get_current_version()
        latest = cls.get_latest_version()

        if not current:
            return {
                "status": "not_installed",
                "current": None,
                "latest": latest,
                "update_available": False,
            }

        if not latest:
            if not silent:
                console.dim("ℹ️ Could not check for updates (network/API unavailable)")
            return {
                "status": "unknown",
                "current": current,
                "latest": None,
                "update_available": False,
            }

        status = cls.compare_versions(current, latest)
        update_available = status == "outdated"

        return {
            "status": status,
            "current": current,
            "latest": latest,
            "update_available": update_available,
        }

    @classmethod
    def show_update_notification(cls, verbose: bool = False) -> bool:
        """
        Show update notification if an update is available.

        Args:
            verbose: If True, show status even when up to date

        Returns:
            True if update is available, False otherwise
        """
        result = cls.check_for_updates(silent=True)

        if result["update_available"]:
            cls._display_update_panel(result["current"], result["latest"])
            return True
        elif verbose and result["status"] == "latest":
            console.success(f"✅ SutraKit is up to date (v{result['current']})")

        return False

    @staticmethod
    def _display_update_panel(current_version: str, latest_version: str):
        """Display a update notification panel."""
        update_text = Text()
        update_text.append("📚 SutraCLI Update Available\n\n", style="bold blue")
        update_text.append(f"v{current_version} ", style="bold yellow")
        update_text.append("🡲 ", style="bold white")
        update_text.append(f"v{latest_version}\n", style="bold green")
        update_text.append("A new version is available!\n", style="bold red")
        update_text.append("\nUpdate with: ", style="bold")
        update_text.append("pip install --upgrade sutrakit", style="bold cyan")

        panel = Panel.fit(update_text, border_style="yellow", padding=(1, 2))
        console.print(panel)

    @staticmethod
    def get_update_command() -> str:
        """Get the pip command to update SutraKit."""
        return f"pip install --upgrade {VersionChecker.PACKAGE_NAME}"


# Convenience functions for easy importing
def check_for_updates(silent: bool = False) -> Dict:
    """Check for SutraKit updates."""
    return VersionChecker.check_for_updates(silent=silent)


def show_update_notification(verbose: bool = False) -> bool:
    """Show update notification if available."""
    return VersionChecker.show_update_notification(verbose=verbose)


def get_version_info() -> Tuple[Optional[str], Optional[str]]:
    """Get current and latest version info."""
    current = VersionChecker.get_current_version()
    latest = VersionChecker.get_latest_version()
    return current, latest
