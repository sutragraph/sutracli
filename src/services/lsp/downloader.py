"""
Static class for downloading and installing LSP servers.
"""

import gzip
import os
import shutil
import subprocess
import tarfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional

from loguru import logger

from config import config
from src.utils.console import console


class Downloader:
    """Static class for downloading and installing LSP servers."""

    @classmethod
    def _get_install_dir(cls) -> Path:
        """Get the LSP servers installation directory from config."""
        return Path(config.storage.lsp_servers_dir).expanduser()

    @classmethod
    def ensure_install_dir(cls):
        """Ensure installation directory exists."""
        install_dir = cls._get_install_dir()
        install_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def is_installed(cls, exec_path: str) -> bool:
        """
        Check if LSP server is already installed.

        Args:
            exec_path: Path to the executable (can include ~)

        Returns:
            True if executable exists and is accessible, False otherwise
        """
        # Expand tilde in path
        exec_path = os.path.expanduser(exec_path)

        # Check if it's an absolute path
        if os.path.isabs(exec_path):
            return os.path.exists(exec_path) and os.path.isfile(exec_path)

        # Check in system PATH
        if shutil.which(exec_path):
            return True

        # Check in our install directory
        install_dir = cls._get_install_dir()
        local_path = install_dir / exec_path
        return local_path.exists() and local_path.is_file()

    @classmethod
    def get_exec_path(cls, exec_name: str) -> Optional[str]:
        """
        Get the full path to an executable.

        Args:
            exec_name: Executable name or path (can include ~)

        Returns:
            Full path to executable, or None if not found
        """
        # Expand tilde in path
        exec_name = os.path.expanduser(exec_name)

        # If it's an absolute path and exists, return it
        if os.path.isabs(exec_name):
            if os.path.exists(exec_name) and os.path.isfile(exec_name):
                return exec_name
            return None

        # Check in system PATH
        system_path = shutil.which(exec_name)
        if system_path:
            return system_path

        # Check in our install directory
        install_dir = cls._get_install_dir()
        local_path = install_dir / exec_name
        if local_path.exists() and local_path.is_file():
            return str(local_path)

        return None

    @classmethod
    def install_via_command(cls, install_cmd: str) -> bool:
        """
        Install LSP server using install command.

        Args:
            install_cmd: Shell command to run for installation

        Returns:
            True if installation succeeded, False otherwise
        """
        try:
            console.process(f"Running installation command: {install_cmd}")
            logger.debug(f"Executing install command: {install_cmd}")
            result = subprocess.run(
                install_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout
            )

            if result.returncode == 0:
                console.success("Installation completed successfully")
                logger.debug(f"Installation command succeeded")
                return True
            else:
                console.error(f"Installation failed with exit code {result.returncode}")
                logger.debug(
                    f"Installation failed with returncode: {result.returncode}"
                )
                if result.stderr:
                    console.error(f"Error output: {result.stderr}")
                    logger.debug(f"Installation stderr: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            console.error("Installation timed out after 5 minutes")
            logger.debug("Installation command timed out after 300 seconds")
            return False
        except Exception as e:
            console.error(f"Installation failed: {e}")
            logger.debug(f"Installation exception: {e}")
            return False

    @classmethod
    def download_and_install(cls, download_url: str, exec_name: str) -> Optional[str]:
        """
        Download and install LSP server from URL.

        Args:
            download_url: URL to download the LSP server from
            exec_name: Name of the executable to extract

        Returns:
            Path to the installed executable, or None if failed
        """
        cls.ensure_install_dir()
        install_dir = cls._get_install_dir()

        try:
            # Download file
            filename = download_url.split("/")[-1]
            download_path = install_dir / filename

            console.process(f"Downloading {filename} from {download_url}...")
            logger.debug(f"Downloading from URL: {download_url} to {download_path}")
            urllib.request.urlretrieve(download_url, download_path)

            # Extract based on file extension
            if filename.endswith(".gz") and not filename.endswith(".tar.gz"):
                # Single gzip file
                console.process("Extracting gzip file...")
                logger.debug(f"Extracting gzip: {download_path}")
                with gzip.open(download_path, "rb") as f_in:
                    exec_path = install_dir / exec_name
                    with open(exec_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                    os.chmod(exec_path, 0o755)

            elif filename.endswith(".tar.gz"):
                # Tar gzip archive
                console.process("Extracting tar.gz archive...")
                logger.debug(f"Extracting tar.gz: {download_path}")
                with tarfile.open(download_path, "r:gz") as tar:
                    tar.extractall(install_dir)

            elif filename.endswith(".zip"):
                # Zip archive
                console.process("Extracting zip archive...")
                logger.debug(f"Extracting zip: {download_path}")
                with zipfile.ZipFile(download_path, "r") as zip_file:
                    zip_file.extractall(install_dir)

            # Clean up download file
            download_path.unlink()

            # Return path to executable
            exec_path = install_dir / exec_name
            if exec_path.exists():
                os.chmod(exec_path, 0o755)
                return str(exec_path)

            # Look for executable in extracted directories
            for path in install_dir.rglob(exec_name):
                if path.is_file():
                    os.chmod(path, 0o755)
                    return str(path)

            console.error(f"Could not find executable {exec_name} after extraction")
            logger.debug(f"Executable not found in extracted files: {exec_name}")
            return None

        except Exception as e:
            console.error(f"Download and installation failed: {e}")
            logger.debug(f"Download/install exception: {e}")
            return None

    @classmethod
    def ensure_lsp_installed(cls, language_config: dict) -> Optional[str]:
        """
        Ensure LSP server is installed, installing if necessary.

        This method checks if the LSP server is already installed and only
        installs it if not found. This makes it safe to call repeatedly.

        Process:
        1. Check if already installed (returns path if found)
        2. Run install_cmd if provided and not installed
        3. Download from download_url if provided and not installed

        Args:
            language_config: Dictionary with LSP server configuration

        Returns:
            Path to the LSP server executable, or None if installation failed
        """
        exec_name = language_config["exec_name"]

        # Ensure install directory exists
        cls.ensure_install_dir()

        # Check if already installed
        if cls.is_installed(exec_name):
            exec_path = cls.get_exec_path(exec_name)
            if exec_path:
                console.info(f"LSP server already installed at: {exec_path}")
                logger.debug(f"Found existing LSP server: {exec_path}")
                return exec_path

        # Install using command if available
        if language_config.get("install_cmd"):
            console.process(
                f"Installing LSP server for {language_config.get('name', 'unknown')}..."
            )
            logger.debug(
                f"Starting installation for language: {language_config.get('name', 'unknown')}"
            )
            if cls.install_via_command(language_config["install_cmd"]):
                # After installation, try to find the executable
                exec_path = cls.get_exec_path(exec_name)
                if exec_path:
                    return exec_path
                else:
                    console.warning(
                        f"Installation succeeded but could not locate executable: {exec_name}"
                    )
                    logger.debug(f"Post-install: executable not found: {exec_name}")

        # Download and install if URL available
        if language_config.get("download_url"):
            console.process(
                f"Downloading LSP server for {language_config.get('name', 'unknown')}..."
            )
            logger.debug(
                f"Starting download for language: {language_config.get('name', 'unknown')}"
            )
            return cls.download_and_install(language_config["download_url"], exec_name)

        return None
