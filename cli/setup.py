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
    """Download a file from URL to destination"""
    try:
        console.info(f"Downloading {url}...")
        urlretrieve(url, destination)
        console.success(f"Downloaded {destination.name}")
        return True
    except URLError as e:
        console.error(f"Failed to download {url}: {e}")
        return False


def extract_tar_gz(archive_path: Path, extract_to: Path) -> bool:
    """Extract a tar.gz file"""
    try:
        console.info(f"Extracting {archive_path}...")
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(extract_to)
        console.success(f"Extracted {archive_path.name}")
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

    # Create system configuration
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
            "llama_model_id": "meta/llama-3.1-8b-instruct",
            "claude_model": "us.anthropic.claude-sonnet-4-20250514-v1:0",
            "gemini_model": "gemini-1.5-flash",
            "aws": {
                "model_id": "us.anthropic.claude-sonnet-4-20250514-v1:0",
                "access_key_id": "",
                "secret_access_key": "",
                "region": "us-east-2",
            },
            "anthropic": {
                "api_key": "",
                "model_id": "us.anthropic.claude-sonnet-4-20250514-v1:0",
            },
            "gcp": {
                "api_key": "",
                "project_id": "",
                "location": "us-central1",
                "llm_endpoint": "https://us-central1-aiplatform.googleapis.com/v1/projects/{project_id}/locations/us-central1/endpoints/openapi/chat/completions",
            },
            "superllm": {
                "api_endpoint": "http://localhost:8000",
                "firebase_token": "",
                "default_model": "gpt-3.5-turbo",
                "default_provider": "openai",
            },
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


def setup_baml_environment():
    """Set up BAML environment variables from config at module level."""
    try:
        # Import here to avoid circular imports
        from src.config.settings import get_config

        # Use the config function to get loaded config
        config = get_config()

        # Environment variable mapping for each provider
        ENV_VAR_MAPPING = {
            "aws": {
                "AWS_ACCESS_KEY_ID": "access_key_id",
                "AWS_SECRET_ACCESS_KEY": "secret_access_key",
                "AWS_MODEL_ID": "model_id",
                "AWS_REGION": "region",
            },
            "openai": {"OPENAI_API_KEY": "api_key", "OPENAI_MODEL_ID": "model_id"},
            "anthropic": {
                "ANTHROPIC_API_KEY": "api_key",
                "ANTHROPIC_MODEL_ID": "model_id",
            },
            "gcp": {"GOOGLE_API_KEY": "api_key", "GOOGLE_MODEL_ID": "model_id"},
        }

        # Check if config has llm attribute
        if not hasattr(config, "llm") or not config.llm:
            return

        provider = config.llm.provider.lower()
        if provider not in ENV_VAR_MAPPING:
            return

        # Get provider-specific config
        provider_config = getattr(config.llm, provider, None)
        if not provider_config:
            return

        # Set environment variables
        env_mapping = ENV_VAR_MAPPING[provider]
        for env_var, config_key in env_mapping.items():
            # Only set if not already set and config value exists
            if env_var not in os.environ:
                value = getattr(provider_config, config_key, None)
                if value:
                    os.environ[env_var] = str(value)

        os.environ["BAML_LOG"] = "OFF"

    except Exception as e:
        # Silent fail - don't break CLI if environment setup fails
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
