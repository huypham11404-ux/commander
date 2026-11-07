import pytest
from commander.runtime.resource_monitor import ResourceMonitor

def test_resource_monitor_metrics():
    monitor = ResourceMonitor(warning_threshold_mb=100.0)
    m = monitor.get_current_metrics()
    assert m["process_rss_mb"] > 0
    assert m["system_total_mb"] > 0
    assert m["system_available_mb"] > 0
    assert isinstance(m["is_memory_under_pressure"], bool)
