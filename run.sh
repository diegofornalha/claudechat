#!/bin/bash

# Script para executar o Claude Chat

# Caminho para o diretório do aplicativo
APP_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Cores para saída no terminal
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Iniciando Claude Chat...${NC}"

# Verificar se o Claude CLI está instalado
if ! command -v claude &> /dev/null; then
    echo -e "${RED}❌ Claude CLI não encontrado. A aplicação não funcionará sem o Claude CLI.${NC}"
    echo -e "${YELLOW}Por favor, instale o Claude CLI seguindo as instruções em: https://docs.anthropic.com/claude/docs/claude-code${NC}"
    
    # Perguntar se o usuário quer continuar mesmo assim
    read -p "🤔 Deseja continuar mesmo assim? (s/n): " choice
    if [[ ! "$choice" =~ [Ss] ]]; then
        echo -e "${RED}Execução cancelada.${NC}"
        exit 1
    fi
fi

# Verificar se o ambiente virtual existe
if [ ! -d "$APP_DIR/venv" ]; then
    echo -e "${YELLOW}📦 Criando ambiente virtual e instalando dependências...${NC}"
    python3 -m venv "$APP_DIR/venv"
    source "$APP_DIR/venv/bin/activate"
    pip install -r "$APP_DIR/requirements.txt"
else
    # Ativar o ambiente virtual
    source "$APP_DIR/venv/bin/activate"
fi

# Mudar para o diretório do aplicativo
cd "$APP_DIR"

# Executar aplicação
echo -e "${BLUE}▶️ Abrindo chat no navegador...${NC}"
"$APP_DIR/venv/bin/streamlit" run app/main.py