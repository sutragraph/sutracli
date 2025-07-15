from loguru import logger
import re
import xmltodict
from typing import Dict, Any
from .xml_validator import XMLValidator
from .xml_issue import XMLAnalysis


class XMLParser:
    """Handles XML parsing with CDATA support."""

    CDATA_PATTERN = re.compile(r"<!\[CDATA\[(.*?)\]\]>", re.DOTALL)

    def parse_single_xml_block(self, xml_block: str) -> Any:
        """Parse a single XML block with CDATA handling."""
        try:
            # Handle CDATA sections
            cdata_replacements = {}
            xml_block_clean = self.CDATA_PATTERN.sub(
                lambda m: self._replace_cdata(m, cdata_replacements), xml_block
            )

            # Parse the XML
            parsed_xml = xmltodict.parse(xml_block_clean)

            # Restore CDATA content
            return self._restore_cdata(parsed_xml, cdata_replacements)

        except Exception as e:
            # Provide detailed error diagnostics
            analysis = self._analyze_xml_parsing_error(xml_block, e)
            logger.error(f"XML parsing failed: {analysis}")
            raise e

    def _replace_cdata(self, match: re.Match, replacements: Dict[str, str]) -> str:
        """Replace CDATA with placeholder."""
        placeholder = f"__CDATA_{len(replacements)}__"
        replacements[placeholder] = match.group(1)
        return placeholder

    def _restore_cdata(self, obj: Any, replacements: Dict[str, str]) -> Any:
        """Restore CDATA content from placeholders."""
        if isinstance(obj, dict):
            return {k: self._restore_cdata(v, replacements) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._restore_cdata(item, replacements) for item in obj]
        elif isinstance(obj, str):
            for placeholder, content in replacements.items():
                obj = obj.replace(placeholder, content)
            return obj
        return obj

    def _analyze_xml_parsing_error(
        self, xml_block: str, error: Exception
    ) -> XMLAnalysis:
        """Analyze XML parsing error to provide detailed diagnostics."""
        validator = XMLValidator()
        issues = validator.detect_xml_issues(xml_block)
        tag_counts = validator._count_tags(xml_block)

        return XMLAnalysis(
            error_type=type(error).__name__,
            error_message=str(error),
            xml_length=len(xml_block),
            xml_preview=xml_block[:200] + "..." if len(xml_block) > 200 else xml_block,
            issues_found=issues,
            tag_structure={
                "tag_counts": tag_counts,
                "opening_tags": validator.OPENING_TAG_PATTERN.findall(xml_block),
                "closing_tags": validator.CLOSING_TAG_PATTERN.findall(xml_block),
            },
        )
