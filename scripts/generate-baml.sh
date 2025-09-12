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
        if baml-cli generate 2>/dev/null; then
            echo "✅ BAML client generated successfully with baml-cli"
            return 0
        else
            echo "⚠️  baml-cli generate failed (likely version compatibility issue)"
        fi
    fi

    return 1
}

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
echo "      baml-cli generate"
echo ""
echo "   2. Or use the pre-generated client files (if available)"
echo ""

# Don't fail the commit if generation fails - just warn
echo ""
echo "⚠️  Continuing with existing BAML client files..."
exit 0
