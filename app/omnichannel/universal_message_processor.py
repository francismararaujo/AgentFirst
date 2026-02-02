"""
Universal message processor for omnichannel message handling.

Processes messages from any channel, extracts email, retrieves context,
and prepares messages for Brain processing.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from app.omnichannel.models import UniversalMessage, ChannelType, MessageContext
from app.omnichannel.channel_mapping_service import ChannelMappingService


class UniversalMessageProcessor:
    """
    Processes messages from any channel into a universal format.
    
    Handles:
    1. Receiving messages from channels (Telegram, WhatsApp, Web, etc)
    2. Converting to UniversalMessage format
    3. Extracting email from channel ID
    4. Retrieving conversation context
    5. Preparing for Brain processing
    """
    
    def __init__(
        self,
        channel_mapping_service: ChannelMappingService,
        session_manager,
        memory_service
    ):
        """
        Initialize processor with required services.
        
        Args:
            channel_mapping_service: Maps channel IDs to emails
            session_manager: Manages user sessions
            memory_service: Retrieves conversation context
        """
        self.channel_mapping = channel_mapping_service
        self.session_manager = session_manager
        self.memory = memory_service
    
    async def process_message(
        self,
        channel: ChannelType,
        channel_user_id: str,
        message_text: str,
        message_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UniversalMessage:
        """
        Process a message from any channel.
        
        Args:
            channel: Channel type (telegram, whatsapp, etc)
            channel_user_id: User ID from the channel
            message_text: Message text content
            message_id: Unique message ID from channel
            metadata: Optional channel-specific metadata
        
        Returns:
            UniversalMessage ready for Brain processing
        
        Raises:
            ValueError: If email cannot be extracted or user not found
        """
        # 1. Extract email from channel ID
        email = await self._extract_email(channel, channel_user_id)
        if not email:
            raise ValueError(
                f"Cannot extract email for {channel.value} user {channel_user_id}"
            )
        
        # 2. Retrieve session
        session = await self.session_manager.get_session_by_email(email)
        if not session:
            # Create new session if not found
            session = await self.session_manager.create_session(
                email=email,
                channel=channel.value,
                channel_id=channel_user_id,
                context={'created_via': 'universal_processor'}
            )
        
        # 3. Retrieve conversation context
        context = await self._retrieve_context(email)
        
        # 4. Create UniversalMessage
        universal_message = UniversalMessage(
            text=message_text,
            channel=channel,
            channel_user_id=channel_user_id,
            message_id=message_id,
            timestamp=datetime.now(),
            email=email,
            session_id=session.session_id,
            context=context,
            metadata=metadata or {}
        )
        
        return universal_message
    
    async def _extract_email(
        self,
        channel: ChannelType,
        channel_user_id: str
    ) -> Optional[str]:
        """
        Extract email from channel user ID.
        
        Args:
            channel: Channel type
            channel_user_id: User ID from channel
        
        Returns:
            Email address if mapping exists, None otherwise
        """
        email = await self.channel_mapping.get_email_by_channel_id(
            channel,
            channel_user_id
        )
        return email
    
    async def _retrieve_context(self, email: str) -> Dict[str, Any]:
        """
        Retrieve conversation context for user.
        
        Includes:
        - Last intent and connector (for follow-up questions)
        - Last order ID (for "confirm that" type requests)
        - Conversation history
        - User preferences
        
        Args:
            email: User email
        
        Returns:
            Context dictionary with conversation state
        """
        # Retrieve from Memory service (DynamoDB)
        memory_data = await self.memory.get_context(email)
        
        if not memory_data:
            return {
                'last_intent': None,
                'last_connector': None,
                'last_order_id': None,
                'conversation_history': [],
                'user_preferences': {}
            }
        
        return {
            'last_intent': memory_data.get('last_intent'),
            'last_connector': memory_data.get('last_connector'),
            'last_order_id': memory_data.get('last_order_id'),
            'conversation_history': memory_data.get('conversation_history', []),
            'user_preferences': memory_data.get('user_preferences', {})
        }
    
    async def update_context(
        self,
        email: str,
        intent: Optional[str] = None,
        connector: Optional[str] = None,
        order_id: Optional[str] = None,
        add_to_history: Optional[str] = None
    ) -> None:
        """
        Update conversation context after processing.
        
        Args:
            email: User email
            intent: Last intent (for follow-up questions)
            connector: Last connector used (iFood, 99food, etc)
            order_id: Last order ID (for "confirm that" requests)
            add_to_history: Message to add to conversation history
        """
        updates = {}
        
        if intent is not None:
            updates['last_intent'] = intent
        
        if connector is not None:
            updates['last_connector'] = connector
        
        if order_id is not None:
            updates['last_order_id'] = order_id
        
        if add_to_history is not None:
            updates['add_to_history'] = add_to_history
        
        if updates:
            await self.memory.update_context(email, updates)
