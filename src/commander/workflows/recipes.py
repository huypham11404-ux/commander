"""Workflow Recipes composing high-level DAW operations into reusable multi-step production routines."""
import random
import copy
from typing import Dict, Any, List, Optional
from commander.driver.base_adapter import IDawAdapter
from commander.protocol.schema import CommandRequest, CommanderError, ErrorCode

class WorkflowRecipes:
    """Reusable multi-step music production workflows (inspired by TwelveTake and Reaper Daemon practices)."""

    @staticmethod
    def humanize_midi(
        notes: List[Dict[str, Any]],
        timing_jitter_beats: float = 0.02, # ~10-15 ticks
        velocity_range: int = 6,          # +/- 6 velocity
        swing_ratio: float = 0.0          # Optional swing ratio on off-beats
    ) -> List[Dict[str, Any]]:
        """Humanize MIDI notes by applying controlled non-destructive timing jitter, velocity variance, and swing."""
        humanized = []
        for n in notes:
            note_copy = copy.deepcopy(n)

            # Apply velocity jitter bounded to 1-127
            v_delta = random.randint(-velocity_range, velocity_range)
            note_copy["velocity"] = max(1, min(127, note_copy.get("velocity", 80) + v_delta))

            # Apply timing jitter
            t_delta = random.uniform(-timing_jitter_beats, timing_jitter_beats)
            new_start = max(0.0, note_copy.get("start_beat", 0.0) + t_delta)

            # Apply swing to off-beats (e.g. beat fractional >= 0.5)
            beat_frac = new_start - int(new_start)
            if swing_ratio > 0.0 and abs(beat_frac - 0.5) < 0.2:
                new_start += swing_ratio * 0.08

            note_copy["start_beat"] = round(new_start, 4)
            humanized.append(note_copy)
        return humanized

    @staticmethod
    def guitar_strum(
        chord_pitches: List[int],
        start_beat: float,
        duration_beats: float,
        strum_speed_beats: float = 0.03, # ~25-30ms per string
        direction: str = "down",         # "down" or "up"
        base_velocity: int = 85
    ) -> List[Dict[str, Any]]:
        """Generate a realistic guitar chord strum with staggered string onsets and dynamic velocity decay."""
        sorted_pitches = sorted(chord_pitches) if direction == "down" else sorted(chord_pitches, reverse=True)
        strummed_notes = []

        for i, pitch in enumerate(sorted_pitches):
            offset = i * strum_speed_beats
            # Downstroke dynamics: top strings often hit slightly softer than bass strike
            v_decay = int(i * 2.5) if direction == "down" else int((len(sorted_pitches) - 1 - i) * 2.0)
            velocity = max(30, min(127, base_velocity - v_decay + random.randint(-3, 3)))

            strummed_notes.append({
                "pitch": pitch,
                "start_beat": round(start_beat + offset, 4),
                "duration_beats": round(max(0.1, duration_beats - offset), 4),
                "velocity": velocity
            })
        return strummed_notes

    @staticmethod
    def setup_reverb_send(
        adapter: IDawAdapter,
        source_track_id: Any,
        reverb_name: str = "Reverb Aux",
        send_level_db: float = -12.0
    ) -> Dict[str, Any]:
        """Workflow: Create FX Aux track -> Add Reverb -> Create routing send -> Set send level."""
        # 1. Create Aux track
        req_track = CommandRequest(command="track.create", params={"name": reverb_name})
        res_track = adapter.send_command(req_track)
        if res_track.status != "ok":
            raise CommanderError(ErrorCode.TRANSACTION_FAILED, f"Failed to create reverb aux track: {res_track.error}")
        aux_id = res_track.result.get("id", res_track.result.get("track_id", 1))

        # 2. Add Reverb plugin to Aux
        req_fx = CommandRequest(command="fx.add", params={"track_id": aux_id, "plugin": "Reverberate"})
        res_fx = adapter.send_command(req_fx)

        # 3. Setup Send Routing from source to aux
        req_send = CommandRequest(command="routing.create_send", params={
            "source_track_id": source_track_id,
            "dest_track_id": aux_id,
            "send_level_db": send_level_db,
            "mode": "post_fader"
        })
        res_send = adapter.send_command(req_send)

        return {
            "status": "ok",
            "aux_track_id": aux_id,
            "source_track_id": source_track_id,
            "send_level_db": send_level_db,
            "routing_confirmed": res_send.status == "ok"
        }

    @staticmethod
    def setup_parallel_compression(
        adapter: IDawAdapter,
        source_track_ids: List[Any],
        bus_name: str = "Parallel Drum Crush",
        compressor_plugin: str = "Compressor"
    ) -> Dict[str, Any]:
        """Workflow: Create Bus Track -> Add aggressive Compressor -> Route multiple stems into bus."""
        # 1. Create Parallel Bus
        req_bus = CommandRequest(command="track.create", params={"name": bus_name})
        res_bus = adapter.send_command(req_bus)
        bus_id = res_bus.result.get("id", res_bus.result.get("track_id", 1))

        # 2. Add Compressor
        req_fx = CommandRequest(command="fx.add", params={"track_id": bus_id, "plugin": compressor_plugin})
        adapter.send_command(req_fx)

        # 3. Route all source tracks into parallel bus
        routed_sources = []
        for src_id in source_track_ids:
            req_send = CommandRequest(command="routing.create_send", params={
                "source_track_id": src_id,
                "dest_track_id": bus_id,
                "send_level_db": 0.0
            })
            r = adapter.send_command(req_send)
            if r.status == "ok":
                routed_sources.append(src_id)

        return {
            "status": "ok",
            "bus_track_id": bus_id,
            "routed_source_count": len(routed_sources),
            "sources": routed_sources
        }

    @staticmethod
    def setup_sidechain_routing(
        adapter: IDawAdapter,
        trigger_track_id: Any, # e.g. Kick
        target_track_id: Any,  # e.g. Bass
        target_fx_idx: int = 0
    ) -> Dict[str, Any]:
        """Workflow: Route trigger track (Kick) into target track (Bass) auxiliary channels (3/4) for sidechain ducking."""
        req = CommandRequest(command="routing.create_sidechain", params={
            "trigger_track_id": trigger_track_id,
            "target_track_id": target_track_id,
            "src_channels": [1, 2],
            "dest_channels": [3, 4], # Channels 3/4 detector
            "target_fx_idx": target_fx_idx
        })
        res = adapter.send_command(req)
        return {
            "status": "ok" if res.status == "ok" else "error",
            "trigger": trigger_track_id,
            "target": target_track_id,
            "detector_channels": [3, 4]
        }
