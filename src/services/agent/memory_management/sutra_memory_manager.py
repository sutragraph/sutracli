"""
Modular Sutra Memory Manager

A refactored version of the original SutraMemoryManager that uses separated components
for better maintainability and modularity.

This is the main interface that combines all the modular components:
- Models (Task, CodeSnippet, etc.)
- Memory Operations (task/code management)
- XML Processing (parsing and processing XML data)
- State Persistence (import/export)
- Memory Formatting (LLM context formatting)
"""

from typing import Dict, List, Optional, Any

from .models import Task, TaskStatus, CodeSnippet, HistoryEntry, ReasoningContext
from .memory_operations import MemoryOperations
from .xml_processor import XMLProcessor
from .state_persistence import StatePersistence
from .memory_formatter import MemoryFormatter
from .memory_updater import MemoryUpdater


class SutraMemoryManager:
    """
    Modular Sutra Memory Manager that orchestrates all memory management components.
    
    This class provides the same interface as the original SutraMemoryManager
    but uses separated, modular components internally.
    """

    def __init__(self, db_connection: Optional[Any] = None):
        # Initialize core components
        self.memory_ops = MemoryOperations(db_connection)
        self.xml_processor = XMLProcessor(self.memory_ops)
        self.state_persistence = StatePersistence(self.memory_ops)
        self.memory_formatter = MemoryFormatter(self.memory_ops)
        self.memory_updater = MemoryUpdater(self.memory_ops, db_connection)
        
        # Initialize reasoning context
        self.reasoning_context = None

    # ID Generation Methods
    def get_next_task_id(self) -> str:
        """Generate next unique task ID"""
        return self.memory_ops.get_next_task_id()

    def get_next_code_id(self) -> str:
        """Generate next unique code ID"""
        return self.memory_ops.get_next_code_id()

    # Task Management Methods
    def add_task(self, task_id: str, description: str, status: TaskStatus) -> bool:
        """Add a new task with validation"""
        return self.memory_ops.add_task(task_id, description, status)

    def move_task(self, task_id: str, new_status: TaskStatus) -> bool:
        """Move task to new status with validation"""
        return self.memory_ops.move_task(task_id, new_status)

    def remove_task(self, task_id: str) -> bool:
        """Remove task from memory"""
        return self.memory_ops.remove_task(task_id)

    def get_current_task(self) -> Optional[Task]:
        """Get the current task if any"""
        return self.memory_ops.get_current_task()

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Get all tasks with specific status"""
        return self.memory_ops.get_tasks_by_status(status)

    def clear_completed_tasks(self) -> int:
        """Remove all completed tasks and return count of removed tasks"""
        return self.memory_ops.clear_completed_tasks()

    # Code Snippet Management Methods
    def add_code_snippet(
        self,
        code_id: str,
        file_path: str,
        start_line: int,
        end_line: int,
        description: str,
    ) -> bool:
        """Add code snippet to memory"""
        return self.memory_ops.add_code_snippet(
            code_id, file_path, start_line, end_line, description
        )

    def remove_code_snippet(self, code_id: str) -> bool:
        """Remove code snippet from memory"""
        return self.memory_ops.remove_code_snippet(code_id)

    def get_code_snippet(self, code_id: str) -> Optional[CodeSnippet]:
        """Get code snippet by ID"""
        return self.memory_ops.get_code_snippet(code_id)

    def get_all_code_snippets(self) -> Dict[str, CodeSnippet]:
        """Get all stored code snippets"""
        return self.memory_ops.get_all_code_snippets()

    def get_code_snippets_by_file(self, file_path: str) -> List[CodeSnippet]:
        """Get all code snippets for a specific file"""
        return self.memory_ops.get_code_snippets_by_file(file_path)

    # File Change Tracking Methods
    def track_file_change(self, file_path: str, operation: str) -> bool:
        """Track file change"""
        return self.memory_ops.track_file_change(file_path, operation)

    # History Management Methods
    def add_history(self, summary: str) -> bool:
        """Add history entry (mandatory in every response)"""
        return self.memory_ops.add_history(summary)
    
    def add_tool_history(self, tool_name: str, tool_result: dict, validation_result: dict, user_query: str) -> bool:
        """Add enhanced history entry with tool execution details"""
        from datetime import datetime
        
        # Create enhanced history entry
        history_entry = HistoryEntry(
            timestamp=datetime.now(),
            summary=f"Tool: {tool_name} - {validation_result.get('confidence', 0):.2f} confidence",
            tool_name=tool_name,
            tool_result=tool_result,
            validation_result=validation_result,
            user_query=user_query
        )
        
        # Add to memory operations (extend the existing add_history method)
        return self.memory_ops.add_history_entry(history_entry)

    def get_recent_history(self, count: int = 5) -> List[HistoryEntry]:
        """Get recent history entries"""
        return self.memory_ops.get_recent_history(count)
    
    def get_tool_history(self, count: int = 10) -> List[HistoryEntry]:
        """Get recent tool execution history with validation results"""
        history = self.get_recent_history(count)
        return [h for h in history if h.tool_name is not None]

    # XML Processing Methods
    def process_sutra_memory_data(
        self, parsed_xml_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process already parsed Sutra Memory XML data from xmltodict"""
        return self.xml_processor.process_sutra_memory_data(parsed_xml_data)

    def extract_and_process_sutra_memory(
        self, xml_response: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract and process sutra memory from parsed XML response"""
        return self.xml_processor.extract_and_process_sutra_memory(xml_response)

    # State Management Methods
    def get_memory_summary(self) -> Dict[str, Any]:
        """Get a summary of current memory state"""
        return self.memory_ops.get_memory_summary()

    def validate_memory_state(self) -> Dict[str, Any]:
        """Validate current memory state and return any issues"""
        return self.memory_ops.validate_memory_state()

    def reset_memory(self) -> bool:
        """Reset all memory state (use with caution)"""
        return self.memory_ops.reset_memory()

    # State Persistence Methods
    def export_memory_state(self) -> Dict[str, Any]:
        """Export current memory state to dictionary for persistence"""
        return self.state_persistence.export_memory_state()

    def import_memory_state(self, state: Dict[str, Any]) -> bool:
        """Import memory state from dictionary"""
        return self.state_persistence.import_memory_state(state)

    # Memory Formatting Methods
    def get_memory_for_llm(self) -> str:
        """Get current memory state formatted for LLM context in text format"""
        return self.memory_formatter.get_memory_for_llm()

    # Memory Update Methods
    def update_memory_for_file_changes(
        self, changed_files: set, deleted_files: set, project_id: int
    ) -> Dict[str, Any]:
        """Update Sutra memory when files change during incremental indexing"""
        return self.memory_updater.update_memory_for_file_changes(
            changed_files, deleted_files, project_id
        )
    
    # Reasoning Integration Methods
    def set_reasoning_context(self, user_query: str) -> None:
        """Set the current reasoning context for tool execution"""
        self.reasoning_context = ReasoningContext(
            user_query=user_query,
            tool_history=[],
            validation_results=[],
            confidence_scores=[]
        )
    
    def validate_tool_result(self, tool_name: str, tool_result: dict, user_query: str) -> dict:
        """Validate tool result using integrated reasoning logic"""
        from ..reasoning_engine import ReasoningEngine
        
        # Use reasoning engine for validation
        reasoning_engine = ReasoningEngine()
        validation_result = reasoning_engine.validate_tool_result(tool_name, tool_result, user_query)
        
        # Store validation result in reasoning context
        if self.reasoning_context:
            self.reasoning_context.validation_results.append(validation_result)
            self.reasoning_context.confidence_scores.append(validation_result.get('confidence', 0))
        
        # Add to tool history
        self.add_tool_history(tool_name, tool_result, validation_result, user_query)
        
        return validation_result
    
    def generate_reasoning_prompt(self, user_query: str) -> str:
        """Generate reasoning prompt based on tool history in memory"""
        tool_history = self.get_tool_history()
        
        if not tool_history:
            return "No previous tool executions found."
        
        reasoning_prompt = f"""
REASONING CHECKPOINT:

User Query: {user_query}

Before selecting your next tool, think through:
1. What specific information or action does this query require?
2. Have I gathered sufficient context from previous tools?
3. What is the most logical next step?
4. How will this tool help answer the user's question?

Previous Tool Results Summary:
"""
        
        for history_entry in tool_history[-3:]:  # Last 3 tools
            tool_name = history_entry.tool_name
            confidence = history_entry.validation_result.get('confidence', 0) if history_entry.validation_result else 0
            success = history_entry.validation_result.get('valid', True) if history_entry.validation_result else True
            reasoning_prompt += f"- {tool_name}: {'SUCCESS' if success else 'FAILED'} (confidence: {confidence:.2f})\n"
        
        reasoning_prompt += """
Choose the most appropriate tool and explain your reasoning briefly.
"""
        
        return reasoning_prompt
    
    def analyze_task_completion(self, user_query: str) -> dict:
        """Analyze if the user's task has been completed based on tool history"""
        tool_history = self.get_tool_history()
        
        analysis = {
            "likely_complete": False,
            "confidence": 0.0,
            "reason": "",
            "missing_actions": []
        }
        
        if not tool_history:
            return analysis
        
        # Simple heuristics for common task patterns
        query_lower = user_query.lower()
        
        # File creation/modification tasks
        if any(word in query_lower for word in ["create", "write", "make", "generate"]):
            write_results = [h for h in tool_history if h.tool_name == "write_to_file"]
            if write_results:
                last_write = write_results[-1]
                if last_write.tool_result and last_write.tool_result.get("successful_files"):
                    analysis["likely_complete"] = True
                    analysis["confidence"] = 0.8
                    analysis["reason"] = "File creation task appears complete"
        
        # Search/find tasks
        elif any(word in query_lower for word in ["find", "search", "look for", "show"]):
            search_results = [h for h in tool_history if h.tool_name in ["semantic_search", "database", "search_keyword"]]
            if search_results:
                last_search = search_results[-1]
                if last_search.tool_result and last_search.tool_result.get("data"):
                    analysis["likely_complete"] = True
                    analysis["confidence"] = 0.7
                    analysis["reason"] = "Search task returned results"
        
        # Command execution tasks
        elif any(word in query_lower for word in ["run", "execute", "install", "build"]):
            command_results = [h for h in tool_history if h.tool_name == "execute_command"]
            if command_results:
                last_command = command_results[-1]
                if last_command.tool_result and last_command.tool_result.get("exit_code") == 0:
                    analysis["likely_complete"] = True
                    analysis["confidence"] = 0.8
                    analysis["reason"] = "Command executed successfully"
        
        return analysis
    
    def should_continue_execution(self, validation_result: dict, consecutive_failures: int) -> bool:
        """Determine if execution should continue based on validation results"""
        # Stop on critical failures
        if not validation_result.get("valid", True):
            return False
        
        # Stop if confidence is too low
        if validation_result.get("confidence", 1.0) < 0.3:
            return False
        
        # Stop if too many consecutive failures
        if consecutive_failures >= 3:
            return False
        
        return True
    
    def clear_reasoning_context(self) -> None:
        """Clear reasoning context for new session"""
        self.reasoning_context = None
