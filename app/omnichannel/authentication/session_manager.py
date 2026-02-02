"""Session Management Service - Manages cross-channel sessions with 24h TTL"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
import uuid
import boto3
from botocore.exceptions import ClientError
from app.config.settings import settings


@dataclass
class Session:
    """Session model"""
    session_id: str
    email: str
    channel: str  # telegram, whatsapp, web, app, email, sms, voice
    channel_id: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: str = field(default_factory=lambda: (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat())
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'session_id': self.session_id,
            'email': self.email,
            'channel': self.channel,
            'channel_id': self.channel_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'expires_at': self.expires_at,
            'context': self.context,
            'metadata': self.metadata,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Session':
        """Create from dictionary"""
        return Session(
            session_id=data['session_id'],
            email=data['email'],
            channel=data['channel'],
            channel_id=data['channel_id'],
            created_at=data.get('created_at', datetime.now(timezone.utc).isoformat()),
            updated_at=data.get('updated_at', datetime.now(timezone.utc).isoformat()),
            expires_at=data.get('expires_at', (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()),
            context=data.get('context', {}),
            metadata=data.get('metadata', {}),
        )

    def is_valid(self) -> bool:
        """Check if session is still valid"""
        expires = datetime.fromisoformat(self.expires_at)
        return datetime.now(timezone.utc) < expires

    def is_expired(self) -> bool:
        """Check if session is expired"""
        return not self.is_valid()


@dataclass
class SessionConfig:
    """Configuration for session management"""
    region: str = settings.AWS_REGION
    sessions_table: str = settings.DYNAMODB_SESSIONS_TABLE
    ttl_hours: int = settings.SESSION_TTL_HOURS
    email_index: str = "email-index"


class SessionManager:
    """Service for managing cross-channel sessions"""

    def __init__(self, config: SessionConfig = None):
        """Initialize session manager"""
        self.config = config or SessionConfig()
        self.dynamodb = boto3.resource('dynamodb', region_name=self.config.region)
        self.table = self.dynamodb.Table(self.config.sessions_table)

    @staticmethod
    def _generate_session_id() -> str:
        """Generate unique session ID"""
        return str(uuid.uuid4())

    @staticmethod
    def _calculate_ttl() -> int:
        """Calculate TTL timestamp for DynamoDB"""
        expires = datetime.now(timezone.utc) + timedelta(hours=24)
        return int(expires.timestamp())

    async def create_session(self, email: str, channel: str, channel_id: str,
                            context: Dict[str, Any] = None,
                            metadata: Dict[str, Any] = None) -> Session:
        """Create new session"""
        if not email or '@' not in email:
            raise ValueError("Invalid email format")

        if not channel or not channel_id:
            raise ValueError("Channel and channel_id are required")

        # Generate session ID
        session_id = self._generate_session_id()

        # Create session
        session = Session(
            session_id=session_id,
            email=email,
            channel=channel.lower(),
            channel_id=channel_id,
            context=context or {},
            metadata=metadata or {}
        )

        try:
            # Add TTL for automatic expiration
            item = session.to_dict()
            item['ttl'] = self._calculate_ttl()

            self.table.put_item(Item=item)
        except ClientError as e:
            raise ValueError(f"Failed to create session: {str(e)}")

        return session

    async def get_session(self, session_id: str, email: str) -> Optional[Session]:
        """Get session by ID and email"""
        if not session_id or not email:
            raise ValueError("Session ID and Email are required")

        try:
            response = self.table.get_item(Key={'email': email, 'session_id': session_id})

            if 'Item' not in response:
                return None

            session = Session.from_dict(response['Item'])

            # Check if expired
            if session.is_expired():
                # Delete expired session
                await self.delete_session(session_id, email)
                return None

            return session
        except ClientError as e:
            raise ValueError(f"Failed to get session: {str(e)}")

    async def get_session_by_email(self, email: str) -> Optional[Session]:
        """Get most recent session for email"""
        if not email or '@' not in email:
            raise ValueError("Invalid email format")

        try:
            response = self.table.query(
                KeyConditionExpression='email = :email',
                ExpressionAttributeValues={':email': email},
                ScanIndexForward=False,  # Sort by created_at descending
                Limit=1
            )

            if not response['Items']:
                return None

            session = Session.from_dict(response['Items'][0])

            # Check if expired
            if session.is_expired():
                # Delete expired session
                await self.delete_session(session.session_id, email)
                return None

            return session
        except ClientError as e:
            raise ValueError(f"Failed to get session: {str(e)}")

    async def get_all_sessions_for_email(self, email: str) -> list:
        """Get all valid sessions for email"""
        if not email or '@' not in email:
            raise ValueError("Invalid email format")

        try:
            response = self.table.query(
                KeyConditionExpression='email = :email',
                ExpressionAttributeValues={':email': email}
            )

            sessions = []
            for item in response['Items']:
                session = Session.from_dict(item)
                # Only include valid sessions
                if session.is_valid():
                    sessions.append(session)
                else:
                    # Delete expired session
                    await self.delete_session(session.session_id, email)

            return sessions
        except ClientError as e:
            raise ValueError(f"Failed to get sessions: {str(e)}")

    async def update_session(self, session_id: str, email: str,
                            context: Dict[str, Any] = None,
                            metadata: Dict[str, Any] = None) -> Optional[Session]:
        """Update session context and metadata"""
        if not session_id or not email:
            raise ValueError("Session ID and Email are required")

        # Get existing session
        session = await self.get_session(session_id, email)
        if not session:
            raise ValueError("Session not found or expired")

        try:
            updates = {
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'ttl': self._calculate_ttl()
            }

            if context is not None:
                updates['context'] = context
            if metadata is not None:
                updates['metadata'] = metadata

            self.table.update_item(
                Key={'email': email, 'session_id': session_id},
                UpdateExpression='SET ' + ', '.join([f'{k} = :{k}' for k in updates.keys()]),
                ExpressionAttributeValues={f':{k}': v for k, v in updates.items()}
            )

            # Fetch updated session
            return await self.get_session(session_id, email)
        except ClientError as e:
            raise ValueError(f"Failed to update session: {str(e)}")

    async def update_session_context(self, session_id: str, email: str, context_updates: Dict[str, Any]) -> Optional[Session]:
        """Update session context (merge with existing)"""
        if not session_id or not email:
            raise ValueError("Session ID and Email are required")

        # Get existing session
        session = await self.get_session(session_id, email)
        if not session:
            raise ValueError("Session not found or expired")

        # Merge context
        merged_context = {**session.context, **context_updates}

        return await self.update_session(session_id, email, context=merged_context)

    async def validate_session(self, session_id: str, email: str) -> bool:
        """Validate if session is still valid"""
        if not session_id or not email:
            return False

        try:
            session = await self.get_session(session_id, email)
            return session is not None and session.is_valid()
        except ValueError:
            return False

    async def delete_session(self, session_id: str, email: str) -> bool:
        """Delete session"""
        if not session_id or not email:
            raise ValueError("Session ID and Email are required")

        try:
            response = self.table.delete_item(
                Key={'email': email, 'session_id': session_id},
                ReturnValues='ALL_OLD'
            )

            return 'Attributes' in response
        except ClientError as e:
            raise ValueError(f"Failed to delete session: {str(e)}")

    async def delete_all_sessions_for_email(self, email: str) -> int:
        """Delete all sessions for email"""
        if not email or '@' not in email:
            raise ValueError("Invalid email format")

        try:
            sessions = await self.get_all_sessions_for_email(email)
            deleted_count = 0

            for session in sessions:
                if await self.delete_session(session.session_id, email):
                    deleted_count += 1

            return deleted_count
        except ClientError as e:
            raise ValueError(f"Failed to delete sessions: {str(e)}")

    async def extend_session(self, session_id: str, email: str) -> Optional[Session]:
        """Extend session expiration by 24 hours"""
        if not session_id or not email:
            raise ValueError("Session ID and Email are required")

        # Get existing session
        session = await self.get_session(session_id, email)
        if not session:
            raise ValueError("Session not found or expired")

        # Update with new expiration
        new_expires = (datetime.now(timezone.utc) + timedelta(hours=self.config.ttl_hours)).isoformat()

        try:
            self.table.update_item(
                Key={'email': email, 'session_id': session_id},
                UpdateExpression='SET expires_at = :expires, updated_at = :updated, ttl = :ttl',
                ExpressionAttributeValues={
                    ':expires': new_expires,
                    ':updated': datetime.now(timezone.utc).isoformat(),
                    ':ttl': self._calculate_ttl()
                }
            )

            return await self.get_session(session_id, email)
        except ClientError as e:
            raise ValueError(f"Failed to extend session: {str(e)}")

    async def get_session_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session context"""
        session = await self.get_session(session_id)
        return session.context if session else None

    async def get_session_metadata(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session metadata"""
        session = await self.get_session(session_id)
        return session.metadata if session else None
