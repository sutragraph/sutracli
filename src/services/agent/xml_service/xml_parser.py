from loguru import logger
import re
import xmltodict
from typing import Dict, Any, Optional
from .xml_validator import XMLValidator
from .xml_issue import XMLAnalysis


class XMLParser:
    """Handles XML parsing with CDATA support and regex fallback."""

    CDATA_PATTERN = re.compile(r"<!\[CDATA\[(.*?)\]\]>", re.DOTALL)

    def parse_single_xml_block(self, xml_block: str) -> Any:
        """Parse a single XML block with CDATA handling and regex fallback."""
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
            
            # Try to clean and retry once if it's a character encoding issue
            if "not well-formed" in str(e) and "invalid token" in str(e):
                try:
                    # Apply additional cleaning for special characters
                    from .xml_cleaner import XMLCleaner
                    cleaner = XMLCleaner()
                    cleaned_block = cleaner.clean_xml_spacing(xml_block)
                    parsed_xml = xmltodict.parse(cleaned_block)
                    return self._restore_cdata(parsed_xml, cdata_replacements)
                except Exception as retry_error:
                    logger.error(f"Retry after cleaning also failed: {retry_error}")
            
            # If xmltodict fails completely, try regex fallback
            logger.warning("xmltodict parsing failed, attempting regex fallback")
            regex_result = self._parse_with_regex_fallback(xml_block)
            if regex_result is not None:
                logger.info("Successfully parsed XML using regex fallback")
                return regex_result
            
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

    def _parse_with_regex_fallback(self, xml_block: str) -> Optional[Dict[str, Any]]:
        """
        Parse XML using regex patterns when xmltodict fails.
        
        This method extracts data from common XML structures found in the system,
        particularly focusing on sutra_memory blocks with task, code, and add_history sections.
        
        Args:
            xml_block: The XML block to parse
            
        Returns:
            Parsed data structure or None if parsing fails
        """
        try:
            logger.debug("Attempting regex fallback parsing")
            
            # Detect the root element
            root_match = re.search(r'<(\w+)(?:\s[^>]*)?>', xml_block)
            if not root_match:
                logger.warning("No root element found in XML block")
                return None
                
            root_element = root_match.group(1)
            logger.debug(f"Detected root element: {root_element}")
            
            # Handle different root elements
            if root_element == "sutra_memory":
                return self._parse_sutra_memory_regex(xml_block)
            else:
                # Generic XML parsing for other elements
                return self._parse_generic_xml_regex(xml_block, root_element)
                
        except Exception as e:
            logger.error(f"Regex fallback parsing failed: {e}")
            return None

    def _parse_sutra_memory_regex(self, xml_block: str) -> Dict[str, Any]:
        """Parse sutra_memory XML block using regex patterns."""
        result = {"sutra_memory": {}}
        
        # Extract task section
        task_match = re.search(r'<task>(.*?)</task>', xml_block, re.DOTALL)
        if task_match:
            task_content = task_match.group(1).strip()
            result["sutra_memory"]["task"] = self._parse_task_content_regex(task_content)
        
        # Extract code section
        code_match = re.search(r'<code>(.*?)</code>', xml_block, re.DOTALL)
        if code_match:
            code_content = code_match.group(1).strip()
            result["sutra_memory"]["code"] = self._parse_code_content_regex(code_content)
        
        # Extract add_history section
        history_match = re.search(r'<add_history>(.*?)</add_history>', xml_block, re.DOTALL)
        if history_match:
            history_content = history_match.group(1).strip()
            result["sutra_memory"]["add_history"] = history_content
            
        return result

    def _parse_task_content_regex(self, task_content: str) -> Dict[str, Any]:
        """Parse task content using regex patterns."""
        task_data = {}
        
        # Extract move operations
        move_matches = re.findall(r'<move\s+from="([^"]*?)"\s+to="([^"]*?)"[^>]*>([^<]*?)</move>', task_content)
        if move_matches:
            moves = []
            for from_val, to_val, content in move_matches:
                moves.append({
                    "@from": from_val,
                    "@to": to_val,
                    "#text": content.strip()
                })
            task_data["move"] = moves if len(moves) > 1 else moves[0]
            
        return task_data

    def _parse_code_content_regex(self, code_content: str) -> Dict[str, Any]:
        """Parse code content using regex patterns to extract add elements."""
        code_data = {}
        
        # Extract add elements with their attributes and nested content
        add_pattern = r'<add\s+id="([^"]*?)"[^>]*?>(.*?)</add>'
        add_matches = re.findall(add_pattern, code_content, re.DOTALL)
        
        if add_matches:
            adds = []
            for add_id, add_content in add_matches:
                add_item = {"@id": add_id}
                
                # Extract nested elements within add
                file_match = re.search(r'<file>(.*?)</file>', add_content)
                if file_match:
                    add_item["file"] = file_match.group(1).strip()
                
                start_line_match = re.search(r'<start_line>(.*?)</start_line>', add_content)
                if start_line_match:
                    add_item["start_line"] = start_line_match.group(1).strip()
                
                end_line_match = re.search(r'<end_line>(.*?)</end_line>', add_content)
                if end_line_match:
                    add_item["end_line"] = end_line_match.group(1).strip()
                
                description_match = re.search(r'<description>(.*?)</description>', add_content, re.DOTALL)
                if description_match:
                    add_item["description"] = description_match.group(1).strip()
                
                adds.append(add_item)
            
            code_data["add"] = adds
            
        return code_data

    def _parse_generic_xml_regex(self, xml_block: str, root_element: str) -> Dict[str, Any]:
        """Parse generic XML structure using regex patterns."""
        result = {root_element: {}}
        
        # Extract all direct child elements
        # This pattern matches opening tag, content, and closing tag
        child_pattern = rf'<(\w+)(?:\s[^>]*)?>(.*?)</\1>'
        child_matches = re.findall(child_pattern, xml_block, re.DOTALL)
        
        for tag_name, content in child_matches:
            if tag_name == root_element:
                continue  # Skip the root element itself
                
            content = content.strip()
            
            # Check if content contains nested XML
            if re.search(r'<\w+', content):
                # Recursively parse nested content
                nested_result = self._parse_generic_xml_regex(f'<{tag_name}>{content}</{tag_name}>', tag_name)
                result[root_element][tag_name] = nested_result.get(tag_name, content)
            else:
                result[root_element][tag_name] = content
                
        return result

    def _extract_xml_attributes_regex(self, tag_content: str) -> Dict[str, str]:
        """Extract attributes from XML tag using regex."""
        attributes = {}
        
        # Pattern to match attribute="value" or attribute='value'
        attr_pattern = r'(\w+)\s*=\s*["\']([^"\']*)["\']'
        attr_matches = re.findall(attr_pattern, tag_content)
        
        for attr_name, attr_value in attr_matches:
            attributes[f"@{attr_name}"] = attr_value
            
        return attributes
