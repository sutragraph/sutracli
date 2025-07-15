#!/usr/bin/env python3
"""
Post-install setup script for Sutra CLI.
This script sets up the ~/.sutra directory and downloads required models and parsers.
"""

import os
import sys
import json
import shutil
import tempfile
import subprocess
from pathlib import Path
from urllib.request import urlretrieve
from urllib.error import URLError
import tarfile
import zipfile
from typing import Optional, Dict, Any

try:
    from setuptools.command.develop import develop
    from setuptools.command.install import install
except ImportError:
    develop = None
    install = None

# Configuration
REPO_URL = "https://github.com/sutragraph/models"
RELEASE_TAG = "v0.2"
INSTALL_DIR = Path.home() / ".sutra"
TEMP_DIR = Path(tempfile.mkdtemp())

# Color codes for output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def log_info(msg: str):
    print(f"{Colors.BLUE}[INFO]{Colors.NC} {msg}")

def log_success(msg: str):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {msg}")

def log_warning(msg: str):
    print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {msg}")

def log_error(msg: str):
    print(f"{Colors.RED}[ERROR]{Colors.NC} {msg}")

def setup_directories():
    """Create the necessary directories in ~/.sutra"""
    log_info("Setting up ~/.sutra directory structure...")
    
    directories = [
        INSTALL_DIR / "config",
        INSTALL_DIR / "models",
        INSTALL_DIR / "build",
        INSTALL_DIR / "data",
        INSTALL_DIR / "logs"
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        log_info(f"Created directory: {directory}")
    
    log_success("Directory structure created successfully")

def download_file(url: str, destination: Path) -> bool:
    """Download a file from URL to destination"""
    try:
        log_info(f"Downloading {url}...")
        urlretrieve(url, destination)
        log_success(f"Downloaded {destination.name}")
        return True
    except URLError as e:
        log_error(f"Failed to download {url}: {e}")
        return False

def extract_tar_gz(archive_path: Path, extract_to: Path) -> bool:
    """Extract a tar.gz file"""
    try:
        log_info(f"Extracting {archive_path}...")
        with tarfile.open(archive_path, 'r:gz') as tar:
            tar.extractall(extract_to)
        log_success(f"Extracted {archive_path.name}")
        return True
    except Exception as e:
        log_error(f"Failed to extract {archive_path}: {e}")
        return False

def setup_models() -> bool:
    """Download and setup ML models"""
    log_info("Setting up ML models from remote repository...")
    
    models_url = f"{REPO_URL}/releases/download/{RELEASE_TAG}/all-MiniLM-L12-v2.tar.gz"
    models_dir = INSTALL_DIR / "models"
    
    # Download models
    archive_path = TEMP_DIR / "all-MiniLM-L12-v2.tar.gz"
    if not download_file(models_url, archive_path):
        log_warning("Failed to download models, continuing without them")
        return False
    
    # Extract models
    if extract_tar_gz(archive_path, TEMP_DIR):
        model_src = TEMP_DIR / "all-MiniLM-L12-v2"
        model_dest = models_dir / "all-MiniLM-L12-v2"
        
        if model_src.exists():
            if model_dest.exists():
                shutil.rmtree(model_dest)
            shutil.copytree(model_src, model_dest)
            log_success(f"Models installed to {model_dest}")
            return True
        else:
            log_error("Model extraction failed - directory not found")
            return False
    
    return False

def setup_parsers() -> bool:
    """Download and setup tree-sitter parsers"""
    log_info("Setting up tree-sitter parsers from remote repository...")
    
    parsers_url = f"{REPO_URL}/releases/download/{RELEASE_TAG}/tree-sitter-build.tar.gz"
    build_dir = INSTALL_DIR / "build"
    
    # Download parsers
    archive_path = TEMP_DIR / "tree-sitter-build.tar.gz"
    if not download_file(parsers_url, archive_path):
        log_warning("Failed to download parsers, continuing without them")
        return False
    
    # Extract parsers
    if extract_tar_gz(archive_path, TEMP_DIR):
        parser_src = TEMP_DIR / "build"
        
        if parser_src.exists():
            # Copy parser files to build directory
            for item in parser_src.iterdir():
                dest_item = build_dir / item.name
                if item.is_dir():
                    if dest_item.exists():
                        shutil.rmtree(dest_item)
                    shutil.copytree(item, dest_item)
                else:
                    shutil.copy2(item, dest_item)
            
            log_success(f"Parsers installed to {build_dir}")
            
            # List installed parsers
            log_info("Installed parser libraries:")
            for parser_file in build_dir.glob("*.so"):
                log_info(f"  - {parser_file.name}")
            for parser_file in build_dir.glob("*.dylib"):
                log_info(f"  - {parser_file.name}")
            
            return True
        else:
            log_error("Parser extraction failed - directory not found")
            return False
    
    return False

def setup_configuration():
    """Setup configuration files"""
    log_info("Setting up configuration files...")
    
    config_dir = INSTALL_DIR / "config"
    
    # Create system configuration
    system_config = {
        "llm": {
            "anthropic": {
                "api_key": "",
                "model": "claude-3-5-sonnet-20241022"
            },
            "openai": {
                "api_key": "",
                "model": "gpt-4o-mini"
            },
            "gcp": {
                "api_key": "",
                "project_id": "",
                "location": "us-central1",
                "model": "gemini-1.5-flash"
            }
        },
        "embeddings": {
            "local": {
                "model_path": str(INSTALL_DIR / "models" / "all-MiniLM-L12-v2"),
                "provider": "local_onnx"
            }
        },
        "web_search": {
            "api_key": "",
            "search_engine_id": "",
            "provider": "google"
        }
    }
    
    system_config_path = config_dir / "system.json"
    with open(system_config_path, 'w') as f:
        json.dump(system_config, f, indent=2)
    log_success(f"System configuration created at {system_config_path}")
    
    # Create parser configuration
    parser_config = {
        "build_directory": str(INSTALL_DIR / "build"),
        "languages": {
            "python": {
                "library": "libtree-sitter-python.so",
                "extensions": [".py"]
            },
            "javascript": {
                "library": "libtree-sitter-javascript.so",
                "extensions": [".js", ".mjs"]
            },
            "typescript": {
                "library": "libtree-sitter-typescript.so",
                "extensions": [".ts"]
            },
            "tsx": {
                "library": "libtree-sitter-tsx.so",
                "extensions": [".tsx"]
            },
            "java": {
                "library": "libtree-sitter-java.so",
                "extensions": [".java"]
            },
            "c": {
                "library": "libtree-sitter-c.so",
                "extensions": [".c", ".h"]
            },
            "cpp": {
                "library": "libtree-sitter-cpp.so",
                "extensions": [".cpp", ".hpp", ".cc", ".cxx"]
            },
            "rust": {
                "library": "libtree-sitter-rust.so",
                "extensions": [".rs"]
            },
            "go": {
                "library": "libtree-sitter-go.so",
                "extensions": [".go"]
            }
        }
    }
    
    parser_config_path = config_dir / "parsers.json"
    with open(parser_config_path, 'w') as f:
        json.dump(parser_config, f, indent=2)
    log_success(f"Parser configuration created at {parser_config_path}")

def setup_environment():
    """Setup environment variables"""
    log_info("Setting up environment variables...")
    
    config_file = INSTALL_DIR / "config" / "system.json"
    
    # Detect shell and setup environment
    shell = os.environ.get('SHELL', '/bin/bash')
    
    if 'zsh' in shell:
        rc_file = Path.home() / ".zshrc"
    elif 'fish' in shell:
        rc_file = Path.home() / ".config" / "fish" / "config.fish"
        rc_file.parent.mkdir(parents=True, exist_ok=True)
    else:
        rc_file = Path.home() / ".bashrc"
    
    # Add environment variable if not already present
    env_line = f'export SUTRAKNOWLEDGE_CONFIG="{config_file}"'
    
    if rc_file.exists():
        with open(rc_file, 'r') as f:
            content = f.read()
        
        if 'SUTRAKNOWLEDGE_CONFIG' not in content:
            with open(rc_file, 'a') as f:
                f.write(f"\n# Sutra Knowledge CLI\n{env_line}\n")
            log_success(f"Added SUTRAKNOWLEDGE_CONFIG to {rc_file}")
        else:
            log_info("SUTRAKNOWLEDGE_CONFIG already set in shell configuration")
    else:
        with open(rc_file, 'w') as f:
            f.write(f"# Sutra Knowledge CLI\n{env_line}\n")
        log_success(f"Created {rc_file} with SUTRAKNOWLEDGE_CONFIG")
    
    # Set for current session
    os.environ['SUTRAKNOWLEDGE_CONFIG'] = str(config_file)
    log_info("Environment variable set for current session")

def check_dependencies():
    """Check if ripgrep is installed and install if missing"""
    log_info("Checking dependencies...")
    
    try:
        subprocess.run(['rg', '--version'], check=True, capture_output=True)
        log_success("ripgrep is already installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        log_warning("ripgrep not found. Please install it manually:")
        log_info("  Ubuntu/Debian: sudo apt-get install ripgrep")
        log_info("  macOS: brew install ripgrep")
        log_info("  CentOS/RHEL: sudo yum install ripgrep")
        log_info("  Arch Linux: sudo pacman -S ripgrep")

def cleanup():
    """Clean up temporary files"""
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
        log_info("Cleaned up temporary files")

def main():
    """Main setup function"""
    print("🚀 Sutra Knowledge CLI - Post-Install Setup")
    print("=" * 50)
    
    try:
        # Check if already installed
        if INSTALL_DIR.exists():
            log_warning(f"Sutra CLI directory already exists at {INSTALL_DIR}")
            response = input("Do you want to reinstall? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                log_info("Installation cancelled")
                return
            shutil.rmtree(INSTALL_DIR)
        
        # Setup steps
        setup_directories()
        setup_configuration()
        check_dependencies()
        
        # Try to setup models and parsers (non-blocking)
        models_success = setup_models()
        parsers_success = setup_parsers()
        
        # Setup environment
        setup_environment()
        
        # Summary
        print("\n" + "=" * 50)
        log_success("🎉 Sutra Knowledge CLI setup completed!")
        print(f"\n📁 Installation directory: {INSTALL_DIR}")
        print(f"🔧 Configuration: {INSTALL_DIR / 'config' / 'system.json'}")
        
        if models_success:
            print(f"📦 Models: {INSTALL_DIR / 'models'}")
        else:
            log_warning("Models setup failed - you may need to install them manually")
        
        if parsers_success:
            print(f"🔨 Parsers: {INSTALL_DIR / 'build'}")
        else:
            log_warning("Parsers setup failed - you may need to install them manually")
        
        print("\n🚀 Usage:")
        print("  sutrakit --help                    # Show help")
        print("  sutrakit                          # Analyze current directory")
        print("  sutrakit --directory /path/to/repo # Analyze specific directory")
        print("\n💡 Restart your shell or run: source ~/.bashrc")
        print("💡 Configure your API keys in ~/.sutra/config/system.json")
        
    except KeyboardInterrupt:
        log_info("Installation cancelled by user")
    except Exception as e:
        log_error(f"Installation failed: {e}")
        return 1
    finally:
        cleanup()
    
    return 0

class PostDevelopCommand(develop if develop else object):
    """Post-installation for development mode."""
    
    def run(self):
        if develop:
            develop.run(self)
        main()


class PostInstallCommand(install if install else object):
    """Post-installation for installation mode."""
    
    def run(self):
        if install:
            install.run(self)
        main()


if __name__ == "__main__":
    sys.exit(main())
