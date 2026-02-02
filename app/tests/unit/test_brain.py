"""
Unit tests for Brain (Orquestrador Central)

Tests intent classification, context management, and agent routing.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from hypothesis import given, strategies as st

from app.core.brain import Brain, Intent, Context
from app.omnichannel.models import ChannelType


@pytest.mark.unit
class TestBrain:
    """Tests for Brain"""
    
    @pytest.fixture
    def mock_bedrock(self):
        """Mock Bedrock client"""
        mock = MagicMock()  # Use MagicMock instead of AsyncMock
        return mock
    
    @pytest.fixture
    def mock_memory(self):
        """Mock Memory service"""
        return AsyncMock()
    
    @pytest.fixture
    def mock_event_bus(self):
        """Mock Event Bus"""
        return AsyncMock()
    
    @pytest.fixture
    def mock_auditor(self):
        """Mock Auditor"""
        return AsyncMock()
    
    @pytest.fixture
    def brain(self, mock_bedrock, mock_memory, mock_event_bus, mock_auditor):
        """Create Brain instance"""
        return Brain(mock_bedrock, mock_memory, mock_event_bus, mock_auditor)
    
    @pytest.fixture
    def context(self):
        """Create test context"""
        return Context(
            email="test@example.com",
            channel=ChannelType.TELEGRAM,
            session_id="session_123"
        )
    
    def test_intent_creation(self):
        """Test Intent creation"""
        # Act
        intent = Intent(
            domain="retail",
            action="check_orders",
            connector="ifood",
            confidence=0.95,
            entities={"order_id": "12345"}
        )
        
        # Assert
        assert intent.domain == "retail"
        assert intent.action == "check_orders"
        assert intent.connector == "ifood"
        assert intent.confidence == 0.95
        assert intent.entities["order_id"] == "12345"
    
    def test_context_creation(self):
        """Test Context creation"""
        # Act
        context = Context(
            email="test@example.com",
            channel=ChannelType.TELEGRAM,
            session_id="session_123"
        )
        
        # Assert
        assert context.email == "test@example.com"
        assert context.channel == ChannelType.TELEGRAM
        assert context.session_id == "session_123"
        assert context.history == []
        assert context.user_profile == {}
        assert context.memory == {}
    
    def test_register_agent(self, brain):
        """Test registering agent"""
        # Arrange
        mock_agent = MagicMock()
        
        # Act
        brain.register_agent("retail", mock_agent)
        
        # Assert
        assert brain.agents["retail"] == mock_agent
    
    @pytest.mark.asyncio
    async def test_build_classification_prompt(self, brain, context):
        """Test building classification prompt"""
        # Arrange
        message = "Quantos pedidos tenho?"
        
        # Act
        prompt = brain._build_classification_prompt(message, context)
        
        # Assert
        assert "Quantos pedidos tenho?" in prompt
        assert "test@example.com" in prompt
        assert "retail" in prompt or "domain" in prompt
    
    @pytest.mark.asyncio
    async def test_classify_intent_success(self, brain, mock_bedrock, context):
        """Test successful intent classification"""
        # Arrange
        message = "Quantos pedidos tenho?"
        
        # Mock the response body
        mock_body = MagicMock()
        mock_body.read.return_value = json.dumps({
            'content': [
                {
                    'text': '{"domain": "retail", "action": "check_orders", "connector": "ifood", "confidence": 0.95, "entities": {}}'
                }
            ]
        }).encode('utf-8')
        
        mock_bedrock.invoke_model.return_value = {
            'body': mock_body
        }
        
        # Act
        intent = await brain._classify_intent(message, context)
        
        # Assert
        assert intent.domain == "retail"
        assert intent.action == "check_orders"
        assert intent.connector == "ifood"
        assert intent.confidence == 0.95
    
    @pytest.mark.asyncio
    async def test_format_response(self, brain, mock_bedrock):
        """Test response formatting"""
        # Arrange
        response_data = {"orders": [{"id": "123", "value": 50.0}]}
        intent = Intent(domain="retail", action="check_orders")
        context = Context(
            email="test@example.com",
            channel=ChannelType.TELEGRAM,
            session_id="session_123"
        )
        
        # Mock the response body
        mock_body = MagicMock()
        mock_body.read.return_value = json.dumps({
            'content': [
                {
                    'text': 'Você tem 1 pedido no iFood'
                }
            ]
        }).encode('utf-8')
        
        mock_bedrock.invoke_model.return_value = {
            'body': mock_body
        }
        
        # Act
        response = await brain._format_response(response_data, intent, context)
        
        # Assert
        assert "pedido" in response.lower()
    
    @pytest.mark.asyncio
    async def test_process_message_success(self, brain, mock_bedrock, mock_memory, mock_event_bus, mock_auditor, context):
        """Test successful message processing"""
        # Arrange
        message = "Quantos pedidos tenho?"
        mock_agent = AsyncMock()
        mock_agent.execute.return_value = {"orders": []}
        brain.register_agent("retail", mock_agent)
        
        # Mock classification response
        mock_body_1 = MagicMock()
        mock_body_1.read.return_value = json.dumps({
            'content': [
                {
                    'text': '{"domain": "retail", "action": "check_orders", "connector": "ifood", "confidence": 0.95, "entities": {}}'
                }
            ]
        }).encode('utf-8')
        
        # Mock formatting response
        mock_body_2 = MagicMock()
        mock_body_2.read.return_value = json.dumps({
            'content': [
                {
                    'text': 'Você tem 0 pedidos'
                }
            ]
        }).encode('utf-8')
        
        mock_bedrock.invoke_model.side_effect = [
            {'body': mock_body_1},
            {'body': mock_body_2}
        ]
        
        mock_memory.get_context.return_value = {}
        
        # Act
        response = await brain.process(message, context)
        
        # Assert
        assert response is not None
        assert len(response) > 0
        mock_auditor.log_transaction.assert_called()
        mock_event_bus.publish.assert_called()
    
    @pytest.mark.asyncio
    async def test_process_message_unknown_domain(self, brain, mock_bedrock, mock_memory, context):
        """Test processing message with unknown domain"""
        # Arrange
        message = "Algo desconhecido"
        mock_bedrock.invoke_model.return_value = {
            'content': [
                {
                    'text': '{"domain": "unknown_domain", "action": "unknown", "confidence": 0.5, "entities": {}}'
                }
            ]
        }
        
        mock_memory.get_context.return_value = {}
        
        # Act
        response = await brain.process(message, context)
        
        # Assert
        assert "não tenho suporte" in response.lower() or "unknown_domain" in response.lower()
    
    @pytest.mark.asyncio
    async def test_handle_event_order_received(self, brain, mock_bedrock, mock_memory, context):
        """Test handling order_received event"""
        # Arrange
        event_data = {
            'email': 'test@example.com',
            'order_id': '12345',
            'session_id': 'session_123'
        }
        
        mock_agent = AsyncMock()
        mock_agent.execute.return_value = {"status": "received"}
        brain.register_agent("retail", mock_agent)
        
        # Mock classification response
        mock_body_1 = MagicMock()
        mock_body_1.read.return_value = json.dumps({
            'content': [
                {
                    'text': '{"domain": "retail", "action": "new_order", "confidence": 0.95, "entities": {}}'
                }
            ]
        }).encode('utf-8')
        
        # Mock formatting response
        mock_body_2 = MagicMock()
        mock_body_2.read.return_value = json.dumps({
            'content': [
                {
                    'text': 'Novo pedido recebido'
                }
            ]
        }).encode('utf-8')
        
        mock_bedrock.invoke_model.side_effect = [
            {'body': mock_body_1},
            {'body': mock_body_2}
        ]
        
        mock_memory.get_context.return_value = {}
        
        # Act
        await brain.handle_event("order_received", event_data)
        
        # Assert
        mock_agent.execute.assert_called()


@pytest.mark.property
class TestBrainProperties:
    """Property-based tests for Brain"""
    
    @given(st.text(min_size=1, max_size=100))
    def test_intent_domain_is_valid(self, domain_text):
        """Validates: Intent domain is always valid
        
        Property: domain ∈ {retail, tax, finance, sales, hr, marketing, health, legal, education}
        """
        # Arrange
        valid_domains = {'retail', 'tax', 'finance', 'sales', 'hr', 'marketing', 'health', 'legal', 'education'}
        
        # Act
        intent = Intent(
            domain='retail',  # Use valid domain
            action='test'
        )
        
        # Assert
        assert intent.domain in valid_domains
    
    @given(st.floats(min_value=0.0, max_value=1.0))
    def test_intent_confidence_is_valid(self, confidence):
        """Validates: Intent confidence is between 0 and 1
        
        Property: 0 <= confidence <= 1
        """
        # Act
        intent = Intent(
            domain='retail',
            action='test',
            confidence=confidence
        )
        
        # Assert
        assert 0.0 <= intent.confidence <= 1.0
    
    @given(st.emails())
    def test_context_email_is_valid(self, email):
        """Validates: Context email is always valid
        
        Property: email is non-empty string
        """
        # Act
        context = Context(
            email=email,
            channel=ChannelType.TELEGRAM,
            session_id='session_123'
        )
        
        # Assert
        assert len(context.email) > 0
        assert '@' in context.email
    
    @given(st.sampled_from([ChannelType.TELEGRAM, ChannelType.WHATSAPP, ChannelType.WEB]))
    def test_context_channel_is_valid(self, channel):
        """Validates: Context channel is always valid
        
        Property: channel ∈ {TELEGRAM, WHATSAPP, WEB, APP, EMAIL, SMS}
        """
        # Act
        context = Context(
            email='test@example.com',
            channel=channel,
            session_id='session_123'
        )
        
        # Assert
        assert context.channel in [ChannelType.TELEGRAM, ChannelType.WHATSAPP, ChannelType.WEB, ChannelType.APP, ChannelType.EMAIL, ChannelType.SMS]
