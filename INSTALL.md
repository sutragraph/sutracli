
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

## Essential Configuration

After installation, you need to configure your preferred LLM provider by editing the system configuration:

- **System Configuration**: `~/.sutra/config/system.json`
- **Parser Configuration**: `~/.sutra/config/parsers.json`

### Supported LLM Providers

The following providers are supported in the configuration:

1. **AWS Bedrock** (`"provider": "aws_bedrock"`)
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_MODEL_ID`
   - `AWS_REGION`

2. **Anthropic Claude** (`"provider": "anthropic"`)
   - `ANTHROPIC_API_KEY`
   - `ANTHROPIC_MODEL_ID`

3. **OpenAI** (`"provider": "openai"`)
   - `OPENAI_API_KEY`
   - `OPENAI_MODEL_ID`

4. **Google Gemini** (`"provider": "google_ai"`)
   - `GEMINI_API_KEY`
   - `GEMINI_MODEL_ID`

5. **Google Vertex AI** (`"provider": "vertex_ai"`)
   - `GCP_LOCATION`
   - `GCP_MODEL_ID`
   - **Authentication**: Uses `gcloud` authentication. Run:
     ```bash
     gcloud auth application-default login --project YOUR_PROJECT_ID
     ```
   - Ensure your GCP project has Vertex AI enabled

6. **Azure OpenAI** (`"provider": "azure_openai"`)
   - `AZURE_OPENAI_API_KEY`
   - `AZURE_RESOURCE_NAME`
   - `AZURE_DEPLOYMENT_ID`
   - `AZURE_API_VERSION`
   - `AZURE_ENDPOINT`
   - `AZURE_MODEL_ID`

### Example Configuration

```json
{
  "llm": {
    "provider": "anthropic",
    "anthropic": {
      "api_key": "your-api-key-here",
      "model_id": "claude-sonnet-4-20250514"
    }
  }
}
```

Refer to the configuration documentation for detailed customization options.
