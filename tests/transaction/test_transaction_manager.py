import pytest
import os
import json
import tempfile
from typing import Dict, Any

from commander.driver.base_adapter import IDawAdapter
from commander.protocol.schema import CommandRequest, CommandResponse, CommanderError
from commander.transaction.manager import TransactionManager, TransactionStep, TransactionState

class MockMemoryAdapter(IDawAdapter):
    def __init__(self):
        self.tracks = []
        self.fail_on_command = None
        self.sent_commands = []

    def is_alive(self) -> bool:
        return True

    def get_project_state(self) -> Dict[str, Any]:
        return {"track_count": len(self.tracks), "tracks": list(self.tracks)}

    def send_command(self, request: CommandRequest, timeout: float = 10.0) -> CommandResponse:
        self.sent_commands.append(request.command)
        if self.fail_on_command and request.command == self.fail_on_command:
            return CommandResponse(id=request.id, status="error", error="Simulated failure in mock")

        if request.command == "track_create":
            name = request.params.get("name", "Unnamed")
            self.tracks.append(name)
            return CommandResponse(id=request.id, status="ok", result={"track_index": len(self.tracks)-1})
        elif request.command == "track_delete":
            name = request.params.get("name")
            if name in self.tracks:
                self.tracks.remove(name)
            return CommandResponse(id=request.id, status="ok", result={"deleted": True})
        elif request.command == "project_undo":
            if self.tracks:
                self.tracks.pop()
            return CommandResponse(id=request.id, status="ok", result={"undone": True})

        return CommandResponse(id=request.id, status="ok", result={"ack": request.command})

def test_transaction_success_commit():
    with tempfile.TemporaryDirectory() as tmpdir:
        adapter = MockMemoryAdapter()
        tm = TransactionManager(adapter, journal_dir=tmpdir)

        steps = [
            TransactionStep(1, "track_create", {"name": "Kick"}, "track_delete", {"name": "Kick"}),
            TransactionStep(2, "track_create", {"name": "Snare"}, "track_delete", {"name": "Snare"}),
            TransactionStep(3, "track_create", {"name": "HiHat"}, "track_delete", {"name": "HiHat"}),
        ]

        journal = tm.execute_transaction(
            description="Add Drum Kit",
            steps=steps,
            postcondition_fn=lambda s: s["track_count"] == 3
        )

        assert journal.state == TransactionState.COMMITTED
        assert len(adapter.tracks) == 3
        assert os.path.exists(tm._journal_path(journal.transaction_id))

def test_transaction_partial_failure_compensating_rollback():
    """Verify that failing step 3 triggers compensating rollback for steps 1 and 2."""
    with tempfile.TemporaryDirectory() as tmpdir:
        adapter = MockMemoryAdapter()
        adapter.fail_on_command = "faulty_cmd"
        tm = TransactionManager(adapter, journal_dir=tmpdir)

        steps = [
            TransactionStep(1, "track_create", {"name": "Kick"}, "track_delete", {"name": "Kick"}),
            TransactionStep(2, "track_create", {"name": "Snare"}, "track_delete", {"name": "Snare"}),
            TransactionStep(3, "faulty_cmd", {}, "noop", {}),
            TransactionStep(4, "track_create", {"name": "Bass"}, "track_delete", {"name": "Bass"}),
        ]

        with pytest.raises(CommanderError):
            tm.execute_transaction(description="Faulty Batch", steps=steps)

        # Confirm rollback cleared state back to 0 tracks
        assert len(adapter.tracks) == 0
        assert "track_delete" in adapter.sent_commands
