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
        # Escapar aspas duplas no input para evitar problemas no shell
        message = message.replace('"', '\\"')
        
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
        
        # Verificar se houve erro ou saída vazia
        if not output:
            if error:
                logger.error(f"Erro ao executar o Claude CLI: {error}")
                return f"Erro: {error}", None
            else:
                logger.error("O Claude CLI não retornou nenhuma resposta")
                return "Erro: Não foi possível obter resposta do Claude CLI", None
        
        # Extrair ID da conversa se for nova
        if not conversation_id:
            # Tentar encontrar o ID da conversa no output
            match = re.search(r'Conversation:\s+(\d+)', output)
            if match:
                conversation_id = match.group(1)
                logger.info(f"Nova conversa iniciada com ID: {conversation_id}")
        
        # Limpar a saída para exibir apenas a resposta
        response = output
        
        # Tratamento mais robusto: se tiver o padrão "Conversation: xxxx" seguido por dois \n
        header_match = re.search(r'^(.*?Conversation:\s+\d+.*?)(\n\n)(.*)', response, flags=re.DOTALL)
        if header_match:
            # Ignorar o cabeçalho e pegar apenas a parte da resposta
            response = header_match.group(3)
        else:
            # Tentar outra abordagem: remover linhas que contenham "Conversation: xxxx"
            response = re.sub(r'.*Conversation:\s+\d+.*\n', '', response)
        
        return response.strip(), conversation_id
    
    except subprocess.TimeoutExpired:
        process.kill()
        logger.error(f"Timeout ao aguardar resposta do Claude (limite: {CLAUDE_TIMEOUT}s)")
        return "Erro: A resposta demorou muito tempo.", None
    except Exception as e:
        logger.exception("Erro inesperado ao comunicar com o Claude CLI")
        return f"Erro: {str(e)}", None

def stream_claude_response(message, conversation_id=None):
    """
    Envia uma mensagem para o Claude Code CLI e retorna a resposta em streaming.
    Permite integração com Streamlit para exibição gradual da resposta.
    
    Args:
        message (str): A mensagem para enviar ao Claude
        conversation_id (str, opcional): ID da conversa para continuar
        
    Yields:
        tuple: (fragmento_de_resposta, flag_de_finalização, conversation_id)
    """
    try:
        # Escapar aspas duplas no input para evitar problemas no shell
        message = message.replace('"', '\\"')
        
        # Se já existe uma conversa, continuar
        if conversation_id:
            cmd = f'{CLAUDE_PATH} -c -p "{message}"'
        else:
            cmd = f'{CLAUDE_PATH} -p "{message}"'
        
        logger.debug(f"Executando comando streaming: {cmd}")
        
        # Executar comando Claude CLI
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Variáveis para controle de streaming
        detected_conversation_id = None
        response_started = False
        complete_output = ""
        buffer = ""
        
        # Ler saída linha por linha para um streaming suave
        for line in iter(process.stdout.readline, ''):
            complete_output += line
            
            # Verificar se encontramos o ID da conversa
            if not detected_conversation_id and not conversation_id:
                match = re.search(r'Conversation:\s+(\d+)', line)
                if match:
                    detected_conversation_id = match.group(1)
                    logger.info(f"Nova conversa streaming iniciada com ID: {detected_conversation_id}")
            
            # Ignorar linha se contiver informações de cabeçalho
            if re.search(r'Conversation:\s+\d+', line):
                continue
                
            # Checar se é uma linha em branco que indica o início da resposta
            if not response_started and line.strip() == "":
                response_started = True
                continue
                
            # Se já começamos a receber a resposta, enviamos cada linha
            if response_started:
                buffer += line
                # Enviamos o buffer a cada 10-50 caracteres para um streaming suave
                if len(buffer) >= 20:
                    yield buffer, False, detected_conversation_id or conversation_id
                    buffer = ""
        
        # Enviar qualquer texto restante no buffer
        if buffer:
            yield buffer, False, detected_conversation_id or conversation_id
            
        # Sinalizar o fim do streaming
        yield "", True, detected_conversation_id or conversation_id
        
        # Verificar se houve erro
        error = process.stderr.read()
        if error:
            logger.error(f"Erro durante o streaming do Claude CLI: {error}")
            yield f"Erro: {error}", True, detected_conversation_id or conversation_id
            
    except subprocess.TimeoutExpired:
        process.kill()
        logger.error(f"Timeout ao aguardar resposta do Claude (limite: {CLAUDE_TIMEOUT}s)")
        yield "Erro: A resposta demorou muito tempo.", True, None
    except Exception as e:
        logger.exception("Erro inesperado durante o streaming com o Claude CLI")
        yield f"Erro: {str(e)}", True, None