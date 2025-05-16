import subprocess
import re
import time
import os
import logging
from config.settings import CLAUDE_PATH, CLAUDE_TIMEOUT, LOG_LEVEL

# Configurar logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def send_to_claude(message, conversation_id=None):
    """
    Envia uma mensagem para o Claude Code CLI e processa a resposta.
    
    Args:
        message (str): A mensagem para enviar ao Claude
        conversation_id (str, opcional): ID da conversa para continuar
        
    Returns:
        tuple: (resposta, conversation_id)
    """
    try:
        # Se já existe uma conversa, continuar
        if conversation_id:
            cmd = f'{CLAUDE_PATH} -c -p "{message}"'
        else:
            cmd = f'{CLAUDE_PATH} -p "{message}"'
        
        logger.debug(f"Executando comando: {cmd}")
        
        # Executar comando Claude CLI
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Coletar resposta
        output, error = process.communicate(timeout=CLAUDE_TIMEOUT)
        
        # Verificar se houve erro
        if error and not output:
            logger.error(f"Erro ao executar o Claude CLI: {error}")
            return f"Erro: {error}", None
        
        # Extrair ID da conversa se for nova
        if not conversation_id:
            # Tentar encontrar o ID da conversa no output
            match = re.search(r'Conversation:\s+(\d+)', output)
            if match:
                conversation_id = match.group(1)
                logger.info(f"Nova conversa iniciada com ID: {conversation_id}")
        
        # Limpar a saída para exibir apenas a resposta
        response = output
        # Remover cabeçalho antes da resposta real
        response = re.sub(r'^.*?Conversation:\s+\d+.*?\n\n', '', response, flags=re.DOTALL)
        # Remover qualquer outro texto de conversa
        response = re.sub(r'Conversation:\s+\d+.*?\n', '', response)
        
        return response.strip(), conversation_id
    
    except subprocess.TimeoutExpired:
        process.kill()
        logger.error(f"Timeout ao aguardar resposta do Claude (limite: {CLAUDE_TIMEOUT}s)")
        return "Erro: A resposta demorou muito tempo.", None
    except Exception as e:
        logger.exception("Erro inesperado ao comunicar com o Claude CLI")
        return f"Erro: {str(e)}", None