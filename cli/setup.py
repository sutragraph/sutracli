#!/usr/bin/env python3
"""
Post-install setup script for Sutra CLI.
This script sets up the ~/.sutra directory and downloads required models and parsers.
"""


import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlretrieve

from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from setuptools.command.develop import develop
from setuptools.command.install import install

from src.utils.console import console

# Configuration
REPO_URL = "https://github.com/sutragraph/models"
RELEASE_TAG = "v0.2"
INSTALL_DIR = Path.home() / ".sutra"
TEMP_DIR = Path(tempfile.mkdtemp())


def setup_directories():
    """Create the necessary directories in ~/.sutra"""
    console.info("Setting up ~/.sutra directory structure...")

    directories = [
        INSTALL_DIR / "config",
        INSTALL_DIR / "models",
        INSTALL_DIR / "build",
        INSTALL_DIR / "data",
        INSTALL_DIR / "data" / "sessions",
        INSTALL_DIR / "data" / "file_changes",
        INSTALL_DIR / "data" / "edits",
        INSTALL_DIR / "parser_results",
        INSTALL_DIR / "logs",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        console.info(f"Created directory: {directory}")

    console.success("Directory structure created successfully")


def download_file(url: str, destination: Path) -> bool:
    """Download a file from URL to destination with Rich progress display"""
    try:
        console.info(f"Starting download from {url}")

        # Create progress bar for download
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Downloading"),
            BarColumn(bar_width=40),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "•",
            DownloadColumn(),
            "•",
            TransferSpeedColumn(),
            "•",
            TimeRemainingColumn(),
            console=console.console,
        ) as progress:
            # Create task
            task = progress.add_task("download", total=None)

            def progress_hook(block_num, block_size, total_size):
                """Progress callback for urlretrieve"""
                if total_size > 0:
                    downloaded = block_num * block_size
                    # Update total size on first call
                    if progress.tasks[task].total is None:
                        progress.update(task, total=total_size)
                    # Update progress
                    progress.update(task, completed=min(downloaded, total_size))

            urlretrieve(url, destination, reporthook=progress_hook)

        console.success(
            f"Downloaded {destination.name} ({destination.stat().st_size / (1024*1024):.1f}MB)"
        )
        return True

    except URLError as e:
        console.error(f"Failed to download {url}: {e}")
        return False


def extract_tar_gz(archive_path: Path, extract_to: Path) -> bool:
    """Extract a tar.gz file with Rich progress display"""
    try:
        console.info(f"Extracting {archive_path.name}")

        with tarfile.open(archive_path, "r:gz") as tar:
            members = tar.getmembers()
            total_files = len(members)

            # Create progress bar for extraction
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold green]Extracting"),
                BarColumn(bar_width=40),
                TaskProgressColumn(),
                "•",
                TextColumn("{task.description}"),
                console=console.console,
            ) as progress:
                task = progress.add_task(
                    total=total_files, description=f"0/{total_files} files"
                )

                for i, member in enumerate(members, 1):
                    tar.extract(member, extract_to)
                    progress.update(
                        task, completed=i, description=f"{i}/{total_files} files"
                    )

        console.success(f"Extracted {archive_path.name} ({total_files} files)")
        return True

    except Exception as e:
        console.error(f"Failed to extract {archive_path}: {e}")
        return False


def setup_models() -> bool:
    """Download and setup ML models"""
    console.info("Setting up ML models from remote repository...")

    models_url = f"{REPO_URL}/releases/download/{RELEASE_TAG}/all-MiniLM-L12-v2.tar.gz"
    models_dir = INSTALL_DIR / "models"

    # Download models
    archive_path = TEMP_DIR / "all-MiniLM-L12-v2.tar.gz"
    if not download_file(models_url, archive_path):
        console.warning("Failed to download models, continuing without them")
        return False

    # Extract models
    if extract_tar_gz(archive_path, TEMP_DIR):
        model_src = TEMP_DIR / "all-MiniLM-L12-v2"
        model_dest = models_dir / "all-MiniLM-L12-v2"

        if model_src.exists():
            if model_dest.exists():
                shutil.rmtree(model_dest)
            shutil.copytree(model_src, model_dest)
            console.success(f"Models installed to {model_dest}")
            return True
        else:
            console.error("Model extraction failed - directory not found")
            return False

    return False


def setup_configuration():
    """Setup configuration files"""
    console.info("Setting up configuration files...")

    config_dir = INSTALL_DIR / "config"

    system_config = {
        "database": {
            "knowledge_graph_db": f"{INSTALL_DIR}/data/knowledge_graph.db",
            "embeddings_db": f"{INSTALL_DIR}/data/knowledge_graph_embeddings.db",
            "connection_timeout": 60,
            "max_retry_attempts": 5,
            "batch_size": 1000,
        },
        "storage": {
            "data_dir": f"{INSTALL_DIR}/data",
            "sessions_dir": f"{INSTALL_DIR}/data/sessions",
            "file_changes_dir": f"{INSTALL_DIR}/data/file_changes",
            "file_edits_dir": f"{INSTALL_DIR}/data/edits",
            "parser_results_dir": f"{INSTALL_DIR}/parser_results",
            "models_dir": f"{INSTALL_DIR}/models",
        },
        "embedding": {
            "model_path": f"{INSTALL_DIR}/models/all-MiniLM-L12-v2",
            "tokenizer_max_length": 256,
            "max_tokens": 240,
            "overlap_tokens": 30,
        },
        "web_search": {"api_key": "", "requests_per_minute": 60, "timeout": 30},
        "web_scrap": {
            "timeout": 30,
            "max_retries": 3,
            "delay_between_retries": 1.0,
            "include_comments": True,
            "include_tables": True,
            "include_images": True,
            "include_links": True,
            "trafilatura_config": {},
            "markdown_options": {"heading_style": "ATX", "bullets": "-", "wrap": True},
        },
        "logging": {
            "level": "INFO",
            "format": "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
            "logs_dir": f"{INSTALL_DIR}/logs",
        },
        "llm": {
            "provider": "",
            "aws_bedrock": {
                "access_key_id": "",
                "secret_access_key": "",
                "region": "",
                "model_id": "",
                "max_tokens": "",
            },
            "anthropic": {
                "api_key": "",
                "model_id": "",
                "max_tokens": "",
            },
            "google_ai": {
                "api_key": "",
                "model_id": "",
                "base_url": "https://generativelanguage.googleapis.com/v1beta",
                "max_tokens": "",
            },
            "vertex_ai": {
                "location": "",
                "model_id": "",
                "max_tokens": "",
            },
            "azure_openai": {
                "api_key": "",
                "base_url": "https://your-resource-name.openai.azure.com/openai/deployments/your-deployment-id",
                "api_version": "",
                "max_tokens": "",
            },
            "openai": {
                "api_key": "",
                "model_id": "",
                "max_tokens": "",
            },
            "azure_aifoundry": {
                "api_key": "",
                "base_url": "https://RESOURCE_NAME.REGION.models.ai.azure.com",
                "max_tokens": "",
            },
            "openrouter": {
                "api_key": "",
                "model_id": "",
                "http_referer": "",
                "x_title": "",
                "max_tokens": "",
            },
            "superllm": {},
        },
    }

    system_config_path = config_dir / "system.json"
    with open(system_config_path, "w") as f:
        json.dump(system_config, f, indent=2)
    console.success(f"System configuration created at {system_config_path}")


def setup_environment():
    """Setup environment variables"""
    console.info("Setting up environment variables...")

    config_file = INSTALL_DIR / "config" / "system.json"

    # Detect shell and setup environment
    shell = os.environ.get("SHELL", "/bin/bash")

    if "zsh" in shell:
        rc_file = Path.home() / ".zshrc"
    elif "fish" in shell:
        rc_file = Path.home() / ".config" / "fish" / "config.fish"
        rc_file.parent.mkdir(parents=True, exist_ok=True)
    else:
        rc_file = Path.home() / ".bashrc"

    # Add environment variable if not already present
    env_line = f'export SUTRAKNOWLEDGE_CONFIG="{config_file}"'

    if rc_file.exists():
        with open(rc_file, "r") as f:
            content = f.read()

        if "SUTRAKNOWLEDGE_CONFIG" not in content:
            with open(rc_file, "a") as f:
                f.write(f"\n# Sutra Knowledge CLI\n{env_line}\n")
            console.success(f"Added SUTRAKNOWLEDGE_CONFIG to {rc_file}")
        else:
            console.info("SUTRAKNOWLEDGE_CONFIG already set in shell configuration")
    else:
        with open(rc_file, "w") as f:
            f.write(f"# Sutra Knowledge CLI\n{env_line}\n")
    console.success(f"Created {rc_file} with SUTRAKNOWLEDGE_CONFIG")

    # Set for current session
    os.environ["SUTRAKNOWLEDGE_CONFIG"] = str(config_file)
    console.info("Environment variable set for current session")


def _check_vertex_ai_auth():
    """Check and prompt for Vertex AI authentication if needed."""
    try:
        import subprocess

        # Check if gcloud is installed
        try:
            result = subprocess.run(
                ["gcloud", "--version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                console.warning("Google Cloud SDK (gcloud) is not installed.")
                console.print(
                    "   Install it from: https://cloud.google.com/sdk/docs/install"
                )
                console.print("   After installation, run: gcloud init")
                return
        except (FileNotFoundError, subprocess.TimeoutExpired):
            console.warning(
                "Google Cloud SDK (gcloud) is not installed or not accessible."
            )
            console.print(
                "   Install it from: https://cloud.google.com/sdk/docs/install"
            )
            console.print("   After installation, run: gcloud init")
            return

        # Check if authenticated
        try:
            result = subprocess.run(
                [
                    "gcloud",
                    "auth",
                    "application-default",
                    "print-access-token",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                # Successfully authenticated
                return
        except subprocess.TimeoutExpired:
            pass

        # Not authenticated, show setup steps and exit
        console.print("\n🔐 Vertex AI Authentication Required")
        console.warning(
            "   You need to authenticate with Google Cloud to use Vertex AI."
        )
        console.print("   Steps:")
        console.print("   1. Run: gcloud init (if not done already)")
        console.print(
            "   2. Run: gcloud auth application-default login --project YOUR_PROJECT_ID"
        )
        console.print("\n   After completing these steps, run the command again.")

    except Exception:
        # Silent fail for authentication check
        pass


def check_dependencies():
    """Check if ripgrep is installed and install if missing"""
    console.info("Checking dependencies...")

    try:
        subprocess.run(["rg", "--version"], check=True, capture_output=True)
        console.success("ripgrep is already installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        console.warning("ripgrep not found. Please install it manually:")
        console.info("  Ubuntu/Debian: sudo apt-get install ripgrep")
        console.info("  macOS: brew install ripgrep")
        console.info("  CentOS/RHEL: sudo yum install ripgrep")
        console.info("  Arch Linux: sudo pacman -S ripgrep")


def cleanup():
    """Clean up temporary files"""
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
        console.info("Cleaned up temporary files")


def main():
    """Main setup function"""
    print("🚀 Sutra Knowledge CLI - Post-Install Setup")
    print("=" * 50)

    try:
        # Check if already installed
        if INSTALL_DIR.exists():
            console.warning(f"Sutra CLI directory already exists at {INSTALL_DIR}")
            response = input("Do you want to reinstall? (y/N): ").strip().lower()
            if response not in ["y", "yes"]:
                console.info("Installation cancelled")
                return
            shutil.rmtree(INSTALL_DIR)

        # Setup steps
        setup_directories()
        setup_configuration()
        check_dependencies()

        # Try to setup models and parsers (non-blocking)
        models_success = setup_models()

        # Setup environment
        setup_environment()

        # Summary
        print("\n" + "=" * 50)
        console.success("🎉 Sutra Knowledge CLI setup completed!")
        print(f"\n📁 Installation directory: {INSTALL_DIR}")
        print(f"🔧 Configuration: {INSTALL_DIR / 'config' / 'system.json'}")

        if models_success:
            print(f"📦 Models: {INSTALL_DIR / 'models'}")
        else:
            console.warning(
                "Models setup failed - you may need to install them manually"
            )

        print("\n🚀 Usage:")
        print("  sutrakit --help                    # Show help")
        print("  sutrakit                          # Analyze current directory")
        print("  sutrakit --directory /path/to/repo # Analyze specific directory")
        print("\n💡 Restart your shell or run: source ~/.bashrc")
        print("💡 Configure your API keys in ~/.sutra/config/system.json")

    except KeyboardInterrupt:
        console.info("Installation cancelled by user")
    except Exception as e:
        console.error(f"Installation failed: {e}")
        return 1
    finally:
        cleanup()

    return 0


class PostDevelopCommand(develop):
    """Post-installation for development mode."""

    def run(self):
        if develop:
            develop.run(self)
        main()


class PostInstallCommand(install):
    """Post-installation for installation mode."""

    def run(self):
        if install:
            install.run(self)
        main()


if __name__ == "__main__":
    sys.exit(main())
