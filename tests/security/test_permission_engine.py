import pytest
from commander.security import PermissionPolicyEngine, PermissionLevel, RiskLevel
from commander.protocol.schema import CommanderError, ErrorCode

def test_permission_tier_transitions():
    engine = PermissionPolicyEngine(PermissionLevel.READ_ONLY)
    # Low risk is always permitted
    assert engine.authorize_execution("inspect_project", RiskLevel.LOW) is True

    # Mutative blocked in READ_ONLY
    with pytest.raises(CommanderError) as exc:
        engine.authorize_execution("add_track", RiskLevel.MEDIUM)
    assert exc.value.code == ErrorCode.PERMISSION_DENIED

    # Switch to PROPOSED_CHANGE
    engine.set_permission_level(PermissionLevel.PROPOSED_CHANGE)
    with pytest.raises(CommanderError):
        engine.authorize_execution("add_track", RiskLevel.MEDIUM)

    # Approve
    engine.approve_proposal("proposal_01")
    assert engine.authorize_execution("add_track", RiskLevel.MEDIUM, proposal_id="proposal_01") is True

    # Switch to DIRECT_EDIT
    engine.set_permission_level(PermissionLevel.DIRECT_EDIT)
    assert engine.authorize_execution("add_track", RiskLevel.MEDIUM) is True
    # Destructive still requires approval
    with pytest.raises(CommanderError):
        engine.authorize_execution("wipe_project", RiskLevel.DESTRUCTIVE)
