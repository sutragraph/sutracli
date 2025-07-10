from loguru import logger
import re
import xmltodict
from typing import Dict, List, Any, Optional
from src.utils.xml_parsing_exceptions import XMLParsingFailedException


class LLMClientBase:
    """Base class for all LLM clients with XML processing capabilities."""

    def parse_xml_response(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Parse LLM response and extract only XML data using xmltodict.

        Handles responses that may contain:
        - Text before and after XML tags
        - Spacing issues in XML tags
        - Multiple XML blocks
        - Malformed XML tags

        Args:
            response_text (str): Raw LLM response text

        Returns:
            List[Dict[str, Any]]: List of parsed XML elements only
        """
        try:
            logger.debug(f"Parsing XML response: {response_text[:200]}...")

            # Clean and fix common XML spacing issues
            cleaned_text = self._clean_xml_spacing(response_text)

            # Find all XML-like blocks with proper structure including attributes
            # This pattern handles XML with attributes like <tool line="1">
            xml_pattern = r"<(\w+)(?:\s[^>]*?)?>(.*?)</\1>"
            xml_matches = list(
                re.finditer(xml_pattern, cleaned_text, re.DOTALL | re.IGNORECASE)
            )

            if not xml_matches:
                logger.warning("No valid XML blocks found in response")
                return []

            parsed_xml_list = []

            # Process each XML block
            for i, match in enumerate(xml_matches):
                xml_block = match.group(0)

                try:
                    # Handle CDATA sections by temporarily replacing them
                    cdata_replacements = {}
                    cdata_pattern = r"<!\[CDATA\[(.*?)\]\]>"

                    def replace_cdata(match):
                        placeholder = f"__CDATA_{len(cdata_replacements)}__"
                        cdata_replacements[placeholder] = match.group(1)
                        return placeholder

                    xml_block_clean = re.sub(
                        cdata_pattern, replace_cdata, xml_block, flags=re.DOTALL
                    )

                    # Parse the cleaned XML
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

                    parsed_xml = restore_cdata(parsed_xml)
                    parsed_xml_list.append(parsed_xml)
                    logger.debug(f"Successfully parsed XML block {i+1}")

                except Exception as xml_error:
                    logger.debug(f"Failed to parse XML block {i+1}: {xml_error}")
                    # Try to extract content manually for diff and content blocks
                    if "<diff>" in xml_block and "</diff>" in xml_block:
                        try:
                            diff_match = re.search(
                                r"<diff>(.*?)</diff>", xml_block, re.DOTALL
                            )
                            if diff_match:
                                diff_content = diff_match.group(1).strip()
                                parsed_xml_list.append({"diff": diff_content})
                                logger.debug(
                                    f"Manually extracted diff content from block {i+1}"
                                )
                                continue
                        except Exception:
                            pass

                    if "<content>" in xml_block and "</content>" in xml_block:
                        try:
                            content_match = re.search(
                                r"<content>(.*?)</content>", xml_block, re.DOTALL
                            )
                            if content_match:
                                content_data = content_match.group(1).strip()
                                parsed_xml_list.append({"content": content_data})
                                logger.debug(
                                    f"Manually extracted content from block {i+1}"
                                )
                                continue
                        except Exception:
                            pass
                    # Instead of skipping, raise exception to trigger retry
                    logger.error(f"XML parsing failed for block {i+1}, discarding response and retrying")
                    raise XMLParsingFailedException(
                        f"Failed to parse XML block {i+1}: {xml_error}",
                        failed_block_index=i+1,
                        original_error=xml_error
                    )

            logger.debug(f"Successfully parsed {len(parsed_xml_list)} XML blocks")
            return parsed_xml_list

        except Exception as e:
            logger.error(f"Error parsing XML response: {e}")
            return []

    def _clean_xml_spacing(self, text: str) -> str:
        """
        Clean and fix common XML spacing issues.

        Args:
            text (str): Raw text with potential XML

        Returns:
            str: Cleaned text with fixed XML spacing
        """
        # Fix spacing in XML opening tags with attributes (e.g., "< tool line = '1' >" -> "<tool line='1'>")
        text = re.sub(r"<\s+(\w+)(?:\s+([^>]*?))?\s*>", r"<\1 \2>", text)
        text = re.sub(r"<\s*/\s*(\w+)\s*>", r"</\1>", text)

        # Remove extra spaces in attribute assignments
        text = re.sub(r'(\w+)\s*=\s*"([^"]*)"', r'\1="\2"', text)
        text = re.sub(r"(\w+)\s*=\s*\'([^\']*)\'", r"\1=\'\2\'", text)

        # Fix common malformed tags and normalize spacing
        text = re.sub(
            r"<\s*(\w+)\s*([^>]*?)\s*>",
            lambda m: f'<{m.group(1)}{" " + m.group(2).strip() if m.group(2).strip() else ""}>',
            text,
        )

        # Ensure there's no trailing space before >
        text = re.sub(r"\s+>", ">", text)

        # Wrap problematic content in CDATA sections for diff tags
        text = self._wrap_diff_content_in_cdata(text)

        return text

    def _wrap_diff_content_in_cdata(self, text: str) -> str:
        """
        Wrap diff, content, and command in CDATA sections to handle special characters.

        Args:
            text (str): Text containing diff/content/command XML

        Returns:
            str: Text with problematic content wrapped in CDATA
        """
        # Pattern to match content that contains problematic characters
        diff_pattern = r"(<diff>)(.*?)(</diff>)"
        content_pattern = r"(<content>)(.*?)(</content>)"
        command_pattern = r"(<command>)(.*?)(</command>)"

        def wrap_in_cdata(match):
            opening_tag = match.group(1)
            content = match.group(2)
            closing_tag = match.group(3)

            # Check if content contains characters that break XML parsing
            if (
                any(
                    char in content
                    for char in ["<<<<<<<", ">>>>>>>", "=======", "-------", "<", ">", "%"]
                )
                and "<![CDATA[" not in content
            ):
                # Wrap in CDATA
                return f"{opening_tag}<![CDATA[{content}]]>{closing_tag}"
            else:
                return match.group(0)

        # Apply to diff, content, and command tags
        text = re.sub(diff_pattern, wrap_in_cdata, text, flags=re.DOTALL)
        text = re.sub(content_pattern, wrap_in_cdata, text, flags=re.DOTALL)
        text = re.sub(command_pattern, wrap_in_cdata, text, flags=re.DOTALL)
        return text

    def extract_specific_xml_tags(
        self, response_text: str, tag_names: List[str]
    ) -> Dict[str, List[Dict]]:
        """
        Extract specific XML tags from the response.

        Args:
            response_text (str): Raw LLM response text
            tag_names (List[str]): List of tag names to extract (e.g., ['tool', 'thinking'])

        Returns:
            Dict[str, List[Dict]]: Dictionary with tag names as keys and list of parsed elements as values
        """
        try:
            parsed_xml_list = self.parse_xml_response(response_text)
            extracted_tags = {tag_name: [] for tag_name in tag_names}

            for xml_data in parsed_xml_list:
                if isinstance(xml_data, dict):
                    # Check each root element in the parsed XML
                    for key, value in xml_data.items():
                        if key in tag_names:
                            if isinstance(value, list):
                                extracted_tags[key].extend(value)
                            else:
                                extracted_tags[key].append(value)

            return extracted_tags

        except Exception as e:
            logger.error(f"Error extracting specific XML tags: {e}")
            return {tag_name: [] for tag_name in tag_names}

    def call_llm(self, *args, **kwargs) -> List[Dict[str, Any]]:
        """
        Base method to be implemented by subclasses.
        Subclasses should call parse_xml_response before returning data.

        Returns:
            List of parsed XML elements
        """
        raise NotImplementedError("Subclasses must implement call_llm method")
