#!/usr/bin/env python3
"""
Linter setup for Sutra CLI.
Downloads platform-specific linters and installs ESLint if Node.js is available.
"""

import os
import sys
import platform
import subprocess
import tempfile
import shutil
from pathlib import Path
from urllib.request import urlretrieve
from urllib.error import URLError
import tarfile

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

def detect_platform():
    """Detect the current platform and architecture."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if system == "linux":
        if machine in ["x86_64", "amd64"]:
            return "linux-x64"
        elif machine in ["aarch64", "arm64"]:
            return "linux-arm64"
    elif system == "darwin":
        if machine in ["x86_64", "amd64"]:
            return "macos-x64"
        elif machine in ["arm64", "aarch64"]:
            return "macos-arm64"
    
    raise ValueError(f"Unsupported platform: {system} {machine}")

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

def check_nodejs():
    """Check if Node.js is installed."""
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            log_success(f"Node.js found: {version}")
            return True
    except FileNotFoundError:
        pass

    log_warning("Node.js not found")
    return False

def setup_linters():
    """Download and setup linters for the current platform."""
    try:
        platform_name = detect_platform()
        log_info(f"Detected platform: {platform_name}")
    except ValueError as e:
        log_error(str(e))
        return False

    linters_url = (
        f"{REPO_URL}/releases/download/{RELEASE_TAG}/linters-{platform_name}.tar.gz"
    )
    linters_dir = INSTALL_DIR / "linters"

    # Create linters directory
    linters_dir.mkdir(parents=True, exist_ok=True)

    # Download linters bundle
    archive_path = TEMP_DIR / f"linters-{platform_name}.tar.gz"
    if not download_file(linters_url, archive_path):
        log_error("Failed to download linters bundle")
        return False

    # Extract linters to temp directory first
    extract_temp_dir = TEMP_DIR / "extracted"
    if not extract_tar_gz(archive_path, extract_temp_dir):
        log_error("Failed to extract linters bundle")
        return False

    # Move all linters from extracted subdirectory to linters folder
    for item in extract_temp_dir.rglob("*"):
        if item.is_file():
            # Move file directly to linters directory
            dest_path = linters_dir / item.name
            shutil.move(str(item), str(dest_path))
            dest_path.chmod(0o755)

    log_success(f"Linters installed to {linters_dir}")

    # List installed linters
    log_info("Installed linters:")
    for linter in linters_dir.iterdir():
        if linter.is_file() and os.access(linter, os.X_OK):
            log_info(f"  - {linter.name}")

    return True


def cleanup():
    """Clean up temporary files"""
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
        log_info("Cleaned up temporary files")

def main():
    """Main linter setup function"""
    print("🔧 Sutra CLI - Linter Setup")
    print("=" * 30)
    
    try:
        # Setup linters from bundle
        linters_success = setup_linters()
        
        # Summary
        print("\n" + "=" * 30)
        if linters_success:
            log_success("✅ Linters setup completed!")
        else:
            log_error("❌ Linters setup failed")
        
        log_warning("⚠️  ESLint will be handled by agent service if Node.js is available")
        
        print(f"\n📁 Linters directory: {INSTALL_DIR / 'linters'}")
        
        return 0 if linters_success else 1
        
    except KeyboardInterrupt:
        log_info("Setup cancelled by user")
        return 1
    except Exception as e:
        log_error(f"Setup failed: {e}")
        return 1
    finally:
        cleanup()

if __name__ == "__main__":
    sys.exit(main())
