# Sutrakit Installation Guide

## Quick Install with pip

You can install Sutrakit directly from the repository using pip:

```bash
# Install sutrakit
pip install git+https://github.com/sutragraph/sutracli.git

# Setup the ~/.sutra directory and download models/parsers
sutrakit-setup
```

## Manual Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/sutragraph/sutracli.git
   cd sutracli
   ```

2. **Install with pip**:
   ```bash
   pip install -e .
   ```

3. **Setup the environment**:
   ```bash
   sutrakit-setup
   ```

## Installation Steps

The `sutrakit-setup` command performs the following actions:

1. **Creates ~/.sutra directory structure**:
   ```
   ~/.sutra/
   ├── config/
   │   ├── system.json      # System configuration
   │   └── parsers.json     # Parser configuration
   ├── models/              # ML models for semantic search
   ├── build/               # Tree-sitter parser libraries
   ├── data/                # User data directory
   └── logs/                # Application logs
   ```

2. **Downloads required components**:
   - ML models (all-MiniLM-L12-v2) for semantic search
   - Tree-sitter parser libraries for code parsing

3. **Sets up configuration**:
   - Creates system.json with LLM provider settings
   - Creates parsers.json with language parser configurations
   - Sets SUTRAKNOWLEDGE_CONFIG environment variable

4. **Checks dependencies**:
   - Verifies ripgrep is installed (required for code search)

## Configuration

After installation, configure your API keys in `~/.sutra/config/system.json`:

```json
{
  "llm": {
    "anthropic": {
      "api_key": "your-anthropic-api-key",
      "model": "claude-3-5-sonnet-20241022"
    },
    "openai": {
      "api_key": "your-openai-api-key",
      "model": "gpt-4o-mini"
    },
    "gcp": {
      "api_key": "your-gcp-api-key",
      "project_id": "your-project-id",
      "location": "us-central1",
      "model": "gemini-1.5-flash"
    }
  },
  "web_search": {
    "api_key": "your-google-search-api-key",
    "search_engine_id": "your-search-engine-id",
    "provider": "google"
  }
}
```

## Usage

Once installed and configured:

```bash
# Analyze current directory
sutrakit
```

## Troubleshooting

### Common Issues

1. **Missing ripgrep**: Install ripgrep for your system:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install ripgrep
   
   # macOS
   brew install ripgrep
   
   # CentOS/RHEL
   sudo yum install ripgrep
   ```

2. **Failed to download models/parsers**: 
   - Check internet connection
   - Models and parsers are downloaded from GitHub releases
   - You can continue without them, but functionality will be limited

3. **Configuration not found**:
   - Ensure SUTRAKNOWLEDGE_CONFIG is set: `echo $SUTRAKNOWLEDGE_CONFIG`
   - Run `sutrakit-setup` again to recreate configuration

4. **Permission errors**:
   - Ensure you have write permissions to your home directory
   - Check that ~/.sutra directory is not owned by root

### Manual Setup

If automatic setup fails, you can manually:

1. Create the directory structure:
   ```bash
   mkdir -p ~/.sutra/{config,models,build,data,logs}
   ```

2. Set the environment variable:
   ```bash
   echo 'export SUTRAKNOWLEDGE_CONFIG="$HOME/.sutra/config/system.json"' >> ~/.bashrc
   source ~/.bashrc
   ```

3. Create basic configuration files following the templates in the repository.

## Uninstallation

To remove Sutrakit:

```bash
# Remove the package
pip uninstall sutrakit

# Remove the data directory
rm -rf ~/.sutra

# Remove environment variable from your shell config
# (manually edit ~/.bashrc, ~/.zshrc, etc.)
```

## Development Installation

For development:

```bash
git clone https://github.com/sutragraph/sutracli.git
cd sutracli
pip install -e .
sutrakit-setup
```

This installs in editable mode, so changes to the code take effect immediately.
