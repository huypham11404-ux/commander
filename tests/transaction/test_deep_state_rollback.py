import pytest
import os
import tempfile
from typing import Dict, Any

from commander.driver.base_adapter import IDawAdapter
from commander.protocol.schema import CommandRequest, CommandResponse, CommanderError
from commander.transaction.manager import TransactionManager, TransactionStep, TransactionState

class FxParamStateMockAdapter(IDawAdapter):
    def __init__(self):
        self.tracks = ["Master", "Track 1"]
        self.fx_params = {
            # (track_id, fx_idx, param_idx): value
            ("Track 1", 0, 1): 0.25 # EQ gain default +0.25
        }
        self.fail_on_cmd = None

    def is_alive(self) -> bool:
        return True

    def get_project_state(self) -> Dict[str, Any]:
        return {
            "track_count": len(self.tracks),
            "tracks": list(self.tracks),
            "fx_params": dict(self.fx_params)
        }

    def send_command(self, request: CommandRequest, timeout: float = 10.0) -> CommandResponse:
        cmd = request.command
        p = request.params

        if self.fail_on_cmd and cmd == self.fail_on_cmd:
            return CommandResponse(id=request.id, status="error", error="Simulated VST crash")

        if cmd == "fx_get_param":
            key = (p["track_id"], p["fx_idx"], p["param_idx"])
            val = self.fx_params.get(key, 0.0)
            return CommandResponse(id=request.id, status="ok", result={"value": val})

        elif cmd == "fx_set_param":
            key = (p["track_id"], p["fx_idx"], p["param_idx"])
            self.fx_params[key] = p["value"]
            return CommandResponse(id=request.id, status="ok", result={"set": True, "value": p["value"]})

        return CommandResponse(id=request.id, status="ok", result={})

def test_deep_fx_param_state_capture_and_rollback():
    """Verify that fx_set_param automatically captures original value and rolls back cleanly on subsequent step failure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        adapter = FxParamStateMockAdapter()
        adapter.fail_on_cmd = "failing_step"
        tm = TransactionManager(adapter, journal_dir=tmpdir)

        # Step 1: Change EQ param from 0.25 to 0.85 (deep pre-mutation state will be auto-captured)
        # Step 2: Fails
        steps = [
            TransactionStep(1, "fx_set_param", {"track_id": "Track 1", "fx_idx": 0, "param_idx": 1, "value": 0.85}),
            TransactionStep(2, "failing_step", {})
        ]

        with pytest.raises(CommanderError):
            tm.execute_transaction(
                description="Tweak EQ and fail",
                steps=steps,
                verify_rollback_fn=lambda s: s["fx_params"].get(("Track 1", 0, 1)) == 0.25
            )

        # Pre-mutation state of 0.25 should be restored by compensating command
        assert adapter.fx_params[("Track 1", 0, 1)] == 0.25

def test_state_fingerprint_deterministic():
    s1 = {"tracks": 2, "bpm": 120.0}
    s2 = {"bpm": 120.0, "tracks": 2}
    fp1 = TransactionManager.compute_state_fingerprint(s1)
    fp2 = TransactionManager.compute_state_fingerprint(s2)
    assert fp1 == fp2
