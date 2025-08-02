"""
XML Processor Module

Handles XML parsing and processing for Sutra Memory data.
"""

from typing import Dict, List, Optional, Any
from loguru import logger

from .models import TaskStatus
from .memory_operations import MemoryOperations


class XMLProcessor:
    """Handles XML processing for Sutra Memory data"""

    def __init__(self, memory_ops: MemoryOperations):
        self.memory_ops = memory_ops

    def process_sutra_memory_data(
        self, parsed_xml_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process already parsed Sutra Memory XML data from xmltodict.

        Args:
            parsed_xml_data: Dictionary containing parsed XML data from xmltodict

        Returns:
            Dict containing processing results and any errors
        """
        results = {
            "success": True,
            "errors": [],
            "warnings": [],
            "changes_applied": {"tasks": [], "code": [], "files": [], "history": []},
        }

        try:
            # Process the parsed XML data
            return self._process_sutra_memory_data(parsed_xml_data, results)

        except Exception as e:
            results["success"] = False
            results["errors"].append(f"Error processing sutra memory data: {str(e)}")
            return results

    def _process_sutra_memory_data(
        self, data: Any, results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Internal method to process sutra memory data from either ET or xmltodict format.

        Args:
            data: Either ET.Element or dict from xmltodict
            results: Results dictionary to populate

        Returns:
            Dict containing processing results and any errors
        """
        try:
            # Handle ET.Element (from raw XML parsing)
            if hasattr(data, "find"):
                return self._process_et_element(data, results)

            # Handle dict (from xmltodict parsing)
            elif isinstance(data, dict):
                return self._process_dict_data(data, results)

            else:
                results["success"] = False
                results["errors"].append(f"Unsupported data type: {type(data)}")
                return results

        except Exception as e:
            results["success"] = False
            results["errors"].append(f"Error in _process_sutra_memory_data: {str(e)}")
            return results

    def _process_dict_data(
        self, data: Dict[str, Any], results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process dict format (from xmltodict parsing)"""
        try:
            # Handle sutra_memory wrapper
            if "sutra_memory" in data:
                sutra_data = data["sutra_memory"]
            # Handle connection_code wrapper (from code manager)
            elif "connection_code" in data:
                sutra_data = data["connection_code"]
                # For connection_code, we only process code snippets (no tasks or history)
                return self._process_connection_code_data(sutra_data, results)
            else:
                sutra_data = data

            # Process tasks
            if "task" in sutra_data:
                task_data = sutra_data["task"]
                self._process_task_dict(task_data, results)

            # Process code snippets
            if "code" in sutra_data:
                code_data = sutra_data["code"]
                self._process_code_dict(code_data, results)

            # Process file changes
            if "files" in sutra_data:
                files_data = sutra_data["files"]
                self._process_files_dict(files_data, results)

            # Process history
            if "add_history" in sutra_data:
                history_data = sutra_data["add_history"]
                self._process_history_dict(history_data, results)
            else:
                results["warnings"].append(
                    "No history entry found - history is mandatory in every response"
                )

            return results

        except Exception as e:
            results["success"] = False
            results["errors"].append(f"Error processing dict data: {str(e)}")
            return results

    def _process_connection_code_data(
        self, connection_data: Dict[str, Any], results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process connection_code format (from code manager)"""
        try:
            # Process code snippets from connection_code format
            if "code" in connection_data:
                code_data = connection_data["code"]
                self._process_code_dict(code_data, results)

            # Add a default history entry for connection code processing
            results["changes_applied"]["history"].append({
                "action": "add_history",
                "content": "Processed connection code from code manager - extracted connection snippets for storage"
            })

            return results

        except Exception as e:
            results["success"] = False
            results["errors"].append(f"Error processing connection_code data: {str(e)}")
            return results

    def _process_task_dict(self, task_data: Any, results: Dict[str, Any]):
        """Process task data from dict format"""
        try:
            # Handle both single item and list of items
            if not isinstance(task_data, list):
                task_items = [task_data] if task_data else []
            else:
                task_items = task_data

            for item in task_items:
                if isinstance(item, dict):
                    # Process add operations
                    if "add" in item:
                        add_data = item["add"]
                        if isinstance(add_data, list):
                            for add_item in add_data:
                                self._process_add_task_dict(add_item, results)
                        else:
                            self._process_add_task_dict(add_data, results)

                    # Process move operations
                    if "move" in item:
                        move_data = item["move"]
                        if isinstance(move_data, list):
                            for move_item in move_data:
                                self._process_move_task_dict(move_item, results)
                        else:
                            self._process_move_task_dict(move_data, results)

                    # Process remove operations
                    if "remove" in item:
                        remove_data = item["remove"]
                        if isinstance(remove_data, list):
                            for remove_item in remove_data:
                                self._process_remove_task_dict(remove_item, results)
                        else:
                            self._process_remove_task_dict(remove_data, results)

        except Exception as e:
            results["errors"].append(f"Error processing task dict: {str(e)}")

    def _process_add_task_dict(self, add_data: Dict[str, Any], results: Dict[str, Any]):
        """Process add task operation from dict"""
        try:
            task_id = add_data.get("@id")
            status = TaskStatus(add_data.get("@to"))
            description = add_data.get("#text", "").strip()

            self.memory_ops.add_task(task_id, description, status)
            results["changes_applied"]["tasks"].append(
                f"Added task {task_id} with status {status.value}"
            )
        except Exception as e:
            results["errors"].append(f"Error processing add task: {str(e)}")

    def _process_move_task_dict(
        self, move_data: Dict[str, Any], results: Dict[str, Any]
    ):
        """Process move task operation from dict"""
        try:
            task_id = move_data.get("#text", "").strip()
            from_status = move_data.get("@from")
            to_status = TaskStatus(move_data.get("@to"))

            self.memory_ops.move_task(task_id, to_status)
            results["changes_applied"]["tasks"].append(
                f"Moved task {task_id} from {from_status} to {to_status.value}"
            )
        except Exception as e:
            results["errors"].append(f"Error processing move task: {str(e)}")

    def _process_remove_task_dict(self, remove_data: Any, results: Dict[str, Any]):
        """Process remove task operation from dict"""
        try:
            if isinstance(remove_data, dict):
                task_id = remove_data.get("#text", "").strip()
            else:
                task_id = str(remove_data).strip()

            if self.memory_ops.remove_task(task_id):
                results["changes_applied"]["tasks"].append(f"Removed task {task_id}")
            else:
                results["warnings"].append(f"Task {task_id} not found for removal")
        except Exception as e:
            results["errors"].append(f"Error processing remove task: {str(e)}")

    def _process_code_dict(self, code_data: Any, results: Dict[str, Any]):
        """Process code data from dict format"""
        try:
            # Handle both single item and list of items
            if not isinstance(code_data, list):
                code_items = [code_data] if code_data else []
            else:
                code_items = code_data

            for item in code_items:
                if isinstance(item, dict):
                    # Process add operations
                    if "add" in item:
                        add_data = item["add"]
                        if isinstance(add_data, list):
                            for add_item in add_data:
                                self._process_add_code_dict(add_item, results)
                        else:
                            self._process_add_code_dict(add_data, results)

                    # Process remove operations
                    if "remove" in item:
                        remove_data = item["remove"]
                        if isinstance(remove_data, list):
                            for remove_item in remove_data:
                                self._process_remove_code_dict(remove_item, results)
                        else:
                            self._process_remove_code_dict(remove_data, results)

        except Exception as e:
            results["errors"].append(f"Error processing code dict: {str(e)}")

    def _process_add_code_dict(self, add_data: Dict[str, Any], results: Dict[str, Any]):
        """Process add code operation from dict"""
        try:
            code_id = add_data.get("@id")
            
            # Handle both nested dict format and direct string format
            file_path_data = add_data.get("file", "")
            if isinstance(file_path_data, dict):
                file_path = file_path_data.get("#text", "").strip()
            else:
                file_path = str(file_path_data).strip()
            
            start_line_data = add_data.get("start_line", "0")
            if isinstance(start_line_data, dict):
                start_line = int(start_line_data.get("#text", "0"))
            else:
                start_line = int(str(start_line_data))
            
            end_line_data = add_data.get("end_line", "0")
            if isinstance(end_line_data, dict):
                end_line = int(end_line_data.get("#text", "0"))
            else:
                end_line = int(str(end_line_data))
            
            description_data = add_data.get("description", "")
            if isinstance(description_data, dict):
                description = description_data.get("#text", "").strip()
            else:
                description = str(description_data).strip()

            self.memory_ops.add_code_snippet(code_id, file_path, start_line, end_line, description)
            results["changes_applied"]["code"].append(f"Added code snippet {code_id}")
        except Exception as e:
            results["errors"].append(f"Error processing add code: {str(e)}")

    def _process_remove_code_dict(self, remove_data: Any, results: Dict[str, Any]):
        """Process remove code operation from dict"""
        try:
            if isinstance(remove_data, dict):
                code_id = remove_data.get("#text", "").strip()
            else:
                code_id = str(remove_data).strip()

            if self.memory_ops.remove_code_snippet(code_id):
                results["changes_applied"]["code"].append(
                    f"Removed code snippet {code_id}"
                )
            else:
                results["warnings"].append(
                    f"Code snippet {code_id} not found for removal"
                )
        except Exception as e:
            results["errors"].append(f"Error processing remove code: {str(e)}")

    def _process_files_dict(self, files_data: Any, results: Dict[str, Any]):
        """Process files data from dict format"""
        try:
            # Handle direct file operations
            for operation in ["modified", "deleted", "added"]:
                if operation in files_data:
                    file_entries = files_data[operation]
                    if not isinstance(file_entries, list):
                        file_entries = [file_entries]

                    for entry in file_entries:
                        if isinstance(entry, dict):
                            file_path = entry.get("#text", "").strip()
                        else:
                            file_path = str(entry).strip()

                        if file_path:
                            self.memory_ops.track_file_change(file_path, operation)
                            results["changes_applied"]["files"].append(
                                f"Tracked {operation} for {file_path}"
                            )
        except Exception as e:
            results["errors"].append(f"Error processing files dict: {str(e)}")

    def _process_history_dict(self, history_data: Any, results: Dict[str, Any]):
        """Process history data from dict format"""
        try:
            if isinstance(history_data, dict):
                summary = history_data.get("#text", "").strip()
            else:
                summary = str(history_data).strip()

            if summary:
                self.memory_ops.add_history(summary)
                results["changes_applied"]["history"].append("Added history entry")
            else:
                results["warnings"].append("Empty history entry")
        except Exception as e:
            results["errors"].append(f"Error processing history: {str(e)}")

    def extract_and_process_sutra_memory(
        self, xml_response: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extract and process sutra memory from parsed XML response (compatible with tool_action_executor).

        This method is designed to work with the existing _extract_sutra_memory method
        from tool_action_executor.py to process sutra memory updates.

        Args:
            xml_response: List of parsed XML blocks from LLM response

        Returns:
            Dict containing processing results and any errors
        """
        try:
            # Extract sutra memory data using the same logic as tool_action_executor
            sutra_memory_data = self._extract_sutra_memory_from_response(xml_response)

            if sutra_memory_data:
                # Process the extracted sutra memory data
                return self.process_sutra_memory_data(sutra_memory_data)
            else:
                return {
                    "success": True,
                    "errors": [],
                    "warnings": ["No sutra memory data found in response"],
                    "changes_applied": {
                        "tasks": [],
                        "code": [],
                        "files": [],
                        "history": [],
                    },
                }

        except Exception as e:
            return {
                "success": False,
                "errors": [f"Error extracting sutra memory: {str(e)}"],
                "warnings": [],
                "changes_applied": {
                    "tasks": [],
                    "code": [],
                    "files": [],
                    "history": [],
                },
            }

    def _extract_sutra_memory_from_response(
        self, xml_response: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Extract sutra memory data from XML response (mirrors tool_action_executor logic).

        Args:
            xml_response: List of parsed XML blocks from LLM response

        Returns:
            Dict containing sutra memory data or None if not found
        """
        for xml_block in xml_response:
            if isinstance(xml_block, dict):
                # Check for sutra_memory tag
                if "sutra_memory" in xml_block:
                    return xml_block["sutra_memory"]
                # Check for connection_code tag (from code manager)
                elif "connection_code" in xml_block:
                    return xml_block["connection_code"]
        return None

    def _process_et_element(self, data: Any, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process ET.Element format (placeholder for future implementation).
        
        Args:
            data: ET.Element data
            results: Results dictionary to populate
            
        Returns:
            Dict containing processing results
        """
        # This method can be implemented if ET.Element processing is needed
        results["warnings"].append("ET.Element processing not implemented")
        return results