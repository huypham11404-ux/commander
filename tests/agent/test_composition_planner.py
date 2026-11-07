import pytest
from commander.agent.composition_planner import CompositionPlanner

def test_composition_planner_nursery_music():
    prompt = "Create a gentle nursery music arrangement with a simple melody, soft accompaniment, and a moderate tempo."
    plan = CompositionPlanner.plan_from_prompt(prompt)

    assert plan.tempo_bpm == 84.0
    assert plan.time_signature == (4, 4)
    assert len(plan.tracks) == 2

    # Track 1: Melody
    melody_track = plan.tracks[0]
    assert melody_track["name"] == "Nursery Melody"
    assert len(melody_track["notes"]) > 5

    # Track 2: Accompaniment
    accomp_track = plan.tracks[1]
    assert accomp_track["name"] == "Soft Accompaniment"
    assert len(accomp_track["notes"]) > 5

def test_modify_melody_plan():
    initial_notes = [{"pitch": 60, "start_beat": 0.0, "duration_beats": 1.0, "velocity": 70}]
    # Transpose up
    transposed = CompositionPlanner.modify_melody_plan(initial_notes, variation_type="higher_octave")
    assert transposed[0]["pitch"] == 72

    # Softer
    softer = CompositionPlanner.modify_melody_plan(initial_notes, variation_type="softer")
    assert softer[0]["velocity"] == 55
