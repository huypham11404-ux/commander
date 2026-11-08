# COMMANDER WORKFLOW CAPABILITY AUDIT & T01–T10 MATRIX

**Date:** 2026-11-06
**Auditor:** Commander Integration & Workflow Engineer
**Target Hardware:** Intel Core i3-1115G4, 8GB RAM, Windows x64
**References:** TwelveTake REAPER MCP (MIT) & Reaper Daemon (MIT)

---

## 1. CAPABILITY AUDIT MATRIX (T01–T10)

| Test ID | Benchmark Operation | Capability Status | Implementation Mapping | Verification Strategy |
| :--- | :--- | :--- | :--- | :--- |
| **T01** | Read Project Summary | **EXISTING** | `IDawAdapter.get_project_state()` | State: bpm, track_count, tracks, playhead |
| **T02** | Inspect Tracks, FX Chains, Params | **PARTIAL $\rightarrow$ FULL** | `fx_get_param`, `track_get_info` | State: track names, FX list, param ranges |
| **T03** | Inspect Transport & State | **EXISTING** | `transport_get_state`, `is_playing` | State: playhead cursor, loop range, playing state |
| **T04** | Humanize MIDI across 16 bars | **PARTIAL $\rightarrow$ FULL** | `WorkflowRecipes.humanize_midi` | Signal/Data: timing jitter ($\le 15\text{ ticks}$), velocity deviation |
| **T05** | Create Reverb Send & Routing | **PARTIAL $\rightarrow$ FULL** | `WorkflowRecipes.setup_reverb_send` | State & Signal: aux track created, VST loaded, send level confirmed |
| **T06** | Modify Exposed FX Parameter | **EXISTING** | `fx_set_param` with pre-state capture | State: parameter value updated and confirmed |
| **T07** | Freeze / Unfreeze Track | **PARTIAL $\rightarrow$ FULL** | `WorkflowRecipes.track_freeze_toggle` | State: track render replace & stem mute |
| **T08** | Intentionally Invalid Op Rollback | **EXISTING** | `TransactionManager` + fingerprinting | State: compensating rollback restored initial state |
| **T09** | Compare Audio/DSP Measurements | **EXISTING** | `DspAnalyzer` (BS.1770-4, Peak, RMS) | Signal: Delta spectrum, True Peak, Crest Factor |
| **T10** | Persistence, Undo, Disconnect Recovery| **EXISTING** | `ProjectSessionMemory` & Driver reconnect | State: session reload, corrupted recovery |
