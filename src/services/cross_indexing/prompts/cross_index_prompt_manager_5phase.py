"""
Cross-Index 5-Phase Prompt Manager

Main orchestrator for all 5-phase cross-indexing prompts and workflow.
"""
from loguru import logger
from services.agent.xml_service.xml_service import XMLService
from services.llm_clients.llm_factory import llm_client_factory
from ..task_manager.cross_indexing_task_manager import CrossIndexingTaskManager
from .phase1_package_discovery.phase1_prompt_manager import Phase1PromptManager
from .phase2_import_discovery.phase2_prompt_manager import Phase2PromptManager
from .phase3_implementation_discovery.phase3_prompt_manager import Phase3PromptManager
from .phase4_data_splitting.phase4_prompt_manager import Phase4PromptManager
from .phase5_connection_matching.phase5_prompt_manager import Phase5PromptManager

class CrossIndex5PhasePromptManager:
    """
    Main prompt manager for 5-phase cross-indexing analysis.

    Orchestrates the complete 5-phase workflow:
    - Phase 1: Package Discovery
    - Phase 2: Import Pattern Discovery  
    - Phase 3: Implementation Discovery
    - Phase 4: Data Splitting
    - Phase 5: Connection Matching
    """

    def __init__(self, db_connection=None):
        self.phase1_manager = Phase1PromptManager()
        self.phase2_manager = Phase2PromptManager()
        self.phase3_manager = Phase3PromptManager()
        self.phase4_manager = Phase4PromptManager()
        self.phase5_manager = Phase5PromptManager()
        self.task_manager = CrossIndexingTaskManager(db_connection)
        self.current_phase = 1
        self.phase_names = {
            1: "Package Discovery",
            2: "Import Pattern Discovery",
            3: "Implementation Discovery",
            4: "Data Splitting",
            5: "Connection Matching"
        }

    def get_current_phase_name(self) -> str:
        """Get the name of the current phase."""
        return self.phase_names.get(self.current_phase, "Unknown Phase")

    def get_system_prompt(self, phase: int = None) -> str:
        """
        Get the system prompt for the specified phase.
        
        Args:
            phase: Phase number (1-5), defaults to current phase
            
        Returns:
            System prompt string for the phase
        """
        phase = phase or self.current_phase

        if phase == 1:
            return self.phase1_manager.get_system_prompt()
        elif phase == 2:
            return self.phase2_manager.get_system_prompt()
        elif phase == 3:
            return self.phase3_manager.get_system_prompt()
        elif phase == 4:
            return self.phase4_manager.get_system_prompt()
        elif phase == 5:
            return self.phase5_manager.get_system_prompt()
        else:
            raise ValueError(f"Invalid phase number: {phase}. Must be 1-5.")

    def get_user_prompt(self, analysis_query: str, memory_context: str = "", phase: int = None, **kwargs) -> str:
        """
        Get the user prompt for the specified phase.
        
        Args:
            analysis_query: The analysis query/request
            memory_context: Current memory context from sutra memory
            phase: Phase number (1-5), defaults to current phase
            **kwargs: Additional phase-specific arguments
            
        Returns:
            User prompt string for the phase
        """
        phase = phase or self.current_phase

        if phase == 1:
            return self.phase1_manager.get_user_prompt(analysis_query, memory_context)
        elif phase == 2:
            return self.phase2_manager.get_user_prompt(analysis_query, memory_context)
        elif phase == 3:
            return self.phase3_manager.get_user_prompt(analysis_query, memory_context)
        elif phase == 4:
            return self.phase4_manager.get_user_prompt(memory_context)
        elif phase == 5:
            incoming_connections = kwargs.get('incoming_connections', [])
            outgoing_connections = kwargs.get('outgoing_connections', [])
            return self.phase5_manager.get_user_prompt(incoming_connections, outgoing_connections)
        else:
            raise ValueError(f"Invalid phase number: {phase}. Must be 1-5.")

    def advance_phase(self) -> bool:
        """
        Advance to the next phase and update task manager.

        Returns:
            True if advanced successfully, False if already at final phase
        """
        if self.current_phase < 5:
            self.current_phase += 1
            self.task_manager.set_current_phase(self.current_phase)
            return True
        return False

    def reset_to_phase(self, phase: int) -> None:
        """
        Reset to a specific phase and update task manager.

        Args:
            phase: Phase number (1-5) to reset to
        """
        if 1 <= phase <= 5:
            self.current_phase = phase
            self.task_manager.set_current_phase(phase)
        else:
            raise ValueError(f"Invalid phase number: {phase}. Must be 1-5.")

    def is_final_phase(self) -> bool:
        """Check if currently at the final phase."""
        return self.current_phase == 5

    def get_task_aware_memory_context(self, memory_context: str = "") -> str:
        """
        Get memory context with task management integration.

        Args:
            memory_context: Base memory context

        Returns:
            Enhanced memory context with task information
        """
        return self.task_manager.get_memory_context_for_phase(self.current_phase)

    def get_task_summary(self) -> dict:
        """
        Get summary of tasks across all phases.

        Returns:
            Task summary dictionary
        """
        return self.task_manager.get_task_summary()

    def validate_phase_completion(self, response: str, phase: int = None) -> bool:
        """
        Validate that the phase response contains proper completion.

        Args:
            response: LLM response to validate
            phase: Phase number (1-5), defaults to current phase

        Returns:
            True if response indicates phase completion, False otherwise
        """
        phase = phase or self.current_phase

        if phase in [1, 2, 3]:
            # Phases 1-3 use attempt_completion tool - validate XML structure
            try:
                xml_service = XMLService(llm_client_factory())
                xml_blocks = xml_service.parse_xml_response(response)

                # Check if any XML block contains attempt_completion with result
                for block in xml_blocks:
                    if isinstance(block, dict) and "attempt_completion" in block:
                        attempt_completion = block["attempt_completion"]
                        if isinstance(attempt_completion, dict) and "result" in attempt_completion:
                            result = attempt_completion["result"]
                            if result and str(result).strip():
                                return True

                return False
            except Exception as e:
                # XML parsing must work - no fallbacks allowed
                logger.error(f"XML parsing failed for phase {phase} response: {e}")
                return False

        elif phase in [4, 5]:
            # Phases 4-5 return JSON directly
            try:
                import json
                response_stripped = response.strip()
                if response_stripped.startswith('{') and response_stripped.endswith('}'):
                    json.loads(response_stripped)  # Validate JSON structure
                    return True
                return False
            except (json.JSONDecodeError, ValueError):
                return False
        else:
            return False

    def get_phase_description(self, phase: int = None) -> str:
        """
        Get a description of what the specified phase does.
        
        Args:
            phase: Phase number (1-5), defaults to current phase
            
        Returns:
            Description string for the phase
        """
        phase = phase or self.current_phase

        descriptions = {
            1: "Discovers connection-related packages in the project and creates tasks for subsequent analysis",
            2: "Finds import statements for discovered packages and creates tasks for subsequent analysis",
            3: "Analyzes actual usage of imported methods and stores connection code via code manager",
            4: "Processes collected connection data and splits it into incoming/outgoing JSON format",
            5: "Matches incoming and outgoing connections and returns matched pairs in JSON format"
        }

        return descriptions.get(phase, "Unknown phase")

    def requires_code_manager(self, phase: int = None) -> bool:
        """
        Check if the specified phase requires code manager integration.
        
        Args:
            phase: Phase number (1-5), defaults to current phase
            
        Returns:
            True if phase requires code manager, False otherwise
        """
        phase = phase or self.current_phase
        return phase == 3  # Only Phase 3 requires code manager integration
