import os
import sys
import time
import json
import psutil

process = psutil.Process(os.getpid())

def get_mem_mb():
    return process.memory_info().rss / (1024 * 1024)

m_base = get_mem_mb()

# 1. Base Python
t0 = time.perf_counter()
import mido
m_after_mido = get_mem_mb()

import pretty_midi
m_after_pretty_midi = get_mem_mb()

import numpy as np
m_after_numpy = get_mem_mb()

import scipy
m_after_scipy = get_mem_mb()

import music21
m_after_music21 = get_mem_mb()

# 2. Heavy Operation: Parse MIDI and Analyze Chords
midi_score = music21.converter.parse("experiments/sample_progression.mid")
_ = midi_score.analyze('key')
_ = midi_score.chordify()
m_after_analysis = get_mem_mb()

# 3. DSP on 30s Audio Buffer
sr = 44100
dur = 30.0
sig = np.random.randn(int(sr * dur)).astype(np.float32)
fft = np.abs(np.fft.rfft(sig))
rms = np.sqrt(np.mean(sig**2))
m_after_dsp = get_mem_mb()

report = {
    "platform": sys.platform,
    "measurements_mb": {
        "python_base_rss": round(m_base, 2),
        "after_mido_rss": round(m_after_mido, 2),
        "after_pretty_midi_rss": round(m_after_pretty_midi, 2),
        "after_numpy_rss": round(m_after_numpy, 2),
        "after_scipy_rss": round(m_after_scipy, 2),
        "after_music21_rss": round(m_after_music21, 2),
        "after_midi_key_chord_analysis_rss": round(m_after_analysis, 2),
        "after_30s_dsp_rss": round(m_after_dsp, 2),
        "delta_music21_import_mb": round(m_after_music21 - m_after_scipy, 2),
        "total_python_process_rss_mb": round(m_after_dsp, 2)
    }
}

with open("evidence/measured_memory_profile.json", "w") as f:
    json.dump(report, f, indent=2)

print(json.dumps(report, indent=2))
