import streamlit as st
import time
import sys
import os
import re

# Adicionar o diretório raiz ao PATH para importar corretamente os módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.claude_cli import send_to_claude

# Configurações da página
st.set_page_config(
    page_title="Chat",
    page_icon="🤖",
    layout="centered"
)

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
</style>
""", unsafe_allow_html=True)

# Título do aplicativo
st.title("Chat")
st.markdown("Qual é a sua pergunta hoje?")

# Inicializar histórico de conversa e informações do usuário na sessão
if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None

# Inicializar o dicionário de memória para armazenar informações do usuário
if "memory" not in st.session_state:
    st.session_state.memory = {
        "user_name": None,
        "preferences": {},
        "context": {}
    }

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
    for key, value in st.session_state.memory["context"].items():
        context += f"{key}: {value}. "
    
    return context.strip()

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
        st.success(f"Nome atualizado para {new_name}!")
    
    st.divider()
    
    st.subheader("Sobre")
    st.markdown("""
    As respostas são primeiro obtidas completamente e depois exibidas gradualmente na tela.
    """)
    
    # Botão para limpar o histórico
    if st.button("Nova Conversa"):
        st.session_state.messages = []
        st.session_state.conversation_id = None
        # Mantém a memória do usuário mesmo em novas conversas
        st.rerun()

# Input do usuário
prompt = st.chat_input("Digite sua mensagem...")

# Processar input do usuário
if prompt:
    # Verificar se há informações para extrair
    name = extract_user_info(prompt)
    if name:
        st.session_state.memory["user_name"] = name
    
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