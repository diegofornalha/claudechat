import streamlit as st
import time
import sys
import os
import re
import json
import datetime
import hashlib
from io import BytesIO

# Adicionar o diretório raiz ao PATH para importar corretamente os módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.claude_cli import send_to_claude

# Configurações da página
st.set_page_config(
    page_title="Chat",
    page_icon="🤖",
    layout="centered"
)

# Caminho para o arquivo de histórico
HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "chat_history.json")

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
</style>
""", unsafe_allow_html=True)

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
    st.subheader("Histórico Temporário")
    
    # Mostrar conversas salvas
    if st.session_state.history_data["conversations"]:
        # Ordenar conversas do mais recente para o mais antigo
        sorted_conversations = sorted(
            st.session_state.history_data["conversations"], 
            key=lambda x: x.get("last_updated", x.get("timestamp", "")), 
            reverse=True
        )
        
        conversation_options = [f"{i}. {conv['timestamp']} - {conv['title']}" 
                             for i, conv in enumerate(sorted_conversations)]
        
        selected_conversation = st.selectbox(
            "Conversas anteriores:",
            options=range(len(sorted_conversations)),
            format_func=lambda i: conversation_options[i]
        )
        
        if st.button("Carregar conversa"):
            selected_conv = sorted_conversations[selected_conversation]
            st.session_state.messages = selected_conv["messages"].copy()
            
            # Atualizar o índice da conversa atual
            original_index = st.session_state.history_data["conversations"].index(selected_conv)
            st.session_state.current_conversation_index = original_index
            
            st.rerun()
    
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