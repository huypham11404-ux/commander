"""Tool Registry managing validated tool schemas and execution."""
from dataclasses import dataclass, field
from typing import Dict, Any, Callable, Optional
from commander.agent.permissions import RiskLevel
from commander.protocol.schema import CommanderError, ErrorCode

@dataclass
class ToolDefinition:
    name: str
    version: str
    description: str
    risk_level: RiskLevel
    idempotent: bool
    handler: Callable[[Dict[str, Any]], Dict[str, Any]]
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register_tool(self, tool: ToolDefinition):
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered.")
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> ToolDefinition:
        if name not in self._tools:
            raise CommanderError(ErrorCode.INVALID_PARAMS, f"Tool '{name}' is not registered.")
        return self._tools[name]

    def list_tools(self) -> Dict[str, Dict[str, Any]]:
        return {
            name: {
                "name": t.name,
                "version": t.version,
                "description": t.description,
                "risk_level": t.risk_level.value,
                "idempotent": t.idempotent
            }
            for name, t in self._tools.items()
        }

    def execute_tool(self, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        tool = self.get_tool(name)
        # Basic validation against input_schema required keys
        req_keys = tool.input_schema.get("required", [])
        for k in req_keys:
            if k not in params:
                raise CommanderError(ErrorCode.INVALID_PARAMS, f"Missing required parameter: '{k}' for tool '{name}'")
        return tool.handler(params)
