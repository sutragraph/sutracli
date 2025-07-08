"""
Tree-sitter Code Analyzer

A clean, simplified analyzer that orchestrates the analysis process.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from loguru import logger
from .utils import AnalysisOrchestrator, NodeIdGenerator
from .factory import get_analyzer_factory
from .config import get_config_manager


class Analyzer:
    """Main analyzer class for processing code files and directories."""

    def __init__(
        self,
        repo_id: str = "default_repo",
        config_path: Optional[str] = None,
    ):
        """Initialize the analyzer."""
        self.repo_id = repo_id
        self.config = get_config_manager(config_path)
        self.analyzer_factory = get_analyzer_factory()
        self.orchestrator = AnalysisOrchestrator(self.config)
        self.node_id_generator = NodeIdGenerator()
        self.node_id_generator.reset_counters()

        # Analysis state
        self.results = {
            "repo_id": repo_id,
            "nodes": [],
            "edges": [],
            "language_stats": {},
            "analysis_stats": {
                "total_files": 0,
                "processed_files": 0,
                "failed_files": 0,
                "processing_time": 0.0,
                "languages_detected": set(),
            },
        }

    async def analyze_directory(
        self, directory_path: str, recursive: bool = True
    ) -> Dict[str, Any]:
        """Analyze all files in a directory."""
        start_time = time.time()

        logger.debug(f"Analyzing directory: {directory_path}")

        # Scan and filter files
        files, languages = self.orchestrator.scan_and_filter_directory(directory_path)

        self.results["analysis_stats"]["total_files"] = len(files)
        self.results["analysis_stats"]["languages_detected"] = languages

        logger.debug(
            f"Found {len(files)} files in {len(languages)} languages: {languages}"
        )

        # Analyze each file
        for file_path in files:
            try:
                file_result = await self.analyze_file(file_path)
                if file_result:
                    self._merge_file_result(file_result)
                    self.results["analysis_stats"]["processed_files"] += 1
                else:
                    self.results["analysis_stats"]["failed_files"] += 1
            except Exception as e:
                logger.debug(f"Error analyzing {file_path}: {e}")
                self.results["analysis_stats"]["failed_files"] += 1

        # Resolve edges using the orchestrator
        self.orchestrator.resolve_analysis_edges(self.results)

        # Clean up unresolved edges after analyzing the whole directory
        removed_count = self.orchestrator.cleanup_unresolved_edges(self.results)
        if removed_count > 0:
            logger.debug(f"Removed {removed_count} unresolved edges from final results")

        # Finalize results
        self.results["analysis_stats"]["processing_time"] = time.time() - start_time
        self.results["analysis_stats"]["languages_detected"] = list(languages)

        logger.debug(
            f"Analysis complete: {self.results['analysis_stats']['processed_files']} files processed"
        )

        return self.results

    async def analyze_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Analyze a single file."""
        try:
            # Get analyzer for file
            analyzer = self.analyzer_factory.create_analyzer_for_file(
                file_path, self.repo_id, node_id_generator=self.node_id_generator
            )

            if not analyzer:
                logger.debug(f"Failed to create analyzer for {file_path}")
                return None

            # Analyze the file
            if asyncio.iscoroutinefunction(analyzer.analyze_file):
                result = await analyzer.analyze_file(file_path)
            else:
                result = await asyncio.get_event_loop().run_in_executor(
                    None, analyzer.analyze_file, file_path
                )

            return result

        except Exception as e:
            logger.debug(f"Error analyzing file {file_path}: {e}")
            return None

    def _merge_file_result(self, file_result: Dict[str, Any]) -> None:
        """Merge file analysis result into overall results."""
        if not file_result:
            return

        # Merge nodes (IDs are already deterministic from the analyzer)
        if "nodes" in file_result:
            for node in file_result["nodes"]:
                self.results["nodes"].append(node)

        # Merge edges (IDs are already correct)
        if "edges" in file_result:
            for edge in file_result["edges"]:
                self.results["edges"].append(edge)

        # Update language stats
        language = file_result.get("language", "unknown")
        self.results["language_stats"][language] = (
            self.results["language_stats"].get(language, 0) + 1
        )

    def export_results(self, output_path: str, format: str = "json") -> None:
        """Export analysis results to file."""
        # Ensure output directory exists
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        if format == "json":
            # Convert sets to lists for JSON serialization
            results_copy = self.results.copy()
            if isinstance(results_copy["analysis_stats"]["languages_detected"], set):
                results_copy["analysis_stats"]["languages_detected"] = list(
                    results_copy["analysis_stats"]["languages_detected"]
                )

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results_copy, f, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    async def analyze_and_save(
        self,
        directory_path: str,
        results_folder: str = "results",
        include_summary: bool = True,
    ) -> str:
        """Analyze a directory and save results to a results folder."""
        # Analyze the directory
        logger.debug(f"Analyzing directory: {directory_path}")
        results = await self.analyze_directory(directory_path)

        # Create results folder
        results_dir = Path(results_folder)
        results_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename based on directory name and timestamp
        dir_name = Path(directory_path).name
        timestamp = time.strftime("%Y%m%d_%H%M%S")

        # Save main results
        results_file = results_dir / f"{dir_name}_analysis_{timestamp}.json"
        self.export_results(str(results_file))
        logger.debug(f"Results saved to: {results_file}")

        # Save summary if requested
        if include_summary:
            summary = self.get_analysis_summary()
            summary_file = results_dir / f"{dir_name}_summary_{timestamp}.json"

            with open(summary_file, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, default=str)
            logger.debug(f"Summary saved to: {summary_file}")

        return str(results_file)

    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get a summary of the analysis results."""
        stats = self.results["analysis_stats"]
        return {
            "repo_id": self.repo_id,
            "total_files": stats["total_files"],
            "processed_files": stats["processed_files"],
            "failed_files": stats["failed_files"],
            "success_rate": stats["processed_files"] / max(stats["total_files"], 1),
            "processing_time": stats["processing_time"],
            "languages_detected": list(stats["languages_detected"]),
            "language_stats": self.results["language_stats"],
            "total_nodes": len(self.results["nodes"]),
            "total_edges": len(self.results["edges"]),
            "node_types": self._count_node_types(),
            "edge_types": self._count_edge_types(),
        }

    def _count_node_types(self) -> Dict[str, int]:
        """Count nodes by type."""
        counts = {}
        for node in self.results["nodes"]:
            node_type = node.get("type", "unknown")
            counts[node_type] = counts.get(node_type, 0) + 1
        return counts

    def _count_edge_types(self) -> Dict[str, int]:
        """Count edges by type."""
        counts = {}
        for edge in self.results["edges"]:
            edge_type = edge.get("type", "unknown")
            counts[edge_type] = counts.get(edge_type, 0) + 1
        return counts


# Convenience functions
async def quick_analyze_file(
    file_path: str, repo_id: str = "quick_analysis"
) -> Optional[Dict[str, Any]]:
    """Quick analysis of a single file."""
    analyzer = Analyzer(repo_id)
    return await analyzer.analyze_file(file_path)


async def quick_analyze_directory(
    directory_path: str, repo_id: str = "quick_analysis"
) -> Dict[str, Any]:
    """Quick analysis of a directory."""
    analyzer = Analyzer(repo_id)
    return await analyzer.analyze_directory(directory_path)
