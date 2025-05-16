"""
Configurações para a aplicação Claude Chat
"""
import os
from dotenv import load_dotenv
import json

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configurações da aplicação
APP_TITLE = "💬 Chat com Claude"
APP_ICON = "💬"
APP_DESCRIPTION = "Interface amigável para o Claude Code CLI"
APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", "default_secret_key")
DEBUG_MODE = json.loads(os.getenv("DEBUG_MODE", "false").lower())

# Mensagens
DEFAULT_PLACEHOLDER = "Digite sua mensagem e aperte Enter..."
TYPING_MESSAGE = "Claude está digitando..."

# Configurações do Claude CLI
CLAUDE_PATH = os.getenv("CLAUDE_PATH", "claude")
CLAUDE_TIMEOUT = int(os.getenv("CLAUDE_TIMEOUT", "90"))

# Configurações de log
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Layout
LAYOUT = "wide"
INITIAL_SIDEBAR_STATE = "collapsed"