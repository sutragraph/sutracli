
# Sutra CLI Installation Guide

## Overview

Sutra CLI is a knowledge management command-line interface that provides intelligent code analysis and semantic search capabilities. This guide covers installation on Linux and macOS systems using bash terminal.

## System Requirements

### Supported Platforms
- **Linux** (Ubuntu, Debian, CentOS, RHEL, Fedora, Arch Linux)
- **macOS** (with Homebrew recommended)
- **Terminal**: Bash shell required
- **Windows**: Not currently supported

### Prerequisites

The installation script will automatically check and install missing prerequisites:

- **Python 3.x** with pip
- **curl** for downloading files
- **tar** for extracting archives
- **PyInstaller** (auto-installed if missing)
- **ripgrep** (auto-installed if missing)

## Installation

### Quick Install

1. **Clone or download the repository**:
   ```bash
   git clone <repository -url>
   cd sutracli
   ```

2. **Run the installation script**:
   ```bash
   bash scripts/build_and_setup.sh
   ```

3. **Restart your shell or source your profile**:
   ```bash
   # For bash users
   source ~/.bashrc
   
   # For zsh users
   source ~/.zshrc
   ```

### Installation Process

The `build_and_setup.sh` script performs the following steps:

1. **Prerequisites Check**: Verifies and installs required tools
2. **Build Executable**: Compiles the Sutra CLI using PyInstaller
3. **Download Models**: Fetches ML models from GitHub releases
4. **Install Parsers**: Downloads and installs tree-sitter parsers
5. **Configuration Setup**: Installs configuration files
6. **Global Installation**: Installs to `~/.sutra` directory
7. **Environment Setup**: Adds CLI to PATH
8. **Installation Test**: Verifies successful installation

### Installation Directory Structure

After installation, Sutra CLI will be installed to `~/.sutra/` with the following structure:

```
~/.sutra/
├── bin/sutra              # Main executable
├── config/
│   ├── system.json        # System configuration
│   └── parsers.json       # Parser configuration
├── models/
│   └── all-MiniLM-L12-v2/ # ML models for semantic search
├── build/                 # Tree-sitter parser libraries
├── data/                  # User data directory
└── logs/                  # Application logs
```

## Usage

Once installed, you can use Sutra CLI with the following commands:

```bash
# Show help and available options
sutra --help

# Analyze current directory
sutra

# Analyze specific directory
sutra --directory /path/to/your/project

# Check version
sutra --version
```

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure you have write permissions to your home directory
   ```bash
   chmod +x scripts/build_and_setup.sh
   ```

2. **Python/Pip Not Found**: Install Python 3 and pip for your system
   ```bash
   # Ubuntu/Debian
   sudo apt-get install python3 python3-pip
   
   # CentOS/RHEL
   sudo yum install python3 python3-pip
   
   # macOS
   brew install python3
   ```

3. **Command Not Found After Installation**: Restart your terminal or source your shell configuration
   ```bash
   source ~/.bashrc  # or ~/.zshrc for zsh users
   ```

4. **Build Failures**: Ensure you're running from the project root directory where `cli/sutra_cli.py` exists

### Reinstallation

If you need to reinstall Sutra CLI:

1. The script will detect existing installation and prompt for confirmation
2. Or manually remove the installation:
   ```bash
   rm -rf ~/.sutra
   # Remove PATH entries from your shell RC file manually
   ```

### Getting Help

- Check the logs in `~/.sutra/logs/` for detailed error information
- Ensure all prerequisites are properly installed
- Verify you're running the script from the correct project directory

## Uninstallation

To completely remove Sutra CLI:

1. **Remove installation directory**:
   ```bash
   rm -rf ~/.sutra
   ```

2. **Remove PATH entries** from your shell configuration file (`~/.bashrc`, `~/.zshrc`, etc.):
   ```bash
   # Remove these lines from your shell RC file:
   export PATH="$HOME/.sutra/bin:$PATH"
   export SUTRAKNOWLEDGE_CONFIG="$HOME/.sutra/config/system.json"
   ```

3. **Restart your shell** or source your configuration file

## Advanced Configuration

After installation, you can customize Sutra CLI by editing:

- **System Configuration**: `~/.sutra/config/system.json`
- **Parser Configuration**: `~/.sutra/config/parsers.json`

Refer to the configuration documentation for detailed customization options.
