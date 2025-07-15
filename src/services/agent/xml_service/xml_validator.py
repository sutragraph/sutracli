from loguru import logger
import re
from typing import Dict, List, Tuple
from .xml_issue import XMLIssue


class XMLValidator:
    """Handles XML validation and issue detection."""

    OPENING_TAG_PATTERN = re.compile(r"<(\w+)(?:\s[^>]*?)?>")
    CLOSING_TAG_PATTERN = re.compile(r"</(\w+)>")
    SPECIAL_CHARS_PATTERN = re.compile(r"[<>&](?![#\w]+;)")
    MALFORMED_ATTRS_PATTERN = re.compile(r'\w+\s*=\s*[^"\'][^>\s]*(?!["\'])')

    def validate_xml_structure(self, xml_text: str) -> bool:
        """Validate XML structure by checking tag matching."""
        try:
            tag_counts = self._count_tags(xml_text)
            return self._tags_are_balanced(tag_counts)
        except Exception as e:
            logger.error(f"Error validating XML structure: {e}")
            return False

    def detect_xml_issues(self, text: str) -> List[XMLIssue]:
        """Detect common XML formatting issues."""
        issues = []

        try:
            tag_counts = self._count_tags(text)

            # Check for unmatched tags
            for tag, (open_count, close_count) in tag_counts.items():
                if open_count != close_count:
                    issues.append(
                        XMLIssue(
                            issue_type="unmatched_tags",
                            description=f"Tag '{tag}': {open_count} opening, {close_count} closing",
                            location=tag,
                        )
                    )

            # Check for other issues
            if self.SPECIAL_CHARS_PATTERN.search(text):
                issues.append(
                    XMLIssue(
                        issue_type="unescaped_chars",
                        description="Contains unescaped special characters",
                    )
                )

            if self.MALFORMED_ATTRS_PATTERN.search(text):
                issues.append(
                    XMLIssue(
                        issue_type="malformed_attrs",
                        description="Contains malformed attributes",
                    )
                )

            if text.count("<![CDATA[") != text.count("]]>"):
                issues.append(
                    XMLIssue(
                        issue_type="unmatched_cdata",
                        description="Unmatched CDATA sections",
                    )
                )

            if text.endswith("<") or text.endswith("</"):
                issues.append(
                    XMLIssue(
                        issue_type="truncated",
                        description="XML appears to be truncated",
                    )
                )

        except Exception as e:
            logger.error(f"Error detecting XML issues: {e}")
            issues.append(
                XMLIssue(
                    issue_type="analysis_error", description=f"Analysis error: {e}"
                )
            )

        return issues

    def _count_tags(self, text: str) -> Dict[str, Tuple[int, int]]:
        """Count opening and closing tags."""
        opening_tags = self.OPENING_TAG_PATTERN.findall(text)
        closing_tags = self.CLOSING_TAG_PATTERN.findall(text)

        tag_counts = {}
        for tag in set(opening_tags + closing_tags):
            open_count = opening_tags.count(tag)
            close_count = closing_tags.count(tag)
            tag_counts[tag] = (open_count, close_count)

        return tag_counts

    def _tags_are_balanced(self, tag_counts: Dict[str, Tuple[int, int]]) -> bool:
        """Check if all tags are balanced."""
        return all(
            open_count == close_count for open_count, close_count in tag_counts.values()
        )
