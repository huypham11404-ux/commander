"""Demonstration Workflow: AI Music Production Commander controlling C++ DAW.
Steps demonstrated:
1. Connect Commander to C++ DAW.
2. Prompt: 'Create a gentle nursery music arrangement with a simple melody, soft accompaniment, and a moderate tempo.'
3. Generate and verify tracks, clips, notes, and instruments inside DAW.
4. Start playback.
5. Prompt: 'Make the melody softer and transpose it up an octave.'
6. Update DAW clip notes and re-verify playback state.
"""
import sys
import time
import argparse
from commander.driver.cpp_daw_adapter import CppDawAdapter
from commander.agent.composition_planner import CompositionPlanner

def run_demo(host: str = "127.0.0.1", port: int = 9988):
    print("=" * 70)
    print("AI MUSIC PRODUCTION COMMANDER -> C++ DAW DEMONSTRATION WORKFLOW")
    print("=" * 70)

    adapter = CppDawAdapter(host=host, port=port)
    print(f"[*] Step 1: Connecting to C++ DAW at {host}:{port}...")
    if not adapter.connect():
        print(f"[!] Could not connect to C++ DAW. Please ensure the C++ DAW is running with socket server on port {port}.")
        sys.exit(1)

    print("[+] Successfully connected to C++ DAW.")
    initial_state = adapter.get_project_state()
    print(f"[*] Initial DAW state: {initial_state}")

    # Step 2: Natural Language Prompt
    user_prompt = "Create a gentle nursery music arrangement with a simple melody, soft accompaniment, and a moderate tempo."
    print(f"\n[*] Step 2: User Prompt: \"{user_prompt}\"")
    plan = CompositionPlanner.plan_from_prompt(user_prompt)
    print(f"[+] AI Composition Plan: {plan.description} (Tempo: {plan.tempo_bpm} BPM, Time: 4/4)")

    # Step 3: Execute Plan in C++ DAW
    print("\n[*] Step 3: Executing plan in C++ DAW...")
    adapter.set_tempo_and_meter(bpm=plan.tempo_bpm, numerator=4, denominator=4)
    created_clips = []

    for trk_info in plan.tracks:
        print(f"    -> Creating track '{trk_info['name']}' with instrument '{trk_info['instrument']}'...")
        t_res = adapter.create_track(name=trk_info["name"], instrument=trk_info["instrument"])
        track_id = t_res.get("id", 1)

        print(f"    -> Creating clip '{trk_info['clip_name']}' on track {track_id}...")
        clip_res = adapter.create_midi_clip(
            track_id=track_id,
            start_beat=trk_info["start_beat"],
            length_beats=trk_info["length_beats"],
            name=trk_info["clip_name"]
        )
        clip_id = clip_res.get("id", 1)
        created_clips.append((clip_id, trk_info["notes"]))

        print(f"    -> Inserting {len(trk_info['notes'])} MIDI notes into clip {clip_id}...")
        adapter.insert_notes(clip_id=clip_id, notes=trk_info["notes"])

    # Step 4: Verify Project State
    updated_state = adapter.get_project_state()
    print(f"\n[+] Verified C++ DAW state after composition: {updated_state}")

    # Step 5: Start Playback
    print("\n[*] Step 4: Starting playback in C++ DAW...")
    adapter.transport_play()
    time.sleep(1.0)
    print("    [Playing composition in C++ DAW...]")
    adapter.transport_stop()
    print("    [Stopped playback.]")

    # Step 6: Follow-up instruction
    followup_prompt = "Make the melody softer and transpose it up an octave."
    print(f"\n[*] Step 5: Follow-up instruction: \"{followup_prompt}\"")
    melody_clip_id, melody_notes = created_clips[0]
    modified_notes = CompositionPlanner.modify_melody_plan(melody_notes, variation_type="higher_octave")
    modified_notes = CompositionPlanner.modify_melody_plan(modified_notes, variation_type="softer")

    print(f"    -> Updating clip {melody_clip_id} with {len(modified_notes)} modified notes...")
    adapter.insert_notes(clip_id=melody_clip_id, notes=modified_notes)

    final_state = adapter.get_project_state()
    print(f"[+] Final DAW Project State: {final_state}")
    print("\n[***] DEMONSTRATION WORKFLOW COMPLETED SUCCESSFULLY.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9988)
    args = parser.parse_args()
    run_demo(args.host, args.port)
