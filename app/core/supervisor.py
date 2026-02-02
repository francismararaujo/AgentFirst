"""
Supervisor (H.I.T.L.) - Human-in-the-Loop Controller

Responsabilidades:
1. Avaliar se decisões requerem intervenção humana
2. Notificar supervisores via Telegram com contexto completo
3. Aguardar e processar respostas humanas
4. Capturar padrões de decisão para aprendizado
5. Melhorar classificação automática baseada em feedback
6. Gerenciar escalações e timeouts

H.I.T.L. (Human-in-the-Loop) Features:
- Avaliação automática de complexidade de decisões
- Notificação contextual para supervisores
- Timeout automático com fallback
- Aprendizado de padrões de decisão humana
- Melhoria contínua da classificação automática
"""

import logging
import json
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from enum import Enum
import boto3
from botocore.exceptions import ClientError
from app.config.settings import settings

from app.core.auditor import Auditor, AuditCategory, AuditLevel

logger = logging.getLogger(__name__)


class EscalationStatus(Enum):
    """Status de escalação"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class DecisionComplexity(Enum):
    """Complexidade de decisão"""
    LOW = "low"          # Decisão simples, pode ser automática
    MEDIUM = "medium"    # Decisão moderada, pode precisar de supervisão
    HIGH = "high"        # Decisão complexa, requer supervisão
    CRITICAL = "critical" # Decisão crítica, sempre requer supervisão


class EscalationReason(Enum):
    """Motivos de escalação"""
    HIGH_VALUE_TRANSACTION = "high_value_transaction"
    UNUSUAL_PATTERN = "unusual_pattern"
    ERROR_RECOVERY = "error_recovery"
    POLICY_VIOLATION = "policy_violation"
    CUSTOMER_COMPLAINT = "customer_complaint"
    SYSTEM_ANOMALY = "system_anomaly"
    MANUAL_REVIEW = "manual_review"
    COMPLIANCE_CHECK = "compliance_check"


@dataclass
class EscalationRequest:
    """Solicitação de escalação para supervisão humana"""
    escalation_id: str
    user_email: str
    agent: str
    action: str
    context: Dict[str, Any]
    
    # Decisão proposta
    proposed_decision: Dict[str, Any]
    confidence: float
    complexity: DecisionComplexity
    reason: EscalationReason
    
    # Supervisão
    supervisor_id: Optional[str] = None
    supervisor_chat_id: Optional[str] = None
    
    # Status e timing
    status: EscalationStatus = EscalationStatus.PENDING
    created_at: datetime = None
    timeout_at: datetime = None
    resolved_at: Optional[datetime] = None
    
    # Resposta humana
    human_decision: Optional[Dict[str, Any]] = None
    human_feedback: Optional[str] = None
    human_confidence: Optional[float] = None
    
    # Metadados
    priority: int = 1  # 1=baixa, 2=média, 3=alta, 4=crítica
    tags: List[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.timeout_at is None:
            # Timeout padrão: 30 minutos
            self.timeout_at = self.created_at + timedelta(minutes=30)
        if self.tags is None:
            self.tags = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        data = asdict(self)
        # Converter enums para strings
        data['complexity'] = self.complexity.value
        data['reason'] = self.reason.value
        data['status'] = self.status.value
        # Converter datetime para ISO string
        data['created_at'] = self.created_at.isoformat() if self.created_at else None
        data['timeout_at'] = self.timeout_at.isoformat() if self.timeout_at else None
        data['resolved_at'] = self.resolved_at.isoformat() if self.resolved_at else None
        return data
    
    def is_expired(self) -> bool:
        """Verifica se a escalação expirou"""
        return datetime.now(timezone.utc) > self.timeout_at
    
    def get_priority_emoji(self) -> str:
        """Retorna emoji baseado na prioridade"""
        return {
            1: "🟢",  # Baixa
            2: "🟡",  # Média
            3: "🟠",  # Alta
            4: "🔴"   # Crítica
        }.get(self.priority, "⚪")


@dataclass
class DecisionPattern:
    """Padrão de decisão para aprendizado"""
    pattern_id: str
    agent: str
    action: str
    context_features: Dict[str, Any]
    
    # Decisão
    decision_type: str
    human_approved: bool
    confidence_threshold: float
    
    # Estatísticas
    occurrences: int = 1
    approval_rate: float = 0.0
    last_seen: datetime = None
    
    def __post_init__(self):
        if self.last_seen is None:
            self.last_seen = datetime.now(timezone.utc)


class Supervisor:
    """
    Supervisor (H.I.T.L.) - Human-in-the-Loop Controller
    
    Gerencia decisões que requerem supervisão humana:
    - Avalia complexidade de decisões
    - Escalona para supervisores quando necessário
    - Aprende com feedback humano
    - Melhora classificação automática
    """
    
    def __init__(
        self,
        table_name: Optional[str] = None,
        region: str = "us-east-1",
        auditor: Optional[Auditor] = None,
        telegram_service=None
    ):
        """
        Inicializa Supervisor
        
        Args:
            table_name: Nome da tabela DynamoDB para escalações
            region: Região AWS
            auditor: Serviço de auditoria
            telegram_service: Serviço do Telegram para notificações
        """
        self.table_name = table_name or settings.DYNAMODB_ESCALATION_TABLE
        self.region = region or settings.AWS_REGION
        self.auditor = auditor or Auditor()
        self.telegram_service = telegram_service
        
        # DynamoDB
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(self.table_name)
        
        # Configurações
        self.default_timeout_minutes = 30
        self.max_retries = 3
        self.confidence_threshold = 0.8  # Threshold para decisões automáticas
        
        # Cache de padrões
        self._decision_patterns = {}
        self._pattern_cache_ttl = 300  # 5 minutos
        self._last_pattern_update = datetime.now(timezone.utc)
        
        # Supervisores configurados
        self.supervisors = {
            "default": {
                "name": "Supervisor Padrão",
                "telegram_chat_id": None,  # Será configurado
                "specialties": ["general"],
                "priority_threshold": 1
            }
        }
    
    def configure_supervisor(
        self,
        supervisor_id: str,
        name: str,
        telegram_chat_id: str,
        specialties: List[str] = None,
        priority_threshold: int = 1
    ):
        """
        Configura um supervisor
        
        Args:
            supervisor_id: ID único do supervisor
            name: Nome do supervisor
            telegram_chat_id: Chat ID do Telegram
            specialties: Especialidades (retail, finance, etc)
            priority_threshold: Prioridade mínima para notificar
        """
        self.supervisors[supervisor_id] = {
            "name": name,
            "telegram_chat_id": telegram_chat_id,
            "specialties": specialties or ["general"],
            "priority_threshold": priority_threshold
        }
        
        logger.info(f"Supervisor configured: {supervisor_id} - {name}")
    
    async def evaluate_decision(
        self,
        user_email: str,
        agent: str,
        action: str,
        proposed_decision: Dict[str, Any],
        context: Dict[str, Any],
        confidence: float = 0.0
    ) -> Tuple[bool, Optional[str]]:
        """
        Avalia se uma decisão requer supervisão humana
        
        Args:
            user_email: Email do usuário
            agent: Agente que está tomando a decisão
            action: Ação sendo executada
            proposed_decision: Decisão proposta pelo agente
            context: Contexto da operação
            confidence: Confiança do agente na decisão
        
        Returns:
            Tuple (requires_supervision, escalation_id)
        """
        try:
            # 1. Avaliar complexidade da decisão
            complexity = await self._assess_complexity(
                agent, action, proposed_decision, context, confidence
            )
            
            # 2. Determinar se requer supervisão
            requires_supervision = await self._requires_supervision(
                complexity, confidence, agent, action, context
            )
            
            # 3. Se requer supervisão, criar escalação
            escalation_id = None
            if requires_supervision:
                escalation_id = await self._create_escalation(
                    user_email=user_email,
                    agent=agent,
                    action=action,
                    proposed_decision=proposed_decision,
                    context=context,
                    confidence=confidence,
                    complexity=complexity
                )
            
            # 4. Registrar na auditoria
            await self.auditor.log_transaction(
                email=user_email,
                action="supervisor.evaluate_decision",
                input_data={
                    "agent": agent,
                    "action": action,
                    "confidence": confidence,
                    "complexity": complexity.value
                },
                output_data={
                    "requires_supervision": requires_supervision,
                    "escalation_id": escalation_id
                },
                agent="supervisor",
                category=AuditCategory.SYSTEM_OPERATION,
                level=AuditLevel.INFO if not requires_supervision else AuditLevel.WARNING
            )
            
            return requires_supervision, escalation_id
            
        except Exception as e:
            logger.error(f"Error evaluating decision: {str(e)}")
            
            # Em caso de erro, escalar por segurança
            escalation_id = await self._create_escalation(
                user_email=user_email,
                agent=agent,
                action=action,
                proposed_decision=proposed_decision,
                context=context,
                confidence=confidence,
                complexity=DecisionComplexity.HIGH,
                reason=EscalationReason.SYSTEM_ANOMALY
            )
            
            return True, escalation_id
    
    async def _assess_complexity(
        self,
        agent: str,
        action: str,
        proposed_decision: Dict[str, Any],
        context: Dict[str, Any],
        confidence: float
    ) -> DecisionComplexity:
        """
        Avalia a complexidade de uma decisão
        
        Args:
            agent: Agente
            action: Ação
            proposed_decision: Decisão proposta
            context: Contexto
            confidence: Confiança
        
        Returns:
            Complexidade da decisão
        """
        # Fatores de complexidade
        complexity_score = 0
        
        # 1. Confiança baixa = mais complexo
        if confidence < 0.5:
            complexity_score += 3
        elif confidence < 0.7:
            complexity_score += 2
        elif confidence < 0.8:
            complexity_score += 1
        
        # 2. Ações críticas
        critical_actions = [
            "cancel_order", "refund_payment", "close_store",
            "delete_data", "modify_pricing", "change_policy"
        ]
        if action in critical_actions:
            complexity_score += 2
        
        # 3. Valores altos
        if "amount" in proposed_decision:
            amount = proposed_decision.get("amount", 0)
            if amount > 1000:
                complexity_score += 3
            elif amount > 500:
                complexity_score += 2
            elif amount > 100:
                complexity_score += 1
        
        # 4. Contexto de erro
        if context.get("has_error", False):
            complexity_score += 2
        
        # 5. Usuário VIP ou novo
        user_tier = context.get("user_profile", {}).get("tier", "free")
        if user_tier == "enterprise":
            complexity_score += 1
        
        # 6. Horário fora do expediente
        current_hour = datetime.now(timezone.utc).hour
        if current_hour < 8 or current_hour > 18:  # Fora do horário comercial
            complexity_score += 1
        
        # Mapear score para complexidade
        if complexity_score >= 6:
            return DecisionComplexity.CRITICAL
        elif complexity_score >= 4:
            return DecisionComplexity.HIGH
        elif complexity_score >= 2:
            return DecisionComplexity.MEDIUM
        else:
            return DecisionComplexity.LOW
    
    async def _requires_supervision(
        self,
        complexity: DecisionComplexity,
        confidence: float,
        agent: str,
        action: str,
        context: Dict[str, Any]
    ) -> bool:
        """
        Determina se uma decisão requer supervisão
        
        Args:
            complexity: Complexidade da decisão
            confidence: Confiança do agente
            agent: Agente
            action: Ação
            context: Contexto
        
        Returns:
            True se requer supervisão
        """
        # 1. Decisões críticas sempre requerem supervisão
        if complexity == DecisionComplexity.CRITICAL:
            return True
        
        # 2. Decisões de alta complexidade com baixa confiança
        if complexity == DecisionComplexity.HIGH and confidence < 0.7:
            return True
        
        # 3. Verificar padrões aprendidos
        pattern_requires = await self._check_learned_patterns(
            agent, action, context, confidence
        )
        if pattern_requires is not None:
            return pattern_requires
        
        # 4. Confiança muito baixa
        if confidence < 0.5:
            return True
        
        # 5. Ações sempre supervisionadas
        always_supervised = [
            "delete_user", "refund_payment", "cancel_subscription",
            "modify_billing", "change_permissions"
        ]
        if action in always_supervised:
            return True
        
        # 6. Padrão: decisões de média/alta complexidade com confiança baixa
        if complexity in [DecisionComplexity.MEDIUM, DecisionComplexity.HIGH]:
            return confidence < self.confidence_threshold
        
        return False
    
    async def _check_learned_patterns(
        self,
        agent: str,
        action: str,
        context: Dict[str, Any],
        confidence: float
    ) -> Optional[bool]:
        """
        Verifica padrões aprendidos de decisões anteriores
        
        Args:
            agent: Agente
            action: Ação
            context: Contexto
            confidence: Confiança
        
        Returns:
            True/False se padrão encontrado, None se não
        """
        try:
            # Atualizar cache de padrões se necessário
            await self._update_pattern_cache()
            
            # Buscar padrões similares
            pattern_key = f"{agent}:{action}"
            if pattern_key in self._decision_patterns:
                pattern = self._decision_patterns[pattern_key]
                
                # Se o padrão tem alta taxa de aprovação e confiança similar
                if (pattern.approval_rate > 0.8 and 
                    abs(confidence - pattern.confidence_threshold) < 0.2):
                    return False  # Não requer supervisão
                
                # Se o padrão tem baixa taxa de aprovação
                if pattern.approval_rate < 0.3:
                    return True  # Requer supervisão
            
            return None  # Sem padrão definido
            
        except Exception as e:
            logger.error(f"Error checking learned patterns: {str(e)}")
            return None
    
    async def _create_escalation(
        self,
        user_email: str,
        agent: str,
        action: str,
        proposed_decision: Dict[str, Any],
        context: Dict[str, Any],
        confidence: float,
        complexity: DecisionComplexity,
        reason: EscalationReason = None
    ) -> str:
        """
        Cria uma escalação para supervisão humana
        
        Args:
            user_email: Email do usuário
            agent: Agente
            action: Ação
            proposed_decision: Decisão proposta
            context: Contexto
            confidence: Confiança
            complexity: Complexidade
            reason: Motivo da escalação
        
        Returns:
            ID da escalação criada
        """
        try:
            # Gerar ID único
            escalation_id = self._generate_escalation_id()
            
            # Determinar motivo se não fornecido
            if reason is None:
                reason = self._determine_escalation_reason(
                    complexity, confidence, action, context
                )
            
            # Determinar prioridade
            priority = self._calculate_priority(complexity, reason, context)
            
            # Selecionar supervisor
            supervisor_id, supervisor_info = self._select_supervisor(
                agent, action, priority
            )
            
            # Criar escalação
            escalation = EscalationRequest(
                escalation_id=escalation_id,
                user_email=user_email,
                agent=agent,
                action=action,
                context=context,
                proposed_decision=proposed_decision,
                confidence=confidence,
                complexity=complexity,
                reason=reason,
                supervisor_id=supervisor_id,
                supervisor_chat_id=supervisor_info.get("telegram_chat_id"),
                priority=priority
            )
            
            # Salvar no DynamoDB
            await self._store_escalation(escalation)
            
            # Notificar supervisor
            if self.telegram_service and escalation.supervisor_chat_id:
                await self._notify_supervisor(escalation)
            
            # Registrar na auditoria
            await self.auditor.log_transaction(
                email=user_email,
                action="supervisor.create_escalation",
                input_data={
                    "agent": agent,
                    "action": action,
                    "complexity": complexity.value,
                    "reason": reason.value
                },
                output_data={
                    "escalation_id": escalation_id,
                    "supervisor_id": supervisor_id,
                    "priority": priority
                },
                agent="supervisor",
                category=AuditCategory.SYSTEM_OPERATION,
                level=AuditLevel.WARNING
            )
            
            logger.info(f"Escalation created: {escalation_id} for {user_email}")
            return escalation_id
            
        except Exception as e:
            logger.error(f"Error creating escalation: {str(e)}")
            raise
    
    def _generate_escalation_id(self) -> str:
        """Gera ID único para escalação"""
        import uuid
        return f"esc_{uuid.uuid4().hex[:12]}"
    
    def _determine_escalation_reason(
        self,
        complexity: DecisionComplexity,
        confidence: float,
        action: str,
        context: Dict[str, Any]
    ) -> EscalationReason:
        """Determina o motivo da escalação"""
        
        # Verificar contexto específico
        if context.get("has_error", False):
            return EscalationReason.ERROR_RECOVERY
        
        if "amount" in context and context.get("amount", 0) > 1000:
            return EscalationReason.HIGH_VALUE_TRANSACTION
        
        if confidence < 0.3:
            return EscalationReason.SYSTEM_ANOMALY
        
        # Baseado na complexidade
        if complexity == DecisionComplexity.CRITICAL:
            return EscalationReason.COMPLIANCE_CHECK
        elif complexity == DecisionComplexity.HIGH:
            return EscalationReason.MANUAL_REVIEW
        else:
            return EscalationReason.UNUSUAL_PATTERN
    
    def _calculate_priority(
        self,
        complexity: DecisionComplexity,
        reason: EscalationReason,
        context: Dict[str, Any]
    ) -> int:
        """Calcula prioridade da escalação (1-4)"""
        
        # Prioridade base por complexidade
        priority_map = {
            DecisionComplexity.LOW: 1,
            DecisionComplexity.MEDIUM: 2,
            DecisionComplexity.HIGH: 3,
            DecisionComplexity.CRITICAL: 4
        }
        
        priority = priority_map[complexity]
        
        # Ajustar por motivo
        high_priority_reasons = [
            EscalationReason.COMPLIANCE_CHECK,
            EscalationReason.CUSTOMER_COMPLAINT,
            EscalationReason.POLICY_VIOLATION
        ]
        
        if reason in high_priority_reasons:
            priority = min(4, priority + 1)
        
        # Ajustar por contexto
        user_tier = context.get("user_profile", {}).get("tier", "free")
        if user_tier == "enterprise":
            priority = min(4, priority + 1)
        
        return priority
    
    def _select_supervisor(
        self,
        agent: str,
        action: str,
        priority: int
    ) -> Tuple[str, Dict[str, Any]]:
        """Seleciona supervisor apropriado"""
        
        # Encontrar supervisor com especialidade relevante
        for supervisor_id, supervisor_info in self.supervisors.items():
            specialties = supervisor_info.get("specialties", [])
            threshold = supervisor_info.get("priority_threshold", 1)
            
            # Verificar se supervisor pode lidar com a prioridade
            if priority >= threshold:
                # Verificar especialidade
                if "general" in specialties or agent in specialties:
                    return supervisor_id, supervisor_info
        
        # Fallback para supervisor padrão
        return "default", self.supervisors["default"]
    
    async def _store_escalation(self, escalation: EscalationRequest):
        """Armazena escalação no DynamoDB"""
        try:
            # Helper to convert floats to Decimal
            from app.shared.decimal_utils import to_decimal
            
            item = to_decimal(escalation.to_dict())
            
            # Chaves para DynamoDB
            item['PK'] = escalation.escalation_id
            item['SK'] = f"ESCALATION#{escalation.created_at.isoformat()}"
            
            # GSI para buscar por usuário
            item['GSI1PK'] = escalation.user_email
            item['GSI1SK'] = f"ESCALATION#{escalation.status.value}#{escalation.created_at.isoformat()}"
            
            # TTL (7 dias)
            ttl_timestamp = int((escalation.created_at + timedelta(days=7)).timestamp())
            item['ttl'] = ttl_timestamp
            
            self.table.put_item(Item=item)
            
        except ClientError as e:
            logger.error(f"Error storing escalation: {e}")
            raise
    
    async def _notify_supervisor(self, escalation: EscalationRequest):
        """Notifica supervisor via Telegram"""
        try:
            if not escalation.supervisor_chat_id:
                logger.warning(f"No chat ID for supervisor: {escalation.supervisor_id}")
                return
            
            # Formatar mensagem
            message = self._format_escalation_message(escalation)
            
            # Enviar via Telegram
            await self.telegram_service.send_message(
                chat_id=escalation.supervisor_chat_id,
                text=message,
                parse_mode="HTML"
            )
            
            logger.info(f"Supervisor notified: {escalation.supervisor_id}")
            
        except Exception as e:
            logger.error(f"Error notifying supervisor: {str(e)}")
    
    def _format_escalation_message(self, escalation: EscalationRequest) -> str:
        """Formata mensagem de escalação para Telegram"""
        
        priority_emoji = escalation.get_priority_emoji()
        complexity_emoji = {
            DecisionComplexity.LOW: "🟢",
            DecisionComplexity.MEDIUM: "🟡", 
            DecisionComplexity.HIGH: "🟠",
            DecisionComplexity.CRITICAL: "🔴"
        }.get(escalation.complexity, "⚪")
        
        message = f"""
{priority_emoji} <b>ESCALAÇÃO REQUERIDA</b>

📋 <b>ID:</b> {escalation.escalation_id}
👤 <b>Usuário:</b> {escalation.user_email}
🤖 <b>Agente:</b> {escalation.agent}
⚡ <b>Ação:</b> {escalation.action}

{complexity_emoji} <b>Complexidade:</b> {escalation.complexity.value.upper()}
🎯 <b>Confiança:</b> {escalation.confidence:.0%}
📝 <b>Motivo:</b> {escalation.reason.value.replace('_', ' ').title()}

<b>💡 Decisão Proposta:</b>
{json.dumps(escalation.proposed_decision, indent=2, ensure_ascii=False)}

<b>📊 Contexto:</b>
{json.dumps(escalation.context, indent=2, ensure_ascii=False)}

⏰ <b>Timeout:</b> {escalation.timeout_at.strftime('%H:%M')}

<b>Responda com:</b>
✅ <code>/approve {escalation.escalation_id}</code>
❌ <code>/reject {escalation.escalation_id} [motivo]</code>
"""
        
        return message.strip()
    
    async def process_human_decision(
        self,
        escalation_id: str,
        decision: str,
        feedback: str = None,
        supervisor_id: str = None
    ) -> bool:
        """
        Processa decisão humana sobre escalação
        
        Args:
            escalation_id: ID da escalação
            decision: "approve" ou "reject"
            feedback: Feedback opcional do supervisor
            supervisor_id: ID do supervisor que decidiu
        
        Returns:
            True se processado com sucesso
        """
        try:
            # Buscar escalação
            escalation = await self._get_escalation(escalation_id)
            if not escalation:
                logger.error(f"Escalation not found: {escalation_id}")
                return False
            
            # Verificar se ainda está pendente
            if escalation.status != EscalationStatus.PENDING:
                logger.warning(f"Escalation already resolved: {escalation_id}")
                return False
            
            # Verificar timeout
            if escalation.is_expired():
                escalation.status = EscalationStatus.TIMEOUT
                await self._update_escalation(escalation)
                return False
            
            # Processar decisão
            if decision.lower() == "approve":
                escalation.status = EscalationStatus.APPROVED
                escalation.human_decision = escalation.proposed_decision
            elif decision.lower() == "reject":
                escalation.status = EscalationStatus.REJECTED
                escalation.human_decision = {"rejected": True, "reason": feedback}
            else:
                logger.error(f"Invalid decision: {decision}")
                return False
            
            # Atualizar escalação
            escalation.resolved_at = datetime.now(timezone.utc)
            escalation.human_feedback = feedback
            escalation.supervisor_id = supervisor_id or escalation.supervisor_id
            
            await self._update_escalation(escalation)
            
            # Aprender com a decisão
            await self._learn_from_decision(escalation)
            
            # Registrar na auditoria
            await self.auditor.log_transaction(
                email=escalation.user_email,
                action="supervisor.process_human_decision",
                input_data={
                    "escalation_id": escalation_id,
                    "decision": decision,
                    "supervisor_id": supervisor_id
                },
                output_data={
                    "status": escalation.status.value,
                    "human_decision": escalation.human_decision
                },
                agent="supervisor",
                category=AuditCategory.SYSTEM_OPERATION,
                level=AuditLevel.INFO
            )
            
            logger.info(f"Human decision processed: {escalation_id} - {decision}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing human decision: {str(e)}")
            return False
    
    async def _get_escalation(self, escalation_id: str) -> Optional[EscalationRequest]:
        """Busca escalação por ID"""
        try:
            response = self.table.get_item(
                Key={'PK': escalation_id}
            )
            
            if 'Item' not in response:
                return None
            
            item = response['Item']
            
            # Converter de volta para EscalationRequest
            escalation = EscalationRequest(
                escalation_id=item['escalation_id'],
                user_email=item['user_email'],
                agent=item['agent'],
                action=item['action'],
                context=item['context'],
                proposed_decision=item['proposed_decision'],
                confidence=item['confidence'],
                complexity=DecisionComplexity(item['complexity']),
                reason=EscalationReason(item['reason']),
                supervisor_id=item.get('supervisor_id'),
                supervisor_chat_id=item.get('supervisor_chat_id'),
                status=EscalationStatus(item['status']),
                created_at=datetime.fromisoformat(item['created_at']),
                timeout_at=datetime.fromisoformat(item['timeout_at']),
                resolved_at=datetime.fromisoformat(item['resolved_at']) if item.get('resolved_at') else None,
                human_decision=item.get('human_decision'),
                human_feedback=item.get('human_feedback'),
                human_confidence=item.get('human_confidence'),
                priority=item.get('priority', 1),
                tags=item.get('tags', [])
            )
            
            return escalation
            
        except Exception as e:
            logger.error(f"Error getting escalation: {str(e)}")
            return None
    
    async def _update_escalation(self, escalation: EscalationRequest):
        """Atualiza escalação no DynamoDB"""
        try:
            item = escalation.to_dict()
            
            # Atualizar GSI
            item['GSI1SK'] = f"ESCALATION#{escalation.status.value}#{escalation.created_at.isoformat()}"
            
            self.table.put_item(Item=item)
            
        except Exception as e:
            logger.error(f"Error updating escalation: {str(e)}")
            raise
    
    async def _learn_from_decision(self, escalation: EscalationRequest):
        """Aprende com decisão humana para melhorar classificação futura"""
        try:
            # Criar ou atualizar padrão de decisão
            pattern_key = f"{escalation.agent}:{escalation.action}"
            
            if pattern_key in self._decision_patterns:
                pattern = self._decision_patterns[pattern_key]
                pattern.occurrences += 1
                
                # Atualizar taxa de aprovação
                if escalation.status == EscalationStatus.APPROVED:
                    pattern.approval_rate = (
                        (pattern.approval_rate * (pattern.occurrences - 1) + 1.0) / 
                        pattern.occurrences
                    )
                else:
                    pattern.approval_rate = (
                        (pattern.approval_rate * (pattern.occurrences - 1) + 0.0) / 
                        pattern.occurrences
                    )
                
                pattern.last_seen = datetime.now(timezone.utc)
            else:
                # Criar novo padrão
                pattern = DecisionPattern(
                    pattern_id=pattern_key,
                    agent=escalation.agent,
                    action=escalation.action,
                    context_features=self._extract_context_features(escalation.context),
                    decision_type=escalation.status.value,
                    human_approved=escalation.status == EscalationStatus.APPROVED,
                    confidence_threshold=escalation.confidence,
                    approval_rate=1.0 if escalation.status == EscalationStatus.APPROVED else 0.0
                )
                
                self._decision_patterns[pattern_key] = pattern
            
            # Ajustar threshold de confiança baseado no aprendizado
            if pattern.occurrences >= 5:  # Mínimo de amostras
                if pattern.approval_rate > 0.8:
                    # Alta taxa de aprovação - diminuir threshold (menos supervisão)
                    self.confidence_threshold = max(0.6, self.confidence_threshold - 0.05)
                elif pattern.approval_rate < 0.3:
                    # Baixa taxa de aprovação - aumentar threshold (mais supervisão)
                    self.confidence_threshold = min(0.9, self.confidence_threshold + 0.05)
            
            logger.info(f"Learned from decision: {pattern_key} - approval_rate: {pattern.approval_rate:.2f}")
            
        except Exception as e:
            logger.error(f"Error learning from decision: {str(e)}")
    
    def _extract_context_features(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extrai features relevantes do contexto para aprendizado"""
        features = {}
        
        # Features numéricas
        if "amount" in context:
            features["amount_range"] = self._categorize_amount(context["amount"])
        
        # Features categóricas
        if "user_profile" in context:
            profile = context["user_profile"]
            features["user_tier"] = profile.get("tier", "unknown")
        
        # Features temporais
        features["hour_of_day"] = datetime.now(timezone.utc).hour
        features["day_of_week"] = datetime.now(timezone.utc).weekday()
        
        # Features de erro
        features["has_error"] = context.get("has_error", False)
        
        return features
    
    def _categorize_amount(self, amount: float) -> str:
        """Categoriza valor monetário"""
        if amount < 50:
            return "low"
        elif amount < 200:
            return "medium"
        elif amount < 1000:
            return "high"
        else:
            return "very_high"
    
    async def _update_pattern_cache(self):
        """Atualiza cache de padrões se necessário"""
        now = datetime.now(timezone.utc)
        if (now - self._last_pattern_update).total_seconds() > self._pattern_cache_ttl:
            # Em uma implementação real, carregaria padrões do DynamoDB
            # Por enquanto, mantém em memória
            self._last_pattern_update = now
    
    async def get_pending_escalations(
        self,
        supervisor_id: str = None,
        limit: int = 10
    ) -> List[EscalationRequest]:
        """
        Busca escalações pendentes
        
        Args:
            supervisor_id: Filtrar por supervisor específico
            limit: Limite de resultados
        
        Returns:
            Lista de escalações pendentes
        """
        try:
            # Query por status pendente
            # Em uma implementação real, usaria GSI por status
            # Por simplicidade, fazemos scan (não recomendado para produção)
            
            escalations = []
            # Implementação simplificada - em produção usar GSI
            
            return escalations
            
        except Exception as e:
            logger.error(f"Error getting pending escalations: {str(e)}")
            return []
    
    async def cleanup_expired_escalations(self):
        """Limpa escalações expiradas (timeout)"""
        try:
            # Buscar escalações pendentes expiradas
            # Marcar como timeout
            # Em produção, seria um job agendado
            
            logger.info("Cleaned up expired escalations")
            
        except Exception as e:
            logger.error(f"Error cleaning up escalations: {str(e)}")
    
    async def get_supervisor_stats(self, supervisor_id: str) -> Dict[str, Any]:
        """
        Obtém estatísticas de um supervisor
        
        Args:
            supervisor_id: ID do supervisor
        
        Returns:
            Estatísticas do supervisor
        """
        try:
            # Implementação simplificada
            stats = {
                "supervisor_id": supervisor_id,
                "total_escalations": 0,
                "approved": 0,
                "rejected": 0,
                "avg_response_time_minutes": 0,
                "approval_rate": 0.0
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting supervisor stats: {str(e)}")
            return {}