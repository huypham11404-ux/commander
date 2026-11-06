# MUSIC INTELLIGENCE SPECIFICATION
## Subsystem: Music Intelligence & Harmony Context Engine

### 1. Requirements
1. **MIDI Parsing:** Track, note, velocity, tick, meter, and contour extraction.
2. **Key & Scale Estimation:** Evaluate root pitch, diatonic profile, and secondary tonal centers.
3. **Harmony Context Engine (Anti-Misclassification):**
   - Detect modal interchange (e.g. borrowed iv, bVI in Major).
   - Recognize secondary dominants (e.g. V/V).
   - Inversion analysis (figured bass / slash chords).
   - Suspensions (sus2, sus4) and non-chord tone passing resolution.
4. **Voice Leading Guardrails:**
   - Pairwise parallel fifths / octaves detection.
   - Hidden (direct) fifths/octaves with soprano leap.
   - Voice crossing detection.
   - Style-aware tolerance (classical counterpoint vs modern modal pop/rock).
