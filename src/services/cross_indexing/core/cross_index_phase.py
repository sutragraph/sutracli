from typing import Dict, Any, List
from src.utils.system_utils import get_home_and_current_directories
from loguru import logger
from src.graph.graph_operations import GraphOperations
from ..utils import format_connections, validate_and_process_baml_results
from baml_client.types import (
    CodeManagerResponse,
    CrossIndexingResponse,
    ConnectionMatchingResponse,
    ConnectionSplittingResponse,
    TaskFilterResponse,
    TechnologyCorrectionResponse,
)
import json
from .technology_validator import TechnologyValidator
from services.baml_service import BAMLService
from services.agent.memory_management.models import Task, TaskStatus


class CrossIndexing:
    """
    Cross-indexing service using-based JSON prompts.

    This class provides all 5 phases and supporting prompt functions as methods,
    replacing the old LLM calls with XML parsing with direct JSON-based functions.
    """

    def __init__(self):
        self.baml_service = BAMLService()
        self.technology_validator = TechnologyValidator()
        self.graph_ops = GraphOperations()
        self.current_phase = 1
        self.phase_names = {
            1: "Package Discovery",
            2: "Import Pattern Discovery",
            3: "Implementation Discovery",
            4: "Data Splitting",
            5: "Connection Matching",
        }

    def run_code_manager(self, tool_results: str) -> Dict[str, Any]:
        """
        Run code manager analysis using.

        Args:
            tool_results: Raw tool results from cross-indexing analysis

        Returns:
            dict: Results from code manager analysis
        """
        try:
            response: CodeManagerResponse = self.baml_service.call(
                function_name="CodeManager",
                tool_results=tool_results,
                system_info=get_home_and_current_directories(),
            )

            return {
                "success": True,
                "results": response,
                "message": "Code manager analysis completed successfully using",
            }

        except Exception as e:
            logger.error(f"❌ Code Manager error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "code manager analysis failed due to unexpected error",
            }

    def run_package_discovery(
        self,
        analysis_query: str,
        memory_context: str = "",
    ) -> Dict[str, Any]:
        """
        Run package discovery analysis using.

        Args:
            analysis_query: The analysis query/request
            memory_context: Current memory context from sutra memory

        Returns:
            dict: Results from package discovery analysis
        """
        try:
            response: CrossIndexingResponse = self.baml_service.call(
                function_name="PackageDiscovery",
                analysis_query=analysis_query,
                memory_context=memory_context or "No previous context",
                system_info=get_home_and_current_directories(),
            )

            return {
                "success": True,
                "results": response,
                "message": "Package discovery analysis completed successfully using",
            }

        except Exception as e:
            logger.error(f"❌ Phase 1 package discovery error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "package discovery analysis failed due to unexpected error",
            }

    def run_import_discovery(
        self, analysis_query: str, memory_context: str = ""
    ) -> Dict[str, Any]:
        """
        Run import pattern discovery analysis using.

        Args:
            analysis_query: The analysis query/request
            memory_context: Current memory context from sutra memory

        Returns:
            dict: Results from import discovery analysis
        """
        try:
            response: CrossIndexingResponse = self.baml_service.call(
                function_name="ImportDiscovery",
                analysis_query=analysis_query,
                memory_context=memory_context or "No previous context",
                system_info=get_home_and_current_directories(),
            )

            return {
                "success": True,
                "results": response,
                "message": "Import discovery analysis completed successfully using",
            }

        except Exception as e:
            logger.error(f"❌ Phase 2 import discovery error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "import discovery analysis failed due to unexpected error",
            }

    def run_implementation_discovery(
        self, analysis_query: str, memory_context: str = ""
    ) -> Dict[str, Any]:
        """
        Run implementation discovery analysis using.

        Args:
            analysis_query: The analysis query/request
            memory_context: Current memory context from sutra memory

        Returns:
            dict: Results from implementation discovery analysis
        """
        try:
            response: CrossIndexingResponse = self.baml_service.call(
                function_name="ImplementationDiscovery",
                analysis_query=analysis_query,
                memory_context=memory_context or "No previous context",
                system_info=get_home_and_current_directories(),
            )

            return {
                "success": True,
                "results": response,
                "message": "Implementation discovery analysis completed successfully using",
            }

        except Exception as e:
            logger.error(f"❌ Phase 3 implementation discovery error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "implementation discovery analysis failed due to unexpected error",
            }

    def run_connection_splitting(self, memory_context: str) -> Dict[str, Any]:
        """
        Run connection splitting analysis using.

        Args:
            memory_context: Code snippets collected by the code manager from Phase 3

        Returns:
            dict: Results from connection splitting analysis
        """
        try:
            response: ConnectionSplittingResponse = self.baml_service.call(
                function_name="ConnectionSplitting", memory_context=memory_context
            )

            return {
                "success": True,
                "results": response,
                "message": "Connection splitting analysis completed successfully using",
            }

        except Exception as e:
            logger.error(f"❌ Phase 4 connection splitting error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "connection splitting analysis failed due to unexpected error",
            }

    def run_connection_matching(self) -> Dict[str, Any]:
        """
        Run connection matching analysis using with optimized approach.

        OPTIMIZATION: Fetch unknown connections once, then for each technology type,
        fetch its connections and add unknown connections to it.

        Returns:
            dict: Matching results ready for database storage
        """
        try:
            # First, get all technology types to check if Unknown exists
            all_types_including_unknown = self.graph_ops.get_all_technology_types()
            has_unknown = "Unknown" in all_types_including_unknown

            # Only fetch unknown connections if they exist
            unknown_connections = {"incoming": [], "outgoing": []}
            if has_unknown:
                print("🔄 Fetching Unknown connections...")
                unknown_connections = self.graph_ops.fetch_connections_by_technology(
                    "Unknown"
                )
                print(
                    f"   Found {len(unknown_connections['incoming'])} incoming and {len(unknown_connections['outgoing'])} outgoing Unknown connections"
                )
            else:
                print("ℹ️ No Unknown connections found, skipping Unknown fetch")

            # Get all distinct technology types (excluding Unknown)
            all_tech_types = self.graph_ops.get_available_technology_types()

            print(
                f"🔗 Phase 5: Starting connection matching for {len(all_tech_types)} technology types"
            )
            print(f"📊 Found technology types: {', '.join(sorted(all_tech_types))}")

            # Collect all matches from each technology type
            all_matches = []
            total_incoming_processed = 0
            total_outgoing_processed = 0

            # Process each technology type one by one
            for tech_type in sorted(all_tech_types):
                print(f"🔄 Processing {tech_type} connections...")

                # Fetch specific technology type connections
                tech_connections = self.graph_ops.fetch_connections_by_technology(
                    tech_type
                )

                # Add unknown connections to this technology type
                connections = {
                    "incoming": tech_connections["incoming"]
                    + unknown_connections["incoming"],
                    "outgoing": tech_connections["outgoing"]
                    + unknown_connections["outgoing"],
                }

                print(
                    f"   Combined {len(tech_connections['incoming'])} + {len(unknown_connections['incoming'])} = {len(connections['incoming'])} incoming connections"
                )
                print(
                    f"   Combined {len(tech_connections['outgoing'])} + {len(unknown_connections['outgoing'])} = {len(connections['outgoing'])} outgoing connections"
                )

                incoming_connections = connections["incoming"]
                outgoing_connections = connections["outgoing"]

                # Skip if no connections for this technology type
                if not incoming_connections and not outgoing_connections:
                    logger.debug(
                        f"   No connections found for {tech_type}, skipping..."
                    )
                    continue

                print(
                    f"   Matching {len(incoming_connections)} incoming with {len(outgoing_connections)} outgoing connections for {tech_type}"
                )

                # Format connections for
                incoming_formatted = format_connections(
                    incoming_connections, "INCOMING"
                )
                outgoing_formatted = format_connections(
                    outgoing_connections, "OUTGOING"
                )

                # Call function for this technology type
                try:
                    response: ConnectionMatchingResponse = self.baml_service.call(
                        function_name="ConnectionMatching",
                        incoming_connections=incoming_formatted,
                        outgoing_connections=outgoing_formatted,
                    )

                    # Process and validate results for this technology type
                    is_valid, tech_results = validate_and_process_baml_results(
                        response, incoming_connections, outgoing_connections
                    )

                    if is_valid:
                        matches = tech_results.get("matches", [])
                        all_matches.extend(matches)
                        print(f"   ✅ Found {len(matches)} matches for {tech_type}")
                        total_incoming_processed += len(incoming_connections)
                        total_outgoing_processed += len(outgoing_connections)
                    else:
                        logger.warning(
                            f"   ⚠️ Failed to process {tech_type}: {tech_results}"
                        )

                except Exception as tech_error:
                    logger.error(f"   ❌ Error processing {tech_type}: {tech_error}")
                    continue

            return {
                "success": True,
                "results": {
                    "matches": all_matches,
                    "total_matches": len(all_matches),
                    "technology_types_processed": all_tech_types,
                    "stats": {
                        "total_incoming_connections_processed": total_incoming_processed,
                        "total_outgoing_connections_processed": total_outgoing_processed,
                        "technology_types_found": len(all_tech_types),
                    },
                },
                "message": f"Successfully matched {len(all_matches)} connections across {len(all_tech_types)} technology types",
            }

        except Exception as e:
            logger.error(f"❌ Phase 5 connection matching error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "connection matching failed due to unexpected error",
            }

    def run_task_filtering(self, tasks: str) -> Dict[str, Any]:
        """
        Run task filtering using.

        Args:
            tasks: List of Task objects to filter

        Returns:
            dict: Results from task filtering
        """
        try:
            response: TaskFilterResponse = self.baml_service.call(
                function_name="TaskFilter", task_list=tasks
            )

            return {
                "success": True,
                "results": response,
                "message": "Task filtering completed successfully using",
            }

        except Exception as e:
            logger.error(f"❌ Task Filtering error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "task filtering failed due to unexpected error",
            }

    def run_technology_correction(self, unmatched_names: list) -> Dict[str, str]:
        """
        Run technology name correction using.

        Args:
            unmatched_names: List of unmatched technology names

        Returns:
            dict: Mapping of original_name -> corrected_name
        """
        try:
            if not unmatched_names:
                logger.debug("No unmatched names to correct")
                return {}

            print(
                f"🔧 Technology Correction: Processing {len(unmatched_names)} unmatched names: {unmatched_names}"
            )

            # Format input for
            unmatched_names_str = json.dumps(unmatched_names, indent=2)
            acceptable_enums_str = json.dumps(
                self.technology_validator.get_valid_enums_list(), indent=2
            )

            # Call function for technology correction
            logger.debug("Calling TechnologyCorrection function")
            response: TechnologyCorrectionResponse = self.baml_service.call(
                function_name="TechnologyCorrection",
                unmatched_names=unmatched_names_str,
                acceptable_enums=acceptable_enums_str,
            )

            if not response:
                logger.error("Empty response from technology correction")
                return {}

            return response

        except Exception as e:
            logger.error(f"❌ Technology Correction error: {e}")
            return {}

    def advance_phase(self) -> bool:
        """
        Advance to the next phase.

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
            return True
        return False

    def reset_to_phase(self, phase: int) -> None:
        """
        Reset to a specific phase.

        Args:
            phase: Phase number (1-5) to reset to
        """
        if 1 <= phase <= 5:
            self.current_phase = phase
        else:
            raise ValueError(f"Invalid phase number: {phase}. Must be 1-5.")

    def correct_technology_names(self, unmatched_names: list) -> dict:
        """
        Correct unmatched technology names using technology correction.

        Args:
            unmatched_names: List of technology names that don't match valid enums

        Returns:
            Dictionary mapping original_name -> corrected_name
        """
        try:
            if not unmatched_names:
                logger.debug("No unmatched names to correct")
                return {}

            print(
                f"🔧 Technology Correction: Processing {len(unmatched_names)} unmatched names: {unmatched_names}"
            )

            # Call function for technology correction
            logger.debug("Calling TechnologyCorrection function")
            response = self.run_technology_correction(unmatched_names)

            if not response:
                logger.error("Empty response from technology correction")
                return {}

            # Process response
            corrections = self._process_technology_correction_response(
                response, unmatched_names
            )

            if not corrections:
                logger.warning("Failed to process corrections")
                return {}

            return corrections

        except Exception as e:
            logger.error(f"❌ Technology Correction error: {e}")
            return {}

    def _process_technology_correction_response(
        self, response: dict, original_names: list
    ) -> dict:
        """
        Process response and extract corrections.

        Args:
            response: Dictionary mapping original_name -> corrected_name from
            original_names: List of original unmatched names for validation

        Returns:
            Dictionary of corrections or empty dict if processing fails
        """
        try:
            corrections = {}

            # Process each correction from response
            for original_name, corrected_name in response.items():
                # Validate that the original name was in our input
                if original_name not in original_names:
                    logger.warning(
                        f"returned correction for unexpected name: {original_name}"
                    )
                    continue

                # Validate that the corrected name is a valid enum
                if (
                    corrected_name
                    not in self.technology_validator.VALID_TECHNOLOGY_ENUMS
                ):
                    logger.warning(
                        f"returned invalid correction: {original_name} -> {corrected_name}, skipping"
                    )
                    continue

                corrections[original_name] = corrected_name
                logger.debug(f"correction: {original_name} -> {corrected_name}")

            # Log any missing corrections but don't add fallbacks
            for original_name in original_names:
                if original_name not in corrections:
                    logger.warning(
                        f"missing correction for '{original_name}', no correction applied"
                    )

            logger.debug(f"Processed {len(corrections)} corrections from response")
            return corrections

        except Exception as e:
            logger.error(f"Error processing response: {e}")
            return {}

    def filter_tasks(self, tasks: list) -> list:
        """
        Filter and deduplicate a list of tasks using-based analysis.

        Args:
            tasks: List of tasks to filter
            phase_info: Context information about the current phase

        Returns:
            List of filtered and deduplicated tasks
        """
        if not tasks:
            print("No tasks to filter")
            return []

        # Use to perform intelligent filtering
        filtered_tasks = self._baml_filter_tasks(tasks)

        return filtered_tasks

    def _baml_filter_tasks(self, tasks: list) -> list:
        """
        Use to intelligently filter and deduplicate tasks.

        Args:
            tasks: List of tasks to filter
            phase_info: Context information about the current phase

        Returns:
            List of filtered tasks
        """
        try:
            logger.debug(f"Sending task filtering request to")

            filtered_tasks = self._format_tasks_for_prompt(tasks)

            # Call task filtering
            result = self.run_task_filtering(filtered_tasks)

            if not result.get("success"):
                error_msg = result.get("error", "task filtering failed")
                logger.error(f"task filtering error: {error_msg}")
                # Return original tasks if filtering fails
                return tasks

            # Extract filtered tasks from response
            baml_response = result.get("results")

            filtered_tasks = []
            for task_data in baml_response.tasks:
                task = Task(
                    id=task_data.id,
                    description=task_data.description,
                    status=TaskStatus.PENDING,
                )
                filtered_tasks.append(task)

            return filtered_tasks

        except Exception as e:
            logger.error(f"Error during task filtering: {e}")
            # Return original tasks if filtering fails completely
            return tasks

    def _format_tasks_for_prompt(self, tasks: List[Task]) -> str:
        """
        Format tasks for display in the prompt.

        Args:
            tasks: List of tasks to format

        Returns:
            Formatted task string
        """
        if not tasks:
            return "No tasks to filter."

        formatted_tasks = []
        for task in tasks:
            formatted_tasks.append(f"- Task {task.id}: {task.description}")

        return "\n".join(formatted_tasks)
