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
import re
import xmltodict
from typing import Dict, List, Any, Optional
from src.utils.xml_parsing_exceptions import XMLParsingFailedException


class XMLService:
    """Comprehensive service for all XML processing operations."""

    def __init__(self, llm_client: Optional[Any] = None):
        """
        Initialize XML service.

        Args:
            llm_client: Optional LLM client for XML repair functionality
        """
        self.llm_client = llm_client

    def parse_xml_response(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Parse LLM response and extract only XML data.

        Args:
            response_text (str): Raw LLM response text

        Returns:
            List[Dict[str, Any]]: List of parsed XML elements
        """
        try:
            logger.debug(f"Parsing XML response: {response_text[:200]}...")

            # Clean and fix common XML spacing issues
            cleaned_text = self.clean_xml_spacing(response_text)

            # Try to find valid XML blocks
            xml_pattern = r"<(\w+)(?:\s[^>]*?)?>(.*?)</\1>"
            xml_matches = list(
                re.finditer(xml_pattern, cleaned_text, re.DOTALL | re.IGNORECASE)
            )

            # If no valid XML found, try to repair malformed XML
            if not xml_matches:
                logger.debug("No valid XML blocks found, attempting repair...")
                repaired_text = self._repair_malformed_xml(cleaned_text)
                if repaired_text != cleaned_text:
                    xml_matches = list(
                        re.finditer(
                            xml_pattern, repaired_text, re.DOTALL | re.IGNORECASE
                        )
                    )
                    cleaned_text = repaired_text

            if not xml_matches:
                logger.warning("No valid XML blocks found after repair")
                return []

            # Parse each XML block
            parsed_xml_list = []
            for i, match in enumerate(xml_matches):
                xml_block = match.group(0)
                try:
                    parsed_xml = self._parse_single_xml_block(xml_block)
                    parsed_xml_list.append(parsed_xml)
                    logger.debug(f"Successfully parsed XML block {i+1}")
                except Exception as e:
                    logger.error(f"Failed to parse XML block {i+1}: {e}")
                    raise XMLParsingFailedException(
                        f"Failed to parse XML block {i+1}: {e}",
                        failed_block_index=i + 1,
                        original_error=e,
                    )

            logger.debug(f"Successfully parsed {len(parsed_xml_list)} XML blocks")
            return parsed_xml_list

        except XMLParsingFailedException:
            raise
        except Exception as e:
            logger.error(f"Error parsing XML response: {e}")
            return []

    def repair_xml(self, malformed_xml: str) -> Optional[str]:
        """
        Repair a single malformed XML block.

        Args:
            malformed_xml (str): The malformed XML that needs fixing

        Returns:
            Optional[str]: Repaired XML if successful, None if repair fails
        """
        if not self.llm_client:
            return None

        repaired_blocks = self._batch_repair_xml([malformed_xml])
        return repaired_blocks[0] if repaired_blocks else None

    def clean_xml_spacing(self, text: str) -> str:
        """
        Clean and fix common XML spacing issues.

        Args:
            text (str): Raw text with potential XML

        Returns:
            str: Cleaned text with fixed XML spacing
        """
        # Fix spacing in XML tags
        text = re.sub(r"<\s+(\w+)(?:\s+([^>]*?))?\s*>", r"<\1 \2>", text)
        text = re.sub(r"<\s*/\s*(\w+)\s*>", r"</\1>", text)

        # Clean attribute spacing
        text = re.sub(r'(\w+)\s*=\s*"([^"]*)"', r'\1="\2"', text)
        text = re.sub(r"(\w+)\s*=\s*\'([^\']*)\'", r"\1='\2'", text)

        # Remove trailing spaces before >
        text = re.sub(r"\s+>", ">", text)

        # Wrap problematic content in CDATA
        text = self.wrap_diff_content_in_cdata(text)

        return text

    def wrap_diff_content_in_cdata(self, text: str) -> str:
        """
        Wrap diff, content, and command content in CDATA sections.

        Args:
            text (str): Text containing XML tags

        Returns:
            str: Text with problematic content wrapped in CDATA
        """
        patterns = [
            (r"(<diff>)(.*?)(</diff>)", "diff"),
            (r"(<content>)(.*?)(</content>)", "content"),
            (r"(<command>)(.*?)(</command>)", "command"),
        ]

        for pattern, tag_name in patterns:

            def wrap_in_cdata(match):
                opening_tag, content, closing_tag = match.groups()

                # Check if content needs CDATA wrapping
                problematic_chars = [
                    "<<<<<<<",
                    ">>>>>>>",
                    "=======",
                    "-------",
                    "<",
                    ">",
                    "%",
                ]
                if (
                    any(char in content for char in problematic_chars)
                    and "<![CDATA[" not in content
                ):
                    return f"{opening_tag}<![CDATA[{content}]]>{closing_tag}"
                return match.group(0)

            text = re.sub(pattern, wrap_in_cdata, text, flags=re.DOTALL)

        return text

    def validate_xml_structure(self, xml_text: str) -> bool:
        """
        Validate XML structure by checking tag matching.

        Args:
            xml_text (str): XML text to validate

        Returns:
            bool: True if XML appears to have valid structure
        """
        try:
            opening_tags = re.findall(r"<(\w+)(?:\s[^>]*?)?>", xml_text)
            closing_tags = re.findall(r"</(\w+)>", xml_text)

            # Count occurrences
            opening_counts = {}
            for tag in opening_tags:
                opening_counts[tag] = opening_counts.get(tag, 0) + 1

            closing_counts = {}
            for tag in closing_tags:
                closing_counts[tag] = closing_counts.get(tag, 0) + 1

            # Check if counts match
            for tag, count in opening_counts.items():
                if closing_counts.get(tag, 0) != count:
                    return False

            return True

        except Exception as e:
            logger.error(f"Error validating XML structure: {e}")
            return False

    def detect_xml_issues(self, text: str) -> List[str]:
        """
        Detect common XML formatting issues.

        Args:
            text (str): XML text to analyze

        Returns:
            List[str]: List of detected issues
        """
        issues = []

        try:
            opening_tags = re.findall(r"<(\w+)(?:\s[^>]*?)?>", text)
            closing_tags = re.findall(r"</(\w+)>", text)

            # Check for unmatched tags
            for opening_tag in opening_tags:
                if opening_tag not in closing_tags:
                    # Look for potential truncated versions
                    truncated_matches = [
                        tag for tag in closing_tags if tag.startswith(opening_tag[:3])
                    ]
                    if truncated_matches:
                        issues.append(
                            f"Potential truncated tag: {opening_tag} -> {truncated_matches[0]}"
                        )
                    else:
                        issues.append(f"Unclosed tag: {opening_tag}")

        except Exception as e:
            logger.error(f"Error detecting XML issues: {e}")
            issues.append(f"Analysis error: {e}")

        return issues

    def set_llm_client(self, llm_client: Any) -> None:
        """
        Set or update the LLM client for repair operations.

        Args:
            llm_client: LLM client instance
        """
        self.llm_client = llm_client

    def _parse_single_xml_block(self, xml_block: str) -> Any:
        """
        Parse a single XML block with CDATA handling.

        Args:
            xml_block (str): XML block to parse

        Returns:
            Dict[str, Any]: Parsed XML data
        """
        # Handle CDATA sections
        cdata_replacements = {}
        cdata_pattern = r"<!\[CDATA\[(.*?)\]\]>"

        def replace_cdata(match):
            placeholder = f"__CDATA_{len(cdata_replacements)}__"
            cdata_replacements[placeholder] = match.group(1)
            return placeholder

        xml_block_clean = re.sub(
            cdata_pattern, replace_cdata, xml_block, flags=re.DOTALL
        )

        # Parse the XML
        parsed_xml = xmltodict.parse(xml_block_clean)

        # Restore CDATA content
        def restore_cdata(obj):
            if isinstance(obj, dict):
                return {k: restore_cdata(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [restore_cdata(item) for item in obj]
            elif isinstance(obj, str):
                for placeholder, content in cdata_replacements.items():
                    obj = obj.replace(placeholder, content)
                return obj
            return obj

        return restore_cdata(parsed_xml)

    def _repair_malformed_xml(self, text: str) -> str:
        """
        Detect and repair all malformed XML in text.

        Args:
            text (str): Text that may contain malformed XML

        Returns:
            str: Text with repaired XML
        """
        if not self.llm_client:
            return text

        # Find potential malformed XML patterns
        malformed_blocks = self._find_malformed_xml_blocks(text)

        if not malformed_blocks:
            return text

        # Repair all blocks in single LLM call
        logger.debug(
            f"Attempting to repair {len(malformed_blocks)} malformed XML blocks..."
        )
        repaired_blocks = self._batch_repair_xml(malformed_blocks)

        # Replace malformed blocks with repaired versions
        repaired_text = text
        for original, repaired in zip(malformed_blocks, repaired_blocks):
            if repaired and repaired != original:
                repaired_text = repaired_text.replace(original, repaired)

        return repaired_text

    def _find_malformed_xml_blocks(self, text: str) -> List[str]:
        """
        Find potentially malformed XML blocks in text.

        Args:
            text (str): Text to search

        Returns:
            List[str]: List of malformed XML blocks
        """
        malformed_blocks = []

        # Simple pattern: find XML-like structures with truncated closing tags
        pattern = r"<(\w+)([^>]*)>(.*?)</(\w+)>"
        matches = re.finditer(pattern, text, re.DOTALL)

        for match in matches:
            opening_tag = match.group(1)
            closing_tag = match.group(4)

            # Check if closing tag is truncated
            if len(closing_tag) < len(opening_tag) and opening_tag.startswith(
                closing_tag
            ):
                malformed_blocks.append(match.group(0))

        return malformed_blocks

    def _batch_repair_xml(self, malformed_blocks: List[str]) -> List[str]:
        """
        Repair multiple malformed XML blocks in a single LLM call.

        Args:
            malformed_blocks (List[str]): List of malformed XML blocks

        Returns:
            List[str]: List of repaired XML blocks
        """
        if not self.llm_client or not malformed_blocks:
            return malformed_blocks

        try:
            # Create batch repair prompt
            prompt = self._create_batch_repair_prompt(malformed_blocks)

            # Call LLM
            system_prompt = (
                "Fix malformed XML by correcting truncated or incomplete tags."
            )
            response_data = self.llm_client.call_llm(system_prompt, prompt)

            if not response_data:
                return malformed_blocks

            # Extract repaired blocks
            return self._extract_repaired_blocks(
                response_data,
            )

        except Exception as e:
            logger.error(f"Failed to batch repair XML: {e}")
            return malformed_blocks

    def _create_batch_repair_prompt(self, malformed_blocks: List[str]) -> str:
        """
        Create prompt for batch XML repair.

        Args:
            malformed_blocks (List[str]): Malformed XML blocks

        Returns:
            str: Repair prompt
        """
        numbered_blocks = [
            f"{i}. {block}" for i, block in enumerate(malformed_blocks, 1)
        ]
        blocks_text = "\n".join(numbered_blocks)

        return f"""Fix these malformed XML blocks by correcting truncated closing tags:

                MALFORMED XML:
                {blocks_text}

                Return the corrected XML blocks in the same numbered format:
                CORRECTED XML:"""

    def _extract_repaired_blocks(
        self,
        response_data: List[Dict],
    ) -> List[str]:
        """
        Extract repaired XML blocks from LLM response.

        Args:
            response_data (List[Dict]): LLM response data

        Returns:
            List[str]: Repaired XML blocks
        """
        # Get response text
        response_text = ""
        for item in response_data:
            if isinstance(item, dict) and "content" in item:
                response_text = item["content"]
                break
            elif isinstance(item, str):
                response_text = item
                break

        if not response_text:
            return []

        # Extract numbered blocks
        repaired_blocks = []
        lines = response_text.split("\n")

        for line in lines:
            line = line.strip()
            if re.match(r"^\d+\.\s*<", line):
                # Extract XML after number
                xml_part = re.sub(r"^\d+\.\s*", "", line)
                if xml_part.startswith("<") and ">" in xml_part:
                    repaired_blocks.append(xml_part)

        return repaired_blocks
