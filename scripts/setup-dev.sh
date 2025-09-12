#!/bin/bash
# Development environment setup script
# This script sets up pre-commit hooks and other development tools

set -e

echo "🚀 Setting up development environment..."

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Error: This script must be run from the root of a git repository"
    exit 1
fi

# Install development dependencies
echo "📦 Installing development dependencies..."
if command -v pip >/dev/null 2>&1; then
    pip install -e ".[dev]"
else
    echo "❌ Error: pip not found. Please install Python and pip first."
    exit 1
fi

# Install pre-commit hooks
echo "🔧 Installing pre-commit hooks..."
if command -v pre-commit >/dev/null 2>&1; then
    pre-commit install
    echo "✅ Pre-commit hooks installed successfully"
else
    echo "❌ Error: pre-commit not found. Installing..."
    pip install pre-commit
    pre-commit install
    echo "✅ Pre-commit hooks installed successfully"
fi

# Test the BAML generation script
echo "🧪 Testing BAML generation script..."
if [ -x "scripts/generate-baml.sh" ]; then
    ./scripts/generate-baml.sh
else
    echo "⚠️  BAML generation script not found or not executable"
fi

# Run pre-commit on all files to test setup
echo "🔍 Running pre-commit on all files to test setup..."
pre-commit run --all-files || echo "⚠️  Some pre-commit checks failed, but setup is complete"

echo ""
echo "✅ Development environment setup complete!"
echo ""
echo "📋 Next steps:"
echo "   • Pre-commit hooks are now active and will run automatically on git commit"
echo "   • BAML client files will be regenerated when baml_src/ files change"
echo "   • Run 'pre-commit run --all-files' to manually run all hooks"
echo "   • Run './scripts/generate-baml.sh' to manually regenerate BAML client"
echo ""
echo "🎉 Happy coding!"
