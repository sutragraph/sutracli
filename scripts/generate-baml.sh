#!/bin/bash
# Script to generate BAML client files with proper error handling
# This script handles the version compatibility issues between baml-cli and baml-py

set -e

BAML_SRC_DIR="baml_src"
BAML_CLIENT_DIR="baml_client"

echo "🔧 Generating BAML client files..."

# Check if baml_src directory exists
if [ ! -d "$BAML_SRC_DIR" ]; then
    echo "❌ Error: $BAML_SRC_DIR directory not found"
    exit 1
fi

# Function to try baml-cli generation
try_baml_cli() {
    echo "ℹ️  Trying baml-cli generate..."

    # Try baml-cli directly
    if command -v baml-cli >/dev/null 2>&1; then
        echo "ℹ️  Found baml-cli in PATH"
        if baml-cli generate --from "$BAML_SRC_DIR" --to "$BAML_CLIENT_DIR" 2>/dev/null; then
            echo "✅ BAML client generated successfully with baml-cli"
            return 0
        else
            echo "⚠️  baml-cli generate failed (likely version compatibility issue)"
        fi
    fi

    # Try python -m baml_cli
    if python -m baml_cli --help >/dev/null 2>&1; then
        echo "ℹ️  Found baml_cli Python module"
        if python -m baml_cli generate --from "$BAML_SRC_DIR" --to "$BAML_CLIENT_DIR" 2>/dev/null; then
            echo "✅ BAML client generated successfully with python -m baml_cli"
            return 0
        else
            echo "⚠️  python -m baml_cli generate failed (likely version compatibility issue)"
        fi
    fi

    return 1
}

# Function to check if client files are up-to-date
check_client_uptodate() {
    if [ ! -d "$BAML_CLIENT_DIR" ]; then
        return 1
    fi

    # Check if any .baml files are newer than the client directory
    if find "$BAML_SRC_DIR" -name "*.baml" -newer "$BAML_CLIENT_DIR" | grep -q .; then
        return 1
    fi

    # Check if baml.toml is newer than the client directory
    if [ -f "$BAML_SRC_DIR/baml.toml" ] && [ "$BAML_SRC_DIR/baml.toml" -nt "$BAML_CLIENT_DIR" ]; then
        return 1
    fi

    return 0
}

# Main logic
if check_client_uptodate; then
    echo "✅ BAML client files are up-to-date"
    exit 0
fi

echo "ℹ️  BAML source files have been modified, regenerating client..."

# Try to generate with baml-cli
if try_baml_cli; then
    exit 0
fi

# If baml-cli fails, provide helpful message
echo ""
echo "⚠️  Could not generate BAML client files automatically."
echo "ℹ️  This is likely due to version compatibility issues between baml-cli and baml-py."
echo ""
echo "📋 Manual options:"
echo "   1. Install a compatible baml-cli version:"
echo "      pip install baml-cli"
echo "      baml-cli generate --from $BAML_SRC_DIR --to $BAML_CLIENT_DIR"
echo ""
echo "   2. Or use the pre-generated client files (if available)"
echo ""
echo "   3. Or skip BAML client generation for now (not recommended for production)"

# Don't fail the commit if generation fails - just warn
echo ""
echo "⚠️  Continuing with existing BAML client files..."
exit 0
