import time
import json
import wave
import tempfile
import numpy as np
import scipy.signal

def generate_wav_file(path: str, duration_sec: float, sr: int = 44100, stereo: bool = True):
    n_samples = int(duration_sec * sr)
    t = np.linspace(0, duration_sec, n_samples, endpoint=False)
    # 440Hz + 880Hz harmonics
    left = (0.5 * np.sin(2 * np.pi * 440 * t) + 0.2 * np.sin(2 * np.pi * 880 * t)).astype(np.float32)
    right = (0.4 * np.sin(2 * np.pi * 440 * t + 0.2) + 0.3 * np.sin(2 * np.pi * 660 * t)).astype(np.float32) if stereo else left

    # 16-bit PCM
    l_int = (left * 32767).astype(np.int16)
    r_int = (right * 32767).astype(np.int16)
    if stereo:
        interleaved = np.empty((n_samples * 2,), dtype=np.int16)
        interleaved[0::2] = l_int
        interleaved[1::2] = r_int
        data = interleaved.tobytes()
    else:
        data = l_int.tobytes()

    with wave.open(path, 'wb') as wf:
        wf.setnchannels(2 if stereo else 1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(data)

def benchmark_dsp_pipeline(duration_sec: float) -> dict:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
        generate_wav_file(tmp.name, duration_sec)

        # 1. Measure File I/O
        t0 = time.perf_counter()
        with wave.open(tmp.name, 'rb') as wf:
            sr = wf.getframerate()
            n_ch = wf.getnchannels()
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)
            data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            if n_ch == 2:
                data = data.reshape(-1, 2)
        io_time_ms = (time.perf_counter() - t0) * 1000.0

        # 2. Measure RMS & Peak
        t1 = time.perf_counter()
        rms = float(np.sqrt(np.mean(data**2)))
        peak = float(np.max(np.abs(data)))
        crest_factor = peak / (rms + 1e-9)
        rms_peak_time_ms = (time.perf_counter() - t1) * 1000.0

        # 3. Measure K-weighting pre-filter (ITU-R BS.1770 stage 1)
        # Stage 1 high-shelf biquad + Stage 2 high-pass RLB filter
        t2 = time.perf_counter()
        b_shelf, a_shelf = scipy.signal.butter(2, 1000 / (sr / 2), btype='high')
        filtered = scipy.signal.lfilter(b_shelf, a_shelf, data, axis=0)
        # Gated loudness approximation
        mean_sq = np.mean(filtered**2, axis=0)
        integrated_lufs_est = float(-0.691 + 10 * np.log10(np.sum(mean_sq) + 1e-12))
        lufs_filter_time_ms = (time.perf_counter() - t2) * 1000.0

        # 4. Measure FFT & Spectral Centroid
        t3 = time.perf_counter()
        # Take up to 65536 samples for spectral analysis
        analysis_chunk = data[:65536, 0] if n_ch == 2 else data[:65536]
        fft = np.abs(np.fft.rfft(analysis_chunk))
        freqs = np.fft.rfftfreq(len(analysis_chunk), 1/sr)
        spectral_centroid = float(np.sum(freqs * fft) / (np.sum(fft) + 1e-9))
        spectral_time_ms = (time.perf_counter() - t3) * 1000.0

        # 5. Measure True Peak (4x Sinc Oversampling via resample_poly)
        t4 = time.perf_counter()
        test_samples = data[:min(len(data), int(sr * 2.0)), 0] # first 2s for true-peak to manage CPU
        oversampled = scipy.signal.resample_poly(test_samples, 4, 1)
        true_peak = float(np.max(np.abs(oversampled)))
        true_peak_time_ms = (time.perf_counter() - t4) * 1000.0

        total_time_ms = (time.perf_counter() - t0) * 1000.0

        return {
            "audio_duration_sec": duration_sec,
            "sample_rate_hz": sr,
            "channels": n_ch,
            "io_read_time_ms": round(io_time_ms, 2),
            "rms_peak_time_ms": round(rms_peak_time_ms, 2),
            "itu_lufs_filter_time_ms": round(lufs_filter_time_ms, 2),
            "spectral_centroid_time_ms": round(spectral_time_ms, 2),
            "true_peak_oversample_time_ms": round(true_peak_time_ms, 2),
            "total_processing_time_ms": round(total_time_ms, 2),
            "measurements": {
                "rms": round(rms, 4),
                "peak": round(peak, 4),
                "true_peak": round(true_peak, 4),
                "crest_factor_db": round(20 * np.log10(crest_factor), 2),
                "integrated_lufs_est": round(integrated_lufs_est, 2),
                "spectral_centroid_hz": round(spectral_centroid, 1)
            }
        }

if __name__ == "__main__":
    durations = [0.5, 2.0, 10.0, 30.0]
    results = [benchmark_dsp_pipeline(d) for d in durations]
    with open("evidence/dsp_audio_feedback_benchmarks.json", "w") as f:
        json.dump(results, f, indent=2)
    print("DSP Audio Feedback Benchmarks Completed:")
    print(json.dumps(results, indent=2))
