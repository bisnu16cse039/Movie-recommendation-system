"""Simple in-memory metrics tracking"""

import time
from collections import defaultdict
from typing import Dict, List
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class MetricsData:
    """Container for metrics data"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_duration_ms: float = 0.0
    errors_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    requests_by_endpoint: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    status_codes: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    start_time: float = field(default_factory=time.time)


class MetricsTracker:
    """Thread-safe in-memory metrics tracker"""
    
    def __init__(self):
        self._data = MetricsData()
        self._lock = Lock()
    
    def record_request(self, method: str, path: str, status_code: int, duration_ms: float):
        """Record a completed request"""
        with self._lock:
            self._data.total_requests += 1
            self._data.total_duration_ms += duration_ms
            self._data.requests_by_endpoint[f"{method} {path}"] += 1
            self._data.status_codes[status_code] += 1
            
            if 200 <= status_code < 400:
                self._data.successful_requests += 1
            else:
                self._data.failed_requests += 1
    
    def record_error(self, method: str, path: str, error_type: str):
        """Record an error"""
        with self._lock:
            self._data.failed_requests += 1
            self._data.errors_by_type[error_type] += 1
    
    def get_metrics(self) -> Dict:
        """Get current metrics snapshot"""
        with self._lock:
            uptime_seconds = time.time() - self._data.start_time
            avg_latency_ms = (
                self._data.total_duration_ms / self._data.total_requests
                if self._data.total_requests > 0
                else 0.0
            )
            
            return {
                "uptime_seconds": round(uptime_seconds, 2),
                "total_requests": self._data.total_requests,
                "successful_requests": self._data.successful_requests,
                "failed_requests": self._data.failed_requests,
                "success_rate": (
                    round(self._data.successful_requests / self._data.total_requests * 100, 2)
                    if self._data.total_requests > 0
                    else 0.0
                ),
                "avg_latency_ms": round(avg_latency_ms, 2),
                "errors_by_type": dict(self._data.errors_by_type),
                "requests_by_endpoint": dict(self._data.requests_by_endpoint),
                "status_codes": dict(self._data.status_codes),
            }
    
    def reset(self):
        """Reset all metrics (useful for testing)"""
        with self._lock:
            self._data = MetricsData()


# Global metrics tracker instance
metrics_tracker = MetricsTracker()
