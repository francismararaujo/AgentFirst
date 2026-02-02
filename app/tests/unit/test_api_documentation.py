"""
Unit tests for API Documentation (Phase 13.1)

Tests the API documentation endpoints and OpenAPI specification:
- OpenAPI spec validation
- Documentation examples endpoint
- Swagger UI accessibility
- API examples functionality
"""

import pytest
import json
import yaml
import requests
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.docs.api_examples import AgentFirstAPI


@pytest.mark.unit
class TestAPIDocumentation:
    """Unit tests for API Documentation"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def api_client(self):
        """Create API client for testing"""
        return AgentFirstAPI("http://testserver")

    def test_openapi_spec_exists(self):
        """Test that OpenAPI spec file exists and is valid YAML"""
        import os
        
        spec_path = "app/docs/openapi.yaml"
        assert os.path.exists(spec_path), "OpenAPI spec file should exist"
        
        # Test YAML parsing with UTF-8 encoding
        with open(spec_path, 'r', encoding='utf-8') as f:
            spec_data = yaml.safe_load(f)
        
        # Validate basic OpenAPI structure
        assert 'openapi' in spec_data
        assert 'info' in spec_data
        assert 'paths' in spec_data
        assert 'components' in spec_data
        
        # Validate info section
        info = spec_data['info']
        assert 'title' in info
        assert 'version' in info
        assert 'description' in info
        assert info['title'] == "AgentFirst2 MVP API"
        assert info['version'] == "1.0.0"

    def test_openapi_spec_paths(self):
        """Test that OpenAPI spec contains required paths"""
        import os
        
        spec_path = "app/docs/openapi.yaml"
        with open(spec_path, 'r', encoding='utf-8') as f:
            spec_data = yaml.safe_load(f)
        
        paths = spec_data['paths']
        
        # Required endpoints
        required_paths = [
            '/health',
            '/status',
            '/webhook/telegram',
            '/webhook/ifood'
        ]
        
        for path in required_paths:
            assert path in paths, f"Path {path} should be documented"
        
        # Validate health endpoint
        health_path = paths['/health']
        assert 'get' in health_path
        assert 'summary' in health_path['get']
        assert 'responses' in health_path['get']
        assert '200' in health_path['get']['responses']

    def test_openapi_spec_components(self):
        """Test that OpenAPI spec contains required components"""
        import os
        
        spec_path = "app/docs/openapi.yaml"
        with open(spec_path, 'r', encoding='utf-8') as f:
            spec_data = yaml.safe_load(f)
        
        components = spec_data['components']
        
        # Required schemas
        required_schemas = [
            'HealthResponse',
            'StatusResponse',
            'ErrorResponse',
            'TelegramUpdate',
            'TelegramMessage',
            'iFoodEvent'
        ]
        
        schemas = components.get('schemas', {})
        for schema in required_schemas:
            assert schema in schemas, f"Schema {schema} should be documented"
        
        # Validate HealthResponse schema
        health_schema = schemas['HealthResponse']
        assert 'type' in health_schema
        assert health_schema['type'] == 'object'
        assert 'required' in health_schema
        assert 'status' in health_schema['required']

    def test_docs_examples_endpoint(self, client):
        """Test documentation examples endpoint"""
        response = client.get("/docs/examples")
        
        assert response.status_code == 200
        
        data = response.json()
        assert 'title' in data
        assert 'description' in data
        assert 'examples' in data
        assert 'integration_patterns' in data
        assert 'resources' in data
        
        # Validate examples structure
        examples = data['examples']
        assert 'health_check' in examples
        assert 'telegram_webhook' in examples
        assert 'ifood_webhook' in examples
        assert 'supervisor_commands' in examples
        
        # Validate health_check example
        health_example = examples['health_check']
        assert 'description' in health_example
        assert 'method' in health_example
        assert 'url' in health_example
        assert 'response' in health_example
        assert health_example['method'] == 'GET'
        assert health_example['url'] == '/health'

    def test_swagger_ui_accessible(self, client):
        """Test that Swagger UI is accessible"""
        response = client.get("/docs")
        
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_redoc_accessible(self, client):
        """Test that ReDoc is accessible"""
        response = client.get("/redoc")
        
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_openapi_json_endpoint(self, client):
        """Test OpenAPI JSON endpoint"""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/json"
        
        data = response.json()
        assert 'openapi' in data
        assert 'info' in data
        assert 'paths' in data


@pytest.mark.unit
class TestAPIExamples:
    """Unit tests for API Examples"""

    def test_api_client_initialization(self):
        """Test API client initialization"""
        client = AgentFirstAPI()
        
        assert client.base_url == "https://ain6spik95.execute-api.us-east-1.amazonaws.com/prod"
        assert client.session is not None
        assert 'Content-Type' in client.session.headers
        assert client.session.headers['Content-Type'] == 'application/json'

    def test_api_client_custom_base_url(self):
        """Test API client with custom base URL"""
        custom_url = "http://localhost:8000"
        client = AgentFirstAPI(custom_url)
        
        assert client.base_url == custom_url

    @patch('requests.Session.get')
    def test_health_check_method(self, mock_get):
        """Test health check method"""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "healthy",
            "environment": "test",
            "version": "1.0.0"
        }
        mock_get.return_value = mock_response
        
        client = AgentFirstAPI("http://testserver")
        result = client.health_check()
        
        # Verify request
        mock_get.assert_called_once_with("http://testserver/health")
        
        # Verify response
        assert result['status'] == 'healthy'
        assert result['environment'] == 'test'
        assert result['version'] == '1.0.0'

    @patch('requests.Session.get')
    def test_get_status_method(self, mock_get):
        """Test get status method"""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "running",
            "environment": "test",
            "version": "1.0.0",
            "debug": True
        }
        mock_get.return_value = mock_response
        
        client = AgentFirstAPI("http://testserver")
        result = client.get_status()
        
        # Verify request
        mock_get.assert_called_once_with("http://testserver/status")
        
        # Verify response
        assert result['status'] == 'running'
        assert result['debug'] is True

    @patch('requests.Session.post')
    def test_send_telegram_update_method(self, mock_post):
        """Test send Telegram update method"""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response
        
        client = AgentFirstAPI("http://testserver")
        
        update_data = {
            "update_id": 123,
            "message": {
                "message_id": 1,
                "text": "test message"
            }
        }
        
        result = client.send_telegram_update(update_data)
        
        # Verify request
        mock_post.assert_called_once_with(
            "http://testserver/webhook/telegram",
            json=update_data
        )
        
        # Verify response
        assert result['ok'] is True

    @patch('requests.Session.post')
    def test_send_ifood_event_method(self, mock_post):
        """Test send iFood event method"""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response
        
        client = AgentFirstAPI("http://testserver")
        
        event_data = {
            "eventId": "evt_123",
            "eventType": "order.placed",
            "data": {"orderId": "order_456"}
        }
        secret_key = "test_secret"
        
        result = client.send_ifood_event(event_data, secret_key)
        
        # Verify request was made
        mock_post.assert_called_once()
        
        # Verify URL
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://testserver/webhook/ifood"
        
        # Verify headers contain signature
        headers = call_args[1]['headers']
        assert 'X-Signature' in headers
        assert headers['X-Signature'].startswith('sha256=')
        
        # Verify response
        assert result['ok'] is True

    def test_hmac_signature_calculation(self):
        """Test HMAC signature calculation in iFood event"""
        import hmac
        import hashlib
        
        client = AgentFirstAPI("http://testserver")
        
        event_data = {"test": "data"}
        secret_key = "test_secret"
        
        # Calculate expected signature
        payload = json.dumps(event_data, separators=(',', ':'))
        expected_signature = hmac.new(
            secret_key.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Mock the post method to capture the signature
        with patch.object(client.session, 'post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"ok": True}
            mock_post.return_value = mock_response
            
            client.send_ifood_event(event_data, secret_key)
            
            # Verify signature
            call_args = mock_post.call_args
            headers = call_args[1]['headers']
            signature = headers['X-Signature']
            
            assert signature == f'sha256={expected_signature}'

    def test_api_examples_file_structure(self):
        """Test that API examples file has correct structure"""
        import os
        import ast
        
        examples_path = "app/docs/api_examples.py"
        assert os.path.exists(examples_path), "API examples file should exist"
        
        # Parse the file to check structure
        with open(examples_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check that file is valid Python
        try:
            ast.parse(content)
        except SyntaxError as e:
            pytest.fail(f"API examples file has syntax error: {e}")
        
        # Check for required functions
        required_functions = [
            'example_health_check',
            'example_telegram_webhook',
            'example_ifood_webhook',
            'example_integration_patterns',
            'example_error_handling'
        ]
        
        for func_name in required_functions:
            assert f"def {func_name}(" in content, f"Function {func_name} should exist"

    def test_api_examples_imports(self):
        """Test that API examples file imports are correct"""
        # Try to import the module
        try:
            from app.docs import api_examples
        except ImportError as e:
            pytest.fail(f"Failed to import API examples: {e}")
        
        # Check that required classes exist
        assert hasattr(api_examples, 'AgentFirstAPI')
        
        # Check that main function exists
        assert hasattr(api_examples, 'main')
        assert callable(api_examples.main)


@pytest.mark.unit
class TestDocumentationIntegration:
    """Unit tests for documentation integration"""

    def test_fastapi_app_metadata(self):
        """Test FastAPI app has correct metadata"""
        assert app.title == "AgentFirst2 MVP API"
        assert app.version == "1.0.0"
        assert "AgentFirst2" in app.description
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"
        assert app.openapi_url == "/openapi.json"

    def test_fastapi_app_contact_info(self):
        """Test FastAPI app has contact information"""
        openapi_schema = app.openapi()
        
        assert 'info' in openapi_schema
        info = openapi_schema['info']
        
        assert 'contact' in info
        contact = info['contact']
        assert 'name' in contact
        assert 'email' in contact
        assert contact['name'] == "AgentFirst2 Support"

    def test_fastapi_app_license_info(self):
        """Test FastAPI app has license information"""
        openapi_schema = app.openapi()
        
        assert 'info' in openapi_schema
        info = openapi_schema['info']
        
        assert 'license' in info
        license_info = info['license']
        assert 'name' in license_info
        assert 'url' in license_info
        assert license_info['name'] == "MIT"

    def test_openapi_schema_generation(self):
        """Test OpenAPI schema generation"""
        schema = app.openapi()
        
        # Basic structure
        assert 'openapi' in schema
        assert 'info' in schema
        assert 'paths' in schema
        
        # Paths should include our endpoints
        paths = schema['paths']
        assert '/health' in paths
        assert '/status' in paths
        assert '/docs/examples' in paths
        assert '/webhook/telegram' in paths
        assert '/webhook/ifood' in paths
        
        # Health endpoint should have proper documentation
        health_endpoint = paths['/health']['get']
        assert 'summary' in health_endpoint
        assert 'operationId' in health_endpoint
        assert 'responses' in health_endpoint