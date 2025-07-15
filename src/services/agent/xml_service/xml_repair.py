from loguru import logger
import re
from typing import List, Any, Optional, Tuple
from .xml_validator import XMLValidator


class XMLRepair:
    """Handles XML repair operations using LLM."""

    def __init__(self, llm_client: Optional[Any] = None):
        self.llm_client = llm_client
        self.validator = XMLValidator()

    def repair_xml(self, malformed_xml: str) -> Optional[str]:
        """Repair a single malformed XML block."""
        if not self.llm_client:
            return None

        repaired_blocks = self.batch_repair_xml([malformed_xml])
        return repaired_blocks[0] if repaired_blocks else None

    def repair_malformed_xml_in_text(self, text: str) -> str:
        """Detect and repair all malformed XML in text."""
        if not self.llm_client:
            logger.debug("No LLM client available for XML repair")
            return text

        malformed_blocks = self._find_malformed_xml_blocks(text)
        logger.debug(f"Found {len(malformed_blocks)} potentially malformed XML blocks")

        if not malformed_blocks:
            return text

        repaired_blocks = self.batch_repair_xml(malformed_blocks)
        return self._replace_malformed_blocks(text, malformed_blocks, repaired_blocks)

    def batch_repair_xml(self, malformed_blocks: List[str]) -> List[str]:
        """Repair multiple malformed XML blocks in a single LLM call."""
        if not self.llm_client or not malformed_blocks:
            return malformed_blocks

        try:
            prompt = self._create_batch_repair_prompt(malformed_blocks)
            system_prompt = self._get_repair_system_prompt()

            raw_response = self.llm_client.call_llm(
                system_prompt, prompt, return_raw=True
            )

            if not raw_response:
                logger.warning("LLM returned empty response")
                return malformed_blocks

            return self._extract_repaired_blocks_from_text(raw_response)

        except Exception as e:
            logger.error(f"Failed to batch repair XML: {e}")
            return malformed_blocks

    def _find_malformed_xml_blocks(self, text: str) -> List[str]:
        """Find potentially malformed XML blocks in text."""
        malformed_blocks = []

        # Pattern 1: XML-like structures with truncated closing tags
        pattern = r"<(\w+)([^>]*)>(.*?)</(\w+)>"
        matches = re.finditer(pattern, text, re.DOTALL)

        for match in matches:
            opening_tag = match.group(1)
            closing_tag = match.group(4)

            if self._is_truncated_tag(opening_tag, closing_tag):
                malformed_blocks.append(match.group(0))

        # Pattern 2: Look for completely unmatched tags if no truncated tags found
        if not malformed_blocks:
            malformed_blocks.extend(self._find_unmatched_tag_blocks(text))

        return malformed_blocks

    def _is_truncated_tag(self, opening_tag: str, closing_tag: str) -> bool:
        """Check if closing tag is truncated version of opening tag."""
        return (
            opening_tag != closing_tag
            and len(closing_tag) < len(opening_tag)
            and opening_tag.startswith(closing_tag)
        )

    def _find_unmatched_tag_blocks(self, text: str) -> List[str]:
        """Find blocks with unmatched tags."""
        tag_counts = self.validator._count_tags(text)
        malformed_blocks = []

        for tag, (open_count, close_count) in tag_counts.items():
            if open_count > close_count:
                tag_pattern = rf"<{tag}(?:\s[^>]*?)?>.*?(?=<{tag}|$)"
                tag_match = re.search(tag_pattern, text, re.DOTALL)
                if tag_match and not tag_match.group(0).endswith(f"</{tag}>"):
                    malformed_blocks.append(tag_match.group(0))
                    break  # Only add one main block per tag type

        return malformed_blocks

    def _replace_malformed_blocks(
        self, text: str, malformed_blocks: List[str], repaired_blocks: List[str]
    ) -> str:
        """Replace malformed blocks with repaired versions."""
        repaired_text = text
        replacements_made = 0

        # Sort by length descending to replace longer blocks first
        replacement_pairs = list(zip(malformed_blocks, repaired_blocks))
        replacement_pairs.sort(key=lambda x: len(x[0]), reverse=True)

        for original, repaired in replacement_pairs:
            if repaired and repaired != original and original in repaired_text:
                repaired_text = repaired_text.replace(original, repaired, 1)
                replacements_made += 1

        logger.debug(f"Made {replacements_made} XML block replacements")
        return repaired_text

    def _create_batch_repair_prompt(self, malformed_blocks: List[str]) -> str:
        """Create prompt for batch XML repair."""
        numbered_blocks = [
            f"{i}. {block}" for i, block in enumerate(malformed_blocks, 1)
        ]
        blocks_text = "\n".join(numbered_blocks)

        return f"""Fix these malformed XML blocks by correcting issues like:
- Truncated or mismatched closing tags
- Missing closing tags
- Structural problems

MALFORMED XML:
{blocks_text}

Return ONLY the corrected XML blocks in the same numbered format. Do not include any explanations or additional text:

CORRECTED XML:"""

    def _get_repair_system_prompt(self) -> str:
        """Get system prompt for XML repair."""
        return (
            "You are an XML repair expert. Fix malformed XML by correcting truncated tags, "
            "missing closing tags, and structural issues. Return only the corrected XML blocks "
            "in the same numbered format as provided."
        )

    def _extract_repaired_blocks_from_text(self, response_text: str) -> List[str]:
        """Extract repaired XML blocks from raw text response."""
        if not response_text:
            return []

        # Try multiple extraction patterns
        patterns = [
            r"(\d+)\.\s*(<\w+[^>]*>.*?</\w+>)",  # Numbered blocks
            r"<(\w+)(?:\s[^>]*?)?>(.*?)</\1>",  # XML blocks
            r"<\w+[^>]*>.*?</\w+>",  # Broad XML pattern
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, response_text, re.DOTALL)
            blocks = []

            for match in matches:
                if pattern == patterns[0]:  # Numbered pattern
                    blocks.append(match.group(2).strip())
                else:
                    blocks.append(match.group(0))

            if blocks:
                return blocks

        return []
