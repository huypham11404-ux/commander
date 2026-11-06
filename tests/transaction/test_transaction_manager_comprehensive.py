import pytest
import os
import tempfile
from typing import Dict, Any

from commander.driver.base_adapter import IDawAdapter
from commander.protocol.schema import CommandRequest, CommandResponse, CommanderError
from commander.transaction.manager import TransactionManager, TransactionStep, TransactionState

class StateTrackingMockAdapter(IDawAdapter):
    def __init__(self):
        self.tracks = []
        self.fail_on_step = None
        self.fail_rollback = False

    def is_alive(self) -> bool:
        return True

    def get_project_state(self) -> Dict[str, Any]:
        return {"track_count": len(self.tracks), "tracks": list(self.tracks)}

    def send_command(self, request: CommandRequest, timeout: float = 10.0) -> CommandResponse:
        cmd = request.command
        params = request.params

        if self.fail_on_step and cmd == self.fail_on_step:
            return CommandResponse(id=request.id, status="error", error="Simulated mid-flight crash")

        if self.fail_rollback and cmd == "compensating_delete":
            return CommandResponse(id=request.id, status="error", error="Compensating delete failed")

        if cmd == "create_track":
            name = params.get("name", "Trk")
            self.tracks.append(name)
            return CommandResponse(id=request.id, status="ok", result={"id": len(self.tracks)})
        elif cmd == "compensating_delete":
            name = params.get("name")
            if name in self.tracks:
                self.tracks.remove(name)
            return CommandResponse(id=request.id, status="ok", result={"deleted": True})

        return CommandResponse(id=request.id, status="ok", result={})

def test_transaction_recovery_failed_state():
    """Verify that if compensating rollback fails, state transitions to RECOVERY_FAILED."""
    with tempfile.TemporaryDirectory() as tmpdir:
        adapter = StateTrackingMockAdapter()
        adapter.fail_on_step = "crash_now"
        adapter.fail_rollback = True
        tm = TransactionManager(adapter, journal_dir=tmpdir)

        steps = [
            TransactionStep(1, "create_track", {"name": "T1"}, "compensating_delete", {"name": "T1"}),
            TransactionStep(2, "crash_now", {}, "noop", {})
        ]

        with pytest.raises(CommanderError) as exc_info:
            tm.execute_transaction("Failing Batch", steps=steps)

        assert "RECOVERY_FAILED" in str(exc_info.value)
        # Read journal from disk
        journals = os.listdir(tmpdir)
        assert len(journals) == 1
        with open(os.path.join(tmpdir, journals[0])) as f:
            data = f.read()
        assert TransactionState.RECOVERY_FAILED in data
