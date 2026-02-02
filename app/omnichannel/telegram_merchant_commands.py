"""Telegram Merchant Management Commands

Handles merchant onboarding and management via Telegram.
Integrates with existing OTP authentication system.
"""

import logging
from typing import Optional, Dict, Any
import re

from app.repositories.merchant_repository import MerchantRepository
from app.domains.retail.ifood_connector import iFoodConnector
from app.config.secrets_manager import SecretsManager

logger = logging.getLogger(__name__)


class TelegramMerchantCommands:
    """Handles merchant-related commands in Telegram"""
    
    def __init__(self):
        self.merchant_repo = MerchantRepository()
        self.secrets_manager = SecretsManager()
    
    async def handle_command(
        self,
        command: str,
        user_email: str,
        message_text: str
    ) -> Optional[str]:
        """
        Handle merchant management commands
        
        Args:
            command: Command name (e.g., 'adicionar_loja', 'minhas_lojas')
            user_email: Authenticated user's email
            message_text: Full message text
            
        Returns:
            Response message or None if command not handled
        """
        handlers = {
            '/adicionar_loja': self._handle_add_merchant,
            '/minhas_lojas': self._handle_list_merchants,
            '/remover_loja': self._handle_remove_merchant,
            '/status_loja': self._handle_merchant_status,
            '/ajuda_lojas': self._handle_help,
        }
        
        handler = handlers.get(command)
        if handler:
            return await handler(user_email, message_text)
        
        return None
    
    async def _handle_add_merchant(self, user_email: str, message_text: str) -> str:
        """
        Add a new merchant (iFood store)
        
        Expected format: /adicionar_loja MERCHANT_ID
        """
        # Extract merchant_id from message
        parts = message_text.strip().split()
        
        if len(parts) < 2:
            return (
                "❌ **Formato incorreto!**\n\n"
                "Para adicionar sua loja iFood, use:\n"
                "`/adicionar_loja SEU_MERCHANT_ID`\n\n"
                "**Como encontrar seu Merchant ID:**\n"
                "1. Acesse o Portal do iFood\n"
                "2. Vá em Configurações > Integrações\n"
                "3. Copie o ID da loja\n\n"
                "Exemplo:\n"
                "`/adicionar_loja 2828a12d-bb09-4104-95c9-659f445c438f`"
            )
        
        merchant_id = parts[1].strip()
        
        # Validate UUID format
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if not re.match(uuid_pattern, merchant_id, re.IGNORECASE):
            return (
                "❌ **Merchant ID inválido!**\n\n"
                "O ID deve estar no formato UUID:\n"
                "`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`\n\n"
                "Exemplo válido:\n"
                "`2828a12d-bb09-4104-95c9-659f445c438f`"
            )
        
        # Check if merchant already exists
        existing = self.merchant_repo.get_merchant(merchant_id, user_email)
        if existing:
            status_emoji = "🟢" if existing['status'] == 'active' else "🔴"
            return (
                f"{status_emoji} **Loja já cadastrada!**\n\n"
                f"**Merchant ID:** `{merchant_id}`\n"
                f"**Status:** {existing['status']}\n"
                f"**Polling:** {'✅ Ativo' if existing['polling_enabled'] else '❌ Desativado'}\n\n"
                "Use `/minhas_lojas` para ver todas as suas lojas."
            )
        
        # Validate with iFood API
        try:
            connector = iFoodConnector(self.secrets_manager, merchant_id)
            
            if not await connector.authenticate():
                return (
                    "❌ **Falha na validação!**\n\n"
                    "Não foi possível autenticar com o iFood usando este Merchant ID.\n\n"
                    "**Verifique:**\n"
                    "• O ID está correto?\n"
                    "• A loja está ativa no iFood?\n"
                    "• Você tem permissão para usar esta loja?\n\n"
                    "Tente novamente ou entre em contato com o suporte."
                )
            
            logger.info(f"Merchant {merchant_id} validated successfully for {user_email}")
            
        except Exception as e:
            logger.error(f"Validation failed for merchant {merchant_id}: {e}")
            return (
                "❌ **Erro na validação!**\n\n"
                f"Ocorreu um erro ao validar o Merchant ID:\n"
                f"`{str(e)}`\n\n"
                "Tente novamente em alguns instantes."
            )
        
        # Create merchant in DynamoDB
        success = self.merchant_repo.create_merchant({
            'merchant_id': merchant_id,
            'user_email': user_email,
            'platform': 'ifood',
            'status': 'active',
            'polling_enabled': True
        })
        
        if not success:
            return (
                "❌ **Erro ao salvar!**\n\n"
                "A loja foi validada, mas ocorreu um erro ao salvar no banco de dados.\n\n"
                "Tente novamente em alguns instantes."
            )
        
        return (
            "✅ **Loja adicionada com sucesso!**\n\n"
            f"**Merchant ID:** `{merchant_id}`\n"
            f"**Plataforma:** iFood\n"
            f"**Status:** Ativa\n"
            f"**Polling:** ✅ Habilitado\n\n"
            "🎉 Sua loja agora está sendo monitorada!\n"
            "O sistema fará polling a cada 30 segundos para manter sua loja aberta e receber pedidos.\n\n"
            "Use `/minhas_lojas` para ver todas as suas lojas."
        )
    
    async def _handle_list_merchants(self, user_email: str, message_text: str) -> str:
        """List all merchants for the user"""
        merchants = self.merchant_repo.get_merchants_by_user(user_email)
        
        if not merchants:
            return (
                "📭 **Você ainda não tem lojas cadastradas.**\n\n"
                "Para adicionar sua primeira loja iFood, use:\n"
                "`/adicionar_loja SEU_MERCHANT_ID`\n\n"
                "Use `/ajuda_lojas` para mais informações."
            )
        
        response = f"🏪 **Suas Lojas ({len(merchants)})**\n\n"
        
        for i, merchant in enumerate(merchants, 1):
            status_emoji = "🟢" if merchant['status'] == 'active' else "🔴"
            polling_status = "✅ Ativo" if merchant['polling_enabled'] else "❌ Desativado"
            
            # Format merchant_id (show first 8 chars + ...)
            short_id = merchant['merchant_id'][:8] + "..."
            
            response += (
                f"{i}. {status_emoji} **{merchant['platform'].upper()}**\n"
                f"   ID: `{short_id}`\n"
                f"   Status: {merchant['status']}\n"
                f"   Polling: {polling_status}\n"
            )
            
            # Show last poll info if available
            if merchant.get('last_poll_success'):
                response += f"   Último poll: ✅ Sucesso\n"
            elif merchant.get('last_poll_error'):
                response += f"   Último poll: ❌ Erro\n"
            
            response += "\n"
        
        response += (
            "**Comandos disponíveis:**\n"
            "• `/adicionar_loja` - Adicionar nova loja\n"
            "• `/status_loja MERCHANT_ID` - Ver detalhes\n"
            "• `/remover_loja MERCHANT_ID` - Remover loja\n"
        )
        
        return response
    
    async def _handle_remove_merchant(self, user_email: str, message_text: str) -> str:
        """Remove (deactivate) a merchant"""
        parts = message_text.strip().split()
        
        if len(parts) < 2:
            return (
                "❌ **Formato incorreto!**\n\n"
                "Para remover uma loja, use:\n"
                "`/remover_loja MERCHANT_ID`\n\n"
                "Use `/minhas_lojas` para ver os IDs das suas lojas."
            )
        
        merchant_id = parts[1].strip()
        
        # Verify merchant exists and belongs to user
        existing = self.merchant_repo.get_merchant(merchant_id, user_email)
        if not existing:
            return (
                "❌ **Loja não encontrada!**\n\n"
                "Você não tem uma loja com este ID.\n\n"
                "Use `/minhas_lojas` para ver suas lojas cadastradas."
            )
        
        # Soft delete (set status to inactive)
        success = self.merchant_repo.delete_merchant(merchant_id, user_email)
        
        if not success:
            return (
                "❌ **Erro ao remover!**\n\n"
                "Ocorreu um erro ao remover a loja.\n\n"
                "Tente novamente em alguns instantes."
            )
        
        return (
            "✅ **Loja removida com sucesso!**\n\n"
            f"**Merchant ID:** `{merchant_id[:8]}...`\n\n"
            "A loja foi desativada e o polling foi interrompido.\n\n"
            "Use `/minhas_lojas` para ver suas lojas ativas."
        )
    
    async def _handle_merchant_status(self, user_email: str, message_text: str) -> str:
        """Get detailed status of a merchant"""
        parts = message_text.strip().split()
        
        if len(parts) < 2:
            return (
                "❌ **Formato incorreto!**\n\n"
                "Para ver o status de uma loja, use:\n"
                "`/status_loja MERCHANT_ID`\n\n"
                "Use `/minhas_lojas` para ver os IDs das suas lojas."
            )
        
        merchant_id = parts[1].strip()
        
        # Get merchant
        merchant = self.merchant_repo.get_merchant(merchant_id, user_email)
        if not merchant:
            return (
                "❌ **Loja não encontrada!**\n\n"
                "Você não tem uma loja com este ID.\n\n"
                "Use `/minhas_lojas` para ver suas lojas cadastradas."
            )
        
        status_emoji = "🟢" if merchant['status'] == 'active' else "🔴"
        polling_emoji = "✅" if merchant['polling_enabled'] else "❌"
        
        response = (
            f"{status_emoji} **Status da Loja**\n\n"
            f"**Merchant ID:** `{merchant['merchant_id']}`\n"
            f"**Plataforma:** {merchant['platform'].upper()}\n"
            f"**Status:** {merchant['status']}\n"
            f"**Polling:** {polling_emoji} {'Habilitado' if merchant['polling_enabled'] else 'Desabilitado'}\n\n"
        )
        
        # Polling status
        if merchant.get('last_poll_success'):
            from datetime import datetime
            last_success = datetime.fromtimestamp(merchant['last_poll_success'])
            response += f"**Último Poll Bem-Sucedido:**\n{last_success.strftime('%d/%m/%Y %H:%M:%S')}\n\n"
        
        if merchant.get('last_poll_error'):
            response += f"**Último Erro:**\n`{merchant['last_poll_error']}`\n\n"
        
        # Health status
        is_healthy = (
            merchant.get('last_poll_success') is not None and 
            merchant.get('last_poll_error') is None
        )
        
        if is_healthy:
            response += "✅ **Loja saudável e recebendo polling!**"
        else:
            response += "⚠️ **Atenção:** Verifique se há erros no polling."
        
        return response
    
    async def _handle_help(self, user_email: str, message_text: str) -> str:
        """Show help for merchant commands"""
        return (
            "🏪 **Gerenciamento de Lojas iFood**\n\n"
            "**Comandos disponíveis:**\n\n"
            "📍 `/adicionar_loja MERCHANT_ID`\n"
            "   Adiciona uma nova loja iFood\n\n"
            "📋 `/minhas_lojas`\n"
            "   Lista todas as suas lojas\n\n"
            "📊 `/status_loja MERCHANT_ID`\n"
            "   Mostra detalhes de uma loja\n\n"
            "🗑️ `/remover_loja MERCHANT_ID`\n"
            "   Remove uma loja\n\n"
            "**Como encontrar seu Merchant ID:**\n"
            "1. Acesse o Portal do iFood\n"
            "2. Vá em Configurações > Integrações\n"
            "3. Copie o ID da loja (formato UUID)\n\n"
            "**Exemplo de uso:**\n"
            "`/adicionar_loja 2828a12d-bb09-4104-95c9-659f445c438f`\n\n"
            "💡 **Dica:** Após adicionar uma loja, o sistema fará polling automático a cada 30 segundos para manter sua loja aberta no iFood!"
        )
