"""Abstract base adapter defining DAW contract (IDawAdapter)."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from commander.protocol.schema import CommandRequest, CommandResponse

class IDawAdapter(ABC):
    @abstractmethod
    def send_command(self, request: CommandRequest, timeout: float = 10.0) -> CommandResponse:
        """Send a single atomic command to the DAW and wait for response."""
        pass

    @abstractmethod
    def is_alive(self) -> bool:
        """Check if DAW engine is currently active and responding to heartbeats."""
        pass

    @abstractmethod
    def get_project_state(self) -> Dict[str, Any]:
        """Fetch snapshot of active project (tracks, bpm, markers, playhead)."""
        pass
