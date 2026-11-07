"""Composition Planner interpreting natural language music production requests into structured DAW execution plans."""
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

@dataclass
class ArrangementPlan:
    tempo_bpm: float
    time_signature: tuple[int, int]
    genre_style: str
    tracks: List[Dict[str, Any]] = field(default_factory=list)
    description: str = ""

class CompositionPlanner:
    """Interprets requests like 'Create a gentle nursery music arrangement with a simple melody, soft accompaniment, and a moderate tempo'."""

    @staticmethod
    def plan_from_prompt(prompt: str) -> ArrangementPlan:
        prompt_lower = prompt.lower()

        # 1. Detect tempo & mood
        if "nursery" in prompt_lower or "lullaby" in prompt_lower or "gentle" in prompt_lower:
            bpm = 84.0
            genre = "Nursery / Lullaby"
            melody_instrument = "SineToneSynth"
            accomp_instrument = "SineToneSynth"

            # Simple 8-bar nursery melody (Twinkle/Brahms style pentatonic in C Major)
            # C4 (60), D4 (62), E4 (64), G4 (67), A4 (69), C5 (72)
            melody_notes = [
                {"pitch": 72, "start_beat": 0.0, "duration_beats": 1.0, "velocity": 70}, # C5
                {"pitch": 72, "start_beat": 1.0, "duration_beats": 1.0, "velocity": 70}, # C5
                {"pitch": 79, "start_beat": 2.0, "duration_beats": 1.0, "velocity": 72}, # G5
                {"pitch": 79, "start_beat": 3.0, "duration_beats": 1.0, "velocity": 72}, # G5
                {"pitch": 81, "start_beat": 4.0, "duration_beats": 1.0, "velocity": 74}, # A5
                {"pitch": 81, "start_beat": 5.0, "duration_beats": 1.0, "velocity": 74}, # A5
                {"pitch": 79, "start_beat": 6.0, "duration_beats": 2.0, "velocity": 68}, # G5
                {"pitch": 77, "start_beat": 8.0, "duration_beats": 1.0, "velocity": 70}, # F5
                {"pitch": 77, "start_beat": 9.0, "duration_beats": 1.0, "velocity": 70}, # F5
                {"pitch": 76, "start_beat": 10.0, "duration_beats": 1.0, "velocity": 68}, # E5
                {"pitch": 76, "start_beat": 11.0, "duration_beats": 1.0, "velocity": 68}, # E5
                {"pitch": 74, "start_beat": 12.0, "duration_beats": 1.0, "velocity": 66}, # D5
                {"pitch": 74, "start_beat": 13.0, "duration_beats": 1.0, "velocity": 66}, # D5
                {"pitch": 72, "start_beat": 14.0, "duration_beats": 2.0, "velocity": 65}, # C5
            ]

            # Soft gentle accompaniment (arpeggiated dyads: C-E, F-A, G-B)
            accomp_notes = [
                # Bar 1-2 (C Major): C3, G3, E4, G3
                {"pitch": 48, "start_beat": 0.0, "duration_beats": 2.0, "velocity": 55},
                {"pitch": 55, "start_beat": 1.0, "duration_beats": 1.0, "velocity": 50},
                {"pitch": 64, "start_beat": 2.0, "duration_beats": 2.0, "velocity": 52},
                {"pitch": 55, "start_beat": 3.0, "duration_beats": 1.0, "velocity": 48},
                # Bar 3-4 (F / C): F3, A3, C4
                {"pitch": 53, "start_beat": 4.0, "duration_beats": 2.0, "velocity": 55},
                {"pitch": 57, "start_beat": 5.0, "duration_beats": 1.0, "velocity": 50},
                {"pitch": 48, "start_beat": 6.0, "duration_beats": 2.0, "velocity": 52},
                # Bar 5-6 (G / C): G3, B3, C4
                {"pitch": 55, "start_beat": 8.0, "duration_beats": 2.0, "velocity": 50},
                {"pitch": 59, "start_beat": 10.0, "duration_beats": 2.0, "velocity": 50},
                {"pitch": 48, "start_beat": 12.0, "duration_beats": 4.0, "velocity": 48},
            ]

        else:
            # Default pop / ambient progression
            bpm = 100.0
            genre = "General"
            melody_instrument = "SineToneSynth"
            accomp_instrument = "SineToneSynth"
            melody_notes = [
                {"pitch": 60, "start_beat": 0.0, "duration_beats": 2.0, "velocity": 80},
                {"pitch": 64, "start_beat": 2.0, "duration_beats": 2.0, "velocity": 80},
                {"pitch": 67, "start_beat": 4.0, "duration_beats": 4.0, "velocity": 85}
            ]
            accomp_notes = [
                {"pitch": 48, "start_beat": 0.0, "duration_beats": 4.0, "velocity": 60},
                {"pitch": 52, "start_beat": 4.0, "duration_beats": 4.0, "velocity": 60}
            ]

        tracks = [
            {
                "name": "Nursery Melody",
                "instrument": melody_instrument,
                "clip_name": "Lead Melody",
                "start_beat": 0.0,
                "length_beats": 16.0,
                "notes": melody_notes
            },
            {
                "name": "Soft Accompaniment",
                "instrument": accomp_instrument,
                "clip_name": "Chords / Arpeggio",
                "start_beat": 0.0,
                "length_beats": 16.0,
                "notes": accomp_notes
            }
        ]

        return ArrangementPlan(
            tempo_bpm=bpm,
            time_signature=(4, 4),
            genre_style=genre,
            tracks=tracks,
            description=f"Generated {genre} arrangement with {len(tracks)} tracks and {len(melody_notes) + len(accomp_notes)} notes."
        )

    @staticmethod
    def modify_melody_plan(existing_notes: List[Dict[str, Any]], variation_type: str = "ornament") -> List[Dict[str, Any]]:
        """Modify existing melody notes (e.g. adding passing notes or transposing up an octave)."""
        modified = []
        for n in existing_notes:
            note_copy = dict(n)
            if variation_type == "higher_octave":
                note_copy["pitch"] += 12
            elif variation_type == "softer":
                note_copy["velocity"] = max(20, note_copy["velocity"] - 15)
            elif variation_type == "staccato":
                note_copy["duration_beats"] = min(0.5, note_copy["duration_beats"] * 0.5)
            modified.append(note_copy)
        return modified
