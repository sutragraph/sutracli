from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List
from pathlib import Path

@dataclass
class LintResult:
    """Result of linting operation."""
    success: bool
    errors: List[str]
    
    @property
    def has_issues(self) -> bool:
        return bool(self.errors or self.warnings)


class BaseLinter(ABC):
    """Base class for language-specific linters."""
    
    @property
    @abstractmethod
    def language(self) -> str:
        """Language this linter supports."""
        pass
    
    @property
    @abstractmethod
    def file_extensions(self) -> List[str]:
        """File extensions this linter handles."""
        pass
    
    @abstractmethod
    def lint_file(self, file_path: Path) -> LintResult:
        """Lint a single file."""
        pass
    