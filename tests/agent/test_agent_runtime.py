import pytest
from commander.agent.permissions import PermissionPolicyEngine, PermissionLevel, RiskLevel
from commander.agent.tool_registry import ToolRegistry, ToolDefinition
from commander.agent.runtime import AgentRuntime
from commander.protocol.schema import CommanderError, ErrorCode

def test_permissions_gatekeeper():
    policy = PermissionPolicyEngine(PermissionLevel.READ_ONLY)
    registry = ToolRegistry()

    # Register tools
    registry.register_tool(ToolDefinition(
        name="read_project",
        version="1.0",
        description="Inspect project",
        risk_level=RiskLevel.LOW,
        idempotent=True,
        handler=lambda p: {"status": "read_ok"}
    ))
    registry.register_tool(ToolDefinition(
        name="delete_track",
        version="1.0",
        description="Delete a track",
        risk_level=RiskLevel.DESTRUCTIVE,
        idempotent=False,
        handler=lambda p: {"status": "deleted"}
    ))

    runtime = AgentRuntime(registry, policy)

    # 1. READ_ONLY allows LOW risk
    res = runtime.execute_plan_step("read_project", {})
    assert res["status"] == "read_ok"

    # 2. READ_ONLY blocks DESTRUCTIVE
    with pytest.raises(CommanderError) as exc_info:
        runtime.execute_plan_step("delete_track", {"track": 1})
    assert exc_info.value.code == ErrorCode.PERMISSION_DENIED

    # 3. Switch to PROPOSED_CHANGE without approval
    policy.set_permission_level(PermissionLevel.PROPOSED_CHANGE)
    with pytest.raises(CommanderError):
        runtime.execute_plan_step("delete_track", {"track": 1})

    # 4. Approve proposal
    policy.approve_proposal("prop_123")
    res_approved = runtime.execute_plan_step("delete_track", {"track": 1}, proposal_id="prop_123")
    assert res_approved["status"] == "deleted"
