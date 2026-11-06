"""Commander Protocol v1.0 schema definitions and constants."""
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
import time
import uuid

PROTOCOL_VERSION = "1.0"

class ErrorCode:
    UNKNOWN = "UNKNOWN"
    TIMEOUT = "TIMEOUT"
    COMMUNICATION_ERROR = "COMMUNICATION_ERROR"
    INVALID_PARAMS = "INVALID_PARAMS"
    REAPER_NOT_RUNNING = "REAPER_NOT_RUNNING"
    TRANSACTION_FAILED = "TRANSACTION_FAILED"
    PERMISSION_DENIED = "PERMISSION_DENIED"

class CommanderError(Exception):
    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message
        self.details = details or {}

@dataclass
class CommandRequest:
    command: str
    params: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    protocol_version: str = PROTOCOL_VERSION
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class CommandResponse:
    id: str
    status: str # "ok" or "error"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    protocol_version: str = PROTOCOL_VERSION
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
