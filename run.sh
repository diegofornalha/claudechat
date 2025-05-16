#!/bin/bash

# Script para executar o Claude Chat

# Caminho para o diretório do aplicativo
APP_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Cores para saída no terminal
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Iniciando Claude Chat...${NC}"

# Verificar se streamlit está instalado
if ! command -v streamlit &> /dev/null; then
    echo -e "${YELLOW}📦 Instalando Streamlit...${NC}"
    pip install streamlit
fi

# Mudar para o diretório do aplicativo
cd "$APP_DIR"

# Executar aplicação
echo -e "${BLUE}▶️ Abrindo chat no navegador...${NC}"
streamlit run app/main.py