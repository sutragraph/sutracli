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
    # Version control
    ".git",
    ".svn",
    ".hg",
    ".bzr",
    "CVS",
    # Dependencies and packages
    "node_modules",
    "bower_components",
    "jspm_packages",
    "vendor",
    "packages",
    "third_party",
    "external",
    # Python specific
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".coverage",
    "htmlcov",
    ".tox",
    ".nox",
    "*venv*",
    "*env",
    "env*",
    "*pyenv*",
    "*conda*",
    ".pip*",
    "site-packages",
    "dist-packages",
    "build",
    "dist",
    "egg-info",
    "*.egg-info",
    ".eggs",
    # JavaScript/Node.js specific
    "node_modules",
    ".npm",
    ".yarn",
    "coverage",
    ".nyc_output",
    "dist",
    "build",
    "out",
    ".next",
    ".nuxt",
    ".parcel-cache",
    ".vuepress",
    # Java specific
    "target",
    "bin",
    ".gradle",
    ".m2",
    "classes",
    # .NET specific
    "bin",
    "obj",
    "packages",
    ".vs",
    # Ruby specific
    ".bundle",
    "vendor/bundle",
    "log",
    "tmp",
    # Go specific
    "vendor",
    # Rust specific
    "target",
    "Cargo.lock",
    # C/C++ specific
    "build",
    "cmake-build-debug",
    "cmake-build-release",
    ".vs",
    "Debug",
    "Release",
    "x64",
    "x86",
    # IDE and editor directories
    ".vscode",
    ".idea",
    ".eclipse",
    ".settings",
    ".project",
    ".classpath",
    ".metadata",
    ".recommenders",
    ".sublime-project",
    ".sublime-workspace",
    # OS specific directories
    ".Trash",
    ".Trashes",
    "__MACOSX",
    "System Volume Information",
    "$Recycle.Bin",
    # Documentation build directories
    "_build",
    "docs/_build",
    "site",
    ".docusaurus",
    # Test and coverage directories
    "coverage",
    "test-results",
    "test-reports",
    ".coverage",
    "htmlcov",
    # Temporary directories
    "tmp",
    "temp",
    ".tmp",
    ".temp",
    # Log directories
    "logs",
    "log",
    # Backup directories
    "backup",
    "backups",
    ".backup",
    # BAML Auto Generated Files
    "baml_client",
]
