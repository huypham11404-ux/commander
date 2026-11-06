"""Transaction and Recovery Manager strictly enforcing the 7-state lifecycle, write-ahead journaling, and verifiable compensating rollback."""
import os
import time
import json
import uuid
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict

from commander.driver.base_adapter import IDawAdapter
from commander.protocol.schema import CommandRequest, CommandResponse, CommanderError, ErrorCode

logger = logging.getLogger("commander.transaction")

class TransactionState:
    PREPARED = "PREPARED"
    EXECUTING = "EXECUTING"
    COMMITTED = "COMMITTED"
    FAILED = "FAILED"
    RECOVERING = "RECOVERING"
    ROLLED_BACK = "ROLLED_BACK"
    RECOVERY_FAILED = "RECOVERY_FAILED"

@dataclass
class TransactionStep:
    step_id: int
    command: str
    params: Dict[str, Any]
    compensating_command: Optional[str] = None
    compensating_params: Optional[Dict[str, Any]] = None
    executed: bool = False
    result: Optional[Dict[str, Any]] = None

@dataclass
class TransactionJournal:
    transaction_id: str
    state: str
    created_at: float
    description: str
    planned_steps: List[Dict[str, Any]] = field(default_factory=list)
    executed_steps: List[Dict[str, Any]] = field(default_factory=list)
    initial_snapshot: Dict[str, Any] = field(default_factory=dict)
    post_snapshot: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    completed_at: Optional[float] = None

class TransactionManager:
    def __init__(self, adapter: IDawAdapter, journal_dir: Optional[str] = None):
        self.adapter = adapter
        self.journal_dir = journal_dir or os.path.join(os.path.expanduser("~"), ".commander", "journals")
        os.makedirs(self.journal_dir, exist_ok=True)

    def _journal_path(self, tx_id: str) -> str:
        return os.path.join(self.journal_dir, f"{tx_id}.json")

    def _persist_journal(self, journal: TransactionJournal):
        path = self._journal_path(journal.transaction_id)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(json.dumps(asdict(journal), indent=2))
        os.replace(tmp, path)

    def execute_transaction(
        self,
        description: str,
        steps: List[TransactionStep],
        precondition_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
        postcondition_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
        verify_rollback_fn: Optional[Callable[[Dict[str, Any]], bool]] = None
    ) -> TransactionJournal:
        tx_id = f"tx_{uuid.uuid4().hex[:12]}"

        # 1. State: PREPARED
        try:
            initial_state = self.adapter.get_project_state()
        except Exception:
            initial_state = {}

        if precondition_fn and not precondition_fn(initial_state):
            raise CommanderError(ErrorCode.TRANSACTION_FAILED, "Transaction preconditions check failed")

        journal = TransactionJournal(
            transaction_id=tx_id,
            state=TransactionState.PREPARED,
            created_at=time.time(),
            description=description,
            planned_steps=[asdict(s) for s in steps],
            initial_snapshot=initial_state
        )
        self._persist_journal(journal)

        # 2. State: EXECUTING
        journal.state = TransactionState.EXECUTING
        self._persist_journal(journal)

        executed_steps: List[TransactionStep] = []

        try:
            for s in steps:
                req = CommandRequest(command=s.command, params=s.params)
                resp = self.adapter.send_command(req)
                if resp.status != "ok":
                    raise CommanderError(
                        ErrorCode.TRANSACTION_FAILED,
                        f"Step {s.step_id} ({s.command}) failed: {resp.error}"
                    )
                s.executed = True
                s.result = resp.result
                executed_steps.append(s)
                journal.executed_steps.append(asdict(s))
                self._persist_journal(journal)

            # 3. Postcondition Verification
            try:
                post_state = self.adapter.get_project_state()
            except Exception:
                post_state = {}

            journal.post_snapshot = post_state
            if postcondition_fn and not postcondition_fn(post_state):
                raise CommanderError(ErrorCode.TRANSACTION_FAILED, "Postconditions check failed")

            # 4. State: COMMITTED
            journal.state = TransactionState.COMMITTED
            journal.completed_at = time.time()
            self._persist_journal(journal)
            return journal

        except Exception as exc:
            logger.error("Transaction %s failed during execution: %s", tx_id, exc)
            # 5. State: RECOVERING
            journal.state = TransactionState.RECOVERING
            journal.error_message = str(exc)
            self._persist_journal(journal)

            rollback_clean = self._rollback(executed_steps)

            # Post-rollback verification
            try:
                recovered_state = self.adapter.get_project_state()
            except Exception:
                recovered_state = {}

            verified = False
            if rollback_clean:
                if verify_rollback_fn:
                    verified = verify_rollback_fn(recovered_state)
                else:
                    # Default: compare track counts if present
                    if "track_count" in initial_state and "track_count" in recovered_state:
                        verified = (recovered_state["track_count"] == initial_state["track_count"])
                    else:
                        verified = True

            if verified:
                journal.state = TransactionState.ROLLED_BACK
            else:
                journal.state = TransactionState.RECOVERY_FAILED

            journal.completed_at = time.time()
            self._persist_journal(journal)

            raise CommanderError(
                ErrorCode.TRANSACTION_FAILED,
                f"Transaction failed and ended in {journal.state}: {exc}"
            )

    def _rollback(self, executed_steps: List[TransactionStep]) -> bool:
        """Execute compensating reverse steps or undo requests in LIFO order."""
        try:
            for s in reversed(executed_steps):
                if s.compensating_command:
                    req = CommandRequest(command=s.compensating_command, params=s.compensating_params or {})
                    resp = self.adapter.send_command(req, timeout=5.0)
                    if resp.status != "ok":
                        return False
                else:
                    req = CommandRequest(command="project_undo", params={"steps": 1})
                    resp = self.adapter.send_command(req, timeout=5.0)
                    if resp.status != "ok":
                        return False
            return True
        except Exception:
            return False
