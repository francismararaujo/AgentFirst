"""Limit Enforcer - Enforces usage limits and prevents overages"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from app.config.settings import settings
from app.billing.usage_tracker import UsageTracker, UsageTrackerConfig


@dataclass
class LimitExceededError(Exception):
    """Exception raised when usage limit is exceeded"""
    email: str
    tier: str
    current_usage: int
    limit: int
    remaining: int
    upgrade_url: Optional[str] = None

    def __str__(self) -> str:
        """Return user-friendly error message"""
        if self.tier == "free":
            return (
                f"You've reached your Free tier limit of {self.limit} messages/month. "
                f"You've used {self.current_usage} messages. "
                f"Upgrade to Pro for 10,000 messages/month."
            )
        elif self.tier == "pro":
            return (
                f"You've reached your Pro tier limit of {self.limit} messages/month. "
                f"You've used {self.current_usage} messages. "
                f"Contact support for Enterprise options."
            )
        else:
            return f"Usage limit exceeded: {self.current_usage}/{self.limit}"


@dataclass
class LimitEnforcerConfig:
    """Configuration for limit enforcer"""
    region: str = settings.AWS_REGION
    usage_table: str = settings.DYNAMODB_USAGE_TABLE
    upgrade_url_template: str = "https://agentfirst.app/upgrade?email={email}&tier={tier}"


class LimitEnforcer:
    """Service for enforcing usage limits"""

    def __init__(self, config: LimitEnforcerConfig = None):
        """Initialize limit enforcer"""
        self.config = config or LimitEnforcerConfig()
        self.tracker = UsageTracker(
            UsageTrackerConfig(
                region=self.config.region,
                usage_table=self.config.usage_table
            )
        )

    @staticmethod
    def _get_tier_limit(tier: str) -> int:
        """Get message limit for tier"""
        limits = {
            'free': 100,
            'pro': 10000,
            'enterprise': 999999999
        }
        return limits.get(tier, 0)

    def _generate_upgrade_url(self, email: str, tier: str) -> str:
        """Generate upgrade URL for user"""
        return self.config.upgrade_url_template.format(email=email, tier=tier)

    async def check_limit(self, email: str, tier: str) -> bool:
        """Check if user can send a message"""
        if not email or '@' not in email:
            raise ValueError("Invalid email format")

        if tier not in ["free", "pro", "enterprise"]:
            raise ValueError("Invalid tier")

        # Enterprise tier has no limits
        if tier == "enterprise":
            return True

        # Get current usage
        count = await self.tracker.get_usage_count(email)
        limit = self._get_tier_limit(tier)

        # Check if limit exceeded
        return count < limit

    async def enforce_limit(self, email: str, tier: str) -> None:
        """Enforce usage limit - raises exception if exceeded"""
        if not email or '@' not in email:
            raise ValueError("Invalid email format")

        if tier not in ["free", "pro", "enterprise"]:
            raise ValueError("Invalid tier")

        # Enterprise tier has no limits
        if tier == "enterprise":
            return

        # Get current usage
        count = await self.tracker.get_usage_count(email)
        limit = self._get_tier_limit(tier)

        # Check if limit exceeded
        if count >= limit:
            remaining = max(0, limit - count)
            upgrade_url = self._generate_upgrade_url(email, tier)
            raise LimitExceededError(
                email=email,
                tier=tier,
                current_usage=count,
                limit=limit,
                remaining=remaining,
                upgrade_url=upgrade_url
            )

    async def get_limit_status(self, email: str, tier: str) -> Dict[str, Any]:
        """Get limit status for user"""
        if not email or '@' not in email:
            raise ValueError("Invalid email format")

        if tier not in ["free", "pro", "enterprise"]:
            raise ValueError("Invalid tier")

        count = await self.tracker.get_usage_count(email)
        limit = self._get_tier_limit(tier)
        remaining = max(0, limit - count)
        percentage = (count / limit * 100) if limit > 0 else 0

        return {
            'email': email,
            'tier': tier,
            'current_usage': count,
            'limit': limit,
            'remaining': remaining,
            'percentage': percentage,
            'exceeded': count >= limit,
            'upgrade_url': self._generate_upgrade_url(email, tier) if count >= limit else None
        }

    async def get_warning_status(self, email: str, tier: str, warning_threshold: float = 80.0) -> Dict[str, Any]:
        """Get warning status when approaching limit"""
        if not email or '@' not in email:
            raise ValueError("Invalid email format")

        if tier not in ["free", "pro", "enterprise"]:
            raise ValueError("Invalid tier")

        if warning_threshold < 0 or warning_threshold > 100:
            raise ValueError("Warning threshold must be between 0 and 100")

        count = await self.tracker.get_usage_count(email)
        limit = self._get_tier_limit(tier)
        percentage = (count / limit * 100) if limit > 0 else 0

        return {
            'email': email,
            'tier': tier,
            'current_usage': count,
            'limit': limit,
            'percentage': percentage,
            'warning_threshold': warning_threshold,
            'is_warning': percentage >= warning_threshold,
            'messages_until_warning': max(0, int(limit * warning_threshold / 100) - count),
            'upgrade_url': self._generate_upgrade_url(email, tier)
        }

    async def can_send_messages(self, email: str, tier: str, count: int = 1) -> bool:
        """Check if user can send N messages"""
        if not email or '@' not in email:
            raise ValueError("Invalid email format")

        if tier not in ["free", "pro", "enterprise"]:
            raise ValueError("Invalid tier")

        if count < 1:
            raise ValueError("Count must be positive")

        # Enterprise tier has no limits
        if tier == "enterprise":
            return True

        # Get current usage
        current = await self.tracker.get_usage_count(email)
        limit = self._get_tier_limit(tier)

        # Check if user can send N messages
        return current + count <= limit

    async def get_messages_available(self, email: str, tier: str) -> int:
        """Get number of messages user can still send"""
        if not email or '@' not in email:
            raise ValueError("Invalid email format")

        if tier not in ["free", "pro", "enterprise"]:
            raise ValueError("Invalid tier")

        # Enterprise tier has no limits
        if tier == "enterprise":
            return 999999999

        # Get current usage
        count = await self.tracker.get_usage_count(email)
        limit = self._get_tier_limit(tier)

        return max(0, limit - count)
