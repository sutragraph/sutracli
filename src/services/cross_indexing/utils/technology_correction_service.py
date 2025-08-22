"""
Technology Correction Service

This service handles the process of correcting unmatched technology names
using BAML technology correction functions.
"""

import json
from typing import Dict, List, Any, Optional
from loguru import logger
from baml_client.types import TechnologyCorrectionResponse
from .technology_validator import TechnologyValidator
from .baml_utils import call_baml


class TechnologyCorrectionService:
    """
    Service for correcting unmatched technology names using LLM.
    """
    
    def __init__(self):
        """Initialize the technology correction service."""
        self.validator = TechnologyValidator()
    
    def correct_technology_names(self, unmatched_names: List[str]) -> Dict[str, str]:
        """
        Correct unmatched technology names using BAML technology correction.
        
        Args:
            unmatched_names: List of technology names that don't match valid enums
            
        Returns:
            Dictionary mapping original_name -> corrected_name
        """
        try:
            if not unmatched_names:
                logger.debug("No unmatched names to correct")
                return {}
            
            logger.info(f"🔧 BAML Technology Correction: Processing {len(unmatched_names)} unmatched names: {unmatched_names}")
            
            # Format input for BAML
            unmatched_names_str = json.dumps(unmatched_names, indent=2)
            acceptable_enums_str = json.dumps(self.validator.get_valid_enums_list(), indent=2)
            
            # Call BAML function for technology correction
            logger.debug("Calling BAML TechnologyCorrection function")
            baml_response = call_baml(
                function_name="TechnologyCorrection",
                unmatched_names=unmatched_names_str,
                acceptable_enums=acceptable_enums_str,
            )
            
            # Extract the actual response content from BAMLResponse
            response = baml_response.content if hasattr(baml_response, 'content') else baml_response
            
            if not response:
                logger.error("Empty response from BAML technology correction")
                return {}
            
            # Process BAML response
            corrections = self._process_baml_response(response, unmatched_names)
            
            if not corrections:
                logger.warning("Failed to process BAML corrections")
                return {}
            
            logger.info(f"✅ BAML Technology Correction: Successfully corrected {len(corrections)} technology names")
            return corrections
            
        except Exception as e:
            logger.error(f"❌ BAML Technology Correction error: {e}")
            return {}
    
    def _process_baml_response(self, response: TechnologyCorrectionResponse, original_names: List[str]) -> Dict[str, str]:
        """
        Process BAML response and extract corrections.
        
        Args:
            response: BAML TechnologyCorrectionResponse object
            original_names: List of original unmatched names for validation
            
        Returns:
            Dictionary of corrections or empty dict if processing fails
        """
        try:
            corrections = {}
            
            # Process each correction from BAML response
            for correction in response.corrections:
                # Validate correction structure
                if not all(hasattr(correction, attr) for attr in ["original_name", "corrected_name"]):
                    logger.warning(f"Invalid correction structure: {correction}")
                    continue
                
                original_name = correction.original_name
                corrected_name = correction.corrected_name
                
                # Validate that the original name was in our input
                if original_name not in original_names:
                    logger.warning(f"BAML returned correction for unexpected name: {original_name}")
                    continue
                
                # Validate that the corrected name is a valid enum
                if corrected_name not in self.validator.VALID_TECHNOLOGY_ENUMS:
                    logger.warning(f"BAML returned invalid correction: {original_name} -> {corrected_name}, skipping")
                    continue
                
                corrections[original_name] = corrected_name
                logger.debug(f"BAML correction: {original_name} -> {corrected_name}")
            
            # Log any missing corrections but don't add fallbacks
            for original_name in original_names:
                if original_name not in corrections:
                    logger.warning(f"BAML missing correction for '{original_name}', no correction applied")
            
            logger.debug(f"Processed {len(corrections)} corrections from BAML response")
            return corrections
            
        except Exception as e:
            logger.error(f"Error processing BAML response: {e}")
            return {}
    
    