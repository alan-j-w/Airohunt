import time
from typing import Dict, Any, List

class ProviderMetric:
    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.total_requests = 0
        self.success_count = 0
        self.error_count = 0
        self.total_latency_ms = 0.0
        self.min_latency_ms = float('inf')
        self.max_latency_ms = 0.0

    def record_request(self, duration_ms: float, success: bool):
        self.total_requests += 1
        if success:
            self.success_count += 1
        else:
            self.error_count += 1

        self.total_latency_ms += duration_ms
        if duration_ms < self.min_latency_ms:
            self.min_latency_ms = duration_ms
        if duration_ms > self.max_latency_ms:
            self.max_latency_ms = duration_ms

    def to_dict(self) -> Dict[str, Any]:
        avg_latency = round(self.total_latency_ms / self.total_requests, 2) if self.total_requests > 0 else 0.0
        error_rate = round((self.error_count / self.total_requests) * 100.0, 2) if self.total_requests > 0 else 0.0
        return {
            "provider": self.provider_name,
            "total_requests": self.total_requests,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "error_rate_pct": error_rate,
            "avg_latency_ms": avg_latency,
            "min_latency_ms": round(self.min_latency_ms, 2) if self.min_latency_ms != float('inf') else 0.0,
            "max_latency_ms": round(self.max_latency_ms, 2)
        }

class MetricsCollector:
    """Metrics collector tracking latency, throughput, and error rates per job source."""
    def __init__(self):
        self._metrics: Dict[str, ProviderMetric] = {}

    def record_provider_latency(self, provider_name: str, duration_ms: float, success: bool = True):
        if provider_name not in self._metrics:
            self._metrics[provider_name] = ProviderMetric(provider_name)
        self._metrics[provider_name].record_request(duration_ms, success)

    def get_summary(self) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in self._metrics.values()]

global_metrics_collector = MetricsCollector()
