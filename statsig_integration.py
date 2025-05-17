"""
Exemplo de integração do Statsig com claudechat

Este arquivo contém exemplos de como integrar o serviço Statsig (feature flags/configurações)
com a aplicação claudechat.

Para uso, você precisará instalar a biblioteca Statsig e adicionar o código
relevante aos arquivos de configuração e inicialização da aplicação.

Instalação: pip install statsig
"""

import os
from statsig import statsig
from statsig.statsig_options import StatsigOptions
from statsig.statsig_user import StatsigUser
from statsig.statsig_environment_tier import StatsigEnvironmentTier

# Classe de integração para encapsular a lógica do Statsig
class StatsigService:
    _instance = None
    
    def __new__(cls):
        # Implementação de singleton para garantir uma única instância
        if cls._instance is None:
            cls._instance = super(StatsigService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def initialize(self, server_secret_key=None, environment="development"):
        """
        Inicializa o serviço Statsig
        
        Args:
            server_secret_key (str): A chave secreta do servidor Statsig
            environment (str): O ambiente (development, staging, production)
        """
        if self._initialized:
            return
            
        # Obter chave do ambiente se não fornecida
        if not server_secret_key:
            server_secret_key = os.getenv("STATSIG_SERVER_KEY")
            
        if not server_secret_key:
            print("AVISO: Chave do Statsig não encontrada, usando valores padrão")
            return
            
        # Mapear ambiente para o tipo correto
        env_map = {
            "development": StatsigEnvironmentTier.development,
            "staging": StatsigEnvironmentTier.staging,
            "production": StatsigEnvironmentTier.production
        }
        
        tier = env_map.get(environment, StatsigEnvironmentTier.development)
        
        # Inicializar SDK com opções
        options = StatsigOptions(
            tier=tier,
            local_mode=False,  # Mudar para True em testes
            api_override=None
        )
        
        try:
            statsig.initialize(server_secret_key, options)
            self._initialized = True
            print(f"Statsig inicializado com sucesso no ambiente: {environment}")
        except Exception as e:
            print(f"Erro ao inicializar Statsig: {e}")
    
    def is_initialized(self):
        """Verifica se o Statsig foi inicializado corretamente"""
        return self._initialized
    
    def get_user(self, user_info=None):
        """
        Cria um objeto de usuário Statsig
        
        Args:
            user_info (dict): Informações do usuário
            
        Returns:
            StatsigUser: Objeto de usuário do Statsig
        """
        if not user_info:
            # Usar ID de sessão ou criar um anônimo
            return StatsigUser(os.getenv("SESSION_ID", "anonymous"))
            
        # Criar usuário com propriedades adicionais
        return StatsigUser(
            user_id=user_info.get("id", "anonymous"),
            email=user_info.get("email"),
            ip=user_info.get("ip"),
            user_agent=user_info.get("user_agent"),
            country=user_info.get("country"),
            locale=user_info.get("locale"),
            app_version=user_info.get("app_version"),
            custom_fields=user_info.get("custom_fields", {})
        )
    
    def check_feature(self, feature_name, user_info=None, default=False):
        """
        Verifica se um recurso está habilitado para o usuário
        
        Args:
            feature_name (str): Nome do recurso (feature flag)
            user_info (dict): Informações do usuário
            default (bool): Valor padrão se Statsig não estiver inicializado
            
        Returns:
            bool: True se o recurso estiver habilitado, False caso contrário
        """
        if not self._initialized:
            return default
            
        user = self.get_user(user_info)
        return statsig.check_gate(user, feature_name)
    
    def get_config(self, config_name, user_info=None, default=None):
        """
        Obtém uma configuração dinâmica do Statsig
        
        Args:
            config_name (str): Nome da configuração
            user_info (dict): Informações do usuário
            default (dict): Valor padrão se Statsig não estiver inicializado
            
        Returns:
            dict: Os valores da configuração dinâmica
        """
        if not self._initialized:
            return default or {}
            
        user = self.get_user(user_info)
        config = statsig.get_config(user, config_name)
        return config.value
    
    def log_event(self, event_name, user_info=None, value=None, metadata=None):
        """
        Registra um evento no Statsig
        
        Args:
            event_name (str): Nome do evento
            user_info (dict): Informações do usuário
            value (numeric): Valor associado ao evento (opcional)
            metadata (dict): Metadados adicionais do evento (opcional)
        """
        if not self._initialized:
            return
            
        from statsig.statsig_event import StatsigEvent
        
        user = self.get_user(user_info)
        event = StatsigEvent(user, event_name, value=value, metadata=metadata)
        statsig.log_event(event)
    
    def shutdown(self):
        """Finaliza o Statsig, enviando eventos pendentes"""
        if self._initialized:
            try:
                statsig.shutdown()
                self._initialized = False
            except Exception as e:
                print(f"Erro ao finalizar Statsig: {e}")


# Exemplo de uso com o claudechat

"""
Exemplos de integração com o claudechat:

1. Adicionar ao config/settings.py:
"""
EXAMPLE_SETTINGS_PY = """
# Configurações do Statsig
STATSIG_SERVER_KEY = os.getenv("STATSIG_SERVER_KEY")
STATSIG_ENVIRONMENT = os.getenv("STATSIG_ENVIRONMENT", "development")
"""

"""
2. Inicializar no app/__init__.py ou no início do main.py:
"""
EXAMPLE_INIT_PY = """
from statsig_integration import StatsigService

# Inicializar serviço de feature flags
statsig_service = StatsigService()
statsig_service.initialize(
    server_secret_key=settings.STATSIG_SERVER_KEY,
    environment=settings.STATSIG_ENVIRONMENT
)
"""

"""
3. Exemplo de uso em main.py:
"""
EXAMPLE_MAIN_PY = """
from statsig_integration import StatsigService

# Obter instância do serviço
statsig = StatsigService()

# No início da função main():
def main():
    # ... código existente ...
    
    # Verificar feature flags para personalizar comportamento
    user_info = {
        "id": st.session_state.get("user_id", "anonymous"),
        "custom_fields": {
            "conversation_id": st.session_state.get("conversation_id"),
            "is_returning_user": "messages" in st.session_state and len(st.session_state.messages) > 0
        }
    }
    
    # Obter configurações de UI
    ui_config = statsig.get_config("app_ui_config", user_info, default={
        "layout": "wide",
        "initial_sidebar_state": "collapsed",
        "show_footer": True,
        "theme_color": "#4f46e5"
    })
    
    # Aplicar configurações
    st.set_page_config(
        page_title=APP_TITLE.replace('💬 ', ''),
        page_icon=APP_ICON,
        layout=ui_config.get("layout", LAYOUT),
        initial_sidebar_state=ui_config.get("initial_sidebar_state", INITIAL_SIDEBAR_STATE)
    )
    
    # ... mais código ...
    
    # Verificar se novos recursos estão habilitados
    if statsig.check_feature("enable_export_chat", user_info):
        with col3:
            if st.button("📥 Exportar Conversa"):
                # Código para exportar conversa
                pass
    
    # ... mais código ...
    
    # Ao enviar mensagem, registrar evento
    if user_input:
        # ... código existente ...
        
        # Registrar evento de mensagem enviada
        statsig.log_event(
            "message_sent", 
            user_info, 
            metadata={"message_length": len(current_input)}
        )
"""

"""
4. Adicionar ao arquivo run.sh para finalizar corretamente:
"""
EXAMPLE_RUN_SH = """
#!/bin/bash

# Iniciar a aplicação
python -m app.main "$@"

# Código de sinal de saída
EXIT_CODE=$?

# Finalizar serviços (opcional - para garantir que eventos sejam enviados)
python -c "from statsig_integration import StatsigService; StatsigService().shutdown()"

exit $EXIT_CODE
"""