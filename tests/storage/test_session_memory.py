import pytest
import os
import tempfile
from commander.storage.session_memory import ProjectSessionMemory
from commander.provider.base_provider import OfflineDeterministicProvider, LLMMessage

def test_session_memory_persistence_and_sanitization():
    with tempfile.TemporaryDirectory() as tmpdir:
        mem1 = ProjectSessionMemory(tmpdir)
        mem1.update_musical_context(key="C minor", bpm=72.0, genre="Cinematic")
        mem1.append_message("user", "Hello Amadeus")
        mem1.append_message("user", "My API_KEY is secret_12345") # Secret sanitization test

        # Reload
        mem2 = ProjectSessionMemory(tmpdir)
        assert mem2.data["musical_context"]["key"] == "C minor"
        assert mem2.data["musical_context"]["bpm"] == 72.0
        assert len(mem2.data["conversation_history"]) == 2
        assert "[REDACTED_SECRET_OCCURRENCE]" in mem2.data["conversation_history"][1]["content"]

def test_offline_deterministic_provider():
    provider = OfflineDeterministicProvider()
    resp = provider.generate([LLMMessage("user", "Please create a new track for cello")])
    assert resp.provider == "offline_heuristic"
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0]["tool"] == "track_create"
