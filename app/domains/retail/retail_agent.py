"""
Retail Agent (Strands) - Agente especializado em operações de varejo

Responsabilidades:
1. Gerenciar pedidos (check, confirm, cancel)
2. Gerenciar estoque (update, forecast)
3. Integrar com conectores (iFood, 99food, etc)
4. Processar eventos de negócio
5. Manter estado da conversa

Padrão Strands:
- Tools específicas para cada ação
- State management para contexto
- Error handling com retry
- Event publishing
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import asyncio

from app.core.brain import Intent, Context
from app.core.auditor import Auditor, AuditCategory, AuditLevel
from app.core.event_bus import EventMessage
from app.omnichannel.database.repositories import UserRepository

logger = logging.getLogger(__name__)


@dataclass
class RetailState:
    """Estado do agente retail"""
    last_connector: Optional[str] = None
    last_orders: List[Dict[str, Any]] = None
    last_revenue: Optional[Dict[str, Any]] = None
    store_status: str = "open"  # open, closed, paused
    
    def __post_init__(self):
        if self.last_orders is None:
            self.last_orders = []


class RetailAgent:
    """
    Agente Retail seguindo padrão Strands
    
    Gerencia operações de varejo:
    - Pedidos (iFood, 99food, etc)
    - Estoque
    - Faturamento
    - Status da loja
    """
    
    def __init__(self, event_bus=None, auditor=None):
        """
        Inicializa Retail Agent
        
        Args:
            event_bus: Event bus para publicar eventos
            auditor: Serviço de auditoria
        """
        self.event_bus = event_bus
        self.auditor = auditor or Auditor()
        self.state = RetailState()
        self.connectors = {}  # Conectores por tipo (ifood, 99food, etc)
        
        # Tools disponíveis
        self.tools = {
            'check_orders': self.check_orders,
            'confirm_order': self.confirm_order,
            'cancel_order': self.cancel_order,
            'check_revenue': self.check_revenue,
            'manage_store': self.manage_store,
            'update_inventory': self.update_inventory,
            'forecast_demand': self.forecast_demand,
            'greeting': self.greeting,
            'dispatch_order': self.dispatch_order,
            'list_cancellation_reasons': self.list_cancellation_reasons,
            'open_store': self.open_store,
            'close_store': self.close_store
        }
    
    def register_connector(self, connector_type: str, connector):
        """
        Registra conector para tipo específico
        
        Args:
            connector_type: Tipo do conector (ifood, 99food, etc)
            connector: Instância do conector
        """
        self.connectors[connector_type] = connector
        logger.info(f"Registered connector: {connector_type}")
    
    async def execute(self, intent: Intent, context: Context) -> Dict[str, Any]:
        """
        Executa ação baseada na intenção
        
        Args:
            intent: Intenção classificada pelo Brain
            context: Contexto da conversa
        
        Returns:
            Resultado da execução
        """
        start_time = datetime.now()
        
        try:
            # Registrar início da operação na auditoria
            await self.auditor.log_transaction(
                email=context.email,
                action=f"retail.{intent.action}.start",
                input_data={
                    'intent': intent.action,
                    'connector': intent.connector,
                    'entities': intent.entities,
                    'confidence': intent.confidence
                },
                output_data={},
                agent="retail_agent",
                category=AuditCategory.BUSINESS_OPERATION,
                level=AuditLevel.INFO,
                status="started",
                session_id=context.session_id,
                channel=context.channel.value
            )
            
            # Verificar se tool existe
            if intent.action not in self.tools:
                error_result = {
                    'success': False,
                    'error': f"Ação '{intent.action}' não suportada",
                    'available_actions': list(self.tools.keys())
                }
                
                # Registrar erro na auditoria
                await self.auditor.log_transaction(
                    email=context.email,
                    action=f"retail.{intent.action}.error",
                    input_data={
                        'intent': intent.action,
                        'available_actions': list(self.tools.keys())
                    },
                    output_data=error_result,
                    agent="retail_agent",
                    category=AuditCategory.ERROR_EVENT,
                    level=AuditLevel.WARNING,
                    status="error",
                    error_message=error_result['error'],
                    session_id=context.session_id,
                    channel=context.channel.value
                )
                
                return error_result
            
            # Executar tool
            tool = self.tools[intent.action]
            result = await tool(intent, context)
            
            # Calcular duração
            end_time = datetime.now()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            # Determinar categoria de auditoria baseada na ação
            audit_category = self._get_audit_category(intent.action)
            audit_level = AuditLevel.INFO if result.get('success') else AuditLevel.ERROR
            
            # Detectar dados sensíveis
            sensitive_data = self._contains_sensitive_data(intent, result)
            financial_data = self._contains_financial_data(intent, result)
            
            # Registrar resultado na auditoria
            await self.auditor.log_transaction(
                email=context.email,
                action=f"retail.{intent.action}",
                input_data={
                    'intent': intent.action,
                    'connector': intent.connector,
                    'entities': intent.entities
                },
                output_data=result,
                agent="retail_agent",
                category=audit_category,
                level=audit_level,
                status="success" if result.get('success') else "error",
                error_message=result.get('error') if not result.get('success') else None,
                duration_ms=duration_ms,
                session_id=context.session_id,
                channel=context.channel.value
            )
            
            # Publicar evento
            if self.event_bus:
                await self.event_bus.publish(
                    topic=f"retail.{intent.action}",
                    message={
                        'email': context.email,
                        'action': intent.action,
                        'connector': intent.connector,
                        'result': result,
                        'timestamp': datetime.now().isoformat()
                    }
                )
            
            return result
            
        except Exception as e:
            # Calcular duração mesmo em caso de erro
            end_time = datetime.now()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            logger.error(f"Error executing retail action {intent.action}: {str(e)}")
            
            error_result = {
                'success': False,
                'error': str(e),
                'action': intent.action
            }
            
            # Registrar erro na auditoria
            await self.auditor.log_transaction(
                email=context.email,
                action=f"retail.{intent.action}.exception",
                input_data={
                    'intent': intent.action,
                    'connector': intent.connector
                },
                output_data=error_result,
                agent="retail_agent",
                category=AuditCategory.ERROR_EVENT,
                level=AuditLevel.ERROR,
                status="error",
                error_message=str(e),
                duration_ms=duration_ms,
                session_id=context.session_id,
                channel=context.channel.value
            )
            
            return error_result
    
    async def check_orders(self, intent: Intent, context: Context) -> Dict[str, Any]:
        """
        Verifica pedidos nos conectores
        
        Args:
            intent: Intenção com parâmetros
            context: Contexto da conversa
        
        Returns:
            Lista de pedidos
        """
        try:
            connector_type = intent.connector or 'ifood'  # Default para iFood
            logger.info(f"RetailAgent checking orders for connector: {connector_type}. Available: {list(self.connectors.keys())}")
            
            if connector_type not in self.connectors:
                return {
                    'success': False,
                    'error': f"Connector '{connector_type}' not found or not initialized",
                    'available_connectors': list(self.connectors.keys())
                }
            
            # Usar conector real
            logger.info(f"Using REAL connector for {connector_type}")
            connector = self.connectors[connector_type]
            orders = await connector.get_orders()
            logger.info(f"Retrieved {len(orders)} orders from connector")
            
            # Atualizar estado
            self.state.last_connector = connector_type
            self.state.last_orders = orders
            
            # Combine with recent saved orders if connector returns empty (API limitation fix)
            if not orders and hasattr(self, 'recent_saved_orders') and self.recent_saved_orders:
                logger.info(f"Connector returned empty, using {len(self.recent_saved_orders)} recent saved orders")
                orders = self.recent_saved_orders
                self.state.last_orders = orders

            return {
                'success': True,
                'connector': connector_type,
                'orders': orders,
                'total_orders': len(orders),
                'pending_orders': len([o for o in orders if o.get('status') in ['PLC', 'PLACED', 'pending']]),
                'message': f"Encontrados {len(orders)} pedidos no {connector_type.upper()}"
            }
            
        except Exception as e:
            logger.error(f"Error checking orders: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f"Erro ao verificar pedidos: {str(e)}"
            }

    def set_recent_orders(self, orders: List[Dict[str, Any]]):
        """Set recent orders from external cache (Webhook)"""
        self.recent_saved_orders = orders
        logger.info(f"RetailAgent loaded {len(orders)} recent orders from cache")
    
    async def confirm_order(self, intent: Intent, context: Context) -> Dict[str, Any]:
        """
        Confirma pedido específico
        
        Args:
            intent: Intenção com order_id
            context: Contexto da conversa
        
        Returns:
            Resultado da confirmação
        """
        try:
            order_id = intent.entities.get('order_id')
            connector_type = intent.connector or self.state.last_connector or 'ifood'
            
            if not order_id:
                # Tentar pegar o primeiro pedido pendente
                if self.state.last_orders:
                    pending_orders = [o for o in self.state.last_orders if o.get('status') == 'pending']
                    if pending_orders:
                        order_id = pending_orders[0]['id']
                    else:
                        return {
                            'success': False,
                            'error': 'Nenhum pedido pendente encontrado'
                        }
                else:
                    return {
                        'success': False,
                        'error': 'ID do pedido não especificado'
                    }
            
            if connector_type not in self.connectors:
                return {
                    'success': False,
                    'error': f"Connector '{connector_type}' not found",
                    'order_id': order_id
                }
            
            # Usar conector real
            connector = self.connectors[connector_type]
            result = await connector.confirm_order(order_id)
            
            return {
                'success': True,
                'order_id': order_id,
                'connector': connector_type,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Error confirming order: {str(e)}")
            return {
                'success': False,
                'error': f"Erro ao confirmar pedido: {str(e)}"
            }
    
    async def cancel_order(self, intent: Intent, context: Context) -> Dict[str, Any]:
        """
        Cancela pedido específico
        
        Args:
            intent: Intenção com order_id e reason
            context: Contexto da conversa
        
        Returns:
            Resultado do cancelamento
        """
        try:
            order_id = intent.entities.get('order_id')
            reason = intent.entities.get('reason', 'Cancelado pelo restaurante')
            connector_type = intent.connector or self.state.last_connector or 'ifood'
            
            if not order_id:
                return {
                    'success': False,
                    'error': 'ID do pedido não especificado'
                }
            
            if connector_type not in self.connectors:
                return {
                    'success': False,
                    'error': f"Connector '{connector_type}' not found",
                    'order_id': order_id
                }
            
            # Usar conector real
            connector = self.connectors[connector_type]
            result = await connector.cancel_order(order_id, reason)
            
            return {
                'success': True,
                'order_id': order_id,
                'reason': reason,
                'connector': connector_type,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Error cancelling order: {str(e)}")
            return {
                'success': False,
                'error': f"Erro ao cancelar pedido: {str(e)}"
            }


    async def list_cancellation_reasons(self, intent: Intent, context: Context) -> Dict[str, Any]:
        """
        Lista motivos de cancelamento
        """
        try:
            order_id = intent.entities.get('order_id')
            connector_type = intent.connector or self.state.last_connector or 'ifood'
            
            if not order_id:
                return {'success': False, 'error': 'ID do pedido não especificado'}
            
            if connector_type not in self.connectors:
                return {'success': False, 'error': f'Conector {connector_type} não configurado'}
                
            connector = self.connectors[connector_type]
            
            if not hasattr(connector, 'get_cancellation_reasons'):
                return {'success': False, 'error': f'Conector {connector_type} não suporta consulta de motivos'}
                
            reasons = await connector.get_cancellation_reasons(order_id)
            
            return {
                'success': True,
                'order_id': order_id,
                'connector': connector_type,
                'reasons': reasons
            }
            
        except Exception as e:
            logger.error(f"Error listing cancellation reasons: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def dispatch_order(self, intent: Intent, context: Context) -> Dict[str, Any]:
        """
        Despacha pedido específico
        """
        try:
            order_id = intent.entities.get('order_id')
            connector_type = intent.connector or self.state.last_connector or 'ifood'
            
            if not order_id:
                return {'success': False, 'error': 'ID do pedido não especificado'}
            
            if connector_type not in self.connectors:
                return {'success': False, 'error': f'Conector {connector_type} não configurado'}
            
            connector = self.connectors[connector_type]
            
            if not hasattr(connector, 'dispatch_order'):
                return {'success': False, 'error': f'Conector {connector_type} não suporta despacho'}
                
            result = await connector.dispatch_order(order_id)
            
            return {
                'success': True,
                'order_id': order_id,
                'connector': connector_type,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Error dispatching order: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def open_store(self, intent: Intent, context: Context) -> Dict[str, Any]:
        """
        Abre a loja
        """
        try:
            connector_type = intent.connector or 'ifood'
            
            if connector_type not in self.connectors:
                return {'success': False, 'error': f'Conector {connector_type} não configurado'}
                
            connector = self.connectors[connector_type]
            
            if not hasattr(connector, 'open_store'):
                return {'success': False, 'error': f'Conector {connector_type} não suporte gestão de loja'}
                
            result = await connector.open_store()
            
            return {
                'success': True,
                'status': 'OPEN',
                'connector': connector_type,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Error opening store: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def close_store(self, intent: Intent, context: Context) -> Dict[str, Any]:
        """
        Fecha a loja
        """
        try:
            reason = intent.entities.get('reason', 'Fechado pelo gestor')
            duration = int(intent.entities.get('duration', 60))
            connector_type = intent.connector or 'ifood'
            
            if connector_type not in self.connectors:
                return {'success': False, 'error': f'Conector {connector_type} não configurado'}
                
            connector = self.connectors[connector_type]
            
            if not hasattr(connector, 'close_store'):
                return {'success': False, 'error': f'Conector {connector_type} não suporte gestão de loja'}
                
            result = await connector.close_store(reason=reason, duration_minutes=duration)
            
            return {
                'success': True,
                'status': 'CLOSED',
                'connector': connector_type,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Error closing store: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def check_revenue(self, intent: Intent, context: Context) -> Dict[str, Any]:
        """
        Verifica faturamento
        
        Args:
            intent: Intenção com período
            context: Contexto da conversa
        
        Returns:
            Dados de faturamento
        """
        try:
            time_period = intent.entities.get('time_period', 'today')
            connector_type = intent.connector or 'ifood'
            
            if connector_type not in self.connectors:
                return {
                    'success': False,
                    'error': f"Connector '{connector_type}' not found",
                    'period': time_period
                }
            
            # Usar conector real
            connector = self.connectors[connector_type]
            revenue = await connector.get_revenue(time_period)
            
            # Atualizar estado
            self.state.last_revenue = revenue
            
            return {
                'success': True,
                'connector': connector_type,
                'revenue': revenue
            }
            
        except Exception as e:
            logger.error(f"Error checking revenue: {str(e)}")
            return {
                'success': False,
                'error': f"Erro ao verificar faturamento: {str(e)}"
            }
    
    async def manage_store(self, intent: Intent, context: Context) -> Dict[str, Any]:
        """
        Gerencia status da loja
        
        Args:
            intent: Intenção com ação (open, close, pause)
            context: Contexto da conversa
        
        Returns:
            Status da loja
        """
        try:
            action = intent.entities.get('action', 'status')
            duration = intent.entities.get('duration')
            connector_type = intent.connector or 'ifood'
            
            if connector_type not in self.connectors:
                return {
                    'success': False,
                    'error': f"Connector '{connector_type}' not found"
                }
            
            # Usar conector real
            connector = self.connectors[connector_type]
            result = await connector.manage_store(action, duration)
            
            return {
                'success': True,
                'connector': connector_type,
                'action': action,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Error managing store: {str(e)}")
            return {
                'success': False,
                'error': f"Erro ao gerenciar loja: {str(e)}"
            }
    
    async def update_inventory(self, intent: Intent, context: Context) -> Dict[str, Any]:
        """
        Atualiza estoque
        
        Args:
            intent: Intenção com item e quantidade
            context: Contexto da conversa
        
        Returns:
            Status do estoque
        """
        try:
            item = intent.entities.get('item')
            quantity = intent.entities.get('quantity')
            connector_type = intent.connector or 'ifood'
            
            if connector_type not in self.connectors:
                return {
                    'success': False,
                    'error': f"Connector '{connector_type}' not found"
                }
            
            # Usar conector real
            connector = self.connectors[connector_type]
            result = await connector.update_inventory(item, quantity)
            
            return {
                'success': True,
                'connector': connector_type,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Error updating inventory: {str(e)}")
            return {
                'success': False,
                'error': f"Erro ao atualizar estoque: {str(e)}"
            }
    
    async def forecast_demand(self, intent: Intent, context: Context) -> Dict[str, Any]:
        """
        Prevê demanda
        
        Args:
            intent: Intenção com período
            context: Contexto da conversa
        
        Returns:
            Previsão de demanda
        """
        try:
            period = intent.entities.get('period', 'week')
            connector_type = intent.connector or 'ifood'
            
            if connector_type not in self.connectors:
                return {
                    'success': False,
                    'error': f"Connector '{connector_type}' not found"
                }
            
            # Usar conector real
            connector = self.connectors[connector_type]
            forecast = await connector.forecast_demand(period)
            
            return {
                'success': True,
                'connector': connector_type,
                'forecast': forecast
            }
            
        except Exception as e:
            logger.error(f"Error forecasting demand: {str(e)}")
            return {
                'success': False,
                'error': f"Erro ao prever demanda: {str(e)}"
            }

    async def greeting(self, intent: Intent, context: Context) -> Dict[str, Any]:
        """
        Responde a cumprimentos
        
        Args:
            intent: Intenção
            context: Contexto
        
        Returns:
            Mensagem de saudação
        """
        return {
            'success': True,
            'message': "Olá! Sou seu assistente de varejo. Como posso ajudar com seus pedidos, estoque ou faturamento hoje?",
            'options': ['Ver pedidos', 'Ver faturamento', 'Gerenciar loja']
        }
    
    async def handle_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """
        Processa eventos do Event Bus
        
        Args:
            event_type: Tipo de evento
            event_data: Dados do evento
        """
        try:
            logger.info(f"Handling retail event: {event_type}")
            
            if event_type == 'order_received':
                # Novo pedido recebido
                await self._handle_new_order(event_data)
            elif event_type == 'order_confirmed':
                # Pedido confirmado
                await self._handle_order_confirmed(event_data)
            elif event_type == 'order_cancelled':
                # Pedido cancelado
                await self._handle_order_cancelled(event_data)
            else:
                logger.warning(f"Unknown event type: {event_type}")
                
        except Exception as e:
            logger.error(f"Error handling event {event_type}: {str(e)}")
    
    async def _handle_new_order(self, event_data: Dict[str, Any]) -> None:
        """Processa novo pedido"""
        order_id = event_data.get('order_id')
        connector = event_data.get('connector')
        merchant_id = event_data.get('merchant_id')
        total_amount = event_data.get('total_amount')
        
        logger.info(f"New order received: {order_id} from {connector}")
        
        try:
            # 1. Notificar usuário em todos os canais
            from app.omnichannel.interface import OmnichannelInterface
            user_repo = UserRepository()
            user = await user_repo.get_by_email(f"merchant_{merchant_id}@ifood.com")
            
            if user and hasattr(self, 'omnichannel_interface'):
                order_notification = {
                    "order_id": order_id,
                    "total_amount": total_amount,
                    "customer": event_data.get("customer", {}),
                    "items": event_data.get("items", [])
                }
                await self.omnichannel_interface.handle_new_order_notification(
                    email=user.email,
                    order_data=order_notification,
                    connector=connector
                )
            
            # 2. Atualizar estatísticas
            await self.auditor.log_transaction(
                email=f"merchant_{merchant_id}@ifood.com",
                action="new_order_received",
                category=AuditCategory.BUSINESS_OPERATION,
                level=AuditLevel.INFO,
                input_data={"order_id": order_id, "connector": connector, "total_amount": total_amount},
                output_data={"notified": True}
            )
            
            # 3. Verificar se requer atenção especial
            if total_amount and total_amount > 500:
                await self.supervisor.evaluate_decision(
                    decision_type="high_value_order",
                    context={"order_id": order_id, "total_amount": total_amount, "connector": connector},
                    user_email=f"merchant_{merchant_id}@ifood.com"
                )
        except Exception as e:
            logger.error(f"Error handling new order: {str(e)}", exc_info=True)
    
    async def _handle_order_confirmed(self, event_data: Dict[str, Any]) -> None:
        """Processa confirmação de pedido"""
        order_id = event_data.get('order_id')
        connector = event_data.get('connector')
        merchant_id = event_data.get('merchant_id')
        
        logger.info(f"Order confirmed: {order_id} from {connector}")
        
        try:
            # 1. Atualizar status interno
            await self.auditor.log_transaction(
                email=f"merchant_{merchant_id}@ifood.com",
                action="order_confirmed",
                category=AuditCategory.BUSINESS_OPERATION,
                level=AuditLevel.INFO,
                input_data={"order_id": order_id, "connector": connector},
                output_data={"status": "confirmed"}
            )
            
            # 2. Iniciar preparação
            from datetime import datetime
            await self.event_bus.publish_event(
                event=EventMessage(
                    event_type="order.preparation_started",
                    source="retail_agent",
                    user_email=f"merchant_{merchant_id}@ifood.com",
                    data={"order_id": order_id, "connector": connector, "timestamp": datetime.now().isoformat()}
                )
            )
        except Exception as e:
            logger.error(f"Error handling order confirmation: {str(e)}", exc_info=True)
    
    async def _handle_order_cancelled(self, event_data: Dict[str, Any]) -> None:
        """Processa cancelamento de pedido"""
        order_id = event_data.get('order_id')
        reason = event_data.get('reason')
        connector = event_data.get('connector')
        merchant_id = event_data.get('merchant_id')
        
        logger.info(f"Order cancelled: {order_id} from {connector}, reason: {reason}")
        
        try:
            # 1. Atualizar estatísticas
            await self.auditor.log_transaction(
                email=f"merchant_{merchant_id}@ifood.com",
                action="order_cancelled",
                category=AuditCategory.BUSINESS_OPERATION,
                level=AuditLevel.WARNING,
                input_data={"order_id": order_id, "connector": connector, "reason": reason},
                output_data={"status": "cancelled"}
            )
            
            # 2. Analisar motivo do cancelamento
            if reason in ["customer_request", "payment_failed", "out_of_stock"]:
                await self.event_bus.publish_event(
                    event=EventMessage(
                        event_type="order.cancellation_analyzed",
                        source="retail_agent",
                        user_email=f"merchant_{merchant_id}@ifood.com",
                        data={"order_id": order_id, "connector": connector, "reason": reason, "category": "cancellation_analysis"}
                    )
                )
        except Exception as e:
            logger.error(f"Error handling order cancellation: {str(e)}", exc_info=True)
    
    def _get_audit_category(self, action: str) -> AuditCategory:
        """
        Determina categoria de auditoria baseada na ação
        
        Args:
            action: Ação executada
        
        Returns:
            Categoria de auditoria apropriada
        """
        if action in ['check_orders', 'check_revenue', 'forecast_demand']:
            return AuditCategory.DATA_ACCESS
        elif action in ['confirm_order', 'cancel_order', 'manage_store', 'update_inventory']:
            return AuditCategory.DATA_MODIFICATION
        else:
            return AuditCategory.BUSINESS_OPERATION
    
    def _contains_sensitive_data(self, intent: Intent, result: Dict[str, Any]) -> bool:
        """
        Verifica se a operação contém dados sensíveis
        
        Args:
            intent: Intenção executada
            result: Resultado da operação
        
        Returns:
            True se contém dados sensíveis
        """
        # Verificar se há informações de clientes
        if 'orders' in result:
            orders = result.get('orders', [])
            for order in orders:
                if isinstance(order, dict) and 'customer' in order:
                    return True
        
        # Verificar se há dados de pagamento
        if any(keyword in str(result).lower() for keyword in ['payment', 'card', 'pix']):
            return True
        
        return False
    
    def _contains_financial_data(self, intent: Intent, result: Dict[str, Any]) -> bool:
        """
        Verifica se a operação contém dados financeiros
        
        Args:
            intent: Intenção executada
            result: Resultado da operação
        
        Returns:
            True se contém dados financeiros
        """
        # Verificar ações relacionadas a dinheiro
        if intent.action in ['check_revenue', 'check_orders']:
            return True
        
        # Verificar se há valores monetários no resultado
        if any(keyword in str(result).lower() for keyword in ['total', 'revenue', 'price', 'amount']):
            return True
        
        return False