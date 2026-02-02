"""
Unit tests for Auditor

Tests the audit system functionality:
- Immutable logging
- Compliance reports
- Data retention
- Integrity verification
- LGPD compliance
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import json
import hashlib
import hmac

from app.core.auditor import (
    Auditor, AuditEntry, AuditLevel, AuditCategory, ComplianceReport
)


@pytest.mark.unit
class TestAuditEntry:
    """Unit tests for AuditEntry"""

    def test_audit_entry_creation(self):
        """Test AuditEntry creation and hash calculation"""
        entry = AuditEntry(
            audit_id="test_audit_123",
            timestamp="2025-01-26T15:00:00Z",
            timezone="UTC",
            user_email="test@example.com",
            user_id=None,
            session_id="session_123",
            channel="telegram",
            agent="retail_agent",
            action="check_orders",
            category=AuditCategory.BUSINESS_OPERATION,
            level=AuditLevel.INFO,
            input_data={"connector": "ifood"},
            output_data={"orders": 3},
            context={"tier": "free"},
            status="success",
            error_message=None,
            duration_ms=150.5,
            request_id="req_123",
            correlation_id="corr_123",
            parent_audit_id=None,
            sensitive_data=False,
            pii_data=False,
            financial_data=True,
            hash="",
            signature=None
        )
        
        # Hash should be calculated automatically
        assert entry.hash != ""
        assert len(entry.hash) == 64  # SHA-256 hex length
        
        # Test properties
        assert entry.audit_id == "test_audit_123"
        assert entry.user_email == "test@example.com"
        assert entry.agent == "retail_agent"
        assert entry.action == "check_orders"
        assert entry.category == AuditCategory.BUSINESS_OPERATION
        assert entry.level == AuditLevel.INFO
        assert entry.status == "success"
        assert entry.financial_data is True

    def test_audit_entry_hash_calculation(self):
        """Test hash calculation for integrity"""
        entry = AuditEntry(
            audit_id="test_audit_123",
            timestamp="2025-01-26T15:00:00Z",
            timezone="UTC",
            user_email="test@example.com",
            user_id=None,
            session_id="session_123",
            channel="telegram",
            agent="retail_agent",
            action="check_orders",
            category=AuditCategory.BUSINESS_OPERATION,
            level=AuditLevel.INFO,
            input_data={"connector": "ifood"},
            output_data={"orders": 3},
            context={"tier": "free"},
            status="success",
            error_message=None,
            duration_ms=150.5,
            request_id="req_123",
            correlation_id="corr_123",
            parent_audit_id=None,
            sensitive_data=False,
            pii_data=False,
            financial_data=True,
            hash="",
            signature=None
        )
        
        # Calculate expected hash
        hash_data = {
            'audit_id': entry.audit_id,
            'timestamp': entry.timestamp,
            'user_email': entry.user_email,
            'agent': entry.agent,
            'action': entry.action,
            'input_data': entry.input_data,
            'output_data': entry.output_data,
            'status': entry.status
        }
        
        hash_string = json.dumps(hash_data, sort_keys=True, separators=(',', ':'))
        expected_hash = hashlib.sha256(hash_string.encode('utf-8')).hexdigest()
        
        assert entry.hash == expected_hash

    def test_audit_entry_integrity_verification(self):
        """Test integrity verification"""
        entry = AuditEntry(
            audit_id="test_audit_123",
            timestamp="2025-01-26T15:00:00Z",
            timezone="UTC",
            user_email="test@example.com",
            user_id=None,
            session_id="session_123",
            channel="telegram",
            agent="retail_agent",
            action="check_orders",
            category=AuditCategory.BUSINESS_OPERATION,
            level=AuditLevel.INFO,
            input_data={"connector": "ifood"},
            output_data={"orders": 3},
            context={"tier": "free"},
            status="success",
            error_message=None,
            duration_ms=150.5,
            request_id="req_123",
            correlation_id="corr_123",
            parent_audit_id=None,
            sensitive_data=False,
            pii_data=False,
            financial_data=True,
            hash="",
            signature=None
        )
        
        # Should verify as intact
        assert entry.verify_integrity() is True
        
        # Tamper with data
        entry.output_data = {"orders": 5}  # Changed from 3 to 5
        
        # Should detect tampering
        assert entry.verify_integrity() is False

    def test_audit_entry_serialization(self):
        """Test serialization to dict and JSON"""
        entry = AuditEntry(
            audit_id="test_audit_123",
            timestamp="2025-01-26T15:00:00Z",
            timezone="UTC",
            user_email="test@example.com",
            user_id=None,
            session_id="session_123",
            channel="telegram",
            agent="retail_agent",
            action="check_orders",
            category=AuditCategory.BUSINESS_OPERATION,
            level=AuditLevel.INFO,
            input_data={"connector": "ifood"},
            output_data={"orders": 3},
            context={"tier": "free"},
            status="success",
            error_message=None,
            duration_ms=150.5,
            request_id="req_123",
            correlation_id="corr_123",
            parent_audit_id=None,
            sensitive_data=False,
            pii_data=False,
            financial_data=True,
            hash="",
            signature=None
        )
        
        # Test to_dict
        entry_dict = entry.to_dict()
        assert isinstance(entry_dict, dict)
        assert entry_dict['audit_id'] == "test_audit_123"
        assert entry_dict['user_email'] == "test@example.com"
        
        # Test to_json
        entry_json = entry.to_json()
        assert isinstance(entry_json, str)
        parsed = json.loads(entry_json)
        assert parsed['audit_id'] == "test_audit_123"


@pytest.mark.unit
class TestAuditor:
    """Unit tests for Auditor"""

    @pytest.fixture
    def mock_dynamodb_table(self):
        """Create mock DynamoDB table"""
        mock_table = MagicMock()
        mock_table.put_item.return_value = {}
        mock_table.query.return_value = {'Items': []}
        return mock_table

    @pytest.fixture
    def auditor(self, mock_dynamodb_table):
        """Create Auditor instance with mocked DynamoDB"""
        with patch('boto3.resource') as mock_resource:
            mock_dynamodb = MagicMock()
            mock_dynamodb.Table.return_value = mock_dynamodb_table
            mock_resource.return_value = mock_dynamodb
            
            auditor = Auditor()
            auditor.table = mock_dynamodb_table
            return auditor

    def test_auditor_initialization(self, auditor):
        """Test Auditor initialization"""
        assert auditor.table_name == "AgentFirst-AuditLogs"
        assert auditor.region == "us-east-1"
        assert auditor.retention_days == 365
        assert auditor._cache == {}

    def test_generate_audit_id(self, auditor):
        """Test audit ID generation"""
        audit_id = auditor._generate_audit_id()
        
        assert audit_id.startswith("audit_")
        assert len(audit_id) == 38  # "audit_" + 32 hex chars
        
        # Should generate unique IDs
        audit_id2 = auditor._generate_audit_id()
        assert audit_id != audit_id2

    def test_detect_sensitive_data(self, auditor):
        """Test sensitive data detection"""
        # Test with sensitive data
        input_data = {"password": "secret123", "user": "test"}
        output_data = {"token": "abc123"}
        
        assert auditor._detect_sensitive_data(input_data, output_data) is True
        
        # Test without sensitive data
        input_data = {"user": "test", "action": "check"}
        output_data = {"result": "success"}
        
        assert auditor._detect_sensitive_data(input_data, output_data) is False

    def test_detect_pii_data(self, auditor):
        """Test PII data detection"""
        # Test with PII data
        input_data = {"name": "João Silva", "email": "joao@example.com"}
        output_data = {"customer_id": "123"}
        
        assert auditor._detect_pii_data(input_data, output_data) is True
        
        # Test without PII data
        input_data = {"action": "check", "connector": "ifood"}
        output_data = {"orders": 3}
        
        assert auditor._detect_pii_data(input_data, output_data) is False

    def test_detect_financial_data(self, auditor):
        """Test financial data detection"""
        # Test with financial data
        input_data = {"action": "check_revenue"}
        output_data = {"total": 1500.00, "payment": "credit_card"}
        
        assert auditor._detect_financial_data(input_data, output_data) is True
        
        # Test without financial data
        input_data = {"action": "check_status"}
        output_data = {"status": "online"}
        
        assert auditor._detect_financial_data(input_data, output_data) is False

    @pytest.mark.asyncio
    async def test_log_transaction_success(self, auditor, mock_dynamodb_table):
        """Test successful transaction logging"""
        audit_id = await auditor.log_transaction(
            email="test@example.com",
            action="check_orders",
            input_data={"connector": "ifood"},
            output_data={"orders": 3},
            agent="retail_agent",
            category=AuditCategory.BUSINESS_OPERATION,
            level=AuditLevel.INFO,
            status="success",
            duration_ms=150.5
        )
        
        # Should return audit ID
        assert audit_id.startswith("audit_")
        
        # Should have called DynamoDB put_item
        mock_dynamodb_table.put_item.assert_called_once()
        
        # Verify the item structure
        call_args = mock_dynamodb_table.put_item.call_args[1]
        item = call_args['Item']
        
        assert item['PK'] == "test@example.com"
        assert item['SK'].startswith("AUDIT#")
        assert item['agent'] == "retail_agent"
        assert item['action'] == "check_orders"
        assert item['status'] == "success"
        assert item['category'] == AuditCategory.BUSINESS_OPERATION.value
        assert item['level'] == AuditLevel.INFO.value
        assert 'ttl' in item  # TTL should be set
        assert 'hash' in item  # Hash should be calculated

    @pytest.mark.asyncio
    async def test_log_transaction_with_error(self, auditor, mock_dynamodb_table):
        """Test transaction logging with error"""
        audit_id = await auditor.log_transaction(
            email="test@example.com",
            action="confirm_order",
            input_data={"order_id": "123"},
            output_data={},
            agent="retail_agent",
            status="error",
            error_message="Order not found"
        )
        
        # Should still return audit ID
        assert audit_id.startswith("audit_")
        
        # Verify error details
        call_args = mock_dynamodb_table.put_item.call_args[1]
        item = call_args['Item']
        
        assert item['status'] == "error"
        assert item['error_message'] == "Order not found"

    @pytest.mark.asyncio
    async def test_log_transaction_with_sensitive_data(self, auditor, mock_dynamodb_table):
        """Test logging with sensitive data detection"""
        audit_id = await auditor.log_transaction(
            email="test@example.com",
            action="authenticate",
            input_data={"password": "secret123"},
            output_data={"token": "abc123"},
            agent="auth_service"
        )
        
        # Verify sensitive data flags
        call_args = mock_dynamodb_table.put_item.call_args[1]
        item = call_args['Item']
        
        assert item['sensitive_data'] is True

    @pytest.mark.asyncio
    async def test_log_transaction_with_pii_data(self, auditor, mock_dynamodb_table):
        """Test logging with PII data detection"""
        audit_id = await auditor.log_transaction(
            email="test@example.com",
            action="create_user",
            input_data={"name": "João Silva", "email": "joao@example.com"},
            output_data={"user_id": "123"},
            agent="user_service"
        )
        
        # Verify PII data flags
        call_args = mock_dynamodb_table.put_item.call_args[1]
        item = call_args['Item']
        
        assert item['pii_data'] is True

    @pytest.mark.asyncio
    async def test_log_transaction_with_financial_data(self, auditor, mock_dynamodb_table):
        """Test logging with financial data detection"""
        audit_id = await auditor.log_transaction(
            email="test@example.com",
            action="process_payment",
            input_data={"amount": 100.00},
            output_data={"payment_id": "pay_123", "total": 100.00},
            agent="payment_service"
        )
        
        # Verify financial data flags
        call_args = mock_dynamodb_table.put_item.call_args[1]
        item = call_args['Item']
        
        assert item['financial_data'] is True

    @pytest.mark.asyncio
    async def test_get_audit_logs(self, auditor, mock_dynamodb_table):
        """Test retrieving audit logs"""
        # Mock DynamoDB response
        mock_items = [
            {
                'PK': 'test@example.com',
                'SK': 'AUDIT#2025-01-26T15:00:00Z#audit_123',
                'audit_id': 'audit_123',
                'timestamp': '2025-01-26T15:00:00Z',
                'timezone': 'UTC',
                'user_email': 'test@example.com',
                'user_id': None,
                'session_id': 'session_123',
                'channel': 'telegram',
                'agent': 'retail_agent',
                'action': 'check_orders',
                'category': 'business_operation',
                'level': 'info',
                'input_data': {'connector': 'ifood'},
                'output_data': {'orders': 3},
                'context': {},
                'status': 'success',
                'error_message': None,
                'duration_ms': 150.5,
                'request_id': None,
                'correlation_id': None,
                'parent_audit_id': None,
                'sensitive_data': False,
                'pii_data': False,
                'financial_data': True,
                'hash': 'abc123',
                'signature': None,
                'version': '1.0',
                'source': 'AgentFirst2',
                'ttl': 1234567890
            }
        ]
        
        mock_dynamodb_table.query.return_value = {'Items': mock_items}
        
        # Get audit logs
        logs = await auditor.get_audit_logs(
            email="test@example.com",
            limit=10
        )
        
        # Verify results
        assert len(logs) == 1
        log = logs[0]
        assert isinstance(log, AuditEntry)
        assert log.audit_id == 'audit_123'
        assert log.user_email == 'test@example.com'
        assert log.agent == 'retail_agent'
        assert log.action == 'check_orders'
        assert log.category == AuditCategory.BUSINESS_OPERATION
        assert log.level == AuditLevel.INFO

    @pytest.mark.asyncio
    async def test_generate_compliance_report(self, auditor):
        """Test compliance report generation"""
        # Mock audit logs
        mock_logs = [
            AuditEntry(
                audit_id="audit_1",
                timestamp="2025-01-26T15:00:00Z",
                timezone="UTC",
                user_email="test@example.com",
                user_id=None,
                session_id="session_1",
                channel="telegram",
                agent="retail_agent",
                action="check_orders",
                category=AuditCategory.BUSINESS_OPERATION,
                level=AuditLevel.INFO,
                input_data={"connector": "ifood"},
                output_data={"orders": 3},
                context={},
                status="success",
                error_message=None,
                duration_ms=150.5,
                request_id=None,
                correlation_id=None,
                parent_audit_id=None,
                sensitive_data=False,
                pii_data=True,
                financial_data=True,
                hash="hash1",
                signature=None
            ),
            AuditEntry(
                audit_id="audit_2",
                timestamp="2025-01-26T16:00:00Z",
                timezone="UTC",
                user_email="test@example.com",
                user_id=None,
                session_id="session_2",
                channel="telegram",
                agent="auth_service",
                action="authenticate",
                category=AuditCategory.AUTHENTICATION,
                level=AuditLevel.SECURITY,
                input_data={"email": "test@example.com"},
                output_data={"success": True},
                context={},
                status="success",
                error_message=None,
                duration_ms=50.0,
                request_id=None,
                correlation_id=None,
                parent_audit_id=None,
                sensitive_data=True,
                pii_data=True,
                financial_data=False,
                hash="hash2",
                signature=None
            )
        ]
        
        with patch.object(auditor, 'get_audit_logs', return_value=mock_logs):
            start_date = datetime(2025, 1, 26, 0, 0, 0)
            end_date = datetime(2025, 1, 26, 23, 59, 59)
            
            report = await auditor.generate_compliance_report(
                start_date=start_date,
                end_date=end_date,
                user_email="test@example.com"
            )
            
            # Verify report
            assert isinstance(report, ComplianceReport)
            assert report.total_operations == 2
            assert report.successful_operations == 2
            assert report.failed_operations == 0
            assert report.security_events == 1
            assert report.pii_operations == 2
            assert report.financial_operations == 1
            assert report.sensitive_operations == 1
            
            # Verify categories
            assert report.operations_by_category['business_operation'] == 1
            assert report.operations_by_category['authentication'] == 1
            
            # Verify agents
            assert report.operations_by_agent['retail_agent'] == 1
            assert report.operations_by_agent['auth_service'] == 1
            
            # Verify levels
            assert report.operations_by_level['info'] == 1
            assert report.operations_by_level['security'] == 1
            
            # Verify compliance flags
            assert report.lgpd_compliant is True  # No integrity violations + PII data
            assert report.hipaa_compliant is True  # No integrity violations + sensitive data
            assert report.sox_compliant is True  # No integrity violations + financial data

    @pytest.mark.asyncio
    async def test_export_logs_for_compliance(self, auditor):
        """Test exporting logs for compliance"""
        # Mock audit logs
        mock_logs = [
            AuditEntry(
                audit_id="audit_1",
                timestamp="2025-01-26T15:00:00Z",
                timezone="UTC",
                user_email="test@example.com",
                user_id=None,
                session_id="session_1",
                channel="telegram",
                agent="retail_agent",
                action="check_orders",
                category=AuditCategory.BUSINESS_OPERATION,
                level=AuditLevel.INFO,
                input_data={"connector": "ifood"},
                output_data={"orders": 3},
                context={},
                status="success",
                error_message=None,
                duration_ms=150.5,
                request_id=None,
                correlation_id=None,
                parent_audit_id=None,
                sensitive_data=False,
                pii_data=False,
                financial_data=True,
                hash="hash1",
                signature=None
            )
        ]
        
        with patch.object(auditor, 'get_audit_logs', return_value=mock_logs):
            start_date = datetime(2025, 1, 26, 0, 0, 0)
            end_date = datetime(2025, 1, 26, 23, 59, 59)
            
            # Test JSON export
            json_export = await auditor.export_logs_for_compliance(
                email="test@example.com",
                start_date=start_date,
                end_date=end_date,
                format="json"
            )
            
            # Verify JSON export
            assert isinstance(json_export, str)
            parsed = json.loads(json_export)
            assert len(parsed) == 1
            assert parsed[0]['audit_id'] == 'audit_1'
            assert parsed[0]['user_email'] == 'test@example.com'

    @pytest.mark.asyncio
    async def test_log_transaction_error_handling(self, auditor, mock_dynamodb_table):
        """Test error handling in log_transaction"""
        # Mock DynamoDB error
        from botocore.exceptions import ClientError
        mock_dynamodb_table.put_item.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Test error'}},
            'PutItem'
        )
        
        # Should not raise exception, but return empty string
        audit_id = await auditor.log_transaction(
            email="test@example.com",
            action="test_action",
            input_data={},
            output_data={}
        )
        
        assert audit_id == ""

    def test_calculate_signature(self, auditor):
        """Test HMAC signature calculation"""
        # Set signature key
        auditor.signature_key = "test_secret_key"
        
        entry = AuditEntry(
            audit_id="test_audit_123",
            timestamp="2025-01-26T15:00:00Z",
            timezone="UTC",
            user_email="test@example.com",
            user_id=None,
            session_id="session_123",
            channel="telegram",
            agent="retail_agent",
            action="check_orders",
            category=AuditCategory.BUSINESS_OPERATION,
            level=AuditLevel.INFO,
            input_data={"connector": "ifood"},
            output_data={"orders": 3},
            context={"tier": "free"},
            status="success",
            error_message=None,
            duration_ms=150.5,
            request_id="req_123",
            correlation_id="corr_123",
            parent_audit_id=None,
            sensitive_data=False,
            pii_data=False,
            financial_data=True,
            hash="",
            signature=None
        )
        
        signature = auditor._calculate_signature(entry)
        
        # Should return HMAC signature
        assert signature != ""
        assert len(signature) == 64  # SHA-256 hex length
        
        # Verify signature calculation
        message = entry.to_json()
        expected_signature = hmac.new(
            "test_secret_key".encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        assert signature == expected_signature


@pytest.mark.unit
class TestComplianceReport:
    """Unit tests for ComplianceReport"""

    def test_compliance_report_creation(self):
        """Test ComplianceReport creation"""
        report = ComplianceReport(
            report_id="report_123",
            generated_at=datetime.now(timezone.utc),
            period_start=datetime(2025, 1, 1),
            period_end=datetime(2025, 1, 31),
            user_email="test@example.com",
            total_operations=100,
            successful_operations=95,
            failed_operations=5,
            security_events=10,
            compliance_events=5,
            operations_by_category={"business_operation": 50, "authentication": 30},
            operations_by_agent={"retail_agent": 60, "auth_service": 40},
            operations_by_level={"info": 80, "warning": 15, "error": 5},
            pii_operations=25,
            financial_operations=30,
            sensitive_operations=20,
            lgpd_compliant=True,
            hipaa_compliant=True,
            sox_compliant=True,
            integrity_violations=[],
            policy_violations=[]
        )
        
        assert report.report_id == "report_123"
        assert report.total_operations == 100
        assert report.successful_operations == 95
        assert report.failed_operations == 5
        assert report.lgpd_compliant is True
        assert report.hipaa_compliant is True
        assert report.sox_compliant is True

    def test_compliance_report_serialization(self):
        """Test ComplianceReport serialization"""
        report = ComplianceReport(
            report_id="report_123",
            generated_at=datetime.now(timezone.utc),
            period_start=datetime(2025, 1, 1),
            period_end=datetime(2025, 1, 31),
            user_email="test@example.com",
            total_operations=100,
            successful_operations=95,
            failed_operations=5,
            security_events=10,
            compliance_events=5,
            operations_by_category={"business_operation": 50},
            operations_by_agent={"retail_agent": 60},
            operations_by_level={"info": 80},
            pii_operations=25,
            financial_operations=30,
            sensitive_operations=20,
            lgpd_compliant=True,
            hipaa_compliant=True,
            sox_compliant=True,
            integrity_violations=[],
            policy_violations=[]
        )
        
        report_dict = report.to_dict()
        
        assert isinstance(report_dict, dict)
        assert report_dict['report_id'] == "report_123"
        assert report_dict['total_operations'] == 100
        assert report_dict['lgpd_compliant'] is True