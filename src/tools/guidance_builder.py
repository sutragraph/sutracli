"""
Tool Guidance Factory

- Pattern: per-tool subclasses implement optional guidance hooks
- Usage: ActionExecutor asks factory for a guidance handler by tool name
- If no handler exists, skip (no-op)
"""

from typing import Optional, Dict, Any, List
from tools.utils.constants import (
    GUIDANCE_MESSAGES,
    SEARCH_CONFIG,
    DELIVERY_QUEUE_CONFIG,
)
from tools import ToolName


class BaseToolGuidance:
    def on_start(self, action) -> Optional[Dict[str, Any]]:  # pre-yield hook
        return None

    def on_event(self, event: Dict[str, Any], action) -> Optional[Dict[str, Any]]:
        return event


class SemanticSearchGuidance(BaseToolGuidance):
    def on_start(self, action):
        return None

    def on_event(self, event: Dict[str, Any], action):
        if not isinstance(event, dict) or event.get("tool_name") != "semantic_search":
            return event

        # Add a simple no-results guidance if missing
        if event.get("total_nodes") == 0:
            note = GUIDANCE_MESSAGES.get("NO_RESULTS_FOUND", "No results found for {search_type}.")
            prefix = note.format(search_type="semantic") + "\n\n"
            data = event.get("data", "")
            event["data"] = prefix + data if data else prefix.strip()
        return event


class DatabaseSearchGuidance(BaseToolGuidance):
    def on_start(self, action):
        return None

    # --- Guidance helpers (ported, simplified) ---
    def _determine_guidance_scenario(
        self, total_nodes: int, include_code: bool, code_lines: Optional[int] = None, chunk_info: Optional[Dict[str, Any]] = None
    ) -> str:
        if total_nodes == 0:
            return "NO_RESULTS_FOUND"
        if total_nodes == 1:
            if not include_code or not code_lines:
                return "NODE_MISSING_CODE_CONTENT"
            if code_lines and code_lines > SEARCH_CONFIG.get("chunking_threshold", 300):
                return "SINGLE_RESULT_LARGE"
            return "SINGLE_RESULT_SMALL"
        return "MULTIPLE_RESULTS"

    def _build_guidance_message(self, search_type: str, scenario: str, **kwargs) -> str:
        if scenario == "NO_RESULTS_FOUND":
            return GUIDANCE_MESSAGES.get("NO_RESULTS_FOUND", "No results found for {search_type}.").format(search_type=search_type)
        if scenario == "SINGLE_RESULT_SMALL":
            return f"Found 1 result from {search_type} search."
        if scenario == "SINGLE_RESULT_LARGE":
            total_lines = kwargs.get("total_lines", 0)
            chunk_start = kwargs.get("chunk_start", 1)
            chunk_end = kwargs.get("chunk_end", total_lines)
            message = f"Found 1 result from {search_type} search."
            if total_lines:
                message += f" Total {total_lines} lines, sending lines {chunk_start}-{chunk_end}."
            message += f" For more use fetch_next (start:end: {chunk_start}:{chunk_end})"
            message += GUIDANCE_MESSAGES.get("FETCH_NEXT_CODE_NOTE", "")
            return message
        if scenario == "MULTIPLE_RESULTS":
            total_nodes = kwargs.get("total_nodes", 0)
            message = f"Found {total_nodes} results from {search_type} search"
            message += GUIDANCE_MESSAGES.get("FETCH_NEXT_CODE_NOTE", "")
            return message
        if scenario == "NODE_MISSING_CODE_CONTENT":
            return GUIDANCE_MESSAGES.get("NODE_MISSING_CODE", "Code not available for this node.")
        if scenario == "BATCH_DELIVERY":
            remaining_count = kwargs.get("remaining_count", 0)
            return GUIDANCE_MESSAGES.get("FETCH_NEXT_CODE_NOTE", "") if remaining_count > 0 else ""
        return f"Results from {search_type} search."

    def _build_batch_guidance_message(
        self,
        search_type: str,
        total_nodes: int,
        include_code: bool,
        **kwargs,
    ) -> str:
        scenario = self._determine_guidance_scenario(total_nodes, include_code, kwargs.get("code_lines"), kwargs.get("chunk_info"))
        return self._build_guidance_message(search_type, scenario, **kwargs)

    def _create_delivery_batches(self, results: List[Dict[str, Any]], batch_size: int) -> List[List[Dict[str, Any]]]:
        return [results[i : i + batch_size] for i in range(0, len(results), batch_size)]

    def _build_delivery_info(self, current_batch: int, total_batches: int, batch_size: int, total_results: int, has_code: bool) -> Dict[str, Any]:
        current_start = (current_batch - 1) * batch_size + 1
        current_end = min(current_batch * batch_size, total_results)
        has_more = current_batch < total_batches
        return {
            "current_batch": current_batch,
            "total_batches": total_batches,
            "current_start": current_start,
            "current_end": current_end,
            "total_results": total_results,
            "batch_size": batch_size,
            "has_more": has_more,
            "has_code": has_code,
        }

    def _format_delivery_guidance(self, delivery_info: Dict[str, Any], search_type: str) -> str:
        start = delivery_info["current_start"]
        end = delivery_info["current_end"]
        total = delivery_info["total_results"]
        cur = delivery_info["current_batch"]
        tot = delivery_info["total_batches"]
        prefix = "KEYWORD SEARCH RESULTS:" if search_type == "keyword" else "DATABASE SEARCH RESULTS:"
        guidance = f"{prefix} Showing {search_type} search results {start}-{end} of {total} total results (batch {cur}/{tot})"
        if delivery_info.get("has_more"):
            guidance += GUIDANCE_MESSAGES.get("FETCH_NEXT_CODE_NOTE", "")
        return guidance

    def on_event(self, event: Dict[str, Any], action) -> Optional[Dict[str, Any]]:
        if not isinstance(event, dict) or event.get("tool_name") != "database":
            return event

        # Add generic no-results guidance if missing
        if event.get("result", "").endswith(": 0"):
            msg = self._build_guidance_message("database", "NO_RESULTS_FOUND")
            data = event.get("data", "")
            event["data"] = (msg + "\n\n" + data).strip() if data else msg
            return event

        # If batch metadata present, ensure guidance prefix exists
        if any(k in event for k in ("current_batch", "total_batches")):
            info = self._build_delivery_info(
                current_batch=event.get("current_batch", 1),
                total_batches=event.get("total_batches", 1),
                batch_size=DELIVERY_QUEUE_CONFIG.get("database_metadata_only", 10),
                total_results=event.get("total_nodes", 0),
                has_code=bool(event.get("include_code", False)),
            )
            guidance = self._format_delivery_guidance(info, "keyword" if action.parameters.get("query_name") == "GET_NODES_BY_KEYWORD_SEARCH" else "database")
            data = event.get("data", "")
            if guidance and (not data or not data.lstrip().startswith("DATABASE SEARCH RESULTS:") and not data.lstrip().startswith("KEYWORD SEARCH RESULTS:")):
                event["data"] = guidance + ("\n\n" + data if data else "")
        return event


class KeywordSearchGuidance(BaseToolGuidance):
    def on_start(self, action):
        return None

    def on_event(self, event: Dict[str, Any], action):
        if not isinstance(event, dict) or event.get("tool_name") != "search_keyword":
            return event
        # Optionally prepend a small header for search results
        if event.get("matches_found") and event.get("data"):
            header = f"KEYWORD: '{event.get('keyword','')}' in {event.get('file_path','selected paths')}\n"
            event["data"] = header + event["data"]
        return event


_REGISTRY = {
    ToolName.SEMANTIC_SEARCH: SemanticSearchGuidance,
    ToolName.DATABASE_SEARCH: DatabaseSearchGuidance,
    ToolName.SEARCH_KEYWORD: KeywordSearchGuidance,
}


def get_tool_guidance(tool_enum: ToolName) -> Optional[BaseToolGuidance]:
    cls = _REGISTRY.get(tool_enum)
    return cls() if cls else None


