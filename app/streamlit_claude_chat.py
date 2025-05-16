import streamlit as st
import time
import sys
import os

# Adicionar o diretório raiz ao PATH para importar corretamente os módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.claude_cli import send_to_claude

# Configurações da página
st.set_page_config(
    page_title="Chat com Claude",
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
st.title("Chat com Claude")
st.markdown("Conversa com streaming usando Claude AI")

# Inicializar histórico de conversa na sessão
if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None

# Exibir mensagens anteriores
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input do usuário
prompt = st.chat_input("Digite sua mensagem...")

# Processar input do usuário
if prompt:
    # Adicionar mensagem do usuário ao histórico
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Exibir mensagem do usuário
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Exibir mensagem do assistente com streaming
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        # Primeiro, obter a resposta completa do Claude
        with st.spinner("Claude está gerando a resposta..."):
            full_response, conv_id = send_to_claude(
                prompt, 
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

# Adicionar instruções de uso
with st.sidebar:
    st.subheader("Sobre")
    st.markdown("""
    Este é um exemplo de chat com streaming usando Claude AI.
    
    As respostas são primeiro obtidas completamente e depois exibidas gradualmente na tela.
    
    A conversa é mantida em uma única sessão, preservando o contexto entre as mensagens.
    """)
    
    # Botão para limpar o histórico
    if st.button("Nova Conversa"):
        st.session_state.messages = []
        st.session_state.conversation_id = None
        st.rerun() 