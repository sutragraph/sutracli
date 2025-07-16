#!/bin/bash
# Build linter bundles for different platforms
# Creates tar.gz files with all linters for each platform

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/../linter_builds"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Platform detection
detect_platform() {
    local os=$(uname -s)
    local arch=$(uname -m)
    
    case "$os" in
        Linux)
            case "$arch" in
                x86_64|amd64) echo "linux-x64" ;;
                aarch64|arm64) echo "linux-arm64" ;;
                i386|i686) echo "linux-x86" ;;
                armv7l) echo "linux-armv7" ;;
                *) echo "linux-generic" ;;
            esac
            ;;
        Darwin)
            case "$arch" in
                x86_64|amd64) echo "macos-x64" ;;
                arm64|aarch64) echo "macos-arm64" ;;
                *) echo "macos-generic" ;;
            esac
            ;;
        *) log_error "Unsupported OS: $os"; exit 1 ;;
    esac
}

# Create Checkstyle wrapper
create_checkstyle_wrapper() {
    local bundle_dir=$1
    curl -fsSL "https://github.com/checkstyle/checkstyle/releases/download/checkstyle-10.26.1/checkstyle-10.26.1-all.jar" -o "$bundle_dir/checkstyle.jar"
}

# Download and extract linters for each platform
build_platform_bundle() {
    local platform=$1
    local bundle_dir="$BUILD_DIR/$platform"
    
    log_info "Building linter bundle for $platform..."
    mkdir -p "$bundle_dir"
    
    case "$platform" in
        "linux-x64")
            curl -fsSL "https://github.com/astral-sh/ruff/releases/download/0.12.3/ruff-x86_64-unknown-linux-gnu.tar.gz" | tar -xz -C "$bundle_dir"
            mv "$bundle_dir"/ruff-*/ruff "$bundle_dir/" 2>/dev/null || true
            rm -rf "$bundle_dir"/ruff-*/
            curl -fsSL "https://github.com/golangci/golangci-lint/releases/download/v2.2.2/golangci-lint-2.2.2-linux-amd64.tar.gz" | tar -xz -C "$bundle_dir" --strip-components=1
            ;;
        "linux-arm64")
            curl -fsSL "https://github.com/astral-sh/ruff/releases/download/0.12.3/ruff-aarch64-unknown-linux-gnu.tar.gz" | tar -xz -C "$bundle_dir"
            mv "$bundle_dir"/ruff-*/ruff "$bundle_dir/" 2>/dev/null || true
            rm -rf "$bundle_dir"/ruff-*/
            curl -fsSL "https://github.com/golangci/golangci-lint/releases/download/v2.2.2/golangci-lint-2.2.2-linux-arm64.tar.gz" | tar -xz -C "$bundle_dir" --strip-components=1
            ;;
        "linux-x86")
            curl -fsSL "https://github.com/astral-sh/ruff/releases/download/0.12.3/ruff-i686-unknown-linux-gnu.tar.gz" | tar -xz -C "$bundle_dir"
            mv "$bundle_dir"/ruff-*/ruff "$bundle_dir/" 2>/dev/null || true
            rm -rf "$bundle_dir"/ruff-*/
            curl -fsSL "https://github.com/golangci/golangci-lint/releases/download/v2.2.2/golangci-lint-2.2.2-linux-386.tar.gz" | tar -xz -C "$bundle_dir" --strip-components=1
            ;;
        "linux-armv7")
            curl -fsSL "https://github.com/astral-sh/ruff/releases/download/0.12.3/ruff-armv7-unknown-linux-gnueabihf.tar.gz" | tar -xz -C "$bundle_dir"
            mv "$bundle_dir"/ruff-*/ruff "$bundle_dir/" 2>/dev/null || true
            rm -rf "$bundle_dir"/ruff-*/
            curl -fsSL "https://github.com/golangci/golangci-lint/releases/download/v2.2.2/golangci-lint-2.2.2-linux-armv7.tar.gz" | tar -xz -C "$bundle_dir" --strip-components=1
            ;;
        "linux-generic")
            log_info "Generic Linux - creating wrapper scripts only"
            cat > "$bundle_dir/ruff" << 'EOF'
#!/bin/bash
echo "Error: Ruff binary not available for this architecture. Please install via pip: pip install ruff"
exit 1
EOF
            chmod +x "$bundle_dir/ruff"
            cat > "$bundle_dir/golangci-lint" << 'EOF'
#!/bin/bash
echo "Error: golangci-lint binary not available for this architecture. Please install manually."
exit 1
EOF
            chmod +x "$bundle_dir/golangci-lint"
            ;;
        "macos-x64")
            curl -fsSL "https://github.com/astral-sh/ruff/releases/download/0.12.3/ruff-x86_64-apple-darwin.tar.gz" | tar -xz -C "$bundle_dir"
            mv "$bundle_dir"/ruff-*/ruff "$bundle_dir/" 2>/dev/null || true
            rm -rf "$bundle_dir"/ruff-*/
            curl -fsSL "https://github.com/golangci/golangci-lint/releases/download/v2.2.2/golangci-lint-2.2.2-darwin-amd64.tar.gz" | tar -xz -C "$bundle_dir" --strip-components=1
            ;;
        "macos-arm64")
            curl -fsSL "https://github.com/astral-sh/ruff/releases/download/0.12.3/ruff-aarch64-apple-darwin.tar.gz" | tar -xz -C "$bundle_dir"
            mv "$bundle_dir"/ruff-*/ruff "$bundle_dir/" 2>/dev/null || true
            rm -rf "$bundle_dir"/ruff-*/
            curl -fsSL "https://github.com/golangci/golangci-lint/releases/download/v2.2.2/golangci-lint-2.2.2-darwin-arm64.tar.gz" | tar -xz -C "$bundle_dir" --strip-components=1
            ;;
        "macos-generic")
            log_info "Generic macOS - creating wrapper scripts only"
            cat > "$bundle_dir/ruff" << 'EOF'
#!/bin/bash
echo "Error: Ruff binary not available for this architecture. Please install via pip: pip install ruff"
exit 1
EOF
            chmod +x "$bundle_dir/ruff"
            cat > "$bundle_dir/golangci-lint" << 'EOF'
#!/bin/bash
echo "Error: golangci-lint binary not available for this architecture. Please install manually."
exit 1
EOF
            chmod +x "$bundle_dir/golangci-lint"
            ;;
    esac
    
    # Add Checkstyle for all platforms
    create_checkstyle_wrapper "$bundle_dir"
    
    # Clean up unnecessary files
    rm -f "$bundle_dir"/LICENSE* "$bundle_dir"/README* "$bundle_dir"/*.md
    
    # Make all binaries executable
    chmod +x "$bundle_dir"/* 2>/dev/null || true
    
    # Create tar.gz bundle
    cd "$BUILD_DIR"
    tar -czf "linters-$platform.tar.gz" "$platform"
    
    log_success "Created bundle: linters-$platform.tar.gz"
}

# Main execution
main() {
    log_info "Building linter bundles for all platforms..."
    
    rm -rf "$BUILD_DIR"
    mkdir -p "$BUILD_DIR"
    
    # Build for all supported platforms
    build_platform_bundle "linux-x64"
    build_platform_bundle "linux-arm64"
    build_platform_bundle "linux-x86"
    build_platform_bundle "linux-armv7"
    build_platform_bundle "linux-generic"
    build_platform_bundle "macos-x64"
    build_platform_bundle "macos-arm64"
    build_platform_bundle "macos-generic"
    
    log_success "All linter bundles created in $BUILD_DIR"
    ls -la "$BUILD_DIR"/*.tar.gz
}

main "$@"