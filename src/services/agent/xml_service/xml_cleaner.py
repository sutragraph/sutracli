import re


class XMLCleaner:
    """Handles XML cleaning and formatting operations."""

    # Precompiled patterns for better performance
    TAG_SPACING_PATTERN = re.compile(r"<\s+(\w+)(?:\s+([^>]*?))?\s*>")
    CLOSING_TAG_PATTERN = re.compile(r"<\s*/\s*(\w+)\s*>")
    ATTRIBUTE_PATTERN = re.compile(r'(\w+)\s*=\s*"([^"]*)"')
    ATTRIBUTE_SINGLE_PATTERN = re.compile(r"(\w+)\s*=\s*'([^']*)'")
    TRAILING_SPACE_PATTERN = re.compile(r"\s+>")

    CDATA_PATTERNS = [
        (re.compile(r"(<diff>)(.*?)(</diff>)", re.DOTALL), "diff"),
        (re.compile(r"(<content>)(.*?)(</content>)", re.DOTALL), "content"),
        (re.compile(r"(<command>)(.*?)(</command>)", re.DOTALL), "command"),
        (re.compile(r"(<thinking>)(.*?)(</thinking>)", re.DOTALL), "thinking"),
    ]

    PROBLEMATIC_CHARS = ["<<<<<<<", ">>>>>>>", "=======", "-------", "<", ">", "%", "&", "'", '"', "\\"]





    def clean_xml_spacing(self, text: str) -> str:
        """Clean and fix common XML spacing issues."""
        # Fix spacing in XML tags
        text = self.TAG_SPACING_PATTERN.sub(r"<\1 \2>", text)
        text = self.CLOSING_TAG_PATTERN.sub(r"</\1>", text)

        # Clean attribute spacing
        text = self.ATTRIBUTE_PATTERN.sub(r'\1="\2"', text)
        text = self.ATTRIBUTE_SINGLE_PATTERN.sub(r"\1='\2'", text)

        # Remove trailing spaces before >
        text = self.TRAILING_SPACE_PATTERN.sub(">", text)

        # Simple XML escaping for ampersands that aren't already escaped
        text = re.sub(r'&(?!(?:amp|lt|gt|quot|apos);)', '&amp;', text)

        # Wrap problematic content in CDATA
        return self.wrap_diff_content_in_cdata(text)

    def wrap_diff_content_in_cdata(self, text: str) -> str:
        """Wrap diff, content, and command content in CDATA sections."""
        for pattern, tag_name in self.CDATA_PATTERNS:
            text = pattern.sub(self._wrap_in_cdata, text)
        return text

    def _wrap_in_cdata(self, match: re.Match) -> str:
        """Helper method to wrap content in CDATA if needed."""
        opening_tag, content, closing_tag = match.groups()

        # Check if content needs CDATA wrapping
        if (
            any(char in content for char in self.PROBLEMATIC_CHARS)
            and "<![CDATA[" not in content
        ):
            return f"{opening_tag}<![CDATA[{content}]]>{closing_tag}"
        return match.group(0)
