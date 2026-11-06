"""LLM Provider Abstraction supporting offline deterministic mode and cloud endpoints."""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class LLMMessage:
    role: str # "system", "user", "assistant"
    content: str

@dataclass
class LLMResponse:
    content: str
    tool_calls: List[Dict[str, Any]]
    usage: Dict[str, int]
    provider: str
    model: str

class ILLMProvider(ABC):
    @abstractmethod
    def generate(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2
    ) -> LLMResponse:
        pass

class OfflineDeterministicProvider(ILLMProvider):
    """Fallback offline deterministic provider that uses rule heuristics when no cloud LLM is connected."""
    def generate(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2
    ) -> LLMResponse:
        user_msg = next((m.content for m in reversed(messages) if m.role == "user"), "")
        content = "Offline rule-based processing: "
        tool_calls = []

        if "track" in user_msg.lower():
            tool_calls.append({
                "tool": "track_create",
                "params": {"name": "New Track"}
            })
            content += "Planned track creation."
        else:
            content += "Analyzed prompt locally."

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            usage={"total_tokens": 10},
            provider="offline_heuristic",
            model="rule_v1"
        )
