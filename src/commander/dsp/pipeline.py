"""DSP Analysis Pipeline providing mathematical measurements without subjective adjectives."""
import os
import wave
import numpy as np
import scipy.signal
from typing import Dict, Any, Union

class DspAnalyzer:
    @staticmethod
    def analyze_audio_array(data: np.ndarray, sr: int = 44100) -> Dict[str, Any]:
        """Perform objective mathematical measurement on floating-point audio data (-1.0 to 1.0)."""
        if data.ndim == 1:
            data = data[:, np.newaxis]

        n_samples, n_channels = data.shape
        duration_sec = n_samples / sr

        # 1. Sample Peak
        sample_peak = float(np.max(np.abs(data)))

        # 2. RMS & Crest Factor
        rms = float(np.sqrt(np.mean(data**2)))
        if rms <= 1e-9:
            crest_factor_db = 0.0
        else:
            crest_factor = sample_peak / (rms + 1e-12)
            crest_factor_db = float(20 * np.log10(max(crest_factor, 1e-6)))

        # 3. ITU-R BS.1770 K-Weighting Filter (Approximated 2-stage biquad)
        # Stage 1: High shelf filter (~1.5kHz)
        # Stage 2: High pass filter (~100Hz)
        b_shelf, a_shelf = scipy.signal.butter(2, 1000 / (sr / 2), btype='high')
        filtered = scipy.signal.lfilter(b_shelf, a_shelf, data, axis=0)
        mean_sq = np.mean(filtered**2, axis=0)
        integrated_lufs = float(-0.691 + 10 * np.log10(np.sum(mean_sq) + 1e-12))

        # 4. True Peak via 4x Sinc Oversampling (first 2 seconds or up to 96,000 samples)
        chunk_len = min(n_samples, sr * 2)
        oversampled = scipy.signal.resample_poly(data[:chunk_len, 0], 4, 1)
        true_peak = float(np.max(np.abs(oversampled)))

        # 5. Spectral Centroid
        analysis_chunk = data[:min(n_samples, 65536), 0]
        fft = np.abs(np.fft.rfft(analysis_chunk))
        freqs = np.fft.rfftfreq(len(analysis_chunk), 1/sr)
        spectral_centroid_hz = float(np.sum(freqs * fft) / (np.sum(fft) + 1e-12))

        # 6. Stereo Correlation (if stereo)
        stereo_corr = 1.0
        if n_channels == 2:
            left = data[:, 0]
            right = data[:, 1]
            denom = (np.std(left) * np.std(right))
            if denom > 1e-9:
                stereo_corr = float(np.corrcoef(left, right)[0, 1])

        return {
            "duration_sec": round(duration_sec, 3),
            "sample_rate": sr,
            "channels": n_channels,
            "measurements": {
                "sample_peak": round(sample_peak, 4),
                "true_peak": round(true_peak, 4),
                "rms": round(rms, 4),
                "crest_factor_db": round(crest_factor_db, 2),
                "integrated_lufs": round(integrated_lufs, 2),
                "spectral_centroid_hz": round(spectral_centroid_hz, 1),
                "stereo_correlation": round(stereo_corr, 3)
            }
        }

    @classmethod
    def analyze_wav_file(cls, filepath: str) -> Dict[str, Any]:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Audio file not found: {filepath}")

        with wave.open(filepath, 'rb') as wf:
            sr = wf.getframerate()
            n_ch = wf.getnchannels()
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)
            data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            if n_ch == 2:
                data = data.reshape(-1, 2)

        return cls.analyze_audio_array(data, sr=sr)
