# utils/performance.py
from __future__ import annotations
import time
import psutil
import threading
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import wraps
import multiprocessing as mp
from contextlib import contextmanager

@dataclass
class PerformanceMetrics:
    execution_time: float
    memory_usage_mb: float
    cpu_percent: float
    events_processed: int
    throughput_events_per_sec: float

class PerformanceMonitor:
    """Monitor and optimize performance for large log processing"""
    
    def __init__(self):
        self.metrics_history: List[PerformanceMetrics] = []
        self.process = psutil.Process()
        
    @contextmanager
    def monitor_operation(self, operation_name: str, event_count: int = 0):
        """Context manager to monitor performance of operations"""
        start_time = time.time()
        start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        start_cpu = self.process.cpu_percent()
        
        try:
            yield
        finally:
            end_time = time.time()
            end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            end_cpu = self.process.cpu_percent()
            
            execution_time = end_time - start_time
            memory_usage = end_memory - start_memory
            cpu_usage = (start_cpu + end_cpu) / 2
            throughput = event_count / execution_time if execution_time > 0 else 0
            
            metrics = PerformanceMetrics(
                execution_time=execution_time,
                memory_usage_mb=memory_usage,
                cpu_percent=cpu_usage,
                events_processed=event_count,
                throughput_events_per_sec=throughput
            )
            
            self.metrics_history.append(metrics)
            print(f"[PERF] {operation_name}: {execution_time:.2f}s, {throughput:.0f} events/sec, {memory_usage:.1f}MB")

def performance_timer(func: Callable) -> Callable:
    """Decorator to time function execution"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"[TIMER] {func.__name__}: {end - start:.3f}s")
        return result
    return wrapper

class BatchProcessor:
    """Process large datasets in optimized batches"""
    
    def __init__(self, batch_size: int = 1000, max_workers: Optional[int] = None):
        self.batch_size = batch_size
        self.max_workers = max_workers or min(mp.cpu_count(), 8)
        
    def process_in_batches(self, items: List[Any], processor_func: Callable, use_multiprocessing: bool = False) -> List[Any]:
        """Process items in batches with optional multiprocessing"""
        batches = [items[i:i + self.batch_size] for i in range(0, len(items), self.batch_size)]
        results = []
        
        if use_multiprocessing and len(batches) > 1:
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                batch_results = list(executor.map(processor_func, batches))
                for batch_result in batch_results:
                    results.extend(batch_result)
        else:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                batch_results = list(executor.map(processor_func, batches))
                for batch_result in batch_results:
                    results.extend(batch_result)
        
        return results

class MemoryOptimizer:
    """Optimize memory usage for large log files"""
    
    @staticmethod
    def stream_file_lines(file_path: str, chunk_size: int = 8192):
        """Stream file lines to avoid loading entire file into memory"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            buffer = ""
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    if buffer:
                        yield buffer
                    break
                
                buffer += chunk
                lines = buffer.split('\n')
                buffer = lines[-1]  # Keep incomplete line in buffer
                
                for line in lines[:-1]:
                    yield line
    
    @staticmethod
    def chunked_processing(items: List[Any], chunk_size: int = 1000):
        """Generator to process items in memory-efficient chunks"""
        for i in range(0, len(items), chunk_size):
            yield items[i:i + chunk_size]
    
    @staticmethod
    def memory_usage_mb() -> float:
        """Get current memory usage in MB"""
        return psutil.Process().memory_info().rss / 1024 / 1024

class CacheManager:
    """Intelligent caching for expensive operations"""
    
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, Any] = {}
        self.access_count: Dict[str, int] = {}
        self.max_size = max_size
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache"""
        with self._lock:
            if key in self.cache:
                self.access_count[key] = self.access_count.get(key, 0) + 1
                return self.cache[key]
        return None
    
    def put(self, key: str, value: Any):
        """Put item in cache with LRU eviction"""
        with self._lock:
            if len(self.cache) >= self.max_size:
                # Remove least recently used item
                lru_key = min(self.access_count.keys(), key=lambda k: self.access_count[k])
                del self.cache[lru_key]
                del self.access_count[lru_key]
            
            self.cache[key] = value
            self.access_count[key] = 1
    
    def clear(self):
        """Clear cache"""
        with self._lock:
            self.cache.clear()
            self.access_count.clear()

# Global instances
performance_monitor = PerformanceMonitor()
cache_manager = CacheManager()
