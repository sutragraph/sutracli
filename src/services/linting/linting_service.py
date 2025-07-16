from pathlib import Path
from typing import Dict, List, Optional
from .base_linter import BaseLinter, LintResult
from .linters import PythonLinter, JavaScriptLinter, GoLinter, JavaLinter
from typing import Dict, Set, Any
from loguru import logger

class LintingService:
    """Main linting service that manages all language-specific linters."""
    
    def __init__(self):
        self.linters: Dict[str, BaseLinter] = {}
        self._register_linters()
    
    def _register_linters(self):
        """Register all linters."""
        linters = [
            PythonLinter(),
            JavaScriptLinter(),
            GoLinter(),
            JavaLinter()
        ]
        
        for linter in linters:
            self.linters[linter.language] = linter
            for ext in linter.file_extensions:
                self.linters[ext] = linter
    
    def get_linter_for_file(self, file_path: Path) -> Optional[BaseLinter]:
        """Get appropriate linter for file."""
        return self.linters.get(file_path.suffix.lower())
    
    def lint_file(self, file_path: Path) -> Optional[LintResult]:
        """Lint a single file."""
        linter = self.get_linter_for_file(file_path)
        if not linter:
            return None
        
        return linter.lint_file(file_path)
    
    def lint_files(self, file_paths: List[Path]) -> Dict[Path, LintResult]:
        """Lint multiple files"""
        results = {}
        for file_path in file_paths:
            result = self.lint_file(file_path)
            if result:
                results[file_path] = result
        return results
    
    def _lint_changed_files(self, file_paths: List) -> List[str]:
        """Run linting on changed and new files."""
        try:
            if not file_paths:
                return []
          
            return self.lint_files(file_paths)
            
        except Exception as e:
            logger.error(f"Error linting changed files: {e}")
            return []
    
