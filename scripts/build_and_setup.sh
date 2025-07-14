#!/bin/bash
# Build executable and setup complete CLI environment from remote repository
# This script creates a production-ready Sutra CLI installation

set -e

REPO_URL="https://github.com/sutragraph/models"
RELEASE_TAG="v0.2"
INSTALL_DIR="$HOME/.sutra"
TEMP_DIR=$(mktemp -d)
PROJECT_ROOT="$(pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

cleanup() {
    if [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
        log_info "Cleaned up temporary directory"
    fi

    # Clean up any remaining downloaded files in current directory
    if [ -f "all-MiniLM-L12-v2.tar.gz" ]; then
        rm -f "all-MiniLM-L12-v2.tar.gz"
    fi
    if [ -f "tree-sitter-build.tar.gz" ]; then
        rm -f "tree-sitter-build.tar.gz"
    fi
}

trap cleanup EXIT

setup_python_environment() {
    log_info "Setting up Python virtual environment..."
    
    # Check if python3-venv is available
    if ! python3 -c "import venv">/dev/null 2>&1; then
        log_error "python3-venv module not available. Please install python3-venv package."
        log_info "On Ubuntu/Debian: sudo apt-get install python3-venv"
        log_info "On CentOS/RHEL: sudo yum install python3-venv"
        exit 1
    fi
    
    local venv_dir="$PROJECT_ROOT/venv"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "$venv_dir" ]; then
        log_info "Creating Python virtual environment at $venv_dir..."
        python3 -m venv "$venv_dir"
        log_success "Virtual environment created"
    else
        log_info "Virtual environment already exists at $venv_dir"
    fi
    
    # Activate virtual environment
    log_info "Activating virtual environment..."
    source "$venv_dir/bin/activate"
    
    # Upgrade pip
    log_info "Upgrading pip..."
    pip install --upgrade pip
    
    # Install requirements if requirements.txt exists
    if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
        log_info "Installing Python dependencies from requirements.txt..."
        pip install -r "$PROJECT_ROOT/requirements.txt"
        log_success "Python dependencies installed"
    else
        log_warning "requirements.txt not found, skipping dependency installation"
    fi
    
    # Install PyInstaller if not already installed
    if ! python3 -c "import PyInstaller">/dev/null 2>&1; then
        log_info "Installing PyInstaller..."
        pip install pyinstaller
        log_success "PyInstaller installed"
    else
        log_info "PyInstaller already available"
    fi
    
    log_success "Python environment setup completed"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local required_commands=("python3" "pip" "curl" "tar")
    
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            log_error "Required command not found: $cmd"
            exit 1
        fi
    done
    
    if ! python3 -c "import PyInstaller" >/dev/null 2>&1; then
        log_info "Installing PyInstaller..."
        pip install pyinstaller
    fi
    
    if ! command -v rg >/dev/null 2>&1; then
        log_info "Installing ripgrep..."
        
        # Detect OS and install ripgrep
        if command -v apt-get >/dev/null 2>&1; then
            # Debian/Ubuntu
            sudo apt-get update && sudo apt-get install -y ripgrep
        elif command -v yum >/dev/null 2>&1; then
            # CentOS/RHEL/Fedora
            sudo yum install -y ripgrep
        elif command -v dnf >/dev/null 2>&1; then
            # Fedora (newer versions)
            sudo dnf install -y ripgrep
        elif command -v pacman >/dev/null 2>&1; then
            # Arch Linux
            sudo pacman -S --noconfirm ripgrep
        elif command -v brew >/dev/null 2>&1; then
            # macOS with Homebrew
            brew install ripgrep
        else
            log_error "Failed to install ripgrep please install manually"
            exit 1
        fi
        
        if command -v rg >/dev/null 2>&1; then
            log_success "ripgrep installed successfully"
        else
            log_error "ripgrep installation failed"
            exit 1
        fi
    else
        log_success "ripgrep already installed"
    fi
    
    if ! command -v tmux >/dev/null 2>&1; then
        log_info "Installing tmux..."
        
        # Detect OS and install tmux
        if command -v apt-get >/dev/null 2>&1; then
            # Debian/Ubuntu
            sudo apt-get update && sudo apt-get install -y tmux
        elif command -v yum >/dev/null 2>&1; then
            # CentOS/RHEL/Fedora
            sudo yum install -y tmux
        elif command -v dnf >/dev/null 2>&1; then
            # Fedora (newer versions)
            sudo dnf install -y tmux
        elif command -v pacman >/dev/null 2>&1; then
            # Arch Linux
            sudo pacman -S --noconfirm tmux
        elif command -v brew >/dev/null 2>&1; then
            # macOS with Homebrew
            brew install tmux
        else
            log_error "Failed to install tmux please install manually"
            exit 1
        fi
        
        if command -v tmux >/dev/null 2>&1; then
            log_success "tmux installed successfully"
        else
            log_error "tmux installation failed"
            exit 1
        fi
    else
        log_success "tmux already installed"
    fi
    
    log_success "All prerequisites satisfied"
}

build_executable() {
    log_info "Building Sutra CLI executable..."
    
    if [ ! -f "$PROJECT_ROOT/cli/sutra_cli.py" ]; then
        log_error "Must run from project root directory (cli/sutra_cli.py not found)"
        log_error "Current directory: $(pwd)"
        log_error "Project root: $PROJECT_ROOT"
        exit 1
    fi

    cd "$PROJECT_ROOT"
    
    if [ -f "scripts/build.sh" ]; then
        log_info "Using build script: scripts/build.sh"
        bash scripts/build.sh
    else
        log_error "No build script found"
        log_info "Please run from the project root directory"
        exit 1
    fi
    
    if [ -f "dist/sutra" ]; then
        log_success "Executable built successfully: dist/sutra"
    else
        log_error "Executable build failed"
        exit 1
    fi
}

setup_models() {
    log_info "Setting up ML models from remote repository..."
    
    local models_url="$REPO_URL/releases/download/$RELEASE_TAG/all-MiniLM-L12-v2.tar.gz"
    local models_dir="$INSTALL_DIR/models"
    
    mkdir -p "$models_dir"
    cd "$TEMP_DIR"
    
    log_info "Downloading models from $models_url..."
    if curl -fsSL "$models_url" -o "all-MiniLM-L12-v2.tar.gz"; then
        log_success "Models downloaded successfully"
        
        log_info "Extracting models..."
        tar -xzf "all-MiniLM-L12-v2.tar.gz"
        
        if [ -d "all-MiniLM-L12-v2" ]; then
            cp -r "all-MiniLM-L12-v2" "$models_dir/"
            log_success "Models installed to $models_dir/all-MiniLM-L12-v2"

            # Clean up downloaded files
            rm -f "all-MiniLM-L12-v2.tar.gz"
            rm -rf "all-MiniLM-L12-v2"
            log_info "Cleaned up temporary model files"
        else
            log_error "Model extraction failed"
            exit 1
        fi
    else
        log_error "Failed to download models from $models_url"
        exit 1
    fi
}

setup_parsers() {
    log_info "Setting up tree-sitter parsers from remote repository..."
    
    local parsers_url="$REPO_URL/releases/download/$RELEASE_TAG/tree-sitter-build.tar.gz"
    local build_dir="$INSTALL_DIR/build"
    
    mkdir -p "$build_dir"
    cd "$TEMP_DIR"
    
    log_info "Downloading parsers from $parsers_url..."
    if curl -fsSL "$parsers_url" -o "tree-sitter-build.tar.gz"; then
        log_success "Parsers downloaded successfully"
        
        log_info "Extracting parsers..."
        tar -xzf "tree-sitter-build.tar.gz"
        
        if [ -d "build" ]; then
            cp -r build/* "$build_dir/"
            log_success "Parsers installed to $build_dir"

            log_info "Installed parser libraries:"
            find "$build_dir" -name "*.so" -o -name "*.dylib" | head -5 | while read file; do
                echo "  - $(basename "$file")"
            done

            # Clean up downloaded files
            rm -f "tree-sitter-build.tar.gz"
            rm -rf "build"
            log_info "Cleaned up temporary parser files"
        else
            log_error "Parser extraction failed"
            exit 1
        fi
    else
        log_error "Failed to download parsers from $parsers_url"
        exit 1
    fi
}

setup_configuration() {
    log_info "Setting up configuration files..."
    
    local config_dir="$INSTALL_DIR/config"
    mkdir -p "$config_dir"
    
    # Copy and fix system configuration (use absolute paths)
    if [ -f "$PROJECT_ROOT/configs/system.json" ]; then
        cp "$PROJECT_ROOT/configs/system.json" "$config_dir/"

        # Fix GCP configuration to include missing api_key field
        if command -v sed >/dev/null 2>&1; then
            # Add api_key field to GCP configuration if missing
            if ! grep -q '"api_key"' "$config_dir/system.json"; then
                sed -i.bak 's/"gcp": {/"gcp": {\n      "api_key": "",/' "$config_dir/system.json"
                rm -f "$config_dir/system.json.bak"
                log_success "Fixed GCP configuration in system.json"
            fi
        fi

        log_success "System configuration installed"
    else
        log_error "System configuration not found: $PROJECT_ROOT/configs/system.json"
        exit 1
    fi

    if [ -f "$PROJECT_ROOT/src/parser/config/parsers.json" ]; then
        # Copy the parser config
        cp "$PROJECT_ROOT/src/parser/config/parsers.json" "$config_dir/"

        if command -v sed >/dev/null 2>&1; then
            # Use sed to replace the build directory path
            sed -i.bak 's|"build_directory": "src/parser/build"|"build_directory": "~/.sutra/build"|g' "$config_dir/parsers.json"
            # Remove backup file
            rm -f "$config_dir/parsers.json.bak"
            log_success "Parser configuration installed and updated for installed environment"
        else
            log_warning "sed not available - parser configuration may need manual adjustment"
            log_success "Parser configuration installed"
        fi
    else
        log_error "Parser configuration not found: $PROJECT_ROOT/src/parser/config/parsers.json"
        exit 1
    fi
}

install_executable() {
    log_info "Installing executable globally..."
    
    local bin_dir="$INSTALL_DIR/bin"
    mkdir -p "$bin_dir"
    
    # Copy executable (use absolute path)
    if [ -f "$PROJECT_ROOT/dist/sutra" ]; then
        cp "$PROJECT_ROOT/dist/sutra" "$bin_dir/"
        chmod +x "$bin_dir/sutra"
        log_success "Executable installed to $bin_dir/sutra"
    else
        log_error "Executable not found: $PROJECT_ROOT/dist/sutra"
        exit 1
    fi
    
    mkdir -p "$INSTALL_DIR/data"
    mkdir -p "$INSTALL_DIR/logs"
    
    log_success "Directory structure created"
}

setup_environment() {
    log_info "Setting up environment variables..."
    
    local bin_dir="$INSTALL_DIR/bin"
    local config_file="$INSTALL_DIR/config/system.json"
    
    # Detect shell
    local shell_rc=""
    local shell_type=""
    if [ -n "$ZSH_VERSION" ]; then
        shell_rc="$HOME/.zshrc"
        shell_type="zsh"
    elif [ -n "$BASH_VERSION" ]; then
        shell_rc="$HOME/.bashrc"
        shell_type="bash"
    elif [ "$SHELL" = "/usr/bin/fish" ] || [ "$SHELL" = "/bin/fish" ] || command -v fish >/dev/null 2>&1; then
        shell_rc="$HOME/.config/fish/config.fish"
        shell_type="fish"
        # Ensure fish config directory exists
        mkdir -p "$HOME/.config/fish"
    else
        shell_rc="$HOME/.profile"
        shell_type="posix"
    fi
    
    # Add to PATH if not already there
    if ! echo "$PATH" | grep -q "$bin_dir"; then
        echo "" >> "$shell_rc"
        echo "# Sutra Knowledge CLI" >> "$shell_rc"

        if [ "$shell_type" = "fish" ]; then
            echo "set -gx PATH $bin_dir \$PATH" >> "$shell_rc"
            echo "set -gx SUTRAKNOWLEDGE_CONFIG \"$config_file\"" >> "$shell_rc"
            log_success "Added Sutra CLI to PATH in $shell_rc (Fish shell)"
            log_info "Restart your shell or run: source $shell_rc"
        else
            echo "export PATH=\"$bin_dir:\$PATH\"" >> "$shell_rc"
            echo "export SUTRAKNOWLEDGE_CONFIG=\"$config_file\"" >> "$shell_rc"
            log_success "Added Sutra CLI to PATH in $shell_rc"
            log_info "Restart your shell or run: source $shell_rc"
        fi
    else
        log_info "Sutra CLI already in PATH"
    fi
    
    # Set for current session
    export PATH="$bin_dir:$PATH"
    export SUTRAKNOWLEDGE_CONFIG="$config_file"
}

test_installation() {
    log_info "Testing installation..."
    
    # Test executable
    if command -v sutra >/dev/null 2>&1; then
        log_success "Sutra command is available"
        
        # Test help
        if sutra --help >/dev/null 2>&1; then
            log_success "Sutra --help works"
        else
            log_error "Sutra --help failed"
            return 1
        fi
        
        # Test version
        if sutra --version >/dev/null 2>&1; then
            log_success "Sutra --version works"
        else
            log_warning "Sutra --version failed (may be normal)"
        fi
        
    else
        log_error "Sutra command not found"
        return 1
    fi
    
    # Test configuration
    if [ -f "$INSTALL_DIR/config/system.json" ]; then
        log_success "Configuration files present"
    else
        log_error "Configuration files missing"
        return 1
    fi
    
    # Test models
    if [ -d "$INSTALL_DIR/models/all-MiniLM-L12-v2" ]; then
        log_success "ML models present"
    else
        log_error "ML models missing"
        return 1
    fi
    
    # Test parsers
    if find "$INSTALL_DIR/build" -name "*.so" -o -name "*.dylib" | grep -q .; then
        log_success "Parser libraries present"
    else
        log_error "Parser libraries missing"
        return 1
    fi
}

main() {
    echo "🚀 Sutra Knowledge CLI - Build and Setup"
    echo "========================================"
    
    if [ -d "$INSTALL_DIR" ]; then
        log_warning "Sutra CLI already installed at $INSTALL_DIR"
        read -p "Do you want to reinstall? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Installation cancelled"
            exit 0
        fi
        rm -rf "$INSTALL_DIR"
    fi
    
    # Run setup steps
    setup_python_environment
    check_prerequisites
    build_executable
    setup_models
    setup_parsers
    setup_configuration
    install_executable
    setup_environment
    test_installation
    
    echo ""
    log_success "🎉 Sutra Knowledge CLI installation completed!"
    echo ""
    echo "📁 Installation directory: $INSTALL_DIR"
    echo "🔧 Configuration: $INSTALL_DIR/config/system.json"
    echo "📦 Models: $INSTALL_DIR/models/"
    echo "🔨 Parsers: $INSTALL_DIR/build/"
    echo ""
    echo "🚀 Usage:"
    echo "  sutra --help                    # Show help"
    echo "  sutra                          # Analyze current directory"
    echo "  sutra --directory /path/to/repo # Analyze specific directory"
    echo ""
    echo "💡 Restart your shell or run: source ~/.bashrc"
}

main "$@"
