import pytest
from commander.intelligence.harmony_engine import HarmonyContextEngine

def test_instrument_range_validator():
    # Cello range is C2 (36) to E5 (76)
    # C2 (36) is in range
    res_valid = HarmonyContextEngine.validate_instrument_range("Cello", ["C2", "G3", "C4"])
    assert res_valid["valid"] is True

    # C1 (24) is below range, C6 (84) is above range
    res_invalid = HarmonyContextEngine.validate_instrument_range("Cello", ["C1", "C6"])
    assert res_invalid["valid"] is False
    assert len(res_invalid["out_of_range_notes"]) == 2

def test_motion_types_classification():
    engine = HarmonyContextEngine()
    # Contrary motion
    res = engine.check_voice_leading(["C4", "B3"], ["E4", "F4"])
    assert "CONTRARY" in res["motion_types"]
    assert res["is_clean"] is True
