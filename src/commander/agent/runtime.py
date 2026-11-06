"""Core Hierarchical Agent Runtime coordinating intent decomposition, permissions, and tool execution."""
import logging
from typing import Dict, Any, List, Optional
from commander.agent.permissions import PermissionPolicyEngine, PermissionLevel, RiskLevel
from commander.agent.tool_registry import ToolRegistry, ToolDefinition
from commander.transaction.manager import TransactionManager, TransactionStep
from commander.protocol.schema import CommanderError, ErrorCode

logger = logging.getLogger("commander.agent.runtime")

class AgentRuntime:
    def __init__(
        self,
        tool_registry: ToolRegistry,
        policy_engine: PermissionPolicyEngine,
        transaction_mgr: Optional[TransactionManager] = None
    ):
        self.tool_registry = tool_registry
        self.policy = policy_engine
        self.tx_mgr = transaction_mgr

    def execute_plan_step(self, tool_name: str, params: Dict[str, Any], proposal_id: Optional[str] = None) -> Dict[str, Any]:
        """Authorize and execute a single tool step."""
        tool = self.tool_registry.get_tool(tool_name)
        # 1. Authorize against permission policy
        self.policy.authorize_execution(tool.name, tool.risk_level, proposal_id=proposal_id)
        # 2. Execute tool
        return self.tool_registry.execute_tool(tool_name, params)

    def execute_atomic_batch(
        self,
        description: str,
        steps: List[Dict[str, Any]],
        proposal_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Authorize batch and execute inside TransactionManager with compensating rollback."""
        # Pre-authorize all steps
        for s in steps:
            tool = self.tool_registry.get_tool(s["tool"])
            self.policy.authorize_execution(tool.name, tool.risk_level, proposal_id=proposal_id)

        if not self.tx_mgr:
            raise CommanderError(ErrorCode.TRANSACTION_FAILED, "Transaction Manager not configured for atomic batch execution.")

        tx_steps = [
            TransactionStep(
                step_id=i+1,
                command=s["tool"],
                params=s.get("params", {}),
                compensating_command=s.get("compensating_tool"),
                compensating_params=s.get("compensating_params")
            )
            for i, s in enumerate(steps)
        ]

        journal = self.tx_mgr.execute_transaction(description=description, steps=tx_steps)
        return {
            "transaction_id": journal.transaction_id,
            "state": journal.state,
            "steps_executed": len(journal.executed_steps)
        }
