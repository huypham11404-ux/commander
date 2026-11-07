"""Resource Monitor and Safeguards tracking process memory and preventing system RAM exhaustion."""
import os
import psutil
from typing import Dict, Any

class ResourceMonitor:
    def __init__(self, warning_threshold_mb: float = 1200.0):
        self.process = psutil.Process(os.getpid())
        self.warning_threshold_mb = warning_threshold_mb # System available RAM warning threshold

    def get_current_metrics(self) -> Dict[str, Any]:
        """Obtain objective current process memory and system memory statistics."""
        mem_info = self.process.memory_info()
        vm = psutil.virtual_memory()

        process_rss_mb = round(mem_info.rss / (1024 * 1024), 2)
        system_available_mb = round(vm.available / (1024 * 1024), 2)
        system_total_mb = round(vm.total / (1024 * 1024), 2)

        is_under_pressure = (system_available_mb < self.warning_threshold_mb)

        return {
            "process_rss_mb": process_rss_mb,
            "system_total_mb": system_total_mb,
            "system_available_mb": system_available_mb,
            "is_memory_under_pressure": is_under_pressure,
            "warning": "System RAM low! Consider closing heavy sample libraries." if is_under_pressure else "Normal"
        }
