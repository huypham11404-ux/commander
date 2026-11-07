# C++ DAW INTEGRATION & PROTOCOL SPECIFICATION
## AI Music Production Commander

### 1. Architectural Overview
The AI Music Production Commander connects to our independently developed C++ DAW as an autonomous AI agent over local socket IPC (default port: `9988`).

```
┌────────────────────────────────────────────────────────┐
│      AI Music Production Commander (Python 3.12)       │
│  [Intent Planner]  [Music Intelligence]  [Permissions] │
└───────────────────────────┬────────────────────────────┘
                            │ Local Socket IPC (JSON-RPC)
                            │ 4-byte length prefix
┌───────────────────────────▼────────────────────────────┐
│         Independent C++ DAW (Audio Engine & GUI)       │
│  [Tracks]  [Clips]  [MIDI Notes]  [SineToneSynth]      │
└────────────────────────────────────────────────────────┘
```

### 2. Supported DAW Protocol Operations
1. `ping`: Verify DAW is running and responsive.
2. `project.get_state`: Query current tempo, tracks, clips, and playback status.
3. `track.create`: Create a track and assign an instrument (e.g. `SineToneSynth`).
4. `track.rename`: Rename an existing track.
5. `transport.set_tempo`: Set BPM and time signature numerator/denominator.
6. `clip.create`: Create a MIDI clip on a specific track with start beat and duration.
7. `notes.insert_batch`: Insert or update a list of notes (`{pitch, start_beat, duration_beats, velocity}`).
8. `transport.play` / `transport.stop`: Control real-time audio playback.
9. `project.save`: Persist the DAW project to disk.

### 3. Demonstration Workflow
To execute the live demonstration workflow:
```bash
# In Terminal 1: Launch C++ DAW with IPC socket enabled on port 9988
./daw --ipc-port 9988

# In Terminal 2: Run Commander demo workflow
python scripts/demo_cpp_daw_workflow.py --port 9988
```
Workflow execution:
1. Connects to C++ DAW.
2. Submits prompt: *"Create a gentle nursery music arrangement with a simple melody, soft accompaniment, and a moderate tempo."*
3. Generates 2 tracks (`Nursery Melody` and `Soft Accompaniment`), creates clips, inserts MIDI notes, and sets tempo to 84 BPM.
4. Triggers playback in the C++ DAW.
5. Issues follow-up modification: transposes melody up an octave and softens velocity.
