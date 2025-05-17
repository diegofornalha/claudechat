"""
Integração entre Claude CLI, Statsig e ClaudeChat
================================================

Este módulo fornece uma solução de integração entre:
- Arquivos de sessão JSONL gerados pelo Claude CLI (/root/.claude/projects/)
- Feature flags e configurações do Statsig (/root/.claude/statsig/)
- Lista de tarefas do todo (/root/.claude/todos/)
- Aplicação Claude Chat (/root/.claude/claudechat/)

A integração permite que a aplicação Claude Chat acesse e apresente 
conversas existentes do Claude CLI, além de usar as mesmas configurações
de feature flags.
"""

import os
import json
import uuid
import logging
import glob
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Caminhos padrão
CLAUDE_DIR = os.environ.get("CLAUDE_DIR", "/root/.claude")
PROJECTS_DIR = os.path.join(CLAUDE_DIR, "projects")
TODOS_DIR = os.path.join(CLAUDE_DIR, "todos")
STATSIG_DIR = os.path.join(CLAUDE_DIR, "statsig")
CLAUDECHAT_DIR = os.path.join(CLAUDE_DIR, "claudechat")
CHAT_HISTORY_PATH = os.path.join(CLAUDECHAT_DIR, "data", "chat_history.json")

# Certificar de que o diretório de dados existe
os.makedirs(os.path.join(CLAUDECHAT_DIR, "data"), exist_ok=True)

class ClaudeIntegration:
    """
    Classe responsável por integrar diferentes componentes do Claude CLI,
    gerenciar histórico de conversas e sincronizar com o Claude Chat.
    """
    
    def __init__(self):
        """Inicializa a integração."""
        self._ensure_dirs_exist()
        
    def _ensure_dirs_exist(self):
        """Garante que todos os diretórios necessários existam."""
        os.makedirs(PROJECTS_DIR, exist_ok=True)
        os.makedirs(TODOS_DIR, exist_ok=True)
        os.makedirs(os.path.join(CLAUDECHAT_DIR, "data"), exist_ok=True)
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """
        Retorna uma lista de todas as sessões disponíveis do Claude CLI
        com seus metadados.
        
        Returns:
            List[Dict]: Lista de sessões com metadados
        """
        sessions = []
        
        # Padrões para encontrar arquivos JSONL
        patterns = [
            os.path.join(PROJECTS_DIR, "-root--claude", "*.jsonl"),
            os.path.join(PROJECTS_DIR, "-root--claude-claudechat", "*.jsonl")
        ]
        
        for pattern in patterns:
            files = glob.glob(pattern)
            for file_path in files:
                session_id = os.path.basename(file_path).replace(".jsonl", "")
                
                # Extrair informações da sessão
                session_info = self.get_session_metadata(session_id)
                if session_info:
                    session_info["file_path"] = file_path
                    sessions.append(session_info)
        
        # Ordenar por data mais recente
        return sorted(sessions, key=lambda x: x.get("last_updated", ""), reverse=True)
    
    def get_session_metadata(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém metadados de uma sessão específica.
        
        Args:
            session_id (str): ID da sessão
            
        Returns:
            Dict: Metadados da sessão ou None se não existir
        """
        # Verificar padrões de arquivos JSONL
        patterns = [
            os.path.join(PROJECTS_DIR, "-root--claude", f"{session_id}.jsonl"),
            os.path.join(PROJECTS_DIR, "-root--claude-claudechat", f"{session_id}.jsonl")
        ]
        
        jsonl_path = None
        for pattern in patterns:
            if os.path.exists(pattern):
                jsonl_path = pattern
                break
        
        if not jsonl_path:
            return None
        
        # Ler primeira e última mensagem para obter metadados
        try:
            with open(jsonl_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
                if not lines:
                    return None
                
                first_message = json.loads(lines[0])
                last_message = json.loads(lines[-1])
                
                # Extrair título da primeira mensagem do usuário
                title = self._extract_title(first_message)
                
                # Calcular estatísticas da conversa
                message_count = len([line for line in lines if '"type":"user"' in line or 
                                      '"role":"user"' in line])
                
                # Verificar timestamp
                created_at = first_message.get("timestamp", "")
                updated_at = last_message.get("timestamp", "")
                
                # Verificar se existe arquivo de tarefas
                todos_path = os.path.join(TODOS_DIR, f"{session_id}.json")
                has_todos = os.path.exists(todos_path)
                
                # Verificar se existe configuração Statsig
                statsig_files = glob.glob(os.path.join(STATSIG_DIR, f"statsig.cached.evaluations.*"))
                statsig_file = None
                
                for sf in statsig_files:
                    try:
                        with open(sf, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if session_id in content:
                                statsig_file = sf
                                break
                    except:
                        continue
                        
                return {
                    "session_id": session_id,
                    "title": title,
                    "created_at": created_at,
                    "last_updated": updated_at,
                    "message_count": message_count,
                    "jsonl_path": jsonl_path,
                    "todos_path": todos_path if has_todos else None,
                    "statsig_path": statsig_file,
                    "has_todos": has_todos
                }
                
        except Exception as e:
            logger.error(f"Erro ao ler metadados da sessão {session_id}: {str(e)}")
            return None
    
    def _extract_title(self, first_message: Dict[str, Any]) -> str:
        """
        Extrai um título apropriado da primeira mensagem de uma conversa.
        
        Args:
            first_message (Dict): Primeira mensagem da conversa
            
        Returns:
            str: Título da conversa
        """
        # Tentar obter conteúdo da mensagem
        content = ""
        
        if "content" in first_message.get("message", {}):
            # Formato antigo
            content = first_message["message"]["content"]
        elif "message" in first_message and "content" in first_message["message"]:
            # Formato novo simples
            content = first_message["message"]["content"]
        elif "message" in first_message and isinstance(first_message["message"].get("content", []), list):
            # Formato novo com conteúdo em lista
            for item in first_message["message"]["content"]:
                if item.get("type") == "text":
                    content = item.get("text", "")
                    break
        
        # Processar conteúdo para título
        if isinstance(content, str):
            # Limitar a 50 caracteres
            title = content.strip().split("\n")[0][:50]
            # Se for muito curto, usar "Nova Conversa"
            if len(title) < 3:
                title = "Nova Conversa"
            return title
        
        return "Conversa Claude"
    
    def get_conversation_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Obtém todas as mensagens de uma conversa em formato padronizado.
        
        Args:
            session_id (str): ID da sessão
            
        Returns:
            List[Dict]: Lista de mensagens formatadas
        """
        session_info = self.get_session_metadata(session_id)
        if not session_info or not session_info.get("jsonl_path"):
            return []
        
        try:
            jsonl_path = session_info["jsonl_path"]
            messages = []
            
            with open(jsonl_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        msg = self._format_message(entry)
                        if msg:
                            messages.append(msg)
                    except json.JSONDecodeError:
                        continue
            
            return messages
        except Exception as e:
            logger.error(f"Erro ao ler mensagens da sessão {session_id}: {str(e)}")
            return []
    
    def _format_message(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Formata uma entrada JSONL em uma mensagem padronizada.
        
        Args:
            entry (Dict): Entrada do arquivo JSONL
            
        Returns:
            Dict: Mensagem formatada ou None se não for mensagem
        """
        # Ignorar entradas que não são mensagens principais
        if entry.get("isSidechain") or not entry.get("message"):
            return None
        
        message = entry.get("message", {})
        timestamp = entry.get("timestamp", "")
        
        # Determinar o papel (role)
        role = message.get("role", entry.get("type", ""))
        
        # Coletar o conteúdo da mensagem
        content = ""
        if isinstance(message.get("content"), str):
            content = message["content"]
        elif isinstance(message.get("content"), list):
            # Processar conteúdo em formato de lista (comum em respostas do Claude)
            for item in message["content"]:
                if item.get("type") == "text":
                    content += item.get("text", "")
        
        # Retornar apenas se for mensagem de usuário ou assistente
        if role in ["user", "assistant"]:
            return {
                "role": role,
                "content": content,
                "timestamp": timestamp
            }
        
        return None
    
    def get_todos(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Obtém a lista de tarefas de uma sessão.
        
        Args:
            session_id (str): ID da sessão
            
        Returns:
            List[Dict]: Lista de tarefas
        """
        todos_path = os.path.join(TODOS_DIR, f"{session_id}.json")
        
        if not os.path.exists(todos_path):
            return []
        
        try:
            with open(todos_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erro ao ler tarefas da sessão {session_id}: {str(e)}")
            return []
    
    def get_statsig_config(self, session_id: str) -> Dict[str, Any]:
        """
        Obtém as configurações Statsig para uma sessão.
        
        Args:
            session_id (str): ID da sessão
            
        Returns:
            Dict: Configurações Statsig
        """
        statsig_files = glob.glob(os.path.join(STATSIG_DIR, "statsig.cached.evaluations.*"))
        
        for statsig_file in statsig_files:
            try:
                with open(statsig_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if session_id in content:
                        data = json.loads(content)
                        # Extrair as configurações relevantes
                        if "data" in data:
                            try:
                                config_data = json.loads(data["data"])
                                return {
                                    "feature_gates": config_data.get("feature_gates", {}),
                                    "dynamic_configs": config_data.get("dynamic_configs", {})
                                }
                            except:
                                pass
            except Exception as e:
                logger.error(f"Erro ao ler configurações Statsig: {str(e)}")
        
        return {"feature_gates": {}, "dynamic_configs": {}}
    
    def sync_with_claudechat(self) -> None:
        """
        Sincroniza as sessões do Claude CLI com o ClaudeChat.
        Atualiza o arquivo chat_history.json com as sessões existentes.
        """
        try:
            # Verificar se o arquivo de histórico existe
            if os.path.exists(CHAT_HISTORY_PATH):
                with open(CHAT_HISTORY_PATH, 'r', encoding='utf-8') as f:
                    chat_history = json.load(f)
            else:
                chat_history = {"conversations": [], "user_info": {"user_name": "", "preferences": {}, "context": {}}}
            
            # Obter todas as sessões do Claude CLI
            sessions = self.get_all_sessions()
            
            # Para cada sessão, verificar se já existe no histórico
            existing_session_ids = {
                conv.get("session_id", ""): idx 
                for idx, conv in enumerate(chat_history["conversations"])
            }
            
            # Processar cada sessão
            for session in sessions:
                session_id = session["session_id"]
                
                # Formato para o histórico do claudechat
                conversation = {
                    "id": len(chat_history["conversations"]) + 1 if session_id not in existing_session_ids else chat_history["conversations"][existing_session_ids[session_id]]["id"],
                    "title": session["title"],
                    "timestamp": self._convert_timestamp(session["created_at"]),
                    "last_updated": self._convert_timestamp(session["last_updated"]),
                    "session_id": session_id,
                    "messages": []
                }
                
                # Obter mensagens formatadas
                messages = self.get_conversation_messages(session_id)
                if messages:
                    # Formatar para o formato esperado pelo claudechat
                    for msg in messages:
                        # Incluir apenas se tiver conteúdo
                        if msg["content"]:
                            conversation["messages"].append({
                                "role": msg["role"],
                                "content": msg["content"]
                            })
                
                # Atualizar ou adicionar a conversa
                if session_id in existing_session_ids:
                    chat_history["conversations"][existing_session_ids[session_id]] = conversation
                else:
                    chat_history["conversations"].append(conversation)
            
            # Ordenar por última atualização
            chat_history["conversations"] = sorted(
                chat_history["conversations"], 
                key=lambda x: x.get("last_updated", ""), 
                reverse=True
            )
            
            # Salvar o arquivo atualizado
            with open(CHAT_HISTORY_PATH, 'w', encoding='utf-8') as f:
                json.dump(chat_history, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Sincronização com Claude Chat concluída: {len(chat_history['conversations'])} conversas")
            
        except Exception as e:
            logger.error(f"Erro ao sincronizar com Claude Chat: {str(e)}")
    
    def _convert_timestamp(self, timestamp: str) -> str:
        """
        Converte timestamp ISO 8601 para formato legível.
        
        Args:
            timestamp (str): Timestamp em formato ISO
            
        Returns:
            str: Data formatada
        """
        try:
            if not timestamp:
                return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
            # Converter de ISO para datetime
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            # Formatar para string legível
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def create_new_session(self, title: str = "Nova Conversa") -> str:
        """
        Cria uma nova sessão de conversa.
        
        Args:
            title (str): Título da conversa
            
        Returns:
            str: ID da sessão criada
        """
        # Gerar ID de sessão único
        session_id = str(uuid.uuid4())
        
        # Criar arquivos necessários
        project_dir = os.path.join(PROJECTS_DIR, "-root--claude-claudechat")
        os.makedirs(project_dir, exist_ok=True)
        
        jsonl_path = os.path.join(project_dir, f"{session_id}.jsonl")
        todos_path = os.path.join(TODOS_DIR, f"{session_id}.json")
        
        # Criar arquivo JSONL vazio com mensagem inicial
        timestamp = datetime.now().isoformat() + "Z"
        initial_message = {
            "userType": "external",
            "cwd": CLAUDE_DIR,
            "sessionId": session_id,
            "type": "user",
            "message": {
                "role": "user",
                "content": title
            },
            "uuid": str(uuid.uuid4()),
            "timestamp": timestamp
        }
        
        with open(jsonl_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(initial_message) + "\n")
        
        # Criar arquivo de tarefas vazio
        with open(todos_path, 'w', encoding='utf-8') as f:
            f.write("[]")
        
        # Sincronizar com claudechat
        self.sync_with_claudechat()
        
        return session_id
    
    def update_chat_history_with_user_info(self, user_info: Dict[str, Any]) -> None:
        """
        Atualiza o arquivo chat_history.json com informações do usuário.
        
        Args:
            user_info (Dict): Informações do usuário
        """
        try:
            if os.path.exists(CHAT_HISTORY_PATH):
                with open(CHAT_HISTORY_PATH, 'r', encoding='utf-8') as f:
                    chat_history = json.load(f)
            else:
                chat_history = {"conversations": [], "user_info": {}}
            
            # Atualizar informações do usuário
            chat_history["user_info"] = user_info
            
            # Salvar o arquivo atualizado
            with open(CHAT_HISTORY_PATH, 'w', encoding='utf-8') as f:
                json.dump(chat_history, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Informações do usuário atualizadas")
            
        except Exception as e:
            logger.error(f"Erro ao atualizar informações do usuário: {str(e)}")


# Exemplo de uso
if __name__ == "__main__":
    integration = ClaudeIntegration()
    
    # Sincronizar conversas
    integration.sync_with_claudechat()
    
    # Listar sessões
    sessions = integration.get_all_sessions()
    print(f"Encontradas {len(sessions)} sessões")
    
    for idx, session in enumerate(sessions[:5]):  # Mostrar até 5 sessões
        print(f"\nSessão {idx+1}:")
        print(f"  ID: {session['session_id']}")
        print(f"  Título: {session['title']}")
        print(f"  Criada em: {session['created_at']}")
        print(f"  Última atualização: {session['last_updated']}")
        print(f"  Mensagens: {session['message_count']}")
        print(f"  Tem tarefas: {'Sim' if session.get('has_todos') else 'Não'}")
        
        # Mostrar algumas mensagens
        messages = integration.get_conversation_messages(session['session_id'])
        print(f"\n  Primeiras mensagens ({min(3, len(messages))}):")
        for msg in messages[:3]:
            print(f"    [{msg['role']}]: {msg['content'][:50]}...")
        
        # Mostrar tarefas
        todos = integration.get_todos(session['session_id'])
        if todos:
            print(f"\n  Tarefas ({len(todos)}):")
            for todo in todos[:3]:
                print(f"    [{todo.get('status', 'unknown')}] {todo.get('content', '')[:50]}")