"""
Centralized Guidance Builder

- Provides a base class and simple factory to generate guidance messages for tool outputs
- To be used by AgentService (or its executors) to attach guidance outside of tool actions
- If a tool has no dedicated builder, we skip gracefully
"""

from __future__ import annotations

from typing import Optional, Dict, Any, Type

from services.agent.agent_prompt.guidance_builder import (
    build_guidance_message,
    build_sequential_node_message,
    determine_guidance_scenario,
    determine_sequential_node_scenario,
    determine_semantic_batch_scenario,
    GuidanceScenario,
    SequentialNodeScenario,
    SearchType,
)


class GuidanceBuilder:
    """Base class for per-tool guidance builders."""

    search_type: SearchType = SearchType.DATABASE

    def build(self, event: Dict[str, Any]) -> Optional[str]:
        """Produce guidance text for a single tool event; return None to skip."""
        return None

    @staticmethod
    def _extract_total_nodes(event: Dict[str, Any]) -> Optional[int]:
        tn = event.get("total_nodes")
        if isinstance(tn, int):
            return tn
        # Fallback: parse result strings like "Found X nodes" or "result found: X"
        result_text = event.get("result") or event.get("data") or ""
        if isinstance(result_text, str):
            import re

            m = re.search(r"\b(Found|result found:)\s*(\d+)", result_text, re.I)
            if m:
                try:
                    return int(m.group(2))
                except Exception:
                    return None
        return None

    @staticmethod
    def _extract_chunk_info(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return event.get("chunk_info")

    @staticmethod
    def _extract_include_code(event: Dict[str, Any]) -> bool:
        return bool(event.get("include_code", False))

    @staticmethod
    def _extract_code_lines(event: Dict[str, Any]) -> Optional[int]:
        # If chunk_info present with total_lines, prefer that
        chunk_info = event.get("chunk_info")
        if isinstance(chunk_info, dict) and "total_lines" in chunk_info:
            try:
                return int(chunk_info["total_lines"])
            except Exception:
                pass

        # Otherwise estimate from data payload if it's likely code
        data = event.get("data")
        if isinstance(data, str):
            # Cap to avoid heavy processing; just a quick heuristic
            lines = data.count("\n") + 1
            return lines
        return None


class DatabaseGuidanceBuilder(GuidanceBuilder):
    search_type = SearchType.DATABASE

    def build(self, event: Dict[str, Any]) -> Optional[str]:
        total_nodes = self._extract_total_nodes(event) or 0
        include_code = self._extract_include_code(event)
        chunk_info = self._extract_chunk_info(event)
        code_lines = self._extract_code_lines(event)

        # Batch delivery hint support
        if event.get("current_batch") is not None and event.get("total_batches") is not None:
            scenario = GuidanceScenario.BATCH_DELIVERY
            remaining = (event.get("total_batches", 1) - event.get("current_batch", 1))
            return build_guidance_message(
                search_type=self.search_type,
                scenario=scenario,
                remaining_count=max(remaining, 0),
                total_nodes=total_nodes,
            )

        # Single/multiple guidance
        scenario = determine_guidance_scenario(
            total_nodes=total_nodes,
            include_code=include_code,
            code_lines=code_lines,
            chunk_info=chunk_info,
        )

        # Provide chunk details if any
        kwargs: Dict[str, Any] = {}
        if isinstance(chunk_info, dict):
            kwargs.update(
                {
                    "chunk_num": chunk_info.get("chunk_num"),
                    "total_chunks": chunk_info.get("total_chunks"),
                    "total_lines": chunk_info.get("total_lines"),
                    "chunk_start": chunk_info.get("chunk_start_line"),
                    "chunk_end": chunk_info.get("chunk_end_line"),
                }
            )

        has_more = bool(event.get("has_more") or event.get("has_more_batches"))
        return build_guidance_message(
            search_type=self.search_type,
            scenario=scenario,
            total_nodes=total_nodes,
            has_more_results=has_more,
            **kwargs,
        )


class SemanticSearchGuidanceBuilder(GuidanceBuilder):
    search_type = SearchType.SEMANTIC

    def build(self, event: Dict[str, Any]) -> Optional[str]:
        # Semantic results are typically delivered in batches
        scenario = determine_semantic_batch_scenario()
        total_nodes = self._extract_total_nodes(event) or 0
        delivered_count = event.get("batch_info", {}).get("delivered_count", 0)
        remaining_count = event.get("batch_info", {}).get("remaining_count", 0)

        return build_guidance_message(
            search_type=self.search_type,
            scenario=scenario,
            total_nodes=total_nodes,
            delivered_count=delivered_count,
            remaining_count=remaining_count,
            batch_number=1,
        )


class KeywordSearchGuidanceBuilder(GuidanceBuilder):
    search_type = SearchType.KEYWORD

    def build(self, event: Dict[str, Any]) -> Optional[str]:
        total_nodes = self._extract_total_nodes(event) or 0
        include_code = self._extract_include_code(event)
        code_lines = self._extract_code_lines(event)
        chunk_info = self._extract_chunk_info(event)

        # Keyword tool sometimes uses delivery batches as well
        if event.get("current_batch") is not None and event.get("total_batches") is not None:
            scenario = GuidanceScenario.BATCH_DELIVERY
            remaining = (event.get("total_batches", 1) - event.get("current_batch", 1))
            return build_guidance_message(
                search_type=self.search_type,
                scenario=scenario,
                remaining_count=max(remaining, 0),
                total_nodes=total_nodes,
            )

        scenario = determine_guidance_scenario(
            total_nodes=total_nodes,
            include_code=include_code,
            code_lines=code_lines,
            chunk_info=chunk_info,
        )

        return build_guidance_message(
            search_type=self.search_type,
            scenario=scenario,
            total_nodes=total_nodes,
        )


_REGISTRY: Dict[str, Type[GuidanceBuilder]] = {
    "database": DatabaseGuidanceBuilder,
    "semantic_search": SemanticSearchGuidanceBuilder,
    "search_keyword": KeywordSearchGuidanceBuilder,
}


def get_guidance_builder(tool_name: str) -> Optional[GuidanceBuilder]:
    """Return a builder instance for a tool name; None if unsupported."""
    cls = _REGISTRY.get(tool_name)
    return cls() if cls else None


def augment_event_with_guidance(event: Dict[str, Any]) -> Dict[str, Any]:
    """Attach guidance to a tool event if a builder exists. Returns the same dict (mutated)."""
    try:
        if not isinstance(event, dict):
            return event
        if event.get("type") not in {"tool_use", "tool"}:
            return event
        tool_name = event.get("tool_name") or event.get("used_tool")
        if not tool_name:
            return event
        builder = get_guidance_builder(tool_name)
        if not builder:
            return event
        guidance = builder.build(event)
        if guidance:
            event["guidance"] = guidance
        return event
    except Exception:
        return event


