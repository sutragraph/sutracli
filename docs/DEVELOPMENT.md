# Development Guide

This document provides information for developers working on the SutraKit project.

## Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality and keep BAML client files synchronized with source changes.

### What the Pre-commit Hooks Do

1. **BAML Client Generation** (`baml-generate`)
   - Automatically regenerates BAML client files when `baml_src/` files are modified
   - Handles version compatibility issues gracefully
   - Uses the custom `scripts/generate-baml.sh` script
   - Adds updated client files to the commit automatically

2. **Code Quality Checks**
   - **Trailing Whitespace**: Removes trailing whitespace from files
   - **End of File**: Ensures files end with a newline
   - **YAML/JSON/TOML Validation**: Validates configuration files
   - **Large Files**: Prevents accidentally committing large files (>1MB)
   - **Merge Conflicts**: Detects unresolved merge conflict markers
   - **Debug Statements**: Warns about Python debug statements

3. **Code Formatting**
   - **Black**: Formats Python code according to Black standards
   - **isort**: Sorts Python imports consistently
   - **Note**: Generated BAML client files are excluded from formatting

### Setup

#### Quick Setup
```bash
./scripts/setup-dev.sh
```

#### Manual Setup
```bash
# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Test the setup
pre-commit run --all-files
```

### Usage

Pre-commit hooks run automatically on `git commit`. You can also run them manually:

```bash
# Run all hooks on all files
pre-commit run --all-files

# Run specific hook
pre-commit run baml-generate

# Run hooks on specific files
pre-commit run --files baml_src/types.baml
```

### BAML Development Workflow

1. **Modify BAML files** in `baml_src/`
2. **Commit your changes** - the pre-commit hook will:
   - Attempt to regenerate BAML client files
   - Add updated client files to your commit
   - Run code quality checks
3. **If BAML generation fails** (due to version compatibility):
   - The commit will still proceed with existing client files
   - You'll see helpful instructions for manual generation
   - For production deployments, ensure client files are up-to-date

### Manual BAML Generation

If you need to manually regenerate BAML client files:

```bash
# Using the project script (recommended)
./scripts/generate-baml.sh

# Using baml-cli directly (if compatible version available)
baml-cli generate --from baml_src --to baml_client

# Using Python module
python -m baml_cli generate --from baml_src --to baml_client
```

### Version Compatibility Notes

- The project uses `baml-py==0.206.0` for runtime
- Older `baml-cli` versions may be incompatible due to API changes
- The pre-commit hook handles this gracefully and provides guidance
- Pre-generated client files are included in the package distribution

### Troubleshooting

#### Pre-commit Hook Fails
```bash
# Check hook configuration
pre-commit validate-config

# Update hook repositories
pre-commit autoupdate

# Clear cache and reinstall
pre-commit clean
pre-commit install
```

#### BAML Generation Issues
```bash
# Check BAML configuration
cat baml_src/baml.toml

# Verify baml-py installation
python -c "import baml_py; print(baml_py.__version__)"

# Test generation script
./scripts/generate-baml.sh
```

#### Code Formatting Issues
```bash
# Run Black manually
black --exclude baml_client/ .

# Run isort manually
isort --profile black --skip baml_client .
```

### Configuration Files

- **`.pre-commit-config.yaml`**: Pre-commit hook configuration
- **`scripts/generate-baml.sh`**: BAML generation script with error handling
- **`scripts/setup-dev.sh`**: Development environment setup script
- **`pyproject.toml`**: Project configuration including dev dependencies

### Best Practices

1. **Always run pre-commit hooks** before pushing changes
2. **Keep BAML source files clean** and well-documented
3. **Test BAML changes** in development before committing
4. **Don't manually edit** files in `baml_client/` - they're auto-generated
5. **Include meaningful commit messages** when modifying BAML configurations

### Contributing

When contributing to the project:

1. Set up the development environment using `./scripts/setup-dev.sh`
2. Make your changes following the project's coding standards
3. Ensure all pre-commit hooks pass
4. Test your changes thoroughly
5. Submit a pull request with a clear description

The pre-commit hooks will help ensure your contributions meet the project's quality standards and maintain consistency across the codebase.
