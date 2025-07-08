import xml.etree.ElementTree as ET
from .xml_preprocessor import preprocess_xml_content

def parse_xml_safely(xml_string: str):
    """Parse XML with preprocessing for special characters."""
    try:
        # Preprocess to handle special characters in content tags
        processed_xml = preprocess_xml_content(xml_string)
        
        # Parse the preprocessed XML
        root = ET.fromstring(processed_xml)
        return root
    except ET.ParseError as e:
        raise ValueError(f"XML parsing failed: {e}")