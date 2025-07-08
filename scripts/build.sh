#!/bin/bash
set -e

echo "🚀 Sutra Knowledge CLI - PyInstaller Builder (Fast & Simple)"
echo "============================================================"

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo "❌ PyInstaller not found. Installing..."
    pip install pyinstaller
fi

echo "✅ PyInstaller found: $(pyinstaller --version)"

# Check required files
echo "🔍 Checking source files..."

# Determine if we're running from build_scripts/ or project root
if [ -f "cli/sutra_cli.py" ]; then
    # Running from project root
    CLI_PATH="cli/sutra_cli.py"
    SRC_PATH="src"
    CONFIG_PATH="configs"
    REQUIREMENTS_PATH="requirements.txt"
elif [ -f "../cli/sutra_cli.py" ]; then
    # Running from build_scripts/
    CLI_PATH="../cli/sutra_cli.py"
    SRC_PATH="../src"
    CONFIG_PATH="../configs"
    REQUIREMENTS_PATH="../requirements.txt"
else
    echo "❌ cli/sutra_cli.py not found"
    exit 1
fi
echo "✅ cli/sutra_cli.py"

if [ ! -d "$SRC_PATH" ]; then
    echo "❌ src/ directory not found"
    exit 1
fi
echo "✅ src/"

if [ ! -d "$CONFIG_PATH" ]; then
    echo "❌ configs/ directory not found"
    exit 1
fi
echo "✅ configs/"


echo "✅ All source files found"

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf dist/ build/ *.spec

echo "🔨 Building executable with PyInstaller (FAST MODE)..."
echo "📦 Creating single-file executable..."

# PyInstaller build - include everything from requirements.txt + essential modules
echo "📦 Reading requirements.txt and including all dependencies..."

# Build the command with all requirements as hidden imports
HIDDEN_IMPORTS="--hidden-import sqlite3"  # Essential built-in module
HIDDEN_IMPORTS="$HIDDEN_IMPORTS --hidden-import cryptography.fernet"  # For token encryption
HIDDEN_IMPORTS="$HIDDEN_IMPORTS --hidden-import cryptography.hazmat.primitives"  # For token encryption
HIDDEN_IMPORTS="$HIDDEN_IMPORTS --hidden-import cryptography.hazmat.primitives.kdf.pbkdf2"  # For key derivation

while IFS= read -r line; do
    # Skip empty lines and comments
    if [[ ! -z "$line" && ! "$line" =~ ^[[:space:]]*# ]]; then
        # Extract package name (before ==, >=, etc.) and handle special cases
        package=$(echo "$line" | sed 's/[>=<].*//' | sed 's/\[.*\]//')

        # Convert package names to import names using associative array
        declare -A package_map=(
            ["python-dotenv"]="dotenv"
            ["sqlite-vec"]="sqlite_vec"
            ["google-auth"]="google.auth"
            ["google-cloud-aiplatform"]="google.cloud.aiplatform"
            ["google-genai"]="google.genai"
            ["tree-sitter"]="tree_sitter"
            ["PyYAML"]="yaml"
            ["cryptography"]="cryptography"
        )

        # Use mapped name if exists, otherwise keep original
        package="${package_map[$package]:-$package}"

        if [[ ! -z "$package" ]]; then
            HIDDEN_IMPORTS="$HIDDEN_IMPORTS --hidden-import $package"
        fi
    fi
done < "$REQUIREMENTS_PATH"

echo "🔍 Found packages: $(echo $HIDDEN_IMPORTS | wc -w | awk '{print $1/2}') packages"

# Find sqlite_vec binary location
SQLITE_VEC_PATH=$(python3 -c "import sqlite_vec; import os; print(os.path.dirname(sqlite_vec.__file__))" 2>/dev/null || echo "")

# Detect platform and check for appropriate binary extension
if [ ! -z "$SQLITE_VEC_PATH" ]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS - check for .dylib
        if [ -f "$SQLITE_VEC_PATH/vec0.dylib" ]; then
            echo "✅ Found sqlite_vec binary at: $SQLITE_VEC_PATH/vec0.dylib (macOS)"
            SQLITE_VEC_BINARY="--add-binary $SQLITE_VEC_PATH/vec0.dylib:sqlite_vec"
        else
            echo "⚠️  sqlite_vec dylib not found at: $SQLITE_VEC_PATH/vec0.dylib"
            SQLITE_VEC_BINARY=""
        fi
    else
        # Linux/other - check for .so
        if [ -f "$SQLITE_VEC_PATH/vec0.so" ]; then
            echo "✅ Found sqlite_vec binary at: $SQLITE_VEC_PATH/vec0.so (Linux)"
            SQLITE_VEC_BINARY="--add-binary $SQLITE_VEC_PATH/vec0.so:sqlite_vec"
        else
            echo "⚠️  sqlite_vec so not found at: $SQLITE_VEC_PATH/vec0.so"
            SQLITE_VEC_BINARY=""
        fi
    fi
else
    echo "⚠️  sqlite_vec package not found - vector search may not work"
    SQLITE_VEC_BINARY=""
fi

pyinstaller \
    --onefile \
    --name sutra \
    --add-data "$CONFIG_PATH:configs" \
    --add-data "$SRC_PATH:src" \
    --add-data "$SRC_PATH/parser/config:parser_config" \
    --add-data "$(python3 -c 'import dateparser; import os; print(os.path.join(os.path.dirname(dateparser.__file__), "data"))'):dateparser/data" \
    $SQLITE_VEC_BINARY \
    $HIDDEN_IMPORTS \
    --noconfirm \
    $CLI_PATH

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Build completed successfully!"
    echo "📁 Executable location: $(pwd)/dist/sutra"
    echo "📊 File size: $(du -h dist/sutra | cut -f1)"
    echo ""
    echo "🧪 Testing executable..."
    if ./dist/sutra --help > /dev/null 2>&1; then
        echo "✅ Executable works!"
    else
        echo "⚠️  Executable test failed, but file was created"
    fi
    echo ""
    echo "📋 Next steps:"
    echo "  1. Test: ./dist/sutra --help"
    echo "  2. Copy to system: sudo cp dist/sutra /usr/local/bin/"
    echo "  3. Or distribute: dist/sutra"
    echo ""
    echo "💡 This executable includes Python runtime but excludes ML models to keep size small"
else
    echo "❌ Build failed!"
    exit 1
fi
