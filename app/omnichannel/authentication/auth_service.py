"""Email-Based Authentication Service for AgentFirst2 MVP

This module provides email-based authentication:
- Verify if email exists
- Create new user (Free tier)
- Retrieve user by email
- User tier management
"""

import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class AuthConfig:
    """Configuration for authentication"""

    def __init__(
        self,
        region: str = None,
        users_table: str = None,
        default_tier: str = "free",
        free_tier_limit: int = None,
        pro_tier_limit: int = None,
    ):
        from app.config.settings import settings
        self.region = region or settings.AWS_REGION
        self.users_table = users_table or settings.DYNAMODB_USERS_TABLE
        self.default_tier = default_tier
        self.free_tier_limit = free_tier_limit or settings.FREE_TIER_LIMIT
        self.pro_tier_limit = pro_tier_limit or settings.PRO_TIER_LIMIT


class User:
    """Represents a user"""

    def __init__(
        self,
        email: str,
        tier: str = "free",
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.email = email
        self.tier = tier
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.updated_at = updated_at or datetime.now(timezone.utc).isoformat()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary"""
        return {
            "email": self.email,
            "tier": self.tier,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        """Create user from dictionary"""
        return cls(
            email=data["email"],
            tier=data.get("tier", "free"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            metadata=data.get("metadata", {}),
        )


class AuthService:
    """Email-based authentication service"""

    def __init__(self, config: AuthConfig):
        self.config = config
        self.dynamodb = boto3.resource("dynamodb", region_name=config.region)
        self.table = self.dynamodb.Table(config.users_table)

    async def user_exists(self, email: str) -> bool:
        """
        Check if user exists by email

        Args:
            email: User email

        Returns:
            True if user exists, False otherwise
        """
        try:
            response = self.table.get_item(Key={"email": email})

            exists = "Item" in response
            logger.info(
                json.dumps({
                    "event": "user_exists_check",
                    "email": email,
                    "exists": exists,
                })
            )

            return exists

        except ClientError as e:
            logger.error(
                json.dumps({
                    "event": "user_exists_check_failed",
                    "error": str(e),
                    "email": email,
                })
            )
            raise

    async def create_user(self, email: str, tier: Optional[str] = None) -> User:
        """
        Create new user with Free tier

        Args:
            email: User email
            tier: User tier (defaults to free)

        Returns:
            Created user

        Raises:
            Exception: If user already exists or creation fails
        """
        try:
            # Check if user already exists
            if await self.user_exists(email):
                raise ValueError(f"User {email} already exists")

            # Create new user
            user = User(
                email=email,
                tier=tier or self.config.default_tier,
            )

            # Store in DynamoDB
            self.table.put_item(Item=user.to_dict())

            logger.info(
                json.dumps({
                    "event": "user_created",
                    "email": email,
                    "tier": user.tier,
                })
            )

            return user

        except ClientError as e:
            logger.error(
                json.dumps({
                    "event": "user_creation_failed",
                    "error": str(e),
                    "email": email,
                })
            )
            raise

    async def get_user(self, email: str) -> Optional[User]:
        """
        Retrieve user by email

        Args:
            email: User email

        Returns:
            User if found, None otherwise
        """
        try:
            response = self.table.get_item(Key={"email": email})

            if "Item" not in response:
                logger.info(
                    json.dumps({
                        "event": "user_not_found",
                        "email": email,
                    })
                )
                return None

            user = User.from_dict(response["Item"])

            logger.info(
                json.dumps({
                    "event": "user_retrieved",
                    "email": email,
                    "tier": user.tier,
                })
            )

            return user

        except ClientError as e:
            logger.error(
                json.dumps({
                    "event": "user_retrieval_failed",
                    "error": str(e),
                    "email": email,
                })
            )
            raise

    async def get_or_create_user(self, email: str) -> User:
        """
        Get user if exists, otherwise create new user

        Args:
            email: User email

        Returns:
            User (existing or newly created)
        """
        try:
            # Try to get existing user
            user = await self.get_user(email)

            if user:
                logger.info(
                    json.dumps({
                        "event": "user_retrieved_existing",
                        "email": email,
                    })
                )
                return user

            # Create new user if doesn't exist
            user = await self.create_user(email)

            logger.info(
                json.dumps({
                    "event": "user_created_new",
                    "email": email,
                })
            )

            return user

        except Exception as e:
            logger.error(
                json.dumps({
                    "event": "get_or_create_user_failed",
                    "error": str(e),
                    "email": email,
                })
            )
            raise

    async def update_user_tier(self, email: str, tier: str) -> User:
        """
        Update user tier

        Args:
            email: User email
            tier: New tier (free, pro, enterprise)

        Returns:
            Updated user

        Raises:
            Exception: If user not found or update fails
        """
        try:
            # Verify user exists
            user = await self.get_user(email)
            if not user:
                raise ValueError(f"User {email} not found")

            # Update tier
            now = datetime.now(timezone.utc).isoformat()
            self.table.update_item(
                Key={"email": email},
                UpdateExpression="SET tier = :tier, updated_at = :updated_at",
                ExpressionAttributeValues={
                    ":tier": tier,
                    ":updated_at": now,
                },
            )

            # Retrieve updated user
            updated_user = await self.get_user(email)

            logger.info(
                json.dumps({
                    "event": "user_tier_updated",
                    "email": email,
                    "new_tier": tier,
                })
            )

            return updated_user

        except ClientError as e:
            logger.error(
                json.dumps({
                    "event": "user_tier_update_failed",
                    "error": str(e),
                    "email": email,
                })
            )
            raise

    async def get_user_tier_limit(self, email: str) -> int:
        """
        Get message limit for user tier

        Args:
            email: User email

        Returns:
            Message limit for user's tier

        Raises:
            Exception: If user not found
        """
        try:
            user = await self.get_user(email)
            if not user:
                raise ValueError(f"User {email} not found")

            # Return limit based on tier
            if user.tier == "pro":
                limit = self.config.pro_tier_limit
            elif user.tier == "enterprise":
                limit = float("inf")
            else:  # free
                limit = self.config.free_tier_limit

            logger.info(
                json.dumps({
                    "event": "user_tier_limit_retrieved",
                    "email": email,
                    "tier": user.tier,
                    "limit": limit if limit != float("inf") else "unlimited",
                })
            )

            return limit

        except Exception as e:
            logger.error(
                json.dumps({
                    "event": "user_tier_limit_retrieval_failed",
                    "error": str(e),
                    "email": email,
                })
            )
            raise

    async def authenticate_user(self, email: str) -> User:
        """
        Authenticate user by email

        Args:
            email: User email

        Returns:
            Authenticated user

        Raises:
            Exception: If authentication fails
        """
        try:
            # Validate email format
            if not self._is_valid_email(email):
                raise ValueError(f"Invalid email format: {email}")

            # Get or create user
            user = await self.get_or_create_user(email)

            logger.info(
                json.dumps({
                    "event": "user_authenticated",
                    "email": email,
                    "tier": user.tier,
                })
            )

            return user

        except Exception as e:
            logger.error(
                json.dumps({
                    "event": "user_authentication_failed",
                    "error": str(e),
                    "email": email,
                })
            )
            raise

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """
        Validate email format

        Args:
            email: Email to validate

        Returns:
            True if valid, False otherwise
        """
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    async def delete_user(self, email: str) -> bool:
        """
        Delete user by email

        Args:
            email: User email

        Returns:
            True if deleted, False if not found

        Raises:
            Exception: If deletion fails
        """
        try:
            # Check if user exists
            if not await self.user_exists(email):
                logger.warning(
                    json.dumps({
                        "event": "user_delete_not_found",
                        "email": email,
                    })
                )
                return False

            # Delete user
            self.table.delete_item(Key={"email": email})

            logger.info(
                json.dumps({
                    "event": "user_deleted",
                    "email": email,
                })
            )

            return True

        except ClientError as e:
            logger.error(
                json.dumps({
                    "event": "user_deletion_failed",
                    "error": str(e),
                    "email": email,
                })
            )
            raise
