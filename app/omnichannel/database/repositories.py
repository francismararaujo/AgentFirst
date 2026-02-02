"""DynamoDB repositories for AgentFirst2 MVP"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError

from app.config.settings import settings
from app.omnichannel.database.models import (
    User, Session, Memory, Usage, AuditLog, Escalation, UserTier
)

logger = logging.getLogger(__name__)


class DynamoDBRepository:
    """Base repository for DynamoDB operations"""

    def __init__(self):
        """Initialize DynamoDB client"""
        self.dynamodb = boto3.resource(
            'dynamodb',
            region_name=settings.AWS_REGION,
            endpoint_url=settings.DYNAMODB_ENDPOINT
        )

    def get_table(self, table_name: str):
        """Get DynamoDB table"""
        return self.dynamodb.Table(table_name)


class UserRepository(DynamoDBRepository):
    """Repository for User table"""

    async def create(self, user: User) -> User:
        """Create a new user"""
        try:
            table = self.get_table(settings.DYNAMODB_USERS_TABLE)
            table.put_item(Item=user.to_dynamodb())
            logger.info(f"User created: {user.email}")
            return user
        except ClientError as e:
            logger.error(f"Error creating user: {str(e)}")
            raise

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        try:
            table = self.get_table(settings.DYNAMODB_USERS_TABLE)
            response = table.get_item(Key={'email': email})
            if 'Item' in response:
                return User.from_dynamodb(response['Item'])
            return None
        except ClientError as e:
            logger.error(f"Error getting user: {str(e)}")
            raise

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID"""
        try:
            table = self.get_table(settings.DYNAMODB_USERS_TABLE)
            
            # Scan table for telegram_id (not ideal, but works for MVP)
            response = table.scan(
                FilterExpression='telegram_id = :telegram_id',
                ExpressionAttributeValues={':telegram_id': telegram_id}
            )
            
            if response['Items']:
                return User.from_dynamodb(response['Items'][0])
            return None
        except ClientError as e:
            logger.error(f"Error getting user by telegram_id: {str(e)}")
            raise

    async def update(self, email: str, updates: Dict[str, Any]) -> User:
        """Update user"""
        try:
            table = self.get_table(settings.DYNAMODB_USERS_TABLE)
            updates['updated_at'] = datetime.utcnow().isoformat()
            
            # Build update expression
            update_expr = "SET " + ", ".join([f"{k} = :{k}" for k in updates.keys()])
            expr_values = {f":{k}": v for k, v in updates.items()}
            
            response = table.update_item(
                Key={'email': email},
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values,
                ReturnValues='ALL_NEW'
            )
            
            logger.info(f"User updated: {email}")
            return User.from_dynamodb(response['Attributes'])
        except ClientError as e:
            logger.error(f"Error updating user: {str(e)}")
            raise

    async def delete(self, email: str) -> None:
        """Delete user"""
        try:
            table = self.get_table(settings.DYNAMODB_USERS_TABLE)
            table.delete_item(Key={'email': email})
            logger.info(f"User deleted: {email}")
        except ClientError as e:
            logger.error(f"Error deleting user: {str(e)}")
            raise


class SessionRepository(DynamoDBRepository):
    """Repository for Session table"""

    async def create(self, session: Session) -> Session:
        """Create a new session"""
        try:
            table = self.get_table(settings.DYNAMODB_SESSIONS_TABLE)
            
            # Calculate TTL (24 hours from now)
            ttl = int((datetime.utcnow() + timedelta(hours=24)).timestamp())
            
            item = session.to_dynamodb()
            item['ttl'] = ttl
            
            table.put_item(Item=item)
            logger.info(f"Session created: {session.email}")
            return session
        except ClientError as e:
            logger.error(f"Error creating session: {str(e)}")
            raise

    async def get_by_email(self, email: str) -> Optional[Session]:
        """Get session by email"""
        try:
            table = self.get_table(settings.DYNAMODB_SESSIONS_TABLE)
            response = table.query(
                KeyConditionExpression='email = :email',
                ExpressionAttributeValues={':email': email},
                Limit=1
            )
            
            if response['Items']:
                return Session.from_dynamodb(response['Items'][0])
            return None
        except ClientError as e:
            logger.error(f"Error getting session: {str(e)}")
            raise

    async def update(self, email: str, session_id: str, updates: Dict[str, Any]) -> Session:
        """Update session"""
        try:
            table = self.get_table(settings.DYNAMODB_SESSIONS_TABLE)
            
            response = table.update_item(
                Key={'email': email, 'session_id': session_id},
                UpdateExpression="SET " + ", ".join([f"{k} = :{k}" for k in updates.keys()]),
                ExpressionAttributeValues={f":{k}": v for k, v in updates.items()},
                ReturnValues='ALL_NEW'
            )
            
            logger.info(f"Session updated: {email}")
            return Session.from_dynamodb(response['Attributes'])
        except ClientError as e:
            logger.error(f"Error updating session: {str(e)}")
            raise

    async def delete(self, email: str, session_id: str) -> None:
        """Delete session"""
        try:
            table = self.get_table(settings.DYNAMODB_SESSIONS_TABLE)
            table.delete_item(Key={'email': email, 'session_id': session_id})
            logger.info(f"Session deleted: {email}")
        except ClientError as e:
            logger.error(f"Error deleting session: {str(e)}")
            raise


class MemoryRepository(DynamoDBRepository):
    """Repository for Memory table"""

    async def create(self, memory: Memory) -> Memory:
        """Create memory entry"""
        try:
            table = self.get_table(settings.DYNAMODB_MEMORY_TABLE)
            
            # Calculate TTL (30 days from now)
            ttl = int((datetime.utcnow() + timedelta(days=30)).timestamp())
            
            item = memory.to_dynamodb()
            item['ttl'] = ttl
            
            table.put_item(Item=item)
            logger.info(f"Memory created: {memory.email}#{memory.domain}")
            return memory
        except ClientError as e:
            logger.error(f"Error creating memory: {str(e)}")
            raise

    async def get_by_email_and_domain(self, email: str, domain: str) -> Optional[Memory]:
        """Get memory by email and domain"""
        try:
            table = self.get_table(settings.DYNAMODB_MEMORY_TABLE)
            response = table.get_item(Key={'email': email, 'domain': domain})
            
            if 'Item' in response:
                return Memory.from_dynamodb(response['Item'])
            return None
        except ClientError as e:
            logger.error(f"Error getting memory: {str(e)}")
            raise

    async def get_by_email(self, email: str) -> List[Memory]:
        """Get all memory entries for email"""
        try:
            table = self.get_table(settings.DYNAMODB_MEMORY_TABLE)
            response = table.query(
                KeyConditionExpression='email = :email',
                ExpressionAttributeValues={':email': email}
            )
            
            return [Memory.from_dynamodb(item) for item in response['Items']]
        except ClientError as e:
            logger.error(f"Error getting memory: {str(e)}")
            raise

    async def update(self, email: str, domain: str, context: Dict[str, Any]) -> Memory:
        """Update memory context"""
        try:
            table = self.get_table(settings.DYNAMODB_MEMORY_TABLE)
            
            response = table.update_item(
                Key={'email': email, 'domain': domain},
                UpdateExpression="SET #context = :context, updated_at = :updated_at",
                ExpressionAttributeNames={'#context': 'context'},
                ExpressionAttributeValues={
                    ':context': context,
                    ':updated_at': datetime.utcnow().isoformat()
                },
                ReturnValues='ALL_NEW'
            )
            
            logger.info(f"Memory updated: {email}#{domain}")
            return Memory.from_dynamodb(response['Attributes'])
        except ClientError as e:
            logger.error(f"Error updating memory: {str(e)}")
            raise

    async def delete(self, email: str, domain: str) -> None:
        """Delete memory entry"""
        try:
            table = self.get_table(settings.DYNAMODB_MEMORY_TABLE)
            table.delete_item(Key={'email': email, 'domain': domain})
            logger.info(f"Memory deleted: {email}#{domain}")
        except ClientError as e:
            logger.error(f"Error deleting memory: {str(e)}")
            raise


class UsageRepository(DynamoDBRepository):
    """Repository for Usage table"""

    async def create(self, usage: Usage) -> Usage:
        """Create usage entry"""
        try:
            table = self.get_table(settings.DYNAMODB_USAGE_TABLE)
            
            # Calculate TTL (1 year from now)
            ttl = int((datetime.utcnow() + timedelta(days=365)).timestamp())
            
            item = usage.to_dynamodb()
            item['ttl'] = ttl
            
            table.put_item(Item=item)
            logger.info(f"Usage created: {usage.email}#{usage.year}#{usage.month}")
            return usage
        except ClientError as e:
            logger.error(f"Error creating usage: {str(e)}")
            raise

    async def get_by_email_and_month(self, email: str, year: int, month: int) -> Optional[Usage]:
        """Get usage by email and month"""
        try:
            table = self.get_table(settings.DYNAMODB_USAGE_TABLE)
            # Use zero-padded month for consistent composite key
            response = table.get_item(Key={'email': email, 'month': f"{year}#{month:02d}"})
            
            if 'Item' in response:
                return Usage.from_dynamodb(response['Item'])
            return None
        except ClientError as e:
            logger.error(f"Error getting usage: {str(e)}")
            raise

    async def increment_message_count(self, email: str, year: int, month: int) -> Usage:
        """Increment message count"""
        try:
            table = self.get_table(settings.DYNAMODB_USAGE_TABLE)
            
            # Use zero-padded month for consistent composite key
            response = table.update_item(
                Key={'email': email, 'month': f"{year}#{month:02d}"},
                UpdateExpression="ADD message_count :inc",
                ExpressionAttributeValues={':inc': 1},
                ReturnValues='ALL_NEW'
            )
            
            logger.info(f"Usage incremented: {email}#{year}#{month}")
            return Usage.from_dynamodb(response['Attributes'])
        except ClientError as e:
            logger.error(f"Error incrementing usage: {str(e)}")
            raise


class AuditLogRepository(DynamoDBRepository):
    """Repository for Audit Logs table"""

    async def create(self, audit_log: AuditLog) -> AuditLog:
        """Create audit log entry"""
        try:
            table = self.get_table(settings.DYNAMODB_AUDIT_TABLE)
            
            # Calculate TTL (1 year from now)
            ttl = int((datetime.utcnow() + timedelta(days=365)).timestamp())
            
            item = audit_log.to_dynamodb()
            item['ttl'] = ttl
            
            table.put_item(Item=item)
            logger.info(f"Audit log created: {audit_log.email}#{audit_log.action_id}")
            return audit_log
        except ClientError as e:
            logger.error(f"Error creating audit log: {str(e)}")
            raise

    async def get_by_email(self, email: str, limit: int = 100) -> List[AuditLog]:
        """Get audit logs by email"""
        try:
            table = self.get_table(settings.DYNAMODB_AUDIT_TABLE)
            response = table.query(
                KeyConditionExpression='email = :email',
                ExpressionAttributeValues={':email': email},
                Limit=limit,
                ScanIndexForward=False  # Most recent first
            )
            
            return [AuditLog.from_dynamodb(item) for item in response['Items']]
        except ClientError as e:
            logger.error(f"Error getting audit logs: {str(e)}")
            raise

    async def get_by_agent(self, agent: str, limit: int = 100) -> List[AuditLog]:
        """Get audit logs by agent (using GSI)"""
        try:
            table = self.get_table(settings.DYNAMODB_AUDIT_TABLE)
            response = table.query(
                IndexName='agent-index',
                KeyConditionExpression='agent = :agent',
                ExpressionAttributeValues={':agent': agent},
                Limit=limit,
                ScanIndexForward=False  # Most recent first
            )
            
            return [AuditLog.from_dynamodb(item) for item in response['Items']]
        except ClientError as e:
            logger.error(f"Error getting audit logs by agent: {str(e)}")
            raise


class EscalationRepository(DynamoDBRepository):
    """Repository for Escalation table"""

    async def create(self, escalation: Escalation) -> Escalation:
        """Create escalation entry"""
        try:
            table = self.get_table(settings.DYNAMODB_ESCALATION_TABLE)
            
            # Calculate TTL (7 days from now)
            ttl = int((datetime.utcnow() + timedelta(days=7)).timestamp())
            
            item = escalation.to_dynamodb()
            item['ttl'] = ttl
            
            table.put_item(Item=item)
            logger.info(f"Escalation created: {escalation.escalation_id}")
            return escalation
        except ClientError as e:
            logger.error(f"Error creating escalation: {str(e)}")
            raise

    async def get_by_id(self, escalation_id: str) -> Optional[Escalation]:
        """Get escalation by ID"""
        try:
            table = self.get_table(settings.DYNAMODB_ESCALATION_TABLE)
            response = table.get_item(Key={'escalation_id': escalation_id})
            
            if 'Item' in response:
                return Escalation.from_dynamodb(response['Item'])
            return None
        except ClientError as e:
            logger.error(f"Error getting escalation: {str(e)}")
            raise

    async def get_by_email(self, email: str, limit: int = 100) -> List[Escalation]:
        """Get escalations by email (using GSI)"""
        try:
            table = self.get_table(settings.DYNAMODB_ESCALATION_TABLE)
            response = table.query(
                IndexName='user-index',
                KeyConditionExpression='email = :email',
                ExpressionAttributeValues={':email': email},
                Limit=limit,
                ScanIndexForward=False  # Most recent first
            )
            
            return [Escalation.from_dynamodb(item) for item in response['Items']]
        except ClientError as e:
            logger.error(f"Error getting escalations by email: {str(e)}")
            raise

    async def update(self, escalation_id: str, updates: Dict[str, Any]) -> Escalation:
        """Update escalation"""
        try:
            table = self.get_table(settings.DYNAMODB_ESCALATION_TABLE)
            
            response = table.update_item(
                Key={'escalation_id': escalation_id},
                UpdateExpression="SET " + ", ".join([f"{k} = :{k}" for k in updates.keys()]),
                ExpressionAttributeValues={f":{k}": v for k, v in updates.items()},
                ReturnValues='ALL_NEW'
            )
            
            logger.info(f"Escalation updated: {escalation_id}")
            return Escalation.from_dynamodb(response['Attributes'])
        except ClientError as e:
            logger.error(f"Error updating escalation: {str(e)}")
            raise


class ChannelMappingRepository(DynamoDBRepository):
    """Repository for Channel Mapping (uses Users table for now)"""

    async def get_by_channel_id(self, channel: str, channel_user_id: str) -> Optional[Dict[str, Any]]:
        """Get email by channel user ID"""
        try:
            # For now, use UserRepository to find by telegram_id
            # In the future, this could be a separate table
            user_repo = UserRepository()
            if channel.lower() == 'telegram':
                user = await user_repo.get_by_telegram_id(int(channel_user_id))
                if user:
                    return {'email': user.email, 'channel': channel, 'channel_user_id': channel_user_id}
            return None
        except Exception as e:
            logger.error(f"Error getting channel mapping: {str(e)}")
            return None

    async def get_by_email(self, email: str) -> List[Dict[str, Any]]:
        """Get all channel mappings for an email address"""
        try:
            # For now, use UserRepository to find user and return their channels
            # In the future, this could be a separate table with multiple channels per user
            user_repo = UserRepository()
            user = await user_repo.get_by_email(email)
            
            mappings = []
            if user and hasattr(user, 'telegram_id') and user.telegram_id:
                mappings.append({
                    'email': user.email,
                    'channel': 'telegram',
                    'channel_user_id': str(user.telegram_id)
                })
            
            return mappings
        except Exception as e:
            logger.error(f"Error getting channel mappings by email: {str(e)}")
            return []

    async def create_mapping(self, channel: str, channel_user_id: str, email: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create channel mapping (for now, just return the mapping)"""
        return {'email': email, 'channel': channel, 'channel_user_id': channel_user_id, 'metadata': metadata}
