#!/usr/bin/env python3
"""
Tree-sitter Parser Builder for Cross-Platform
Builds binary parser files from parsers.json configuration
Supports macOS (.dylib) and Linux (.so) with proper platform detection
"""

import json
import os
import subprocess
import sys
import shutil
import platform
from pathlib import Path
from typing import Dict, Any, List, Tuple
import tempfile
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TreeSitterBuilder:
    def __init__(self, config_path: str = "parsers.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.build_dir = Path(self.config.get("settings", {}).get("build_directory", "./build"))
        self.lib_dir = Path(self.config.get("settings", {}).get("lib_directory", "./lib"))
        
        # Platform detection
        self.platform_info = self._detect_platform()
        logger.info(f"Detected platform: {self.platform_info['os']} ({self.platform_info['arch']})")
        logger.info(f"Library extension: {self.platform_info['lib_ext']}")
        
        # Create directories if they don't exist
        self.build_dir.mkdir(parents=True, exist_ok=True)
        self.lib_dir.mkdir(parents=True, exist_ok=True)
        
    def _detect_platform(self) -> Dict[str, str]:
        """Detect platform and return appropriate settings."""
        system = platform.system()
        machine = platform.machine()
        
        # Normalize architecture names
        arch_map = {
            'x86_64': 'x86_64',
            'AMD64': 'x86_64',
            'arm64': 'arm64',
            'aarch64': 'arm64',
            'armv7l': 'arm32',
        }
        
        normalized_arch = arch_map.get(machine, machine)
        
        if system == "Darwin":  # macOS
            return {
                'os': 'macOS',
                'arch': normalized_arch,
                'lib_ext': '.dylib',
                'compiler_flags': ['-undefined', 'dynamic_lookup'],
                'preferred_compiler': 'clang'
            }
        elif system == "Linux":
            return {
                'os': 'Linux',
                'arch': normalized_arch,
                'lib_ext': '.so',
                'compiler_flags': [],
                'preferred_compiler': 'gcc'
            }
        else:  # Windows or other
            return {
                'os': system,
                'arch': normalized_arch,
                'lib_ext': '.so',  # fallback
                'compiler_flags': [],
                'preferred_compiler': 'gcc'
            }
    
    def _load_config(self) -> Dict[str, Any]:
        """Load parser configuration from JSON file."""
        if not os.path.exists(self.config_path):
            logger.error(f"Config file {self.config_path} not found")
            sys.exit(1)
            
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing config file: {e}")
            sys.exit(1)
            
    def _check_dependencies(self) -> bool:
        """Check if required dependencies are available."""
        # Base dependencies
        dependencies = ["git", "make"]
        
        # Add platform-specific compiler
        preferred_compiler = self.platform_info['preferred_compiler']
        fallback_compilers = ['gcc', 'clang', 'cc']
        
        # Check for preferred compiler first
        compiler_found = None
        for compiler in [preferred_compiler] + fallback_compilers:
            if shutil.which(compiler):
                compiler_found = compiler
                break
                
        if not compiler_found:
            dependencies.extend(['gcc', 'clang'])
        
        missing = []
        for dep in dependencies:
            if not shutil.which(dep):
                missing.append(dep)
                
        if missing:
            logger.error(f"Missing dependencies: {', '.join(missing)}")
            if self.platform_info['os'] == 'macOS':
                logger.error("Please install missing dependencies:")
                logger.error("  brew install git gcc make")
                if 'clang' in missing:
                    logger.error("  xcode-select --install  # for clang")
            elif self.platform_info['os'] == 'Linux':
                logger.error("Please install missing dependencies:")
                logger.error("  # Ubuntu/Debian:")
                logger.error("  sudo apt-get install git build-essential")
                logger.error("  # CentOS/RHEL/Fedora:")
                logger.error("  sudo yum install git gcc make  # or dnf")
            return False
            
        if compiler_found:
            logger.info(f"Using compiler: {compiler_found}")
            
        return True
        
    def _get_compiler_command(self, has_cpp: bool = False) -> Tuple[str, List[str]]:
        """Get the appropriate compiler and base flags for the platform."""
        # Choose compiler
        if has_cpp:
            # For C++ files, prefer g++ or clang++
            for compiler in ['g++', 'clang++', 'c++']:
                if shutil.which(compiler):
                    chosen_compiler = compiler
                    break
            else:
                logger.warning("No C++ compiler found, falling back to gcc")
                chosen_compiler = 'gcc'
        else:
            # For C files, use platform preference
            preferred = self.platform_info['preferred_compiler']
            if shutil.which(preferred):
                chosen_compiler = preferred
            else:
                # Fallback chain
                for compiler in ['gcc', 'clang', 'cc']:
                    if shutil.which(compiler):
                        chosen_compiler = compiler
                        break
                else:
                    logger.error("No suitable compiler found")
                    chosen_compiler = 'gcc'  # last resort
        
        # Base compilation flags
        base_flags = [
            "-shared",
            "-fPIC",
            "-O2",
            "-std=c99"  if not has_cpp else "-std=c++11",
        ]
        
        # Add platform-specific flags
        platform_flags = self.platform_info.get('compiler_flags', [])
        
        return chosen_compiler, base_flags + platform_flags
        
    def _clone_repository(self, repo_url: str, target_dir: Path) -> bool:
        """Clone a git repository."""
        try:
            if target_dir.exists():
                logger.info(f"Repository already exists at {target_dir}, pulling latest changes...")
                result = subprocess.run(
                    ["git", "pull"],
                    cwd=target_dir,
                    capture_output=True,
                    text=True,
                    check=True
                )
            else:
                logger.info(f"Cloning {repo_url} to {target_dir}...")
                result = subprocess.run(
                    ["git", "clone", repo_url, str(target_dir)],
                    capture_output=True,
                    text=True,
                    check=True
                )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to clone {repo_url}: {e.stderr}")
            return False
            
    def _compile_parser(self, parser_name: str, parser_config: Dict[str, Any]) -> bool:
        """Compile a tree-sitter parser."""
        repo_url = parser_config["repository"]
        build_path = parser_config["build_path"]
        parser_lib_name = parser_config["parser_name"]
        
        # Clone repository
        repo_dir = self.build_dir / build_path
        if not self._clone_repository(repo_url, repo_dir):
            return False
            
        # Find the parser source files
        src_dir = repo_dir
        if "typescript" in build_path and parser_name == "typescript":
            src_dir = repo_dir / "typescript"
        elif "xml" in build_path and parser_name == "xml":
            src_dir = repo_dir / "xml"
            
        parser_c = src_dir / "src" / "parser.c"
        scanner_c = src_dir / "src" / "scanner.c"
        scanner_cc = src_dir / "src" / "scanner.cc"
        
        if not parser_c.exists():
            logger.error(f"parser.c not found in {src_dir}/src/")
            return False
            
        # Determine if we have C++ components
        has_cpp = scanner_cc.exists()
        
        # Get compiler and flags
        compiler, base_flags = self._get_compiler_command(has_cpp)
        
        # Use platform-appropriate extension
        lib_ext = self.platform_info['lib_ext']
        output_file = self.lib_dir / f"{parser_lib_name}{lib_ext}"
        
        # Prepare compilation command
        compile_cmd = [compiler] + base_flags + [
            "-I", str(src_dir / "src"),
            str(parser_c),
        ]
        
        # Add scanner file if it exists
        if scanner_c.exists():
            compile_cmd.append(str(scanner_c))
        elif scanner_cc.exists():
            compile_cmd.append(str(scanner_cc))
            
        compile_cmd.extend(["-o", str(output_file)])
        
        try:
            logger.info(f"Compiling {parser_name} for {self.platform_info['os']} {self.platform_info['arch']}...")
            logger.debug(f"Command: {' '.join(compile_cmd)}")
            
            result = subprocess.run(
                compile_cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            if output_file.exists():
                # Verify the binary architecture (on macOS/Linux)
                if shutil.which('file'):
                    try:
                        file_result = subprocess.run(
                            ['file', str(output_file)],
                            capture_output=True,
                            text=True,
                            check=True
                        )
                        logger.info(f"Built binary info: {file_result.stdout.strip()}")
                    except subprocess.CalledProcessError:
                        pass  # file command failed, but that's okay
                
                logger.info(f"Successfully compiled {parser_name} -> {output_file}")
                return True
            else:
                logger.error(f"Compilation succeeded but output file not found: {output_file}")
                return False
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to compile {parser_name}:")
            logger.error(f"stdout: {e.stdout}")
            logger.error(f"stderr: {e.stderr}")
            return False
            
    def build_all(self) -> bool:
        """Build all parsers defined in the configuration."""
        if not self._check_dependencies():
            return False
            
        parsers = self.config.get("parsers", {})
        if not parsers:
            logger.error("No parsers found in configuration")
            return False
            
        logger.info(f"Building {len(parsers)} parsers for {self.platform_info['os']} {self.platform_info['arch']}...")
        
        success_count = 0
        failed_parsers = []
        
        for parser_name, parser_config in parsers.items():
            logger.info(f"\n{'='*50}")
            logger.info(f"Building parser: {parser_name}")
            logger.info(f"{'='*50}")
            
            if self._compile_parser(parser_name, parser_config):
                success_count += 1
            else:
                failed_parsers.append(parser_name)
                
        # Summary
        logger.info(f"\n{'='*50}")
        logger.info("BUILD SUMMARY")
        logger.info(f"{'='*50}")
        logger.info(f"Platform: {self.platform_info['os']} {self.platform_info['arch']}")
        logger.info(f"Library format: {self.platform_info['lib_ext']}")
        logger.info(f"Successfully built: {success_count}/{len(parsers)} parsers")
        
        if failed_parsers:
            logger.error(f"Failed to build: {', '.join(failed_parsers)}")
            return False
        else:
            logger.info("All parsers built successfully!")
            logger.info(f"Parser libraries saved to: {self.lib_dir}")
            return True
            
    def clean(self):
        """Clean build and lib directories."""
        logger.info("Cleaning build and lib directories...")
        
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
            logger.info(f"Removed {self.build_dir}")
            
        if self.lib_dir.exists():
            shutil.rmtree(self.lib_dir)
            logger.info(f"Removed {self.lib_dir}")
            
        logger.info("Clean completed")
        
    def list_parsers(self):
        """List all available parsers in the configuration."""
        parsers = self.config.get("parsers", {})
        
        print(f"\nAvailable parsers ({len(parsers)}):")
        print(f"Target platform: {self.platform_info['os']} {self.platform_info['arch']}")
        print(f"Library extension: {self.platform_info['lib_ext']}")
        print("-" * 50)
        
        for name, config in parsers.items():
            extensions = ", ".join(config.get("extensions", []))
            lib_name = config.get("parser_name", name)
            output_name = f"{lib_name}{self.platform_info['lib_ext']}"
            print(f"  {name:<15} -> {output_name:<20} ({extensions})")
            
        print()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Build tree-sitter parsers from configuration")
    parser.add_argument("--config", default="parsers.json", help="Path to parsers.json config file")
    parser.add_argument("--clean", action="store_true", help="Clean build and lib directories")
    parser.add_argument("--list", action="store_true", help="List available parsers")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    builder = TreeSitterBuilder(args.config)
    
    if args.clean:
        builder.clean()
        return
        
    if args.list:
        builder.list_parsers()
        return
        
    # Build all parsers
    success = builder.build_all()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()