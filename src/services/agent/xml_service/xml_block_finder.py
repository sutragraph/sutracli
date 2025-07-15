from typing import List, NamedTuple
import re


class XMLMatch(NamedTuple):
    """Immutable match object for XML blocks."""

    text: str
    start_pos: int
    end_pos: int

    def group(self, index: int = 0) -> str:
        return self.text if index == 0 else None

    def start(self) -> int:
        return self.start_pos

    def end(self) -> int:
        return self.end_pos


class XMLBlockFinder:
    """Parser for finding complete XML blocks with proper nesting support."""

    OPENING_PATTERN = re.compile(r"<(\w+)(?:\s[^>]*?)?>")
    CLOSING_PATTERN = re.compile(r"</(\w+)>")

    def find_complete_xml_blocks(self, text: str) -> List[XMLMatch]:
        """
        Find complete XML blocks that properly handle nested structures.

        Args:
            text: Text to search for XML blocks

        Returns:
            List of XMLMatch objects for complete XML blocks
        """
        xml_blocks = []
        position = 0

        while position < len(text):
            block_match = self._find_next_complete_block(text, position)
            if not block_match:
                break

            xml_blocks.append(block_match)
            position = block_match.end_pos

        return xml_blocks

    def _find_next_complete_block(self, text: str, start_pos: int) -> XMLMatch:
        """Find the next complete XML block starting from the given position."""
        opening_match = self.OPENING_PATTERN.search(text, start_pos)
        if not opening_match:
            return None

        tag_name = opening_match.group(1)
        block_start = opening_match.start()
        content_start = opening_match.end()

        block_end = self._find_matching_closing_tag(text, content_start, tag_name)
        if block_end is None:
            return None

        xml_text = text[block_start:block_end]
        return XMLMatch(xml_text, block_start, block_end)

    def _find_matching_closing_tag(
        self, text: str, start_pos: int, tag_name: str
    ) -> int:
        """Find the position after the matching closing tag, handling nesting."""
        nesting_level = 1
        position = start_pos

        while position < len(text) and nesting_level > 0:
            next_tag = self._find_next_tag(text, position)
            if not next_tag:
                break

            tag_type, found_tag_name, tag_end = next_tag

            if found_tag_name == tag_name:
                nesting_level += 1 if tag_type == "opening" else -1

            position = tag_end

        return position if nesting_level == 0 else None

    def _find_next_tag(self, text: str, start_pos: int) -> tuple:
        """
        Find the next XML tag (opening or closing) starting from the given position.

        Returns:
            Tuple of (tag_type, tag_name, end_position) or None if no tag found
        """
        opening_match = self.OPENING_PATTERN.search(text, start_pos)
        closing_match = self.CLOSING_PATTERN.search(text, start_pos)

        # Determine which tag comes first
        if opening_match and closing_match:
            if opening_match.start() < closing_match.start():
                return ("opening", opening_match.group(1), opening_match.end())
            else:
                return ("closing", closing_match.group(1), closing_match.end())
        elif opening_match:
            return ("opening", opening_match.group(1), opening_match.end())
        elif closing_match:
            return ("closing", closing_match.group(1), closing_match.end())

        return None
