"""
Ignore patterns configuration for AST Parser

This module contains patterns for files and directories that should be ignored
when parsing directories, similar to .gitignore functionality.
"""

from typing import List

# File patterns to ignore (glob patterns)
IGNORE_FILE_PATTERNS: List[str] = [
    # Compiled files
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.so",
    "*.dll",
    "*.dylib",
    "*.o",
    "*.obj",
    "*.exe",
    "*.class",
    "*.jar",
    "*.war",
    "*.ear",
    # Temporary files
    "*~",
    "*.tmp",
    "*.temp",
    "*.bak",
    "*.backup",
    "*.swp",
    "*.swo",
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
    # Log files
    "*.log",
    "*.out",
    "*.err",
    # Cache files
    "*.cache",
    "*.pid",
    # Binary files
    "*.bin",
    "*.dat",
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    # Image files
    "*.jpg",
    "*.jpeg",
    "*.png",
    "*.gif",
    "*.bmp",
    "*.tiff",
    "*.ico",
    "*.svg",
    "*.webp",
    # Video files
    "*.mp4",
    "*.avi",
    "*.mov",
    "*.wmv",
    "*.flv",
    "*.webm",
    "*.mkv",
    # Audio files
    "*.mp3",
    "*.wav",
    "*.flac",
    "*.aac",
    "*.ogg",
    "*.wma",
    # Archive files
    "*.zip",
    "*.tar",
    "*.gz",
    "*.bz2",
    "*.xz",
    "*.7z",
    "*.rar",
    # Document files
    "*.pdf",
    "*.doc",
    "*.docx",
    "*.xls",
    "*.xlsx",
    "*.ppt",
    "*.pptx",
    # Font files
    "*.ttf",
    "*.otf",
    "*.woff",
    "*.woff2",
    "*.eot",
    # Lock files
    "*.lock",
    "package-lock.json",
    "yarn.lock",
    "Pipfile.lock",
    "poetry.lock",
    "Gemfile.lock",
    "Cargo.lock",
    "composer.lock",
    # Minified files
    "*.min.js",
    "*.min.css",
    # Source maps
    "*.map",
    "*.js.map",
    "*.css.map",
    # IDE and editor files
    "*.sublime-project",
    "*.sublime-workspace",
    "*.code-workspace",
    # OS specific files
    ".DS_Store",
    "Thumbs.db",
    "ehthumbs.db",
    "Desktop.ini",
    "$RECYCLE.BIN",
    ".editorconfig",
    ".eslintrc*",
    ".prettierrc*",
    ".stylelintrc*",
    ".babelrc*",
    ".npmrc",
    ".yarnrc",
]


# Directory patterns to ignore (glob patterns)
IGNORE_DIRECTORY_PATTERNS: List[str] = [
    # Hidden directories (all directories starting with dot)
    ".*",
    # Version control (non-hidden)
    "CVS",
    # Dependencies and packages
    "node_modules",
    "bower_components",
    "jspm_packages",
    "vendor",
    "packages",
    "third_party",
    "external",
    # Python specific (non-hidden)
    "__pycache__",
    "site-packages",
    "dist-packages",
    "build",
    "dist",
    "egg-info",
    "*.egg-info",
    ".eggs",
    # JavaScript/Node.js specific (non-hidden)
    "node_modules",
    "coverage",
    ".nyc_output",
    "dist",
    "build",
    "out",
    # Java specific (non-hidden)
    "target",
    "bin",
    "classes",
    # .NET specific (non-hidden)
    "bin",
    "obj",
    "packages",
    # Ruby specific (non-hidden)
    "vendor/bundle",
    "log",
    "tmp",
    # Go specific (non-hidden)
    "vendor",
    # Rust specific (non-hidden)
    "target",
    "Cargo.lock",
    # C/C++ specific (non-hidden)
    "build",
    "cmake-build-debug",
    "cmake-build-release",
    "Debug",
    "Release",
    "x64",
    "x86",
    # IDE and editor directories (non-hidden)
    ".sublime-project",
    ".sublime-workspace",
    # OS specific directories (non-hidden)
    "__MACOSX",
    "System Volume Information",
    "$Recycle.Bin",
    # Documentation build directories (non-hidden)
    "_build",
    "docs/_build",
    "site",
    # Test and coverage directories (non-hidden)
    "coverage",
    "test-results",
    "test-reports",
    "htmlcov",
    # Temporary directories (non-hidden)
    "tmp",
    "temp",
    # Log directories (non-hidden)
    "logs",
    "log",
    # Backup directories (non-hidden)
    "backup",
    "backups",
    # BAML Auto Generated Files
    "baml_client",
]
