import re
import html

def preprocess_xml_content(xml_content: str) -> str:
    """Preprocess XML content to handle special characters in specific tags."""
    
    content_tags = ['diff', 'content']
    
    for tag in content_tags:
        pattern = f'<{tag}>(.*?)</{tag}>'
        
        def escape_content(match):
            content = match.group(1)
            # Only escape if not already escaped
            if '&lt;' not in content and '&gt;' not in content and '&amp;' not in content:
                content = html.escape(content, quote=False)
            return f'<{tag}>{content}</{tag}>'
        
        xml_content = re.sub(pattern, escape_content, xml_content, flags=re.DOTALL)
    
    return xml_content