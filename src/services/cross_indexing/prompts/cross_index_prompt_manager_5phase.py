"""
Cross-Index 5-Phase Prompt Manager

Main orchestrator for all 5-phase cross-indexing prompts and workflow.
"""
from loguru import logger
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

    def __init__(self):
        self.phase1_manager = Phase1PromptManager()
        self.phase2_manager = Phase2PromptManager()
        self.phase3_manager = Phase3PromptManager()
        self.phase4_manager = Phase4PromptManager()
        self.phase5_manager = Phase5PromptManager()
        self.task_manager = CrossIndexingTaskManager()
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
            return "DEPRECATED: Phase 5 user prompt is no longer used. Use task manager instead."
        else:
            raise ValueError(f"Invalid phase number: {phase}. Must be 1-5.")

    def advance_phase(self) -> bool:
        """
        Advance to the next phase and update task manager.

        Notes:
        - Phase 3 → 4 advancement is orchestrated by the cross-index service, since
          Phase 4 consumes code snippets collected in Phase 3 and must not clear them.

        Returns:
            True if advanced successfully, False if blocked or already at final phase
        """
        # Block automatic advancement from Phase 3 to 4 to avoid clearing code snippets
        # Collected in Phase 3. The service will handle Phase 4 trigger explicitly.
        if self.current_phase == 3:
            logger.debug(
                "advance_phase called at Phase 3 - skipping automatic 3→4 advancement; service handles Phase 4"
            )
            return False

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
