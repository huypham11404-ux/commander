"""3-Tier Permission and Policy Engine."""
from enum import Enum
from typing import Dict, Any, Set
from commander.protocol.schema import CommanderError, ErrorCode

class PermissionLevel(str, Enum):
    READ_ONLY = "READ_ONLY"
    PROPOSED_CHANGE = "PROPOSED_CHANGE"
    DIRECT_EDIT = "DIRECT_EDIT"

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    DESTRUCTIVE = "DESTRUCTIVE"

class PermissionPolicyEngine:
    def __init__(self, default_level: PermissionLevel = PermissionLevel.READ_ONLY):
        self.current_level = default_level
        self.approved_requests: Set[str] = set()

    def set_permission_level(self, level: PermissionLevel):
        self.current_level = level

    def approve_proposal(self, proposal_id: str):
        self.approved_requests.add(proposal_id)

    def authorize_execution(self, tool_name: str, risk: RiskLevel, proposal_id: str = None) -> bool:
        """Evaluate if an action is permitted under the current mode and risk level."""
        # 1. READ_ONLY blocks all mutative tools
        if self.current_level == PermissionLevel.READ_ONLY:
            if risk != RiskLevel.LOW:
                raise CommanderError(
                    ErrorCode.PERMISSION_DENIED,
                    f"Action '{tool_name}' (Risk: {risk.value}) is blocked in READ_ONLY mode."
                )
            return True

        # 2. PROPOSED_CHANGE requires explicit user approval
        if self.current_level == PermissionLevel.PROPOSED_CHANGE:
            if risk == RiskLevel.LOW:
                return True
            if proposal_id and proposal_id in self.approved_requests:
                return True
            raise CommanderError(
                ErrorCode.PERMISSION_DENIED,
                f"Action '{tool_name}' requires explicit user approval under PROPOSED_CHANGE mode."
            )

        # 3. DIRECT_EDIT allows low/medium/high, but DESTRUCTIVE always requires explicit confirmation
        if self.current_level == PermissionLevel.DIRECT_EDIT:
            if risk == RiskLevel.DESTRUCTIVE:
                if proposal_id and proposal_id in self.approved_requests:
                    return True
                raise CommanderError(
                    ErrorCode.PERMISSION_DENIED,
                    f"Destructive action '{tool_name}' requires explicit approval even in DIRECT_EDIT mode."
                )
            return True

        return False
