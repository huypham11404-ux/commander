# TRANSACTION AND RECOVERY DESIGN SPECIFICATION
## Subsystem Priority: P0 Data Integrity

### 1. State Machine
A Commander transaction transitions through explicit states:
- `PREPARED`: Preconditions verified, snapshot recorded, transaction journal written to disk.
- `EXECUTING`: Sub-commands dispatched through `IDawAdapter`.
- `COMMITTED`: Postconditions verified against DAW state, transaction marked successful.
- `FAILED`: Failure detected at step K (timeout, API error, precondition mismatch).
- `RECOVERING`: Rollback initiated (calling `project_undo(steps=K-1)` or compensating actions).
- `ROLLED_BACK`: Project state confirmed reverted to pre-transaction snapshot.
- `RECOVERY_FAILED`: Rollback could not verify initial state. Alert raised to user.

### 2. Journal Schema
Every transaction persists:
```json
{
  "transaction_id": "tx_uuid",
  "state": "PREPARED",
  "created_at": 1799283741.12,
  "pre_state": {"tracks": 4, "bpm": 72.0},
  "planned_steps": [
    {"step_id": 1, "action": "track_create", "params": {"name": "Violin I"}},
    {"step_id": 2, "action": "midi_insert", "params": {"track_index": 4}}
  ],
  "executed_steps": [],
  "post_state": null
}
```
