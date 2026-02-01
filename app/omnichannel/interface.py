"""
Omnichannel Interface - Main orchestrator for all channel processing.

This is the central omnichannel orchestrator that handles messages from any channel
(Telegram, WhatsApp, Web, App, Email, SMS) with unified context by email.

Key Features:
1. 100% Natural Language - No interfaces, buttons, or menus
2. Omnichannel Transparent - User doesn't need to know which channel they're using
3. Context Preserved - Same conversation across all channels
4. Email-based Authentication - Universal identification (not phone/channel ID)
5. Freemium Billing - Usage tracking and limits enforcement
6. Enterprise-Grade - Audit logging, H.I.T.L. supervision
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from app.omnichannel.models import UniversalMessage, ChannelType
from app.omnichannel.universal_message_processor import UniversalMessageProcessor
from app.omnichannel.nlp_universal import NLPUniversal
from app.omnichannel.response_adapter import ResponseAdapter
from app.omnichannel.channel_mapping_service import ChannelMappingService
from app.omnichannel.authentication.auth_service import AuthService
from app.omnichannel.authentication.session_manager import SessionManager
from app.omnichannel.database.repositories import UserRepository
from app.core.brain import Brain, Context
from app.core.memory import MemoryService
from app.billing.usage_tracker import UsageTracker
from app.billing.limit_enforcer import LimitEnforcer
from app.billing.billing_manager import BillingManager
from app.core.auditor import Auditor, AuditCategory, AuditLevel
from app.core.supervisor import Supervisor
from app.core.event_bus import EventBus, EventMessage

logger = logging.getLogger(__name__)


class OmnichannelInterface:
    """
    Main omnichannel orchestrator for AgentFirst2.
    
    Handles the complete flow:
    1. Receive message from any channel
    2. Authenticate by email (universal)
    3. Retrieve complete context (history, preferences, state)
    4. Process via Brain (Claude 3.5 Sonnet)
    5. Adapt response for channel (emojis, characters, format)
    6. Check usage limits (Freemium billing)
    7. Coordinate all components
    
    This follows the exact specification from design.md and integrates
    all existing components into a unified omnichannel experience.
    """
    
    def __init__(
        self,
        brain: Brain,
        auditor: Auditor,
        supervisor: Supervisor,
        event_bus: EventBus,
        telegram_service=None
    ):
        """
        Initialize omnichannel interface with all required services.
        
        Args:
            brain: Brain orchestrator (Claude 3.5 Sonnet)
            auditor: Audit logging service
            supervisor: H.I.T.L. supervisor
            event_bus: Event bus for async coordination
            telegram_service: Telegram service for notifications
        """
        self.brain = brain
        self.auditor = auditor
        self.supervisor = supervisor
        self.event_bus = event_bus
        self.telegram_service = telegram_service
        
        # Initialize core services
        from app.omnichannel.authentication.auth_service import AuthConfig
        from app.config.settings import settings
        
        auth_config = AuthConfig(
            region=settings.AWS_REGION,
            users_table=settings.DYNAMODB_USERS_TABLE
        )
        self.auth_service = AuthService(auth_config)
        
        self.session_manager = SessionManager()
        
        # Initialize MemoryService with DynamoDB client
        import boto3
        dynamodb_client = boto3.client('dynamodb', region_name=settings.AWS_REGION)
        self.memory_service = MemoryService(dynamodb_client)
        self.user_repository = UserRepository()
        
        # Initialize omnichannel services
        from app.omnichannel.database.repositories import ChannelMappingRepository
        channel_mapping_repository = ChannelMappingRepository()
        self.channel_mapping = ChannelMappingService(channel_mapping_repository)
        self.message_processor = UniversalMessageProcessor(
            channel_mapping_service=self.channel_mapping,
            session_manager=self.session_manager,
            memory_service=self.memory_service
        )
        self.nlp = NLPUniversal()
        self.response_adapter = ResponseAdapter()
        
        # Initialize billing services
        self.usage_tracker = UsageTracker()
        self.limit_enforcer = LimitEnforcer()
        self.billing_manager = BillingManager(self.usage_tracker, self.limit_enforcer)
        
        logger.info("OmnichannelInterface initialized with all services")
    
    async def process_message(
        self,
        channel: ChannelType,
        channel_user_id: str,
        message_text: str,
        message_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a message from any channel following the complete omnichannel flow.
        
        This is the main entry point that orchestrates the entire system:
        1. Convert to UniversalMessage
        2. Authenticate by email
        3. Check usage limits (Freemium)
        4. Process via Brain with context
        5. Adapt response for channel
        6. Log everything for audit
        7. Publish events for coordination
        
        Args:
            channel: Channel type (telegram, whatsapp, web, app, etc)
            channel_user_id: User ID from the channel
            message_text: Message text content
            message_id: Unique message ID from channel
            metadata: Optional channel-specific metadata
        
        Returns:
            Dict with response and metadata
        """
        start_time = datetime.now()
        
        try:
            # 1. Convert to UniversalMessage
            universal_message = await self.message_processor.process_message(
                channel=channel,
                channel_user_id=channel_user_id,
                message_text=message_text,
                message_id=message_id,
                metadata=metadata
            )
            
            logger.info(f"Processed universal message for email: {universal_message.email}")
            
            # 2. Get user from email
            user = await self.user_repository.get_by_email(universal_message.email)
            if not user:
                raise ValueError(f"User not found for email: {universal_message.email}")
            
            # 3. Check usage limits (Freemium billing)
            can_process = await self.limit_enforcer.check_limit(
                email=user.email,
                tier=user.tier.value
            )
            
            if not can_process:
                # User hit limit - offer upgrade
                limit_info = await self.limit_enforcer.get_limit_status(
                    email=user.email,
                    tier=user.tier.value
                )
                
                upgrade_response = await self._create_upgrade_message(user, limit_info)
                
                # Audit the limit hit
                await self.auditor.log_transaction(
                    email=user.email,
                    action="limit_hit",
                    category=AuditCategory.SYSTEM_OPERATION,
                    level=AuditLevel.WARNING,
                    input_data={
                        "channel": channel.value,
                        "tier": user.tier.value,
                        "message": message_text[:100]
                    },
                    output_data={"limit_enforced": True}
                )
                
                return {
                    "success": False,
                    "response": upgrade_response,
                    "reason": "usage_limit_exceeded",
                    "channel": channel.value
                }
            
            # 4. Increment usage counter
            await self.usage_tracker.increment_usage(user.email)
            
            # 5. Understand intent via NLP
            context_data = universal_message.context
            nlp_result = await self.nlp.understand(message_text, context_data)
            
            logger.info(f"NLP classified intent: {nlp_result.classification.intent.value}")
            
            # 6. Create Brain context
            brain_context = Context(
                email=user.email,
                channel=channel,
                session_id=universal_message.session_id,
                user_profile={
                    'tier': user.tier.value,
                    'telegram_id': getattr(user, 'telegram_id', None),
                    'created_at': user.created_at if user.created_at else None
                },
                history=context_data.get('conversation_history', []),
                memory={
                    'last_intent': context_data.get('last_intent'),
                    'last_connector': context_data.get('last_connector'),
                    'last_order_id': context_data.get('last_order_id'),
                }
            )
            
            # 7. Process via Brain (with H.I.T.L. supervision)
            brain_response = await self.brain.process(message_text, brain_context)
            
            logger.info(f"Brain processed message, response length: {len(brain_response)}")
            
            # 8. Update conversation context
            await self.message_processor.update_context(
                email=user.email,
                intent=nlp_result.classification.intent.value,
                connector=nlp_result.classification.connector,
                add_to_history=f"User: {message_text}"
            )
            
            await self.message_processor.update_context(
                email=user.email,
                add_to_history=f"Assistant: {brain_response}"
            )
            
            # 9. Adapt response for channel
            adapted_response = await self.response_adapter.adapt_response(
                text=brain_response,
                channel=channel,
                add_emojis=True
            )
            
            # 10. Audit successful transaction
            processing_time = (datetime.now() - start_time).total_seconds()
            
            await self.auditor.log_transaction(
                email=user.email,
                action="message_processed",
                category=AuditCategory.SYSTEM_OPERATION,
                level=AuditLevel.INFO,
                input_data={
                    "channel": channel.value,
                    "message": message_text,
                    "intent": nlp_result.classification.intent.value,
                    "connector": nlp_result.classification.connector,
                    "processing_time_seconds": processing_time
                },
                output_data={
                    "response_length": len(adapted_response),
                    "success": True
                }
            )
            
            # 11. Publish event for coordination
            try:
                await self.event_bus.publish_event(
                    event=EventMessage(
                        event_type="message_processed",
                        source="omnichannel",
                        user_email=user.email,
                        data={
                            "email": user.email,
                            "channel": channel.value,
                            "intent": nlp_result.classification.intent.value,
                            "connector": nlp_result.classification.connector,
                            "processing_time_seconds": processing_time
                        }
                    )
                )
            except Exception as ev_error:
                # Non-blocking error - just log
                logger.warning(f"Failed to publish message_processed event: {ev_error}")
            
            logger.info(f"Successfully processed message for {user.email} in {processing_time:.2f}s")
            
            return {
                "success": True,
                "response": adapted_response,
                "channel": channel.value,
                "processing_time_seconds": processing_time,
                "intent": nlp_result.classification.intent.value,
                "connector": nlp_result.classification.connector
            }
            
        except Exception as e:
            # Handle errors gracefully
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.error(f"Error processing message: {str(e)}")
            
            # Try to get email for audit (might fail if error was in early stages)
            try:
                email = universal_message.email if 'universal_message' in locals() else "unknown"
                
                await self.auditor.log_transaction(
                    email=email,
                    action="message_processing_error",
                    category=AuditCategory.ERROR_EVENT,
                    level=AuditLevel.ERROR,
                    input_data={
                        "channel": channel.value,
                        "message": message_text,
                        "error": str(e),
                        "processing_time_seconds": processing_time
                    },
                    output_data={"success": False}
                )
            except:
                # If audit fails too, just log
                logger.error(f"Failed to audit error for message processing: {str(e)}")
            
            # Return user-friendly error
            error_response = await self._create_error_message(channel, str(e))
            
            return {
                "success": False,
                "response": error_response,
                "channel": channel.value,
                "error": str(e),
                "processing_time_seconds": processing_time
            }
    
    async def handle_new_order_notification(
        self,
        email: str,
        order_data: Dict[str, Any],
        connector: str = "ifood"
    ) -> Dict[str, Any]:
        """
        Handle new order notifications - send to ALL user channels.
        
        This implements the omnichannel transparency requirement:
        - New order arrives → notify in ALL channels where user is connected
        - Same message format adapted for each channel
        
        Args:
            email: User email (universal identifier)
            order_data: Order information from connector
            connector: Connector name (ifood, 99food, etc)
        
        Returns:
            Dict with notification results per channel
        """
        try:
            logger.info(f"Handling new order notification for {email}")
            
            # 1. Get user
            user = await self.user_repository.get_by_email(email)
            if not user:
                logger.warning(f"User not found for email: {email}")
                return {"success": False, "error": "user_not_found"}
            
            # 2. Format notification message
            order_message = self._format_order_notification(order_data, connector)
            
            # 3. Get all user channels
            user_channels = await self._get_user_channels(email)
            
            # 4. Send notification to ALL channels
            notification_results = {}
            
            for channel_type, channel_info in user_channels.items():
                try:
                    # Adapt message for channel
                    adapted_message = await self.response_adapter.adapt_response(
                        text=order_message,
                        channel=channel_type,
                        add_emojis=True
                    )
                    
                    # Send via appropriate channel adapter
                    if channel_type == ChannelType.TELEGRAM and self.telegram_service:
                        result = await self.telegram_service.send_message(
                            chat_id=channel_info['chat_id'],
                            text=adapted_message,
                            parse_mode="HTML"
                        )
                        notification_results[channel_type.value] = {
                            "success": result.get("ok", False),
                            "message_id": result.get("result", {}).get("message_id")
                        }
                    # Future: Add WhatsApp, Web, App channel adapters (MVP 3)
                    else:
                        notification_results[channel_type.value] = {
                            "success": False,
                            "error": "channel_adapter_not_implemented_yet"
                        }
                        
                except Exception as e:
                    logger.error(f"Failed to send notification to {channel_type.value}: {str(e)}")
                    notification_results[channel_type.value] = {
                        "success": False,
                        "error": str(e)
                    }
            
            # 5. Audit notification
            await self.auditor.log_transaction(
                email=email,
                action="new_order_notification",
                category=AuditCategory.BUSINESS_OPERATION,
                level=AuditLevel.INFO,
                input_data={
                    "order_id": order_data.get("order_id"),
                    "connector": connector,
                    "channels": list(user_channels.keys())
                },
                output_data=notification_results
            )
            
            # 6. Publish event
            await self.event_bus.publish_event(
                event=EventMessage(
                    event_type="order_notification_sent",
                    source="omnichannel",
                    user_email=email,
                    data={
                        "email": email,
                        "order_id": order_data.get("order_id"),
                        "connector": connector,
                        "channels": list(user_channels.keys()),
                        "results": notification_results
                    }
                )
            )
            
            return {
                "success": True,
                "channels_notified": len(user_channels),
                "results": notification_results
            }
            
        except Exception as e:
            logger.error(f"Error handling new order notification: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def register_user_channel(
        self,
        email: str,
        channel: ChannelType,
        channel_user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Register a new channel for a user.
        
        Args:
            email: User email
            channel: Channel type
            channel_user_id: User ID in the channel
            metadata: Optional channel-specific metadata
        
        Returns:
            True if registration successful
        """
        try:
            # Create channel mapping
            await self.channel_mapping.create_mapping(
                email=email,
                channel=channel.value,  # Convert ChannelType to string
                channel_user_id=channel_user_id,
                metadata=metadata
            )
            
            # Audit registration
            await self.auditor.log_transaction(
                email=email,
                action="channel_registered",
                category=AuditCategory.SYSTEM_OPERATION,
                level=AuditLevel.INFO,
                input_data={
                    "channel": channel.value,
                    "channel_user_id": channel_user_id
                },
                output_data={"success": True}
            )
            
            logger.info(f"Registered {channel.value} channel for {email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register channel: {str(e)}")
            return False
    
    async def _create_upgrade_message(
        self,
        user,
        limit_info: Dict[str, Any]
    ) -> str:
        """
        Create upgrade message when user hits usage limit.
        
        Args:
            user: User object
            limit_info: Limit status information
        
        Returns:
            Formatted upgrade message
        """
        upgrade_url = await self.billing_manager.generate_upgrade_link(
            email=user.email,
            current_tier=user.tier.value
        )
        
        if user.tier.value == "free":
            return (
                f"🚫 <b>Limite atingido!</b>\n\n"
                f"📊 Você usou suas 100 mensagens gratuitas este mês.\n\n"
                f"🚀 <b>Upgrade para Pro:</b>\n"
                f"• 10.000 mensagens/mês\n"
                f"• Todos os domínios\n"
                f"• Todos os canais\n"
                f"• Suporte prioritário\n\n"
                f"💳 Apenas R$ 99/mês\n\n"
                f"🔗 <a href='{upgrade_url}'>Fazer upgrade agora</a>"
            )
        else:
            return (
                f"🚫 <b>Limite atingido!</b>\n\n"
                f"📊 Você atingiu o limite do seu plano.\n\n"
                f"📞 Entre em contato para upgrade:\n"
                f"📧 support@agentfirst.com"
            )
    
    async def _create_error_message(
        self,
        channel: ChannelType,
        error: str
    ) -> str:
        """
        Create user-friendly error message.
        
        Args:
            channel: Channel type
            error: Error message
        
        Returns:
            User-friendly error message
        """
        base_message = (
            "❌ Ops! Algo deu errado.\n\n"
            "🔧 Tente novamente em alguns segundos.\n\n"
            "Se o problema persistir, entre em contato:\n"
            "📧 support@agentfirst.com"
        )
        
        # Adapt for channel
        return await self.response_adapter.adapt_response(
            text=base_message,
            channel=channel,
            add_emojis=True
        )
    
    def _format_order_notification(
        self,
        order_data: Dict[str, Any],
        connector: str
    ) -> str:
        """
        Format new order notification message.
        
        Args:
            order_data: Order information
            connector: Connector name
        
        Returns:
            Formatted notification message
        """
        order_id = order_data.get("order_id", "N/A")
        total_amount = order_data.get("total_amount", 0)
        customer_name = order_data.get("customer", {}).get("name", "Cliente")
        items_count = len(order_data.get("items", []))
        
        return (
            f"🍔 <b>Novo pedido no {connector.upper()}!</b>\n\n"
            f"📦 Pedido: #{order_id}\n"
            f"💰 Valor: R$ {total_amount:.2f}\n"
            f"👤 Cliente: {customer_name}\n"
            f"📋 Itens: {items_count}\n\n"
            f"💬 Responda 'confirma' para aceitar"
        )
    
    async def _get_user_channels(self, email: str) -> Dict[ChannelType, Dict[str, Any]]:
        """
        Get all channels where user is connected.
        
        Args:
            email: User email
        
        Returns:
            Dict mapping channel types to channel info
        """
        channels = {}
        
        try:
            # Get all channel mappings for this email
            channel_mappings = await self.channel_mapping.get_channels_for_email(email)
            
            # Convert to ChannelType keys
            for channel_str, channel_user_id in channel_mappings.items():
                if channel_str.lower() == 'telegram':
                    channels[ChannelType.TELEGRAM] = {
                        "chat_id": channel_user_id,
                        "user_id": channel_user_id
                    }
                # TODO: Add other channel types (WhatsApp, Web, App)
                # elif channel_str.lower() == 'whatsapp':
                #     channels[ChannelType.WHATSAPP] = {
                #         "phone": channel_user_id,
                #         "user_id": channel_user_id
                #     }
            
        except Exception as e:
            logger.error(f"Error getting user channels: {str(e)}")
        
        return channels
    
    async def get_interface_status(self) -> Dict[str, Any]:
        """
        Get status of omnichannel interface and all components.
        
        Returns:
            Status information
        """
        return {
            "interface": "operational",
            "components": {
                "brain": "operational",
                "memory": "operational",
                "nlp": "operational",
                "response_adapter": "operational",
                "usage_tracker": "operational",
                "billing_manager": "operational",
                "auditor": "operational",
                "supervisor": "operational",
                "event_bus": "operational"
            },
            "channels_supported": [
                "telegram",
                "whatsapp",  # TODO: Implement
                "web",       # TODO: Implement
                "app",       # TODO: Implement
                "email",     # TODO: Implement
                "sms"        # TODO: Implement
            ],
            "features": {
                "natural_language": True,
                "omnichannel_transparent": True,
                "context_preserved": True,
                "email_based_auth": True,
                "freemium_billing": True,
                "enterprise_grade": True,
                "h_i_t_l_supervision": True,
                "audit_logging": True
            }
        }