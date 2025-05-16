import streamlit as st
import sys
import os
import logging

# Adicionar diretório pai ao path para imports relativos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.claude_cli import send_to_claude
from config.settings import (
    APP_TITLE, APP_ICON, APP_DESCRIPTION, 
    DEFAULT_PLACEHOLDER, TYPING_MESSAGE,
    LAYOUT, INITIAL_SIDEBAR_STATE,
    APP_SECRET_KEY, DEBUG_MODE, LOG_LEVEL
)

# Configurar logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_css():
    """Carrega o CSS da aplicação"""
    css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                           'static', 'css', 'style.css')
    with open(css_path, 'r') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def main():
    """Função principal do aplicativo"""
    # Configuração da página
    st.set_page_config(
        page_title=APP_TITLE.replace('💬 ', ''),
        page_icon=APP_ICON,
        layout=LAYOUT,
        initial_sidebar_state=INITIAL_SIDEBAR_STATE
    )
    
    # Configurar cache e segurança
    if not DEBUG_MODE:
        # Adicionar segurança em produção
        st.session_state.setdefault("_app_secure", APP_SECRET_KEY)
    
    logger.debug("Iniciando aplicação")
    
    # Carregar CSS
    load_css()
    
    # Cabeçalho com título e descrição
    st.title(APP_TITLE)
    st.markdown(f"<p style='color: #718096; margin-bottom: 20px;'>{APP_DESCRIPTION}</p>", 
               unsafe_allow_html=True)
    
    # Inicializar histórico de mensagens
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    # Inicializar ID da conversa
    if 'conversation_id' not in st.session_state:
        st.session_state.conversation_id = None
    
    # Controles acima da área de chat
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("🔄 Nova Conversa", type="primary"):
            st.session_state.messages = []
            st.session_state.conversation_id = None
            st.rerun()

    with col2:
        if st.button("🗑️ Limpar Mensagens"):
            st.session_state.messages = []
            st.rerun()

    with col3:
        if st.session_state.conversation_id:
            st.info(f"📝 Conversa ativa: #{st.session_state.conversation_id}")
    
    # Exibir mensagens anteriores
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            role = message["role"]
            content = message["content"]
            
            if role == "user":
                st.markdown(f'<div class="user-message">{content}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="assistant-message">{content}</div>', unsafe_allow_html=True)
    
    # Inicializar variáveis de controle
    if 'input_key' not in st.session_state:
        st.session_state.input_key = 0
    
    # Input de mensagem com envio ao pressionar Enter
    user_input = st.text_input(DEFAULT_PLACEHOLDER, key=f"user_input_{st.session_state.input_key}")
    
    # Processar envio de mensagem
    if user_input:
        # Armazenar o input atual
        current_input = user_input
        
        # Adicionar mensagem do usuário ao histórico
        st.session_state.messages.append({"role": "user", "content": current_input})
        
        # Limpar o campo de input alterando sua chave
        st.session_state.input_key += 1
        
        # Enviar para o Claude
        with st.spinner(TYPING_MESSAGE):
            logger.info(f"Enviando mensagem para o Claude (conversa ID: {st.session_state.conversation_id})")
            response, conv_id = send_to_claude(current_input, st.session_state.conversation_id)
            st.session_state.conversation_id = conv_id
            logger.debug(f"Resposta recebida, usando conversa ID: {conv_id}")
        
        # Adicionar resposta do Claude ao histórico
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Recarregar a página para exibir as novas mensagens
        st.rerun()
    
    # Informações adicionais no rodapé
    st.markdown("---")
    st.markdown("""
    <div class="footer">
        <div>
            <strong>Dica:</strong> Pressione Enter para enviar a mensagem
        </div>
        <div>
            Desenvolvido com ❤️ usando Streamlit e Claude Code CLI
        </div>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()