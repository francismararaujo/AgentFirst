"""Usage Tracker - Tracks message usage per user with monthly reset"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError
from app.config.settings import settings


@dataclass
class Usage:
    """Usage model"""
    email: str
    year: int
    month: int
    message_count: int = 0
    tier: str = "free"
    reset_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'email': self.email,
            'year': self.year,
            'month': self.month,
            'message_count': self.message_count,
            'tier': self.tier,
            'reset_at': self.reset_at,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'metadata': self.metadata,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Usage':
        """Create from dictionary"""
        return Usage(
            email=data['email'],
            year=data['year'],
            month=data['month'],
            message_count=data.get('message_count', 0),
            tier=data.get('tier', 'free'),
            reset_at=data.get('reset_at', datetime.now(timezone.utc).isoformat()),
            created_at=data.get('created_at', datetime.now(timezone.utc).isoformat()),
            updated_at=data.get('updated_at', datetime.now(timezone.utc).isoformat()),
            metadata=data.get('metadata', {}),
        )

    def is_reset_due(self) -> bool:
        """Check if usage should be reset"""
        reset_time = datetime.fromisoformat(self.reset_at)
        return datetime.now(timezone.utc) >= reset_time


@dataclass
class UsageTrackerConfig:
    """Configuration for usage tracker"""
    region: str = settings.AWS_REGION
    usage_table: str = settings.DYNAMODB_USAGE_TABLE
    email_index: str = "email-index"


class UsageTracker:
    """Service for tracking message usage per user"""

    def __init__(self, config: UsageTrackerConfig = None):
        """Initialize usage tracker"""
        self.config = config or UsageTrackerConfig()
        self.dynamodb = boto3.resource('dynamodb', region_name=self.config.region)
        self.table = self.dynamodb.Table(self.config.usage_table)

    @staticmethod
    def _get_current_month() -> tuple:
        """Get current year and month"""
        now = datetime.now(timezone.utc)
        return now.year, now.month

    @staticmethod
    def _calculate_next_month_reset() -> str:
        """Calculate next month's reset time (first day of next month at 00:00 UTC)"""
        now = datetime.now(timezone.utc)
        # Get first day of next month
        if now.month == 12:
            next_month = datetime(now.year + 1, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        else:
            next_month = datetime(now.year, now.month + 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        return next_month.isoformat()

    async def get_or_create_usage(self, email: str, tier: str = "free") -> Usage:
        """Get or create usage record for current month"""
        if not email or '@' not in email:
            raise ValueError("Invalid email format")

        if tier not in ["free", "pro", "enterprise"]:
            raise ValueError("Invalid tier")

        year, month = self._get_current_month()

        try:
            # Try to get existing usage
            response = self.table.get_item(
                Key={
                    'email': email,
                    'month': f"{year}#{month:02d}"
                }
            )

            if 'Item' in response:
                usage = Usage.from_dict(response['Item'])
                # Check if reset is due
                if usage.is_reset_due():
                    # Reset the usage
                    return await self.reset_usage(email, tier)
                return usage

            # Create new usage record
            usage = Usage(
                email=email,
                year=year,
                month=month,
                message_count=0,
                tier=tier,
                reset_at=self._calculate_next_month_reset()
            )

            item = usage.to_dict()
            item['month'] = f"{year}#{month:02d}"
            self.table.put_item(Item=item)

            return usage
        except ClientError as e:
            raise ValueError(f"Failed to get or create usage: {str(e)}")

    async def get_usage(self, email: str) -> Optional[Usage]:
        """Get usage for current month"""
        if not email or '@' not in email:
            raise ValueError("Invalid email format")

        year, month = self._get_current_month()

        try:
            response = self.table.get_item(
                Key={
                    'email': email,
                    'month': f"{year}#{month:02d}"
                }
            )

            if 'Item' not in response:
                return None

            usage = Usage.from_dict(response['Item'])

            # Check if reset is due
            if usage.is_reset_due():
                return await self.reset_usage(email, usage.tier)

            return usage
        except ClientError as e:
            raise ValueError(f"Failed to get usage: {str(e)}")

    async def increment_usage(self, email: str, count: int = 1) -> Usage:
        """Increment message count for current month"""
        if not email or '@' not in email:
            raise ValueError("Invalid email format")

        if count < 1:
            raise ValueError("Count must be positive")

        year, month = self._get_current_month()

        try:
            # Get or create usage
            usage = await self.get_or_create_usage(email)

            # Increment counter
            self.table.update_item(
                Key={
                    'email': email,
                    'month': f"{year}#{month:02d}"
                },
                UpdateExpression='ADD message_count :inc SET updated_at = :updated',
                ExpressionAttributeValues={
                    ':inc': count,
                    ':updated': datetime.now(timezone.utc).isoformat()
                }
            )

            # Fetch updated usage
            return await self.get_usage(email)
        except ClientError as e:
            raise ValueError(f"Failed to increment usage: {str(e)}")

    async def reset_usage(self, email: str, tier: str = "free") -> Usage:
        """Reset usage for new month"""
        if not email or '@' not in email:
            raise ValueError("Invalid email format")

        if tier not in ["free", "pro", "enterprise"]:
            raise ValueError("Invalid tier")

        year, month = self._get_current_month()

        try:
            usage = Usage(
                email=email,
                year=year,
                month=month,
                message_count=0,
                tier=tier,
                reset_at=self._calculate_next_month_reset()
            )

            item = usage.to_dict()
            item['month'] = f"{year}#{month:02d}"
            self.table.put_item(Item=item)

            return usage
        except ClientError as e:
            raise ValueError(f"Failed to reset usage: {str(e)}")

    async def get_usage_count(self, email: str) -> int:
        """Get current month's message count"""
        if not email or '@' not in email:
            raise ValueError("Invalid email format")

        usage = await self.get_usage(email)
        return usage.message_count if usage else 0
# ... (rest of file)
    async def delete_usage(self, email: str, year: int, month: int) -> bool:
        """Delete usage record for specific month"""
        if not email or '@' not in email:
            raise ValueError("Invalid email format")

        if month < 1 or month > 12:
            raise ValueError("Month must be between 1 and 12")

        try:
            response = self.table.delete_item(
                Key={
                    'email': email,
                    'month': f"{year}#{month:02d}"
                },
                ReturnValues='ALL_OLD'
            )

            return 'Attributes' in response
        except ClientError as e:
            raise ValueError(f"Failed to delete usage: {str(e)}")
