import pytest
import os
import tempfile
from commander.memory import ProjectSessionMemory

def test_session_corrupted_file_recovery():
    with tempfile.TemporaryDirectory() as tmpdir:
        session_file = os.path.join(tmpdir, "commander_session.json")
        # Write corrupted garbage
        with open(session_file, "w") as f:
            f.write("{ invalid json corrupted!#$@ ")

        # Loading corrupted session should not crash, but reset to clean session defaults
        mem = ProjectSessionMemory(tmpdir)
        assert mem.data["version"] == "1.0"
        assert len(mem.data["conversation_history"]) == 0

        # Can cleanly write new data
        mem.update_musical_context(key="D major")
        assert os.path.exists(session_file)
