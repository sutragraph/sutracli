"""
XML Service

This service handles all XML processing functionality including parsing, cleaning,
validation, and repair of XML content from LLM responses. It consolidates all
XML-related operations in a clean, efficient manner.

Main responsibilities:
- Parse LLM responses and extract XML data
- Clean and fix common XML formatting issues
- Handle CDATA sections properly
- Repair malformed/truncated XML using LLM calls (batched for efficiency)
- Validate XML structure
"""

from loguru import logger
from typing import Dict, List, Any, Optional
from utils.xml_parsing_exceptions import XMLParsingFailedException
from .xml_block_finder import XMLBlockFinder, XMLMatch
from .xml_parser import XMLParser
from .xml_cleaner import XMLCleaner
from .xml_validator import XMLValidator
from .xml_repair import XMLRepair
from .xml_issue import XMLIssue


class XMLService:
    """Comprehensive service for all XML processing operations."""

    def __init__(self, llm_client: Optional[Any] = None):
        self.llm_client = llm_client
        self.cleaner = XMLCleaner()
        self.validator = XMLValidator()
        self.repair_service = XMLRepair(llm_client)
        self.parser = XMLParser()
        self.block_finder = XMLBlockFinder()

    def parse_xml_response(self, response_text: str) -> List[Dict[str, Any]]:
        """Parse LLM response and extract only XML data."""
        try:
            # Clean and fix common XML spacing issues
            cleaned_text = self.cleaner.clean_xml_spacing(response_text)

            # Check for malformed XML first and repair if needed
            repaired_text = self.repair_service.repair_malformed_xml_in_text(
                cleaned_text
            )

            # Find complete XML blocks with proper nesting support
            xml_matches = self.block_finder.find_complete_xml_blocks(repaired_text)

            if not xml_matches:
                logger.warning("No valid XML blocks found after repair")
                return []

            # Parse each XML block
            return self._parse_xml_blocks(xml_matches)

        except XMLParsingFailedException:
            raise
        except Exception as e:
            logger.error(f"Error parsing XML response: {e}")
            return []

    def repair_xml(self, malformed_xml: str) -> Optional[str]:
        """Repair a single malformed XML block."""
        return self.repair_service.repair_xml(malformed_xml)

    def repair_malformed_xml_in_text(self, text: str) -> str:
        """Detect and repair all malformed XML in text."""
        return self.repair_service.repair_malformed_xml_in_text(text)

    def clean_xml_spacing(self, text: str) -> str:
        """Clean and fix common XML spacing issues."""
        return self.cleaner.clean_xml_spacing(text)

    def validate_xml_structure(self, xml_text: str) -> bool:
        """Validate XML structure by checking tag matching."""
        return self.validator.validate_xml_structure(xml_text)

    def detect_xml_issues(self, text: str) -> List[XMLIssue]:
        """Detect common XML formatting issues."""
        return self.validator.detect_xml_issues(text)

    def set_llm_client(self, llm_client: Any) -> None:
        """Set or update the LLM client for repair operations."""
        self.llm_client = llm_client
        self.repair_service.llm_client = llm_client

    def _parse_xml_blocks(self, xml_matches: List[XMLMatch]) -> List[Dict[str, Any]]:
        """Parse multiple XML blocks."""
        parsed_xml_list = []

        for i, match in enumerate(xml_matches):
            xml_block = match.group(0)
            try:
                parsed_xml = self.parser.parse_single_xml_block(xml_block)
                parsed_xml_list.append(parsed_xml)
                logger.debug(f"Successfully parsed XML block {i+1}")
            except Exception as e:
                logger.error(f"Failed to parse XML block {i+1}: {e}")
                raise XMLParsingFailedException(
                    f"Failed to parse XML block {i+1} - {xml_block}: {e}",
                    failed_block_index=i + 1,
                    original_error=e,
                )

        logger.debug(f"Successfully parsed {len(parsed_xml_list)} XML blocks")
        return parsed_xml_list
