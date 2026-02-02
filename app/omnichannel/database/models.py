"""Data models for DynamoDB tables"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from enum import Enum


class UserTier(str, Enum):
    """User tier enumeration"""
    UNVERIFIED = "unverified"
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class PaymentStatus(str, Enum):
    """Payment status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TRIAL = "trial"


@dataclass
class User:
    """User model"""
    email: str
    tier: UserTier = UserTier.FREE
    created_at: str = None
    updated_at: str = None
    telegram_id: Optional[int] = None
    usage_month: int = 0
    usage_total: int = 0
    payment_status: PaymentStatus = PaymentStatus.ACTIVE
    trial_ends_at: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_dynamodb(self) -> Dict[str, Any]:
        """Convert to DynamoDB format"""
        data = asdict(self)
        data['tier'] = self.tier.value
        data['payment_status'] = self.payment_status.value
        return data

    @classmethod
    def from_dynamodb(cls, data: Dict[str, Any]) -> 'User':
        """Convert from DynamoDB format"""
        # Filter to only known User fields
        known_fields = {
            'email', 'tier', 'created_at', 'updated_at', 'telegram_id',
            'usage_month', 'usage_total', 'payment_status', 'trial_ends_at'
        }
        filtered_data = {k: v for k, v in data.items() if k in known_fields}
        
        # Convert enum fields
        filtered_data['tier'] = UserTier(filtered_data.get('tier', 'free'))
        filtered_data['payment_status'] = PaymentStatus(filtered_data.get('payment_status', 'active'))
        
        return cls(**filtered_data)


@dataclass
class Session:
    """Session model"""
    email: str
    session_id: str
    authenticated: bool = True
    created_at: str = None
    expires_at: str = None
    active_channels: List[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.active_channels is None:
            self.active_channels = []

    def to_dynamodb(self) -> Dict[str, Any]:
        """Convert to DynamoDB format"""
        return asdict(self)

    @classmethod
    def from_dynamodb(cls, data: Dict[str, Any]) -> 'Session':
        """Convert from DynamoDB format"""
        return cls(**data)


@dataclass
class Memory:
    """Memory/Context model"""
    email: str
    domain: str
    context: Dict[str, Any] = None
    updated_at: str = None

    def __post_init__(self):
        if self.context is None:
            self.context = {}
        if self.updated_at is None:
            self.updated_at = datetime.utcnow().isoformat()

    def to_dynamodb(self) -> Dict[str, Any]:
        """Convert to DynamoDB format"""
        return asdict(self)

    @classmethod
    def from_dynamodb(cls, data: Dict[str, Any]) -> 'Memory':
        """Convert from DynamoDB format"""
        return cls(**data)


@dataclass
class Usage:
    """Usage/Billing model"""
    email: str
    year: int
    month: int
    message_count: int = 0
    tier: UserTier = UserTier.FREE
    reset_at: Optional[str] = None

    def to_dynamodb(self) -> Dict[str, Any]:
        """Convert to DynamoDB format"""
        data = asdict(self)
        data['tier'] = self.tier.value
        # Create composite sort key matching DynamoDB schema (String)
        # Using zero-padding for correct lexical sorting
        data['month'] = f"{self.year}#{self.month:02d}"
        return data

    @classmethod
    def from_dynamodb(cls, data: Dict[str, Any]) -> 'Usage':
        """Convert from DynamoDB format"""
        data['tier'] = UserTier(data.get('tier', 'free'))
        
        # Parse composite month string back to integer if necessary
        # The Usage dataclass expects month to be an int
        if isinstance(data.get('month'), str) and '#' in data['month']:
            try:
                # Format "YYYY#MM" -> extract MM
                _, month_str = data['month'].split('#')
                data['month'] = int(month_str)
            except (ValueError, IndexError):
                # Fallback or keep as is if parsing fails (shouldn't happen with correct data)
                pass
                
        return cls(**data)


@dataclass
class AuditLog:
    """Audit log model"""
    email: str
    timestamp: str
    action_id: str
    agent: str
    action: str
    input_data: Dict[str, Any] = None
    output_data: Dict[str, Any] = None
    context: Dict[str, Any] = None
    status: str = "success"

    def __post_init__(self):
        if self.input_data is None:
            self.input_data = {}
        if self.output_data is None:
            self.output_data = {}
        if self.context is None:
            self.context = {}

    def to_dynamodb(self) -> Dict[str, Any]:
        """Convert to DynamoDB format"""
        return asdict(self)

    @classmethod
    def from_dynamodb(cls, data: Dict[str, Any]) -> 'AuditLog':
        """Convert from DynamoDB format"""
        return cls(**data)


@dataclass
class Escalation:
    """Escalation model for H.I.T.L."""
    escalation_id: str
    email: str
    created_at: str
    decision_type: str
    context: Dict[str, Any] = None
    human_decision: Optional[str] = None
    resolved_at: Optional[str] = None

    def __post_init__(self):
        if self.context is None:
            self.context = {}

    def to_dynamodb(self) -> Dict[str, Any]:
        """Convert to DynamoDB format"""
        return asdict(self)

    @classmethod
    def from_dynamodb(cls, data: Dict[str, Any]) -> 'Escalation':
        """Convert from DynamoDB format"""
        return cls(**data)
