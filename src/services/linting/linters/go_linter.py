import subprocess
from pathlib import Path
from typing import List
from ..base_linter import BaseLinter, LintResult
from config.settings import config


class GoLinter(BaseLinter):
    """Go linter using golangci-lint."""
    
    @property
    def language(self) -> str:
        return "go"
    
    @property
    def file_extensions(self) -> List[str]:
        return [".go"]
    
    def lint_file(self, file_path: Path) -> LintResult:
        errors = []
        
        linter_path = Path(config.storage.linters_dir) / "golangci-lint"
        result = subprocess.run(
            [str(linter_path), "run", str(file_path)],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            errors.extend(result.stdout.strip().split('\n'))
        
        return LintResult(
            success=len(errors) == 0,
            errors=errors,
        )