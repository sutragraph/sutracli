import subprocess
from pathlib import Path
from typing import List
from ..base_linter import BaseLinter, LintResult
from config.settings import config


class JavaLinter(BaseLinter):
    """Java linter using checkstyle."""
    
    @property
    def language(self) -> str:
        return "java"
    
    @property
    def file_extensions(self) -> List[str]:
        return [".java"]
    
    def lint_file(self, file_path: Path) -> LintResult:
        errors = []

        linter_path = Path(config.storage.linters_dir) / "checkstyle"
        result = subprocess.run(
            [str(linter_path), "-c", "/google_checks.xml", str(file_path)],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            errors.extend(result.stdout.strip().split('\n'))
        
        return LintResult(
            success=len(errors) == 0,
            errors=errors,
        )