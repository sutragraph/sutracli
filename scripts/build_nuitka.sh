#!/bin/bash
set -e

# Check if Nuitka is installed
echo "🚀 Sutra Knowledge CLI - Nuitka Builder (High Performance)"
echo "======="

# Create and activate virtual environment
VENV_DIR="$HOME/.sutra/venv"
echo "🔧 Setting up virtual environment..."

if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment"
        exit 1
    fi
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

echo "🔌 Activating virtual environment..."
source "$VENV_DIR/bin/activate"
if [ $? -ne 0 ]; then
    echo "❌ Failed to activate virtual environment"
    exit 1
fi
echo "✅ Virtual environment activated"

# Upgrade pip in virtual environment
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Check if Nuitka is installed
echo "=========================================================="

# Check if Nuitka is installed
if ! command -v nuitka &> /dev/null; then
    echo "❌ Nuitka not found. Installing..."
    pip install nuitka
fi

echo "✅ Nuitka found: $(nuitka --version)"

# Check required files
echo "🔍 Checking source files..."

# Determine if we're running from scripts/ or project root
if [ -f "cli/sutra_cli.py" ]; then
    # Running from project root
    CLI_PATH="cli/sutra_cli.py"
    SRC_PATH="src"
    CONFIG_PATH="configs"
    REQUIREMENTS_PATH="requirements.txt"
    PROJECT_ROOT="."
elif [ -f "../cli/sutra_cli.py" ]; then
    # Running from scripts/
    CLI_PATH="../cli/sutra_cli.py"
    SRC_PATH="../src"
    CONFIG_PATH="../configs"
    REQUIREMENTS_PATH="../requirements.txt"
    PROJECT_ROOT=".."
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
# Ensure ~/.sutra directory exists
mkdir -p "$HOME/.sutra"
rm -rf "$HOME/.sutra/sutra.dist/" "$HOME/.sutra/sutra.build/" "$HOME/.sutra/sutra.onefile-build/"

echo "🔨 Building executable with Nuitka (PERFORMANCE MODE)..."
echo "📦 Creating optimized standalone executable..."

# Build include modules list from requirements.txt
echo "📦 Reading requirements.txt and including all dependencies..."

INCLUDE_MODULES=""
while IFS= read -r line; do
    # Skip empty lines and comments
    if [[ ! -z "$line" && ! "$line" =~ ^[[:space:]]*# ]]; then
        # Extract package name (before ==,>=, etc.) and handle special cases
        package=$(echo "$line" | sed 's/[>=<].*//' | sed 's/\[.*\]//')

# Convert package names to import names using case statement (portable)
        case "$package" in
            "python-dotenv")
                package="dotenv"
                ;;
            "sqlite-vec")
                package="sqlite_vec"
                ;;
            "google-auth")
                package="google.auth"
                ;;
            "google-cloud-aiplatform")
                package="google.cloud.aiplatform"
                ;;
            "google-genai")
                package="google.genai"
                ;;
            "tree-sitter")
                package="tree_sitter"
                ;;
            "PyYAML")
                package="yaml"
                ;;
            "cryptography")
                package="cryptography"
                ;;
            *)
                # Keep original package name if no mapping exists
                ;;
        esac

        if [[ ! -z "$package" ]]; then
            INCLUDE_MODULES="$INCLUDE_MODULES --include-module=$package"
        fi
    fi
done < "$REQUIREMENTS_PATH"

echo "🔍 Found packages: $(echo $INCLUDE_MODULES | wc -w | awk '{print $1/2}') packages"

# Find sqlite_vec binary location for data files
SQLITE_VEC_PATH=$(python3 -c "import sqlite_vec; import os; print(os.path.dirname(sqlite_vec.__file__))" 2>/dev/null || echo "")

DATA_FILES=""
if [ ! -z "$SQLITE_VEC_PATH" ]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS - check for .dylib
        if [ -f "$SQLITE_VEC_PATH/vec0.dylib" ]; then
            echo "✅ Found sqlite_vec binary at: $SQLITE_VEC_PATH/vec0.dylib (macOS)"
            DATA_FILES="$DATA_FILES --include-data-file=$SQLITE_VEC_PATH/vec0.dylib=sqlite_vec/vec0.dylib"
        else
            echo "⚠️  sqlite_vec dylib not found at: $SQLITE_VEC_PATH/vec0.dylib"
        fi
    else
        # Linux/other - check for .so
        if [ -f "$SQLITE_VEC_PATH/vec0.so" ]; then
            echo "✅ Found sqlite_vec binary at: $SQLITE_VEC_PATH/vec0.so (Linux)"
            DATA_FILES="$DATA_FILES --include-data-file=$SQLITE_VEC_PATH/vec0.so=sqlite_vec/vec0.so"
        else
            echo "⚠️  sqlite_vec so not found at: $SQLITE_VEC_PATH/vec0.so"
        fi
    fi
else
    echo "⚠️  sqlite_vec package not found - vector search may not work"
fi

# Add dateparser data
DATEPARSER_DATA=$(python3 -c 'import dateparser; import os; print(os.path.join(os.path.dirname(dateparser.__file__), "data"))' 2>/dev/null || echo "")
if [ ! -z "$DATEPARSER_DATA" ] && [ -d "$DATEPARSER_DATA" ]; then
    echo "✅ Found dateparser data at: $DATEPARSER_DATA"
    DATA_FILES="$DATA_FILES --include-data-dir=$DATEPARSER_DATA=dateparser/data"
else
    echo "⚠️  dateparser data not found"
fi

# Build with Nuitka
cd "$PROJECT_ROOT"

nuitka \
    --onefile \
    --output-filename=sutra \
    --include-data-dir=configs=configs \
    --include-data-dir=src=src \
    --include-data-dir=src/parser/config=parser_config \
    $DATA_FILES \
    $INCLUDE_MODULES \
    --include-module=sqlite3 \
    --include-module=cryptography.fernet \
    --include-module=cryptography.hazmat.primitives \
    --include-module=cryptography.hazmat.primitives.kdf.pbkdf2 \
    --enable-plugin=anti-bloat \
    --assume-yes-for-downloads \
    --output-dir="$HOME/.sutra/dist" \
    "$CLI_PATH"

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Build completed successfully!"
    echo "📁 Executable location: $HOME/.sutra/dist/sutra"
    echo "📊 File size: $(du -h "$HOME/.sutra/dist/sutra" | cut -f1)"
    echo ""
    echo "🧪 Testing executable..."
    if "$HOME/.sutra/dist/sutra" --help> /dev/null 2>&1; then
        echo "✅ Executable works!"
    else
        echo "⚠️  Executable test failed, but file was created"
    fi
    echo ""
    echo "📋 Next steps:"
    echo "  1. Test: $HOME/.sutra/dist/sutra --help"
    echo "  2. Copy to system: sudo cp '$HOME/.sutra/dist/sutra' /usr/local/bin/"
    echo "  3. Or distribute: $HOME/.sutra/dist/sutra"
    echo ""
    echo "💡 This Nuitka executable is fully optimized and includes Python runtime"
    echo "🚀 Performance benefits: Faster startup, better optimization, smaller memory footprint"
else
    echo "❌ Build failed!"
    exit 1
fi
