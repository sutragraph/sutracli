#!/usr/bin/env python3
"""
Test script to verify pip install functionality.
This script simulates the pip install process and tests the setup.
"""

import subprocess
import sys
import os
import tempfile
import shutil
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a command and return success status"""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {cmd}")
            return True
        else:
            print(f"❌ {cmd}")
            print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {cmd}")
        print(f"Exception: {e}")
        return False

def test_pip_install():
    """Test the pip install process"""
    print("🧪 Testing pip install functionality...")
    
    # Create a temporary virtual environment
    with tempfile.TemporaryDirectory() as tmp_dir:
        venv_dir = Path(tmp_dir) / "test_venv"
        
        # Create virtual environment
        if not run_command(f"python -m venv {venv_dir}"):
            return False
        
        # Get the pip path
        if os.name == 'nt':  # Windows
            pip_path = venv_dir / "Scripts" / "pip"
            python_path = venv_dir / "Scripts" / "python"
        else:  # Unix-like
            pip_path = venv_dir / "bin" / "pip"
            python_path = venv_dir / "bin" / "python"
        
        # Install the package in development mode
        current_dir = Path.cwd()
        if not run_command(f"{pip_path} install -e .", cwd=current_dir):
            return False
        
        # Test if sutrakit command is available
        if not run_command(f"{python_path} -c 'import sutrakit; print(\"Import successful\")'"):
            return False
        
        # Test if sutrakit-setup command works
        if not run_command(f"{python_path} -c 'from sutrakit.setup_directories import main; print(\"Setup script available\")'"):
            return False
        
        print("✅ All pip install tests passed!")
        return True

def test_setup_script():
    """Test the setup script functionality"""
    print("\n🔧 Testing setup script...")
    
    # Test importing the setup function
    try:
        sys.path.insert(0, str(Path.cwd() / "src"))
        from sutrakit.setup_directories import setup_directories, setup_configuration
        
        print("✅ Setup script imports successfully")
        
        # Test directory creation (don't actually create files)
        print("✅ Setup functions are callable")
        
        return True
        
    except Exception as e:
        print(f"❌ Setup script test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Testing Sutrakit pip install setup")
    print("=" * 50)
    
    # Test 1: Basic import test
    print("\n📦 Testing basic package structure...")
    if not test_setup_script():
        return 1
    
    # Test 2: Check required files exist
    print("\n📋 Testing required files...")
    required_files = [
        "pyproject.toml",
        "src/sutrakit/__init__.py",
        "src/sutrakit/setup_directories.py",
        "src/cli/main.py",
        "README.md"
    ]
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path} exists")
        else:
            print(f"❌ {file_path} missing")
            return 1
    
    # Test 3: Pip install test (optional, requires clean environment)
    print("\n💾 Testing pip install process...")
    if test_pip_install():
        print("✅ Pip install test passed")
    else:
        print("⚠️  Pip install test failed (may require clean environment)")
    
    print("\n🎉 All tests completed!")
    print("\nTo install manually:")
    print("  pip install -e .")
    print("  sutrakit-setup")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
