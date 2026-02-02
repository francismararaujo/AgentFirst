"""
Memory Service - Armazena contexto persistente por email

Responsabilidades:
1. Recuperar contexto de Memory (DynamoDB)
2. Armazenar histórico de conversas
3. Manter preferências do usuário
4. Suportar GSI por domínio para queries eficientes
5. TTL configurável (padrão: 30 dias)
"""

from typing import Dict, Optional, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
from app.config.settings import settings


@dataclass
class MemoryEntry:
    """Entrada de memória"""
    email: str
    domain: str  # retail, tax, finance, etc
    key: str  # Chave específica (last_orders, preferences, etc)
    value: Any
    timestamp: str
    ttl: int = 2592000  # 30 dias em segundos
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            'email': self.email,
            'domain': self.domain,
            'key': key,
            'value': self.value if isinstance(self.value, (str, int, float, bool)) else json.dumps(self.value),
            'timestamp': self.timestamp,
            'ttl': self.ttl
        }


class MemoryService:
    """
    Serviço de memória usando DynamoDB
    """
    
    def __init__(self, dynamodb_client, table_name: Optional[str] = None):
        """
        Inicializa Memory Service
        
        Args:
            dynamodb_client: Cliente DynamoDB
            table_name: Nome da tabela
        """
        self.dynamodb = dynamodb_client
        self.table_name = table_name or settings.DYNAMODB_MEMORY_TABLE
    
    async def get_context(self, email: str) -> Dict[str, Any]:
        """
        Recupera contexto completo do usuário
        
        Args:
            email: Email do usuário
        
        Returns:
            Dicionário com contexto
        """
        try:
            # Buscar todos os itens para este email
            # Boto3 client is synchronous, do not await!
            response = self.dynamodb.query(
                TableName=self.table_name,
                KeyConditionExpression='email = :email',
                ExpressionAttributeValues={
                    ':email': {'S': email}
                }
            )
            
            # Construir contexto
            context = {
                'email': email,
                'last_intent': None,
                'last_domain': None,
                'last_connector': None,
                'last_response': None,
                'history': [],
                'preferences': {},
                'domains': {}
            }
            
            # Processar itens
            for item in response.get('Items', []):
                domain = item.get('domain', {}).get('S', '')
                key = item.get('key', {}).get('S', '')
                value = item.get('value', {})
                
                # Parsear valor
                if 'S' in value:
                    parsed_value = value['S']
                    try:
                        parsed_value = json.loads(parsed_value)
                    except json.JSONDecodeError:
                        pass
                elif 'N' in value:
                    parsed_value = int(value['N'])
                else:
                    parsed_value = value
                
                # Atribuir ao contexto
                if key == 'last_intent':
                    context['last_intent'] = parsed_value
                elif key == 'last_domain':
                    context['last_domain'] = parsed_value
                elif key == 'last_connector':
                    context['last_connector'] = parsed_value
                elif key == 'last_response':
                    context['last_response'] = parsed_value
                elif key == 'history':
                    context['history'] = parsed_value if isinstance(parsed_value, list) else []
                elif key == 'preferences':
                    context['preferences'] = parsed_value if isinstance(parsed_value, dict) else {}
                elif domain:
                    if domain not in context['domains']:
                        context['domains'][domain] = {}
                    context['domains'][domain][key] = parsed_value
            
            return context
            
        except Exception as e:
            print(f"Erro ao recuperar contexto: {e}")
            return {
                'email': email,
                'last_intent': None,
                'last_domain': None,
                'last_connector': None,
                'last_response': None,
                'history': [],
                'preferences': {},
                'domains': {}
            }
    
    async def update_context(
        self,
        email: str,
        updates: Dict[str, Any],
        domain: Optional[str] = None
    ) -> None:
        """
        Atualiza contexto do usuário
        
        Args:
            email: Email do usuário
            updates: Dicionário com atualizações
            domain: Domínio específico (opcional)
        """
        try:
            timestamp = datetime.now().isoformat()
            ttl = int((datetime.now() + timedelta(days=30)).timestamp())
            
            # Atualizar cada campo
            for key, value in updates.items():
                # Serializar valor
                if isinstance(value, (dict, list)):
                    value_str = json.dumps(value)
                else:
                    value_str = str(value)
                
                # Preparar item
                item = {
                    'email': {'S': email},
                    'domain': {'S': domain or 'global'},
                    'key': {'S': key},
                    'value': {'S': value_str},
                    'timestamp': {'N': str(int(datetime.now().timestamp()))},
                    'ttl': {'N': str(ttl)}
                }
                
                # Salvar em DynamoDB
                # Boto3 client is synchronous, do not await!
                self.dynamodb.put_item(
                    TableName=self.table_name,
                    Item=item
                )
        
        except Exception as e:
            print(f"Erro ao atualizar contexto: {e}")
    
    async def get_domain_context(
        self,
        email: str,
        domain: str
    ) -> Dict[str, Any]:
        """
        Recupera contexto específico de um domínio
        
        Args:
            email: Email do usuário
            domain: Domínio (retail, tax, etc)
        
        Returns:
            Dicionário com contexto do domínio
        """
        try:
            # Buscar itens para este email e domínio
            # Boto3 client is synchronous, do not await!
            response = self.dynamodb.query(
                TableName=self.table_name,
                KeyConditionExpression='email = :email AND domain = :domain',
                ExpressionAttributeValues={
                    ':email': {'S': email},
                    ':domain': {'S': domain}
                }
            )
            
            # Construir contexto
            context = {}
            
            for item in response.get('Items', []):
                key = item.get('key', {}).get('S', '')
                value = item.get('value', {})
                
                # Parsear valor
                if 'S' in value:
                    parsed_value = value['S']
                    try:
                        parsed_value = json.loads(parsed_value)
                    except json.JSONDecodeError:
                        pass
                elif 'N' in value:
                    parsed_value = int(value['N'])
                else:
                    parsed_value = value
                
                context[key] = parsed_value
            
            return context
            
        except Exception as e:
            print(f"Erro ao recuperar contexto do domínio: {e}")
            return {}
    
    async def add_to_history(
        self,
        email: str,
        message: str,
        response: str,
        domain: str
    ) -> None:
        """
        Adiciona mensagem ao histórico
        
        Args:
            email: Email do usuário
            message: Mensagem do usuário
            response: Resposta do sistema
            domain: Domínio
        """
        try:
            # Recuperar histórico atual
            context = await self.get_context(email)
            history = context.get('history', [])
            
            # Adicionar nova entrada
            history.append({
                'timestamp': datetime.now().isoformat(),
                'domain': domain,
                'message': message,
                'response': response
            })
            
            # Manter apenas últimas 100 mensagens
            if len(history) > 100:
                history = history[-100:]
            
            # Atualizar
            await self.update_context(email, {'history': history})
        
        except Exception as e:
            print(f"Erro ao adicionar ao histórico: {e}")
    
    async def set_preference(
        self,
        email: str,
        key: str,
        value: Any
    ) -> None:
        """
        Define preferência do usuário
        
        Args:
            email: Email do usuário
            key: Chave da preferência
            value: Valor
        """
        try:
            # Recuperar preferências atuais
            context = await self.get_context(email)
            preferences = context.get('preferences', {})
            
            # Atualizar
            preferences[key] = value
            
            # Salvar
            await self.update_context(email, {'preferences': preferences})
        
        except Exception as e:
            print(f"Erro ao definir preferência: {e}")
    
    async def get_preference(
        self,
        email: str,
        key: str,
        default: Any = None
    ) -> Any:
        """
        Recupera preferência do usuário
        
        Args:
            email: Email do usuário
            key: Chave da preferência
            default: Valor padrão
        
        Returns:
            Valor da preferência
        """
        try:
            context = await self.get_context(email)
            preferences = context.get('preferences', {})
            return preferences.get(key, default)
        
        except Exception as e:
            print(f"Erro ao recuperar preferência: {e}")
            return default
    
    async def clear_context(self, email: str) -> None:
        """
        Limpa contexto do usuário
        
        Args:
            email: Email do usuário
        """
        try:
            # Buscar todos os itens
            response = await self.dynamodb.query(
                TableName=self.table_name,
                KeyConditionExpression='email = :email',
                ExpressionAttributeValues={
                    ':email': {'S': email}
                }
            )
            
            # Deletar cada item
            for item in response.get('Items', []):
                # Boto3 client is synchronous, do not await!
                self.dynamodb.delete_item(
                    TableName=self.table_name,
                    Key={
                        'email': item['email'],
                        'domain': item['domain']
                    }
                )
        
        except Exception as e:
            print(f"Erro ao limpar contexto: {e}")
