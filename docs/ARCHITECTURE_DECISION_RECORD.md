# ARCHITECTURE DECISION RECORD (ADR)
## AI Music Production Commander

**Status:** ACCEPTED & FROZEN
**Date:** 2026-11-06
**Context:** Transitioning AI Music Production Commander from Research & Red-Team Audit to autonomous software engineering implementation.

---

### Decision 1: Single Hierarchical Agent vs Multi-Agent
- **Decision:** Adopt a **Single Hierarchical Agent with Specialized Tools**.
- **Rationale:** Red-team audit and latency benchmarks confirmed multi-agent architectures introduce 5-20s latency overhead, token multiplication, and fragmented state. The single agent decomposes high-level intent, executes deterministic pre-flight checks, and invokes validated tools sequentially.

### Decision 2: DAW Integration & IPC Mechanism
- **Decision:** Use an **Abstract DAW Adapter (`IDawAdapter`)** with a **File-based Atomic Swap REAPER Driver** for REAPER on Windows.
- **Rationale:** Raw filesystem swap (`os.replace` via `MoveFileExW` on NTFS) guarantees zero-port-conflict and cross-process safety via OS-level mutex (`msvcrt.locking` on Windows, `fcntl.flock` on POSIX).
- **Caveat:** Distinguish raw IPC latency (~0.26ms) from REAPER execution latency (15-33ms bounded by REAPER's `defer()` tick).

### Decision 3: Transaction & Recovery Model
- **Decision:** Implement **Client-side Transaction & Recovery Management** with a persistent write-ahead journal and explicit state machine.
- **Rationale:** Red-team findings showed REAPER Lua drops open undo blocks across defer ticks, so `undo_group` only labels steps and cannot collapse multi-step actions into a single `Ctrl+Z`. On partial failure, the client-side recovery manager issues compensating reverse actions or calls `project_undo_group`.

### Decision 4: Music Intelligence Dual-Layering
- **Decision:** Combine `music21` with a custom **Harmony Context Engine**.
- **Rationale:** Stock `music21` Krumhansl-Schmuckler fails on modal interchange (borrowed chords) and produces pairwise voice leading false positives. The Harmony Context Engine evaluates chromatic passing chords, inversions, and tonal center heuristics.

### Decision 5: Objective DSP Pipeline
- **Decision:** Dedicated offline DSP pipeline implementing ITU-R BS.1770 K-weighting LUFS, sample peak, 4x sinc true-peak oversampling, RMS, crest factor, and spectral centroid.
- **Rationale:** Complete separation between mathematical measurements and subjective mix interpretations.

### Decision 6: 3-Tier Permission & Zero Arbitrary Shell Execution
- **Decision:** Strict enforcement of `READ_ONLY`, `PROPOSED_CHANGE`, and `DIRECT_EDIT` tiers.
- **Rationale:** LLMs are strictly forbidden from executing arbitrary shell commands or modifying state outside registered tool schemas.
