"""
Gerenciador de sessões para o Claude Chat
Integra com a biblioteca de integração para acessar sessões do Claude CLI

Este módulo permite que o Claude Chat acesse as sessões existentes
do Claude CLI, incluindo histórico de conversas, configurações do 
Statsig e tarefas.
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Adicionar diretório pai ao path para imports relativos
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Importar a classe de integração
from claudechat.claudechat_integration import ClaudeIntegration

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SessionManager:
    """
    Gerencia as sessões de conversa para o Claude Chat,
    integrado com o sistema de arquivo do Claude CLI.
    """
    
    def __init__(self):
        """Inicializa o gerenciador de sessões."""
        self.integration = ClaudeIntegration()
        self.chat_history_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                            "data", "chat_history.json")
        self._ensure_data_dir()
        
    def _ensure_data_dir(self):
        """Garante que o diretório de dados existe."""
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        os.makedirs(data_dir, exist_ok=True)
    
    def sync_sessions(self) -> None:
        """
        Sincroniza as sessões do Claude CLI com o Claude Chat.
        """
        self.integration.sync_with_claudechat()
    
    def get_all_conversations(self) -> List[Dict[str, Any]]:
        """
        Retorna todas as conversas disponíveis.
        
        Returns:
            List[Dict]: Lista de conversas
        """
        self.sync_sessions()  # Garantir que estamos com dados atualizados
        
        try:
            if os.path.exists(self.chat_history_path):
                with open(self.chat_history_path, 'r', encoding='utf-8') as f:
                    chat_history = json.load(f)
                return chat_history.get("conversations", [])
            else:
                return []
        except Exception as e:
            logger.error(f"Erro ao obter conversas: {str(e)}")
            return []
    
    def get_conversation(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém uma conversa específica pelo ID da sessão.
        
        Args:
            session_id (str): ID da sessão
            
        Returns:
            Dict: Conversa ou None se não existir
        """
        conversations = self.get_all_conversations()
        
        for conv in conversations:
            if conv.get("session_id") == session_id:
                return conv
        
        return None
    
    def create_new_conversation(self, title: str = "Nova Conversa") -> str:
        """
        Cria uma nova conversa.
        
        Args:
            title (str): Título da conversa
            
        Returns:
            str: ID da sessão criada
        """
        session_id = self.integration.create_new_session(title)
        self.sync_sessions()
        return session_id
    
    def add_message(self, session_id: str, role: str, content: str) -> None:
        """
        Adiciona uma mensagem a uma conversa existente.
        
        Args:
            session_id (str): ID da sessão
            role (str): Papel (user ou assistant)
            content (str): Conteúdo da mensagem
        """
        if not session_id:
            logger.error("ID de sessão não fornecido")
            return
        
        # Obter metadados da sessão
        session_info = self.integration.get_session_metadata(session_id)
        if not session_info or not session_info.get("jsonl_path"):
            logger.error(f"Sessão não encontrada: {session_id}")
            return
        
        try:
            jsonl_path = session_info["jsonl_path"]
            
            # Preparar nova mensagem
            timestamp = datetime.now().isoformat() + "Z"
            new_message = {
                "userType": "external" if role == "user" else "claude",
                "cwd": os.environ.get("CLAUDE_DIR", "/root/.claude"),
                "sessionId": session_id,
                "type": role,
                "message": {
                    "role": role,
                    "content": content
                },
                "uuid": os.urandom(16).hex(),
                "timestamp": timestamp
            }
            
            # Adicionar ao arquivo JSONL
            with open(jsonl_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(new_message) + "\n")
            
            # Atualizar o chat_history.json
            self.sync_sessions()
            
        except Exception as e:
            logger.error(f"Erro ao adicionar mensagem: {str(e)}")
    
    def get_user_info(self) -> Dict[str, Any]:
        """
        Obtém informações do usuário.
        
        Returns:
            Dict: Informações do usuário
        """
        try:
            if os.path.exists(self.chat_history_path):
                with open(self.chat_history_path, 'r', encoding='utf-8') as f:
                    chat_history = json.load(f)
                return chat_history.get("user_info", {})
            else:
                return {}
        except Exception as e:
            logger.error(f"Erro ao obter informações do usuário: {str(e)}")
            return {}
    
    def update_user_info(self, user_info: Dict[str, Any]) -> None:
        """
        Atualiza informações do usuário.
        
        Args:
            user_info (Dict): Novas informações do usuário
        """
        self.integration.update_chat_history_with_user_info(user_info)
    
    def get_todos(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Obtém a lista de tarefas de uma sessão.
        
        Args:
            session_id (str): ID da sessão
            
        Returns:
            List[Dict]: Lista de tarefas
        """
        return self.integration.get_todos(session_id)
    
    def get_feature_flags(self, session_id: str) -> Dict[str, Any]:
        """
        Obtém os feature flags do Statsig para uma sessão.
        
        Args:
            session_id (str): ID da sessão
            
        Returns:
            Dict: Feature flags
        """
        statsig_config = self.integration.get_statsig_config(session_id)
        return statsig_config.get("feature_gates", {})
    
    def get_dynamic_configs(self, session_id: str) -> Dict[str, Any]:
        """
        Obtém as configurações dinâmicas do Statsig para uma sessão.
        
        Args:
            session_id (str): ID da sessão
            
        Returns:
            Dict: Configurações dinâmicas
        """
        statsig_config = self.integration.get_statsig_config(session_id)
        return statsig_config.get("dynamic_configs", {})
    
    def check_feature(self, session_id: str, feature_name: str, default: bool = False) -> bool:
        """
        Verifica se um feature flag está ativado para uma sessão.
        
        Args:
            session_id (str): ID da sessão
            feature_name (str): Nome do feature flag
            default (bool): Valor padrão se não encontrado
            
        Returns:
            bool: True se o feature estiver ativado, False caso contrário
        """
        feature_flags = self.get_feature_flags(session_id)
        
        # Buscar por nomes ou por hashes numéricos
        for key, flag in feature_flags.items():
            if key == feature_name or flag.get("name") == feature_name:
                return flag.get("value", default)
        
        return default
    
    def get_config_value(self, session_id: str, config_name: str, default: Any = None) -> Any:
        """
        Obtém o valor de uma configuração dinâmica.
        
        Args:
            session_id (str): ID da sessão
            config_name (str): Nome da configuração
            default (Any): Valor padrão se não encontrado
            
        Returns:
            Any: Valor da configuração
        """
        configs = self.get_dynamic_configs(session_id)
        
        # Buscar por nomes ou por hashes numéricos
        for key, config in configs.items():
            if key == config_name or config.get("name") == config_name:
                return config.get("value", default)
        
        return default