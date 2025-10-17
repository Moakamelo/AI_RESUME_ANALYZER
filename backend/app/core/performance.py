import time
import functools
import logging
from typing import Dict, Any, Callable
from contextlib import contextmanager
import asyncio

logger = logging.getLogger(__name__)

# Global performance metrics storage
performance_metrics: Dict[str, list] = {}

def timer(metric_name: str):
    """
    Decorator to measure function execution time and store metrics
    FIXED: Properly handles both sync and async functions
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                end_time = time.perf_counter()
                duration = end_time - start_time
                
                # Store metric
                if metric_name not in performance_metrics:
                    performance_metrics[metric_name] = []
                performance_metrics[metric_name].append(duration)
                
                logger.info(f"⏱️ {metric_name}: {duration:.3f}s")
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.perf_counter()
                duration = end_time - start_time
                
                # Store metric
                if metric_name not in performance_metrics:
                    performance_metrics[metric_name] = []
                performance_metrics[metric_name].append(duration)
                
                logger.info(f"⏱️ {metric_name}: {duration:.3f}s")
        
        # Return the appropriate wrapper
        if hasattr(func, '__await__') or asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator

@contextmanager
def timing_context(metric_name: str):
    """
    Context manager for timing code blocks
    """
    start_time = time.perf_counter()
    try:
        yield
    finally:
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        if metric_name not in performance_metrics:
            performance_metrics[metric_name] = []
        performance_metrics[metric_name].append(duration)
        
        logger.info(f"⏱️ {metric_name}: {duration:.3f}s")

def get_performance_summary() -> Dict[str, Any]:
    """
    Get summary statistics for all performance metrics
    """
    summary = {}
    for metric_name, durations in performance_metrics.items():
        if durations:
            summary[metric_name] = {
                "count": len(durations),
                "avg": sum(durations) / len(durations),
                "min": min(durations),
                "max": max(durations),
                "p95": sorted(durations)[int(len(durations) * 0.95)] if len(durations) > 1 else durations[0],
                "total": sum(durations)
            }
    return summary

def clear_metrics():
    """Clear all performance metrics"""
    performance_metrics.clear()