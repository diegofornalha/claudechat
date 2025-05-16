# Claude Chat

Interface amigável para o Claude Code CLI.

## Estrutura de Arquivos

```
claudechat/
├── app/                    # Código principal da aplicação
│   ├── __init__.py
│   └── main.py             # Ponto de entrada da aplicação
├── config/                 # Configurações
│   └── settings.py         # Configurações da aplicação
├── static/                 # Recursos estáticos
│   └── css/
│       └── style.css       # Estilos da aplicação
├── utils/                  # Utilitários
│   ├── __init__.py
│   └── claude_cli.py       # Funções para interagir com o Claude CLI
├── __init__.py
├── README.md               # Este arquivo
├── requirements.txt        # Dependências
└── run.sh                  # Script para executar a aplicação
```

## Requisitos

- Python 3.6+
- Streamlit
- python-dotenv
- Claude Code CLI instalado e configurado

## Configuração

1. Copie o arquivo `.env.example` para `.env`:

```bash
cp .env.example .env
```

2. Edite o arquivo `.env` com suas configurações:

```
# Configurações do Claude CLI
CLAUDE_PATH=/path/to/claude/executable
CLAUDE_TIMEOUT=90

# Configurações da aplicação
APP_SECRET_KEY=your_secret_key_here
DEBUG_MODE=False

# Configurações de log
LOG_LEVEL=INFO
```

- `CLAUDE_PATH`: Caminho para o executável do Claude CLI
- `CLAUDE_TIMEOUT`: Tempo máximo em segundos para esperar uma resposta
- `APP_SECRET_KEY`: Chave secreta para segurança da aplicação
- `DEBUG_MODE`: Define se a aplicação está em modo de depuração
- `LOG_LEVEL`: Nível de logs (DEBUG, INFO, WARNING, ERROR, CRITICAL)

## Como Executar

A partir do diretório principal:

```bash
./run.sh
```

Ou a partir do diretório raiz:

```bash
/root/.claude/run_claude_chat.sh
```

## Funcionalidades

- Interface de chat amigável para o Claude Code CLI
- Suporte para conversas contínuas
- Nova conversa com um clique
- Exibição de ID da conversa ativa
- Envio de mensagens com Enter

## Troubleshooting

### Problema ao enviar segunda mensagem

Se você encontrar problemas ao enviar uma segunda mensagem:

1. Certifique-se de que o estado de submissão está sendo limpo corretamente
2. O campo de entrada deve ser limpo após cada envio
3. Verifique se o Claude CLI está funcionando corretamente com a flag `-c`

## Desenvolvimento

### Adicionar novos recursos

Para adicionar novos recursos:

1. Modifique os arquivos na pasta `app/`
2. Adicione novos utilitários em `utils/`
3. Configure estilos em `static/css/`
4. Atualize configurações em `config/settings.py`