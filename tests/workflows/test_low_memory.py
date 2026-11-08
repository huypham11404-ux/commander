import pytest
from commander.runtime.resource_monitor import ResourceMonitor

def test_low_memory_footprint():
    """Verify that Commander runtime operates safely within 8GB target machine budget."""
    monitor = ResourceMonitor(warning_threshold_mb=1200.0)
    metrics = monitor.get_current_metrics()
    # Process RSS should be well under 120MB for core operations
    assert metrics["process_rss_mb"] < 150.0
