"""
Performance monitoring utilities for the agent system.
"""

import time
import functools
from typing import Dict, Any, Optional, List
from loguru import logger
from collections import defaultdict


class PerformanceMonitor:
    """Monitor and track performance metrics for the agent system."""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = defaultdict(list)
        self.start_times: Dict[str, float] = {}
        self.call_counts: Dict[str, int] = defaultdict(int)
    
    def start_timer(self, operation: str) -> None:
        """Start timing an operation."""
        self.start_times[operation] = time.time()
    
    def end_timer(self, operation: str) -> float:
        """End timing an operation and record the duration."""
        if operation not in self.start_times:
            logger.warning(f"No start time recorded for operation: {operation}")
            return 0.0
        
        duration = time.time() - self.start_times[operation]
        self.metrics[operation].append(duration)
        self.call_counts[operation] += 1
        del self.start_times[operation]
        
        return duration
    
    def get_stats(self, operation: str) -> Dict[str, Any]:
        """Get statistics for an operation."""
        if operation not in self.metrics:
            return {}
        
        durations = self.metrics[operation]
        if not durations:
            return {}
        
        return {
            "count": len(durations),
            "total_time": sum(durations),
            "avg_time": sum(durations) / len(durations),
            "min_time": min(durations),
            "max_time": max(durations),
            "last_time": durations[-1]
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all operations."""
        return {op: self.get_stats(op) for op in self.metrics.keys()}
    
    def log_performance_summary(self) -> None:
        """Log a performance summary."""
        logger.info("=== Performance Summary ===")
        for operation, stats in self.get_all_stats().items():
            if stats:
                logger.info(
                    f"{operation}: {stats['count']} calls, "
                    f"avg: {stats['avg_time']:.3f}s, "
                    f"total: {stats['total_time']:.3f}s"
                )
    
    def clear(self) -> None:
        """Clear all metrics."""
        self.metrics.clear()
        self.start_times.clear()
        self.call_counts.clear()


# Global performance monitor instance
_performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    return _performance_monitor


def performance_timer(operation_name: str):
    """Decorator to automatically time function calls."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            monitor.start_timer(operation_name)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = monitor.end_timer(operation_name)
                logger.debug(f"{operation_name} took {duration:.3f}s")
        return wrapper
    return decorator


def log_slow_operations(threshold_seconds: float = 1.0):
    """Log operations that are taking longer than threshold."""
    monitor = get_performance_monitor()
    slow_ops = []
    
    for operation, stats in monitor.get_all_stats().items():
        if stats and stats['avg_time'] > threshold_seconds:
            slow_ops.append((operation, stats['avg_time']))
    
    if slow_ops:
        logger.warning("Slow operations detected:")
        for op, avg_time in sorted(slow_ops, key=lambda x: x[1], reverse=True):
            logger.warning(f"  {op}: {avg_time:.3f}s average")
