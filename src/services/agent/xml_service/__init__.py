"""
XML Service Module

This module provides comprehensive XML processing services for LLM responses including:
- Parsing and extracting XML data from LLM responses
- Cleaning and fixing common XML formatting issues
- Repairing malformed/truncated XML using LLM calls
- Validating XML structure
- Extracting specific XML tags

Main Components:
- XMLService: Main service class for all XML processing operations

Usage:
    from src.services.agent.xml_service import XMLService

    # Create XML service with LLM client for repair capabilities
    xml_service = XMLService(llm_client)

    # Parse XML response
    parsed_data = xml_service.parse_xml_response(response_text)

    # Filter parsed data as needed (e.g., extract specific tags)
    tools = [item.get('tool') for item in parsed_data if 'tool' in item]

    # Repair malformed XML (prompts are handled internally)
    repaired = xml_service.repair_xml(malformed_xml)
"""

from .xml_service import XMLService

__all__ = [
    'XMLService'
]
