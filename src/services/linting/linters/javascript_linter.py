import subprocess
from pathlib import Path
from typing import List
from ..base_linter import BaseLinter, LintResult
from config.settings import config


class JavaScriptLinter(BaseLinter):
    """JavaScript/TypeScript linter using eslint."""

    @property
    def language(self) -> str:
        return "javascript"

    @property
    def file_extensions(self) -> List[str]:
        return [".js", ".jsx", ".ts", ".tsx"]

    def lint_file(self, file_path: Path) -> LintResult:
        errors = []

        linter_path = Path(config.storage.linters_dir) / "eslint"
        # Use biome instead of eslint for JS/TS linting
        biome_path = Path(config.storage.base_dir) / "linters" / "biome"
        if biome_path.exists():
            result = subprocess.run(
                [str(biome_path), "lint", str(file_path)],
                capture_output=True,
                text=True,
            )
        else:
            # Fallback to eslint if available
            result = subprocess.run(
                [str(linter_path), str(file_path), "--format", "compact"],
                capture_output=True,
                text=True,
            )
            
        if result.returncode != 0:
            errors.extend(result.stdout.strip().split("\n"))

        return LintResult(
            success=len(errors) == 0,
            errors=errors,
        )
