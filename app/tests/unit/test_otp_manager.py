
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta, timezone
from app.omnichannel.authentication.otp_manager import OTPManager

@pytest.fixture
def mock_email_service():
    return Mock()

@pytest.fixture
def mock_dynamodb_table():
    table = Mock()
    table.put_item = Mock()
    table.get_item = Mock()
    table.delete_item = Mock()
    table.update_item = Mock()
    return table

@pytest.fixture
def otp_manager(mock_email_service, mock_dynamodb_table):
    with patch("boto3.resource") as mock_resource:
        mock_resource.return_value.Table.return_value = mock_dynamodb_table
        # Mock settings to avoid environment errors
        with patch("app.omnichannel.authentication.otp_manager.settings") as mock_settings:
            mock_settings.AWS_REGION = "us-east-1"
            mock_settings.DYNAMODB_OTP_TABLE = "test-otp-table"
            
            manager = OTPManager(mock_email_service)
            # Override table with our mock fixture explicitly just in case
            manager.table = mock_dynamodb_table
            return manager

@pytest.mark.asyncio
async def test_generate_otp(otp_manager):
    otp = otp_manager.generate_otp()
    assert len(otp) == 6
    assert otp.isdigit()

@pytest.mark.asyncio
async def test_send_otp_success(otp_manager, mock_email_service, mock_dynamodb_table):
    mock_email_service.send_otp_email.return_value = True
    email = "test@example.com"
    
    result = await otp_manager.send_otp(email)
    
    assert result is True
    mock_dynamodb_table.put_item.assert_called_once()
    mock_email_service.send_otp_email.assert_called_once()
    
    # Check if put_item was called with correct arguments
    call_args = mock_dynamodb_table.put_item.call_args[1]["Item"]
    assert call_args["email"] == email
    assert len(call_args["otp_code"]) == 6
    assert call_args["attempts"] == 0

@pytest.mark.asyncio
async def test_verify_otp_success(otp_manager, mock_dynamodb_table):
    email = "test@example.com"
    code = "123456"
    expires_at = int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp())
    
    mock_dynamodb_table.get_item.return_value = {
        "Item": {
            "email": email,
            "otp_code": code,
            "expires_at": expires_at,
            "attempts": 0
        }
    }
    
    result = await otp_manager.verify_otp(email, code)
    
    assert result["success"] is True
    assert "sucesso" in result["message"].lower()
    mock_dynamodb_table.delete_item.assert_called_with(Key={"email": email})

@pytest.mark.asyncio
async def test_verify_otp_wrong_code(otp_manager, mock_dynamodb_table):
    email = "test@example.com"
    stored_code = "123456"
    wrong_code = "654321"
    expires_at = int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp())
    
    mock_dynamodb_table.get_item.return_value = {
        "Item": {
            "email": email,
            "otp_code": stored_code,
            "expires_at": expires_at,
            "attempts": 0
        }
    }
    
    result = await otp_manager.verify_otp(email, wrong_code)
    
    assert result["success"] is False
    assert "incorreto" in result["message"].lower()
    mock_dynamodb_table.update_item.assert_called_once()  # Should increment attempts

@pytest.mark.asyncio
async def test_verify_otp_expired(otp_manager, mock_dynamodb_table):
    email = "test@example.com"
    code = "123456"
    # Create expired timestamp
    expires_at = int((datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp())
    
    mock_dynamodb_table.get_item.return_value = {
        "Item": {
            "email": email,
            "otp_code": code,
            "expires_at": expires_at,
            "attempts": 0
        }
    }
    
    result = await otp_manager.verify_otp(email, code)
    
    assert result["success"] is False
    assert "expirou" in result["message"].lower()

@pytest.mark.asyncio
async def test_verify_otp_max_attempts(otp_manager, mock_dynamodb_table):
    email = "test@example.com"
    code = "123456"
    expires_at = int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp())
    
    mock_dynamodb_table.get_item.return_value = {
        "Item": {
            "email": email,
            "otp_code": code,
            "expires_at": expires_at,
            "attempts": 3
        }
    }
    
    result = await otp_manager.verify_otp(email, code)
    
    assert result["success"] is False
    assert "invalidado" in result["message"].lower()
    mock_dynamodb_table.delete_item.assert_called_with(Key={"email": email})
