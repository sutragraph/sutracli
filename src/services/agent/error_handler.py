"""
Enhanced error handling and recovery for agent operations
"""

from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
import traceback
from enum import Enum


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorHandler:
    """Enhanced error handling with recovery suggestions."""

    def __init__(self):
        self.error_history = []
        self.recovery_attempts = {}

    def handle_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle and categorize errors with recovery suggestions.
        
        Args:
            error: The exception that occurred
            context: Context information about when the error occurred
            
        Returns:
            Dict with error analysis and recovery suggestions
        """
        error_info = {
            "error_type": type(error).__name__,
            "message": str(error),
            "severity": self._determine_severity(error),
            "context": context,
            "traceback": traceback.format_exc(),
            "recovery_suggestions": [],
            "should_retry": False,
            "max_retries": 0
        }

        # Add to error history
        self.error_history.append(error_info)

        # Analyze error and provide recovery suggestions
        error_info = self._analyze_error(error_info)

        logger.error(f"Error handled: {error_info['error_type']} - {error_info['message']}")
        if error_info["recovery_suggestions"]:
            print(f"Recovery suggestions: {error_info['recovery_suggestions']}")

        return error_info

    def _determine_severity(self, error: Exception) -> ErrorSeverity:
        """Determine error severity based on exception type."""
        error_type = type(error).__name__

        # Critical errors that should stop execution
        if error_type in ["KeyboardInterrupt", "SystemExit", "MemoryError"]:
            return ErrorSeverity.CRITICAL

        # High severity errors
        if error_type in ["FileNotFoundError", "PermissionError", "ConnectionError", "TimeoutError"]:
            return ErrorSeverity.HIGH

        # Medium severity errors
        if error_type in ["ValueError", "TypeError", "AttributeError", "ImportError"]:
            return ErrorSeverity.MEDIUM

        # Low severity errors
        return ErrorSeverity.LOW

    def _analyze_error(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze error and provide specific recovery suggestions."""
        error_type = error_info["error_type"]
        message = error_info["message"].lower()

        # File operation errors
        if error_type == "FileNotFoundError":
            error_info["recovery_suggestions"].extend([
                "Check if the file path is correct",
                "Verify the file exists before attempting to read",
                "Use list_files tool to explore directory structure"
            ])
            error_info["should_retry"] = True
            error_info["max_retries"] = 2

        elif error_type == "PermissionError":
            error_info["recovery_suggestions"].extend([
                "Check file permissions",
                "Ensure the file is not locked by another process",
                "Try using sudo if appropriate (with caution)"
            ])
            error_info["should_retry"] = False

        # Network errors
        elif error_type in ["ConnectionError", "TimeoutError"]:
            error_info["recovery_suggestions"].extend([
                "Check network connectivity",
                "Verify the URL is correct and accessible",
                "Try again after a brief delay"
            ])
            error_info["should_retry"] = True
            error_info["max_retries"] = 3

        # Import errors
        elif error_type == "ImportError":
            error_info["recovery_suggestions"].extend([
                "Check if the module is installed",
                "Verify the module name is correct",
                "Install missing dependencies if needed"
            ])
            error_info["should_retry"] = False

        # Database errors
        elif "database" in message or "sqlite" in message:
            error_info["recovery_suggestions"].extend([
                "Check database connection",
                "Verify database file exists and is accessible",
                "Check SQL query syntax"
            ])
            error_info["should_retry"] = True
            error_info["max_retries"] = 2

        # XML parsing errors
        elif "xml" in message.lower():
            error_info["recovery_suggestions"].extend([
                "Check XML structure and syntax",
                "Ensure all XML tags are properly closed",
                "Verify XML content is well-formed"
            ])
            error_info["should_retry"] = True
            error_info["max_retries"] = 3

        # Command execution errors
        elif "command" in message or "exit code" in message:
            error_info["recovery_suggestions"].extend([
                "Check command syntax",
                "Verify command exists and is in PATH",
                "Check working directory and file permissions"
            ])
            error_info["should_retry"] = True
            error_info["max_retries"] = 2

        return error_info

    def should_stop_execution(self, error_info: Dict[str, Any]) -> bool:
        """Determine if execution should stop based on error severity."""
        severity = error_info["severity"]

        # Always stop for critical errors
        if severity == ErrorSeverity.CRITICAL:
            return True

        # Stop if we've seen too many errors of the same type
        error_type = error_info["error_type"]
        same_type_errors = [e for e in self.error_history if e["error_type"] == error_type]

        if len(same_type_errors) >= 3:
            logger.warning(f"Too many {error_type} errors, stopping execution")
            return True

        # Stop if we've seen too many high severity errors
        high_severity_errors = [e for e in self.error_history if e["severity"] in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]]

        if len(high_severity_errors) >= 5:
            logger.warning("Too many high severity errors, stopping execution")
            return True

        return False

    def get_recovery_actions(self, error_info: Dict[str, Any]) -> List[str]:
        """Get specific recovery actions for an error."""
        actions = []

        error_type = error_info["error_type"]
        context = error_info.get("context", {})

        # Tool-specific recovery actions
        tool_name = context.get("tool_name", "")

        if tool_name == "write_to_file" and error_type == "FileNotFoundError":
            actions.append("Use list_files to verify the target directory exists")
            actions.append("Create the directory structure if it doesn't exist")

        elif tool_name == "semantic_search" and "database" in error_info["message"].lower():
            actions.append("Check if the project is properly indexed")
            actions.append("Run incremental indexing to update the database")

        elif tool_name == "execute_command" and "command not found" in error_info["message"].lower():
            actions.append("Check if the command is installed")
            actions.append("Use absolute path to the command")
            actions.append("Verify the command name is correct")

        # General recovery actions
        if error_info["should_retry"]:
            actions.append(f"Retry the operation (max {error_info['max_retries']} attempts)")

        actions.extend(error_info["recovery_suggestions"])

        return actions

    def clear_history(self):
        """Clear error history for new session."""
        self.error_history.clear()
        self.recovery_attempts.clear()

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors encountered."""
        if not self.error_history:
            return {"total_errors": 0, "error_types": {}, "severity_distribution": {}}

        error_types = {}
        severity_distribution = {}

        for error in self.error_history:
            error_type = error["error_type"]
            severity = error["severity"].value

            error_types[error_type] = error_types.get(error_type, 0) + 1
            severity_distribution[severity] = severity_distribution.get(severity, 0) + 1

        return {
            "total_errors": len(self.error_history),
            "error_types": error_types,
            "severity_distribution": severity_distribution,
            "recent_errors": self.error_history[-5:] if len(self.error_history) > 5 else self.error_history
        }


class ResultVerifier:
    """Verify tool results for correctness and completeness."""
    
    def __init__(self):
        self.verification_history = []
    
    def verify_result(self, tool_name: str, result: Dict[str, Any], expected_outcome: str = None) -> Dict[str, Any]:
        """
        Verify tool result meets expected criteria.
        
        Args:
            tool_name: Name of the tool that generated the result
            result: The result to verify
            expected_outcome: Expected outcome description
            
        Returns:
            Dict with verification results
        """
        verification = {
            "tool_name": tool_name,
            "verified": True,
            "issues": [],
            "recommendations": [],
            "result_quality": "good"
        }
        
        # Tool-specific verification
        if tool_name == "write_to_file":
            verification = self._verify_file_write(result, verification)
        elif tool_name == "semantic_search":
            verification = self._verify_search_result(result, verification)
        elif tool_name == "execute_command":
            verification = self._verify_command_result(result, verification)
        elif tool_name == "apply_diff":
            verification = self._verify_diff_result(result, verification)
        else:
            verification = self._verify_generic_result(result, verification)
        
        # Add to verification history
        self.verification_history.append(verification)
        
        return verification
    
    def _verify_file_write(self, result: Dict[str, Any], verification: Dict[str, Any]) -> Dict[str, Any]:
        """Verify file write operation results."""
        successful_files = result.get("successful_files", [])
        failed_files = result.get("failed_files", [])
        
        if failed_files:
            verification["verified"] = False
            verification["issues"].append(f"Failed to write files: {failed_files}")
            verification["result_quality"] = "failed"
        
        if not successful_files:
            verification["verified"] = False
            verification["issues"].append("No files were written successfully")
            verification["result_quality"] = "failed"
        
        return verification
    
    def _verify_search_result(self, result: Dict[str, Any], verification: Dict[str, Any]) -> Dict[str, Any]:
        """Verify search result quality."""
        data = result.get("data", "")
        count = result.get("count", 0)
        
        if not data or data.strip() == "":
            verification["issues"].append("No search results returned")
            verification["result_quality"] = "poor"
            verification["recommendations"].append("Try different search terms or broader query")
        
        elif count == 0:
            verification["issues"].append("Zero results found")
            verification["result_quality"] = "poor"
        
        elif count > 100:
            verification["issues"].append("Too many results, may be too broad")
            verification["result_quality"] = "fair"
            verification["recommendations"].append("Refine search query to be more specific")
        
        return verification
    
    def _verify_command_result(self, result: Dict[str, Any], verification: Dict[str, Any]) -> Dict[str, Any]:
        """Verify command execution results."""
        exit_code = result.get("exit_code")
        error = result.get("error", "")
        
        if exit_code is not None and exit_code != 0:
            verification["verified"] = False
            verification["issues"].append(f"Command failed with exit code: {exit_code}")
            verification["result_quality"] = "failed"
        
        if error:
            verification["issues"].append(f"Command error: {error}")
            verification["result_quality"] = "poor"
        
        return verification
    
    def _verify_diff_result(self, result: Dict[str, Any], verification: Dict[str, Any]) -> Dict[str, Any]:
        """Verify diff application results."""
        successful_files = result.get("successful_files", [])
        failed_files = result.get("failed_files", [])
        failed_diffs = result.get("failed_diffs", [])
        
        if failed_files or failed_diffs:
            verification["verified"] = False
            verification["issues"].append(f"Diff application failed: files={failed_files}, diffs={failed_diffs}")
            verification["result_quality"] = "failed"
        
        if not successful_files:
            verification["verified"] = False
            verification["issues"].append("No diffs were applied successfully")
            verification["result_quality"] = "failed"
        
        return verification
    
    def _verify_generic_result(self, result: Dict[str, Any], verification: Dict[str, Any]) -> Dict[str, Any]:
        """Verify generic tool results."""
        if result.get("error"):
            verification["verified"] = False
            verification["issues"].append(f"Tool error: {result['error']}")
            verification["result_quality"] = "failed"
        
        if result.get("success") is False:
            verification["verified"] = False
            verification["issues"].append("Tool reported failure")
            verification["result_quality"] = "failed"
        
        return verification
    
    def clear_history(self):
        """Clear verification history."""
        self.verification_history.clear()
