"""Standalone MIDI Parser and Melodic Feature Extractor using pretty_midi and mido."""
import os
import pretty_midi
from typing import Dict, Any, List

class MidiAnalyzer:
    @staticmethod
    def parse_midi(filepath: str) -> Dict[str, Any]:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"MIDI file not found: {filepath}")

        pm = pretty_midi.PrettyMIDI(filepath)
        total_time = pm.get_end_time()

        tracks_info = []
        all_notes = []
        for i, inst in enumerate(pm.instruments):
            track_notes = []
            for n in inst.notes:
                track_notes.append({
                    "pitch": n.pitch,
                    "name": pretty_midi.note_number_to_name(n.pitch),
                    "start": round(n.start, 3),
                    "end": round(n.end, 3),
                    "duration": round(n.end - n.start, 3),
                    "velocity": n.velocity
                })
                all_notes.append(n.pitch)

            tracks_info.append({
                "track_index": i,
                "name": inst.name or f"Track {i}",
                "program": inst.program,
                "is_drum": inst.is_drum,
                "note_count": len(track_notes),
                "notes": track_notes
            })

        min_pitch = min(all_notes) if all_notes else None
        max_pitch = max(all_notes) if all_notes else None

        return {
            "duration_sec": round(total_time, 2),
            "track_count": len(pm.instruments),
            "tracks": tracks_info,
            "overall_pitch_range": {
                "min_pitch": min_pitch,
                "max_pitch": max_pitch,
                "min_name": pretty_midi.note_number_to_name(min_pitch) if min_pitch else None,
                "max_name": pretty_midi.note_number_to_name(max_pitch) if max_pitch else None
            }
        }
