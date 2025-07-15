from dataclasses import dataclass
from typing import Dict, List, Any, Optional


@dataclass
class XMLIssue:
    """Data class for XML validation issues."""

    issue_type: str
    description: str
    location: Optional[str] = None


@dataclass
class XMLAnalysis:
    """Data class for XML parsing error analysis."""

    error_type: str
    error_message: str
    xml_length: int
    xml_preview: str
    issues_found: List[XMLIssue]
    tag_structure: Dict[str, Any]
