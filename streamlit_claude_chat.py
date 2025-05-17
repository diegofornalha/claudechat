import streamlit as st
import time
import sys
import os
import re
import json
import datetime
import hashlib
import glob
from io import BytesIO
from pathlib import Path

# Adicionar o diretório raiz ao PATH para importar corretamente os módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.claude_cli import send_to_claude

#########################################################
# DEFINIÇÃO DE TODAS AS FUNÇÕES - INÍCIO
#########################################################

# Função para carregar o histórico do arquivo JSON
def load_history():
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"conversations": [], "user_info": {"user_name": None, "preferences": {}, "context": {}}}
    except Exception as e:
        st.error(f"Erro ao carregar histórico: {str(e)}")
        return {"conversations": [], "user_info": {"user_name": None, "preferences": {}, "context": {}}}

# Função para salvar o histórico no arquivo JSON
def save_history(history_data):
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar histórico: {str(e)}")
        return False

# Função para extrair informações do usuário das mensagens
def extract_user_info(message):
    # Verificar comando direto para trocar nome
    name_change_patterns = [
        r"(?:me\s+chame\s+de|meu\s+nome\s+agora\s+é|mudar\s+(?:meu\s+)?nome\s+para|trocar\s+(?:meu\s+)?nome\s+(?:para|por))\s+([A-Za-zÀ-ÿ]+)",
    ]
    
    for pattern in name_change_patterns:
        match = re.search(pattern, message.lower())
        if match:
            # Extrair o nome do texto original para preservar capitalização
            original_text = message[match.start(1):match.end(1)]
            return original_text
    
    # Verificar menções a nome (primeira vez)
    name_patterns = [
        r"meu nome\s+(?:é|eh)\s+([A-Za-zÀ-ÿ]+)",
        r"me chamo\s+([A-Za-zÀ-ÿ]+)",
        r"sou\s+(?:o|a)\s+([A-Za-zÀ-ÿ]+)",
        r"pode me chamar de\s+([A-Za-zÀ-ÿ]+)"
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, message.lower())
        if match:
            # Extrair o nome do texto original para preservar capitalização
            original_text = message[match.start(1):match.end(1)]
            return original_text
    
    return None

# Função para criar o contexto para o Claude com base na memória
def build_context():
    context = ""
    if st.session_state.memory["user_name"]:
        context += f"O nome do usuário é {st.session_state.memory['user_name']}. "
    
    # Adicionar outras informações da memória quando necessário
    for key, value in st.session_state.memory.get("context", {}).items():
        context += f"{key}: {value}. "
    
    # Adicionar preferências do usuário, se houver
    if st.session_state.memory.get("preferences"):
        context += "Preferências do usuário: "
        for pref, value in st.session_state.memory.get("preferences", {}).items():
            context += f"{pref}: {value}, "
        context = context.rstrip(", ") + ". "
    
    return context.strip()

# Função para carregar e gerenciar todos
def load_todos_for_session(session_id):
    """
    Carrega as tarefas (todos) associadas a um ID de sessão específico.
    """
    todos_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "todos")
    todos_path = os.path.join(todos_dir, f"{session_id}.json")
    
    if os.path.exists(todos_path):
        try:
            with open(todos_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Erro ao carregar todos: {str(e)}")
    
    return []

# Função para salvar todos para uma sessão
def save_todos_for_session(session_id, todos):
    """
    Salva as tarefas (todos) associadas a um ID de sessão específico.
    """
    todos_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "todos")
    os.makedirs(todos_dir, exist_ok=True)
    todos_path = os.path.join(todos_dir, f"{session_id}.json")
    
    try:
        with open(todos_path, 'w', encoding='utf-8') as f:
            json.dump(todos, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Erro ao salvar todos: {str(e)}")
        return False

# Função para salvar a conversa atual no histórico
def save_current_conversation():
    if not st.session_state.messages:
        return False
        
    # Verificar se é uma conversa existente ou nova
    if st.session_state.current_conversation_index >= 0 and st.session_state.current_conversation_index < len(st.session_state.history_data["conversations"]):
        # Atualizar conversa existente
        st.session_state.history_data["conversations"][st.session_state.current_conversation_index]["messages"] = st.session_state.messages.copy()
        st.session_state.history_data["conversations"][st.session_state.current_conversation_index]["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        # Criar nova conversa
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Extrai o primeiro e último mensaje para criar um título
        first_user_msg = next((msg["content"] for msg in st.session_state.messages if msg["role"] == "user"), "Nova conversa")
        title = first_user_msg[:30] + "..." if len(first_user_msg) > 30 else first_user_msg
        
        conversation = {
            "id": len(st.session_state.history_data["conversations"]) + 1,
            "title": title,
            "timestamp": timestamp,
            "last_updated": timestamp,
            "messages": st.session_state.messages.copy(),
            "session_id": st.session_state.session_id
        }
        
        st.session_state.history_data["conversations"].append(conversation)
        st.session_state.current_conversation_index = len(st.session_state.history_data["conversations"]) - 1
    
    # Atualizar informações do usuário no histórico
    st.session_state.history_data["user_info"] = st.session_state.memory
    
    # Salvar o histórico no arquivo
    return save_history(st.session_state.history_data)

# Função para excluir uma conversa específica
def delete_conversation(conv_index):
    # Obter o índice original na lista de conversas
    sorted_conversations = sorted(
        st.session_state.history_data["conversations"], 
        key=lambda x: x.get("last_updated", x.get("timestamp", "")), 
        reverse=True
    )
    
    # Obter a conversa a ser excluída
    conv_to_delete = sorted_conversations[conv_index]
    
    # Encontrar o índice original na lista não ordenada
    original_index = st.session_state.history_data["conversations"].index(conv_to_delete)
    
    # Remover a conversa do histórico
    st.session_state.history_data["conversations"].pop(original_index)
    
    # Se estamos excluindo a conversa atual, resetar para uma nova conversa
    if st.session_state.current_conversation_index == original_index:
        st.session_state.messages = []
        st.session_state.conversation_id = None
        st.session_state.current_conversation_index = -1
    
    # Atualizar índices de conversas que estavam depois da excluída
    elif st.session_state.current_conversation_index > original_index:
        st.session_state.current_conversation_index -= 1
    
    # Salvar as alterações
    save_history(st.session_state.history_data)
    return True

# Função para excluir uma conversa por arquivo JSONL
def delete_conversation_file(session_id, jsonl_path):
    """
    Exclui uma conversa baseada no arquivo JSONL.
    Também remove do histórico local se estiver presente.
    
    Args:
        session_id: ID da sessão
        jsonl_path: Caminho para o arquivo JSONL
    
    Returns:
        bool: True se a exclusão foi bem-sucedida
    """
    # Verificar se o arquivo existe
    if not os.path.exists(jsonl_path):
        return False
    
    try:
        # Verificar se existe um arquivo todos correspondente
        todos_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "todos")
        todos_path = os.path.join(todos_dir, f"{session_id}.json")
        
        # Excluir o arquivo JSONL
        os.remove(jsonl_path)
        
        # Excluir o arquivo todos se existir
        if os.path.exists(todos_path):
            os.remove(todos_path)
        
        # Verificar se a conversa está no histórico local
        for idx, conv in enumerate(st.session_state.history_data["conversations"]):
            if conv.get("session_id") == session_id:
                # Remover do histórico local
                st.session_state.history_data["conversations"].pop(idx)
                
                # Se for a conversa atual, resetar
                if st.session_state.current_conversation_index == idx:
                    st.session_state.messages = []
                    st.session_state.conversation_id = None
                    st.session_state.current_conversation_index = -1
                elif st.session_state.current_conversation_index > idx:
                    st.session_state.current_conversation_index -= 1
                
                # Salvar alterações no histórico
                save_history(st.session_state.history_data)
                break
        
        return True
    except Exception as e:
        print(f"Erro ao excluir conversa: {str(e)}")
        return False

# Função para obter conversas organizadas por projetos
def get_conversations_by_project():
    """
    Retorna um dicionário de conversas organizadas por projeto,
    baseando-se na estrutura de pastas dos arquivos JSONL
    """
    projects_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "projects")
    
    # Estrutura para armazenar as conversas por projeto
    projects = {
        "Claude Direto": {"path": os.path.join(projects_dir, "-root--claude"), "conversations": []},
        "Claude Chat": {"path": os.path.join(projects_dir, "-root--claude-claudechat"), "conversations": []},
        "Claude App": {"path": os.path.join(projects_dir, "-root--claude-claudechat-app"), "conversations": []}
    }
    
    # Para cada projeto, buscar as conversas nos arquivos JSONL
    for project_name, project_info in projects.items():
        if os.path.exists(project_info["path"]):
            jsonl_files = glob.glob(os.path.join(project_info["path"], "*.jsonl"))
            
            for jsonl_file in jsonl_files:
                session_id = os.path.basename(jsonl_file).replace(".jsonl", "")
                
                # Ler o arquivo para extrair título e timestamp
                try:
                    with open(jsonl_file, 'r', encoding='utf-8') as f:
                        first_line = f.readline()
                        if first_line:
                            try:
                                first_msg = json.loads(first_line)
                                # Extrair primeiro conteúdo como título
                                title = ""
                                if "message" in first_msg and "content" in first_msg["message"]:
                                    content = first_msg["message"]["content"]
                                    if isinstance(content, str):
                                        title = content.split("\n")[0][:30]
                                    elif isinstance(content, list) and len(content) > 0:
                                        for item in content:
                                            if item.get("type") == "text":
                                                title = item.get("text", "")[:30]
                                                break
                                
                                # Fallback se não conseguir extrair um título
                                if not title:
                                    title = f"Conversa {session_id[:8]}"
                                
                                # Extrair timestamp
                                timestamp = first_msg.get("timestamp", "")
                                if timestamp:
                                    try:
                                        # Converter de ISO para formato legível
                                        dt = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                                        timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
                                    except:
                                        timestamp = "Data desconhecida"
                                
                                # Adicionar à lista de conversas do projeto
                                project_info["conversations"].append({
                                    "session_id": session_id,
                                    "title": title,
                                    "timestamp": timestamp,
                                    "jsonl_path": jsonl_file
                                })
                            except json.JSONDecodeError:
                                pass
                except Exception as e:
                    print(f"Erro ao ler arquivo {jsonl_file}: {str(e)}")
            
            # Ordenar conversas do mais recente para o mais antigo
            project_info["conversations"] = sorted(
                project_info["conversations"],
                key=lambda x: x.get("timestamp", ""),
                reverse=True
            )
    
    return projects

# Função para listar arquivos Statsig
def list_statsig_files():
    """
    Lista todos os arquivos do diretório Statsig
    """
    statsig_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "statsig")
    if not os.path.exists(statsig_dir):
        return []
    
    files = []
    for file in os.listdir(statsig_dir):
        file_path = os.path.join(statsig_dir, file)
        if os.path.isfile(file_path):
            # Obter tamanho do arquivo
            size_bytes = os.path.getsize(file_path)
            if size_bytes < 1024:
                size_str = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes/1024:.1f} KB"
            else:
                size_str = f"{size_bytes/(1024*1024):.1f} MB"
            
            # Obter data de modificação
            mod_time = os.path.getmtime(file_path)
            mod_time_str = datetime.datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M")
            
            files.append({
                "name": file,
                "path": file_path,
                "size": size_str,
                "modified": mod_time_str
            })
    
    # Ordenar por data de modificação (mais recente primeiro)
    return sorted(files, key=lambda x: x["modified"], reverse=True)

# Função para excluir arquivo Statsig
def delete_statsig_file(file_path):
    """
    Exclui um arquivo Statsig específico
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception as e:
        print(f"Erro ao excluir arquivo Statsig: {str(e)}")
        return False

# Função para limpar todos os arquivos Statsig
def clear_all_statsig_files():
    """
    Exclui todos os arquivos do diretório Statsig
    """
    statsig_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "statsig")
    if not os.path.exists(statsig_dir):
        return True
    
    success = True
    for file in os.listdir(statsig_dir):
        file_path = os.path.join(statsig_dir, file)
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Erro ao excluir arquivo {file}: {str(e)}")
                success = False
    
    return success

#########################################################
# DEFINIÇÃO DE TODAS AS FUNÇÕES - FIM
#########################################################

# Configurações da página
st.set_page_config(
    page_title="Chat",
    page_icon="🤖",
    layout="centered"
)

# Caminho para o arquivo de histórico
HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "chat_history.json")

# Garantir que o diretório de dados exista
os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)

# Estilo personalizado
st.markdown("""
<style>
.chat-container {
    border-radius: 10px;
    margin-bottom: 10px;
    padding: 10px;
}
.user-message {
    background-color: #e1f5fe;
    border-radius: 10px;
    padding: 10px;
    margin-bottom: 10px;
}
.assistant-message {
    background-color: #f5f5f5;
    border-radius: 10px;
    padding: 10px;
    margin-bottom: 10px;
}
.stTextInput>div>div>input {
    background-color: white;
}
.history-controls {
    padding: 10px;
    background-color: #f9f9f9;
    border-radius: 5px;
    margin-top: 20px;
}
.conversation-row {
    display: flex;
    align-items: center;
    margin-bottom: 8px;
}
.conversation-item {
    flex-grow: 1;
    cursor: pointer;
    padding: 5px;
    border-radius: 4px;
}
.conversation-item:hover {
    background-color: #f0f0f0;
}
.delete-btn {
    color: #ff4b4b;
    cursor: pointer;
    margin-left: 5px;
}
.delete-btn:hover {
    color: #ff0000;
}
</style>
""", unsafe_allow_html=True)

# Gerar um ID único para a sessão se não existir
if "session_id" not in st.session_state:
    st.session_state.session_id = hashlib.md5(str(datetime.datetime.now()).encode()).hexdigest()

# Carregar histórico existente
if "history_data" not in st.session_state:
    st.session_state.history_data = load_history()

# Inicializar o dicionário de memória com informações do histórico
if "memory" not in st.session_state:
    st.session_state.memory = st.session_state.history_data.get("user_info", {
        "user_name": None,
        "preferences": {},
        "context": {}
    })

# Inicializar histórico de conversa e informações do usuário na sessão
if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None

# Inicializar o indicador de conversa atual
if "current_conversation_index" not in st.session_state:
    st.session_state.current_conversation_index = -1  # -1 significa conversa nova

# Título do aplicativo
st.title("Chat")
st.markdown("Qual é a sua pergunta hoje?")

# Adicionar seção de todos se tiver uma conversa atual
if st.session_state.conversation_id:
    # Carregar todos para a sessão atual
    todos = load_todos_for_session(st.session_state.conversation_id)
    
    if todos:
        with st.expander("Tarefas da Conversa"):
            st.markdown("### Lista de Tarefas")
            
            # Criar colunas para conteúdo, status e ações
            for i, todo in enumerate(todos):
                col1, col2, col3, col4 = st.columns([0.6, 0.15, 0.15, 0.1])
                
                with col1:
                    content = st.text_input("", value=todo["content"], key=f"todo_content_{i}")
                    todos[i]["content"] = content
                
                with col2:
                    status_options = ["pending", "in_progress", "completed"]
                    status_index = status_options.index(todo["status"]) if todo["status"] in status_options else 0
                    status = st.selectbox("", status_options, index=status_index, format_func=lambda x: x.replace("_", " ").title(), key=f"todo_status_{i}")
                    todos[i]["status"] = status
                
                with col3:
                    priority_options = ["low", "medium", "high"]
                    priority_index = priority_options.index(todo["priority"]) if todo["priority"] in priority_options else 1
                    priority = st.selectbox("", priority_options, index=priority_index, format_func=lambda x: x.title(), key=f"todo_priority_{i}")
                    todos[i]["priority"] = priority
                
                with col4:
                    if st.button("🗑️", key=f"todo_delete_{i}"):
                        todos.pop(i)
                        save_todos_for_session(st.session_state.conversation_id, todos)
                        st.rerun()
            
            # Adicionar nova tarefa
            st.markdown("### Adicionar Nova Tarefa")
            with st.form("add_todo", clear_on_submit=True):
                todo_content = st.text_input("Descrição da tarefa")
                cols = st.columns(2)
                with cols[0]:
                    todo_status = st.selectbox("Status", ["pending", "in_progress", "completed"], format_func=lambda x: x.replace("_", " ").title())
                with cols[1]:
                    todo_priority = st.selectbox("Prioridade", ["low", "medium", "high"], index=1, format_func=lambda x: x.title())
                
                if st.form_submit_button("Adicionar"):
                    if todo_content:
                        new_todo = {
                            "content": todo_content,
                            "status": todo_status,
                            "priority": todo_priority,
                            "id": str(len(todos) + 1)
                        }
                        todos.append(new_todo)
                        save_todos_for_session(st.session_state.conversation_id, todos)
                        st.rerun()
            
            # Salvar alterações
            if st.button("Salvar Alterações"):
                save_todos_for_session(st.session_state.conversation_id, todos)
                st.success("Tarefas atualizadas com sucesso!")
            
            # Botão para limpar chat mantendo tarefas
            if st.button("Limpar Chat (Manter Tarefas)"):
                # Salvar histórico atual primeiro para garantir que tudo está salvo
                save_current_conversation()
                
                # Limpar apenas as mensagens, mantendo o ID da conversa
                st.session_state.messages = []
                
                # Manter o mesmo ID de conversa e índice
                # Isso garante que as tarefas continuem associadas
                
                # Exibir confirmação
                st.success("Chat limpo, tarefas mantidas!")
                st.rerun()

# Exibir mensagens anteriores
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Barra lateral com controles e informações
with st.sidebar:
    st.subheader("Perfil do Usuário")
    
    # Campo para editar o nome diretamente
    current_name = st.session_state.memory["user_name"] or ""
    new_name = st.text_input("Seu nome:", value=current_name)
    if new_name and new_name != current_name:
        st.session_state.memory["user_name"] = new_name
        # Atualizar o nome no histórico e salvar
        st.session_state.history_data["user_info"]["user_name"] = new_name
        save_history(st.session_state.history_data)
        st.success(f"Nome atualizado para {new_name}!")
    
    st.divider()
    
    # Histórico de conversas
    st.subheader("Histórico por Projeto")
    
    # Obter conversas organizadas por projeto
    projects = get_conversations_by_project()
    
    # Mostrar cada projeto em um expander
    for project_name, project_info in projects.items():
        if project_info["conversations"]:
            with st.expander(f"{project_name} ({len(project_info['conversations'])} conversas)"):
                # Renderizar cada conversa com um botão de lixeira
                for i, conv in enumerate(project_info["conversations"]):
                    col1, col2 = st.columns([0.9, 0.1])
                    with col1:
                        # Usar session_id como chave única para evitar conflitos
                        if st.button(f"{conv['timestamp']} - {conv['title']}", 
                                    key=f"proj_{project_name}_{i}"):
                            # Carregar esta conversa do arquivo JSONL
                            messages = []
                            try:
                                with open(conv["jsonl_path"], 'r', encoding='utf-8') as f:
                                    for line in f:
                                        try:
                                            entry = json.loads(line)
                                            
                                            # Extrair role e content
                                            role = "user"
                                            content = ""
                                            
                                            if "type" in entry and entry["type"] in ["user", "assistant"]:
                                                role = entry["type"]
                                            elif "message" in entry and "role" in entry["message"]:
                                                role = entry["message"]["role"]
                                            
                                            if "message" in entry and "content" in entry["message"]:
                                                content_data = entry["message"]["content"]
                                                if isinstance(content_data, str):
                                                    content = content_data
                                                elif isinstance(content_data, list):
                                                    # Processar conteúdo em formato de lista
                                                    for item in content_data:
                                                        if item.get("type") == "text":
                                                            content += item.get("text", "")
                                            
                                            if role in ["user", "assistant"] and content:
                                                messages.append({
                                                    "role": role,
                                                    "content": content
                                                })
                                        except:
                                            # Ignorar linhas com erro
                                            pass
                                
                                # Atualizar mensagens e outros estados
                                st.session_state.messages = messages
                                st.session_state.conversation_id = conv["session_id"]
                                
                                # Atualizar conversa atual no histórico local
                                found = False
                                for idx, existing_conv in enumerate(st.session_state.history_data["conversations"]):
                                    if existing_conv.get("session_id") == conv["session_id"]:
                                        st.session_state.current_conversation_index = idx
                                        found = True
                                        break
                                
                                if not found:
                                    # Criar nova entrada no histórico local
                                    new_conv = {
                                        "id": len(st.session_state.history_data["conversations"]) + 1,
                                        "title": conv["title"],
                                        "timestamp": conv["timestamp"],
                                        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "messages": messages,
                                        "session_id": conv["session_id"]
                                    }
                                    st.session_state.history_data["conversations"].append(new_conv)
                                    st.session_state.current_conversation_index = len(st.session_state.history_data["conversations"]) - 1
                                
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao carregar conversa: {str(e)}")
                    with col2:
                        if st.button("🗑️", key=f"del_{project_name}_{i}"):
                            if delete_conversation_file(conv["session_id"], conv["jsonl_path"]):
                                st.success(f"Conversa excluída com sucesso!")
                                st.rerun()
                            else:
                                st.error("Erro ao excluir conversa")
    
    # Controles para o histórico
    with st.expander("Gerenciar histórico"):
        col1, col2 = st.columns(2)
        
        with col2:
            if st.button("Limpar histórico"):
                if st.session_state.history_data["conversations"]:
                    # Manter as preferências do usuário
                    user_info = st.session_state.history_data["user_info"]
                    # Resetar o histórico
                    st.session_state.history_data = {"conversations": [], "user_info": user_info}
                    save_history(st.session_state.history_data)
                    st.session_state.current_conversation_index = -1
                    st.success("Histórico temporário limpo!")
                    st.rerun()
        
        # Exportar histórico
        if st.session_state.history_data["conversations"]:
            st.download_button(
                label="Exportar histórico (JSON)",
                data=json.dumps(st.session_state.history_data, ensure_ascii=False, indent=2),
                file_name=f"chat_historico_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    st.divider()
    
    # Gerenciar arquivos Statsig
    st.subheader("Gerenciar Statsig")
    
    statsig_files = list_statsig_files()
    if not statsig_files:
        st.info("Nenhum arquivo Statsig encontrado")
    else:
        st.text(f"Total de arquivos: {len(statsig_files)}")
        
        # Botão para limpar todos os arquivos
        if st.button("Limpar todos os arquivos Statsig"):
            if clear_all_statsig_files():
                st.success("Todos os arquivos Statsig foram excluídos!")
                st.rerun()
            else:
                st.error("Erro ao excluir alguns arquivos Statsig")
        
        # Listar arquivos com opção de exclusão individual
        st.markdown("### Arquivos Statsig")
        for file in statsig_files:
            col1, col2, col3 = st.columns([0.5, 0.35, 0.15])
            with col1:
                st.text(file["name"])
            with col2:
                st.text(f"{file['size']} - {file['modified']}")
            with col3:
                if st.button("🗑️", key=f"del_statsig_{file['name']}"):
                    if delete_statsig_file(file["path"]):
                        st.success(f"Arquivo {file['name']} excluído!")
                        st.rerun()
                    else:
                        st.error(f"Erro ao excluir {file['name']}")
    
    st.divider()
    
    st.subheader("Sobre")
    st.markdown("""
    As respostas são primeiro obtidas completamente e depois exibidas gradualmente na tela.
    """)
    
    # Botão para limpar o histórico
    if st.button("Nova Conversa"):
        # Se houver uma conversa atual, salvá-la automaticamente
        if st.session_state.messages:
            save_current_conversation()
        
        # Iniciar nova conversa
        st.session_state.messages = []
        st.session_state.conversation_id = None
        st.session_state.current_conversation_index = -1  # Indicar que é uma nova conversa
        
        # Manter a memória do usuário
        st.rerun()
    
    # Botão para limpar apenas o chat (na barra lateral)
    if st.session_state.conversation_id and st.button("Limpar Chat (Manter Tarefas)", key="sidebar_clear"):
        # Salvar histórico atual primeiro
        save_current_conversation()
        
        # Limpar apenas as mensagens, mantendo o ID da conversa e tarefas
        st.session_state.messages = []
        
        st.success("Chat limpo! As tarefas foram mantidas.")
        st.rerun()

# Input do usuário
prompt = st.chat_input("Digite sua mensagem...")

# Processar input do usuário
if prompt:
    # Verificar se há informações para extrair
    name = extract_user_info(prompt)
    if name:
        st.session_state.memory["user_name"] = name
        # Atualizar automaticamente o nome no histórico
        st.session_state.history_data["user_info"]["user_name"] = name
    
    # Adicionar mensagem do usuário ao histórico
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Exibir mensagem do usuário
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Exibir mensagem do assistente com streaming
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        # Construir o prompt com o contexto da memória
        context = build_context()
        enhanced_prompt = prompt
        if context:
            enhanced_prompt = f"[CONTEXTO: {context}]\n\n{prompt}"
        
        # Primeiro, obter a resposta completa do Claude
        with st.spinner("Claude está gerando a resposta..."):
            full_response, conv_id = send_to_claude(
                enhanced_prompt, 
                conversation_id=st.session_state.conversation_id
            )
            
            # Atualizar o ID da conversa se for novo
            if conv_id and not st.session_state.conversation_id:
                st.session_state.conversation_id = conv_id
        
        # Agora que temos a resposta completa, exibi-la gradualmente
        displayed_response = ""
        for i in range(len(full_response) + 1):
            # Mostra partes da resposta gradualmente
            displayed_response = full_response[:i]
            message_placeholder.markdown(displayed_response + "▌" if i < len(full_response) else displayed_response)
            
            # Ajuste a velocidade do streaming visual aqui (menor = mais rápido)
            time.sleep(0.005)  # 5 milissegundos por caractere
        
        # Adicionar a resposta completa ao histórico
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        
        # Salvar automaticamente a conversa após cada interação
        save_current_conversation()
    
    # Verificar se precisamos extrair preferências do contexto
    if "gost" in prompt.lower() or "prefer" in prompt.lower():
        preference_patterns = [
            r"(?:gosto|adoro|amo|prefiro)\s+(?:de\s+)?([A-Za-zÀ-ÿ\s]+)",
            r"minha\s+(?:comida|bebida|cor|música|musica)\s+(?:preferida|favorita)\s+(?:é|eh)\s+([A-Za-zÀ-ÿ\s]+)"
        ]
        
        for pattern in preference_patterns:
            match = re.search(pattern, prompt.lower())
            if match:
                # Preferência encontrada
                preference = match.group(1).strip()
                if 'morang' in preference:
                    st.session_state.memory.setdefault("preferences", {})["frutas"] = "morangos"
                    # Atualizar e salvar
                    save_current_conversation() 