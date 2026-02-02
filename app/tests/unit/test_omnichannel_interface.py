"""
Unit tests for OmnichannelInterface.

Tests the main omnichannel orchestrator that handles messages from any channel
with unified context by email.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.omnichannel.interface import OmnichannelInterface
from app.omnichannel.models import ChannelType, UniversalMessage
from app.omnichannel.database.models import User, UserTier
from app.core.brain import Brain, Context
from app.core.auditor import Auditor
from app.core.supervisor import Supervisor
from app.core.event_bus import EventBus


@pytest.mark.unit
class TestOmnichannelInterface:
    """Unit tests for OmnichannelInterface"""
    
    @pytest.fixture
    def mock_brain(self):
        """Mock Brain service"""
        brain = AsyncMock(spec=Brain)
        brain.process.return_value = "Mocked brain response"
        return brain
    
    @pytest.fixture
    def mock_auditor(self):
        """Mock Auditor service"""
        auditor = AsyncMock(spec=Auditor)
        return auditor
    
    @pytest.fixture
    def mock_supervisor(self):
        """Mock Supervisor service"""
        supervisor = AsyncMock(spec=Supervisor)
        return supervisor
    
    @pytest.fixture
    def mock_event_bus(self):
        """Mock EventBus service"""
        event_bus = AsyncMock(spec=EventBus)
        return event_bus
    
    @pytest.fixture
    def mock_telegram_service(self):
        """Mock Telegram service"""
        telegram = AsyncMock()
        telegram.send_message.return_value = {"ok": True, "result": {"message_id": 123}}
        return telegram
    
    @pytest.fixture
    def sample_user(self):
        """Sample user for testing"""
        return User(
            email="test@example.com",
            tier=UserTier.FREE,
            telegram_id=123456789,
            created_at=datetime.now()
        )
    
    @pytest.fixture
    def omnichannel_interface(self, mock_brain, mock_auditor, mock_supervisor, mock_event_bus, mock_telegram_service):
        """Create OmnichannelInterface instance with mocked dependencies"""
        return OmnichannelInterface(
            brain=mock_brain,
            auditor=mock_auditor,
            supervisor=mock_supervisor,
            event_bus=mock_event_bus,
            telegram_service=mock_telegram_service
        )
    
    @pytest.mark.asyncio
    async def test_process_message_success(self, omnichannel_interface, sample_user):
        """Test successful message processing"""
        # Mock dependencies
        with patch.object(omnichannel_interface.message_processor, 'process_message') as mock_process:
            mock_process.return_value = UniversalMessage(
                text="Quantos pedidos tenho?",
                channel=ChannelType.TELEGRAM,
                channel_user_id="123456789",
                message_id="msg_123",
                timestamp=datetime.now(),
                email="test@example.com",
                session_id="session_123",
                context={"last_intent": None},
                metadata={}
            )
            
            with patch.object(omnichannel_interface.user_repository, 'get_by_email') as mock_get_user:
                mock_get_user.return_value = sample_user
                
                with patch.object(omnichannel_interface.limit_enforcer, 'check_limit') as mock_check_limit:
                    mock_check_limit.return_value = True
                    
                    with patch.object(omnichannel_interface.usage_tracker, 'increment_usage') as mock_increment:
                        mock_increment.return_value = None
                        
                        with patch.object(omnichannel_interface.nlp, 'understand') as mock_nlp:
                            from app.omnichannel.nlp_models import IntentType, IntentClassification, NLPResult
                            mock_nlp.return_value = NLPResult(
                                classification=IntentClassification(
                                    intent=IntentType.CHECK_ORDERS,
                                    confidence=0.95,
                                    raw_text="Quantos pedidos tenho?",
                                    domain="retail",
                                    connector="ifood"
                                ),
                                language="pt-BR",
                                confidence_overall=0.95
                            )
                            
                            with patch.object(omnichannel_interface.response_adapter, 'adapt_response') as mock_adapt:
                                mock_adapt.return_value = "📦 Você tem 3 pedidos no iFood"
                                
                                # Test
                                result = await omnichannel_interface.process_message(
                                    channel=ChannelType.TELEGRAM,
                                    channel_user_id="123456789",
                                    message_text="Quantos pedidos tenho?",
                                    message_id="msg_123"
                                )
                                
                                # Assertions
                                assert result["success"] is True
                                assert "📦 Você tem 3 pedidos no iFood" in result["response"]
                                assert result["channel"] == "telegram"
                                assert result["intent"] == "check_orders"
                                assert result["connector"] == "ifood"
                                assert "processing_time_seconds" in result
                                
                                # Verify services were called
                                mock_process.assert_called_once()
                                mock_get_user.assert_called_once_with("test@example.com")
                                mock_check_limit.assert_called_once_with(email="test@example.com", tier="free")
                                mock_increment.assert_called_once_with("test@example.com")
                                omnichannel_interface.brain.process.assert_called_once()
                                omnichannel_interface.auditor.log_transaction.assert_called()
                                omnichannel_interface.event_bus.publish_event.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_message_usage_limit_exceeded(self, omnichannel_interface, sample_user):
        """Test message processing when usage limit is exceeded"""
        # Mock dependencies
        with patch.object(omnichannel_interface.message_processor, 'process_message') as mock_process:
            mock_process.return_value = UniversalMessage(
                text="Quantos pedidos tenho?",
                channel=ChannelType.TELEGRAM,
                channel_user_id="123456789",
                message_id="msg_123",
                timestamp=datetime.now(),
                email="test@example.com",
                session_id="session_123",
                context={},
                metadata={}
            )
            
            with patch.object(omnichannel_interface.user_repository, 'get_by_email') as mock_get_user:
                mock_get_user.return_value = sample_user
                
                with patch.object(omnichannel_interface.limit_enforcer, 'check_limit') as mock_check_limit:
                    mock_check_limit.return_value = False
                    
                    with patch.object(omnichannel_interface.limit_enforcer, 'get_limit_status') as mock_limit_status:
                        mock_limit_status.return_value = {
                            "messages_used": 100,
                            "messages_remaining": 0,
                            "limit": 100
                        }
                        
                        with patch.object(omnichannel_interface.billing_manager, 'generate_upgrade_link') as mock_upgrade:
                            mock_upgrade.return_value = "https://agentfirst.com/upgrade?email=test@example.com"
                            
                            # Test
                            result = await omnichannel_interface.process_message(
                                channel=ChannelType.TELEGRAM,
                                channel_user_id="123456789",
                                message_text="Quantos pedidos tenho?",
                                message_id="msg_123"
                            )
                            
                            # Assertions
                            assert result["success"] is False
                            assert result["reason"] == "usage_limit_exceeded"
                            assert "Limite atingido" in result["response"]
                            assert "upgrade" in result["response"].lower()
                            
                            # Verify audit was called for limit hit
                            omnichannel_interface.auditor.log_transaction.assert_called()
                            
                            # Verify brain was NOT called
                            omnichannel_interface.brain.process.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_process_message_error_handling(self, omnichannel_interface):
        """Test error handling in message processing"""
        # Mock message processor to raise exception
        with patch.object(omnichannel_interface.message_processor, 'process_message') as mock_process:
            mock_process.side_effect = Exception("Test error")
            
            with patch.object(omnichannel_interface.response_adapter, 'adapt_response') as mock_adapt:
                mock_adapt.return_value = "❌ Ops! Algo deu errado."
                
                # Test
                result = await omnichannel_interface.process_message(
                    channel=ChannelType.TELEGRAM,
                    channel_user_id="123456789",
                    message_text="Quantos pedidos tenho?",
                    message_id="msg_123"
                )
                
                # Assertions
                assert result["success"] is False
                assert "❌ Ops! Algo deu errado." in result["response"]
                assert result["error"] == "Test error"
                assert "processing_time_seconds" in result
    
    @pytest.mark.asyncio
    async def test_handle_new_order_notification(self, omnichannel_interface, sample_user):
        """Test new order notification to all channels"""
        order_data = {
            "order_id": "order_123",
            "total_amount": 45.50,
            "customer": {"name": "João Silva"},
            "items": [{"name": "Hambúrguer", "quantity": 1}]
        }
        
        # Mock dependencies
        with patch.object(omnichannel_interface.user_repository, 'get_by_email') as mock_get_user:
            mock_get_user.return_value = sample_user
            
            with patch.object(omnichannel_interface, '_get_user_channels') as mock_get_channels:
                mock_get_channels.return_value = {
                    ChannelType.TELEGRAM: {"chat_id": "123456789", "user_id": "123456789"}
                }
                
                with patch.object(omnichannel_interface.response_adapter, 'adapt_response') as mock_adapt:
                    mock_adapt.return_value = "🍔 Novo pedido no IFOOD! 📦 Pedido: #order_123"
                    
                    # Test
                    result = await omnichannel_interface.handle_new_order_notification(
                        email="test@example.com",
                        order_data=order_data,
                        connector="ifood"
                    )
                    
                    # Assertions
                    assert result["success"] is True
                    assert result["channels_notified"] == 1
                    assert "telegram" in result["results"]
                    assert result["results"]["telegram"]["success"] is True
                    
                    # Verify Telegram service was called
                    omnichannel_interface.telegram_service.send_message.assert_called_once()
                    
                    # Verify audit and event bus were called
                    omnichannel_interface.auditor.log_transaction.assert_called()
                    omnichannel_interface.event_bus.publish_event.assert_called()
    
    @pytest.mark.asyncio
    async def test_register_user_channel(self, omnichannel_interface):
        """Test registering a new channel for a user"""
        # Mock channel mapping service
        with patch.object(omnichannel_interface.channel_mapping, 'create_mapping') as mock_create:
            mock_create.return_value = None
            
            # Test
            result = await omnichannel_interface.register_user_channel(
                email="test@example.com",
                channel=ChannelType.TELEGRAM,
                channel_user_id="123456789",
                metadata={"chat_id": "123456789"}
            )
            
            # Assertions
            assert result is True
            
            # Verify mapping was created
            mock_create.assert_called_once_with(
                email="test@example.com",
                channel=ChannelType.TELEGRAM,
                channel_user_id="123456789",
                metadata={"chat_id": "123456789"}
            )
            
            # Verify audit was called
            omnichannel_interface.auditor.log_transaction.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_interface_status(self, omnichannel_interface):
        """Test getting interface status"""
        status = await omnichannel_interface.get_interface_status()
        
        # Assertions
        assert status["interface"] == "operational"
        assert "components" in status
        assert "channels_supported" in status
        assert "features" in status
        
        # Check components
        components = status["components"]
        assert components["brain"] == "operational"
        assert components["memory"] == "operational"
        assert components["nlp"] == "operational"
        assert components["auditor"] == "operational"
        
        # Check features
        features = status["features"]
        assert features["natural_language"] is True
        assert features["omnichannel_transparent"] is True
        assert features["context_preserved"] is True
        assert features["email_based_auth"] is True
        assert features["freemium_billing"] is True
        assert features["enterprise_grade"] is True
    
    def test_format_order_notification(self, omnichannel_interface):
        """Test order notification formatting"""
        order_data = {
            "order_id": "order_123",
            "total_amount": 45.50,
            "customer": {"name": "João Silva"},
            "items": [{"name": "Hambúrguer"}, {"name": "Refrigerante"}]
        }
        
        message = omnichannel_interface._format_order_notification(order_data, "ifood")
        
        # Assertions
        assert "🍔" in message
        assert "Novo pedido no IFOOD" in message
        assert "order_123" in message
        assert "R$ 45.50" in message
        assert "João Silva" in message
        assert "2" in message  # items count
        assert "confirma" in message.lower()
    
    @pytest.mark.asyncio
    async def test_create_upgrade_message_free_tier(self, omnichannel_interface, sample_user):
        """Test upgrade message creation for free tier user"""
        limit_info = {
            "messages_used": 100,
            "messages_remaining": 0,
            "limit": 100
        }
        
        with patch.object(omnichannel_interface.billing_manager, 'generate_upgrade_link') as mock_upgrade:
            mock_upgrade.return_value = "https://agentfirst.com/upgrade"
            
            message = await omnichannel_interface._create_upgrade_message(sample_user, limit_info)
            
            # Assertions
            assert "Limite atingido" in message
            assert "100 mensagens gratuitas" in message
            assert "Upgrade para Pro" in message
            assert "10.000 mensagens/mês" in message
            assert "R$ 99/mês" in message
            assert "https://agentfirst.com/upgrade" in message
    
    @pytest.mark.asyncio
    async def test_create_error_message(self, omnichannel_interface):
        """Test error message creation"""
        with patch.object(omnichannel_interface.response_adapter, 'adapt_response') as mock_adapt:
            mock_adapt.return_value = "❌ Ops! Algo deu errado."
            
            message = await omnichannel_interface._create_error_message(
                ChannelType.TELEGRAM,
                "Test error"
            )
            
            # Assertions
            assert message == "❌ Ops! Algo deu errado."
            mock_adapt.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_channels(self, omnichannel_interface, sample_user):
        """Test getting user channels"""
        with patch.object(omnichannel_interface.channel_mapping, 'get_channels_for_email') as mock_get_channels:
            mock_get_channels.return_value = {"telegram": "123456789"}
            
            channels = await omnichannel_interface._get_user_channels("test@example.com")
            
            # Assertions
            assert ChannelType.TELEGRAM in channels
            assert channels[ChannelType.TELEGRAM]["chat_id"] == "123456789"
            assert channels[ChannelType.TELEGRAM]["user_id"] == "123456789"


@pytest.mark.unit
class TestOmnichannelInterfaceEdgeCases:
    """Edge case tests for OmnichannelInterface"""
    
    @pytest.fixture
    def omnichannel_interface(self):
        """Create minimal OmnichannelInterface for edge case testing"""
        brain = AsyncMock(spec=Brain)
        auditor = AsyncMock(spec=Auditor)
        supervisor = AsyncMock(spec=Supervisor)
        event_bus = AsyncMock(spec=EventBus)
        
        return OmnichannelInterface(
            brain=brain,
            auditor=auditor,
            supervisor=supervisor,
            event_bus=event_bus
        )
    
    @pytest.mark.asyncio
    async def test_process_message_user_not_found(self, omnichannel_interface):
        """Test processing message when user is not found"""
        with patch.object(omnichannel_interface.message_processor, 'process_message') as mock_process:
            mock_process.return_value = UniversalMessage(
                text="Test message",
                channel=ChannelType.TELEGRAM,
                channel_user_id="999999999",
                message_id="msg_123",
                timestamp=datetime.now(),
                email="nonexistent@example.com",
                session_id="session_123",
                context={},
                metadata={}
            )
            
            with patch.object(omnichannel_interface.user_repository, 'get_by_email') as mock_get_user:
                mock_get_user.return_value = None
                
                with patch.object(omnichannel_interface, '_create_error_message') as mock_error:
                    mock_error.return_value = "❌ Usuário não encontrado"
                    
                    # Test
                    result = await omnichannel_interface.process_message(
                        channel=ChannelType.TELEGRAM,
                        channel_user_id="999999999",
                        message_text="Test message",
                        message_id="msg_123"
                    )
                    
                    # Assertions
                    assert result["success"] is False
                    assert "Usuário não encontrado" in result["response"]
    
    @pytest.mark.asyncio
    async def test_handle_new_order_notification_user_not_found(self, omnichannel_interface):
        """Test new order notification when user is not found"""
        with patch.object(omnichannel_interface.user_repository, 'get_by_email') as mock_get_user:
            mock_get_user.return_value = None
            
            # Test
            result = await omnichannel_interface.handle_new_order_notification(
                email="nonexistent@example.com",
                order_data={"order_id": "test"},
                connector="ifood"
            )
            
            # Assertions
            assert result["success"] is False
            assert result["error"] == "user_not_found"
    
    @pytest.mark.asyncio
    async def test_register_user_channel_failure(self, omnichannel_interface):
        """Test channel registration failure"""
        with patch.object(omnichannel_interface.channel_mapping, 'create_mapping') as mock_create:
            mock_create.side_effect = Exception("Database error")
            
            # Test
            result = await omnichannel_interface.register_user_channel(
                email="test@example.com",
                channel=ChannelType.TELEGRAM,
                channel_user_id="123456789"
            )
            
            # Assertions
            assert result is False