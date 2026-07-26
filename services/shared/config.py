"""
Configuración centralizada para todos los microservicios de Netxia.
Usa pydantic-settings para validar variables de entorno.

NOTA IMPORTANTE (lección aprendida): pydantic-settings usa por defecto
extra="forbid", lo que revienta si el .env tiene variables no declaradas
aquí. Usamos extra="ignore" para evitar ese problema.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Entorno
    environment: str = "production"
    log_level: str = "INFO"

    # PostgreSQL
    postgres_user: str = "netxia"
    postgres_password: str = "changeme"
    postgres_db: str = "netxia"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str = ""
    redis_context_ttl_seconds: int = 1800  # 30 minutos de inactividad

    # RabbitMQ
    rabbitmq_user: str = "netxia"
    rabbitmq_password: str = "changeme"
    rabbitmq_host: str = "rabbitmq"
    rabbitmq_port: int = 5672

    # Ollama / LLM
    ollama_host: str = "http://ollama:11434"
    default_llm_model: str = "llama3.2:3b"
    fast_llm_model: str = "gemma2:2b"
    reasoning_llm_model: str = "mistral:7b"

    # Voice
    stt_model_size: str = "base"
    tts_voice: str = "es_ES-sharon-medium"

    # Evolution API (WhatsApp)
    evolution_api_url: str = "http://evolution-api:8080"
    evolution_api_key: str = "changeme"

    # Seguridad
    jwt_secret: str = "changeme"
    encryption_key: str = "changeme"

    # Feature flags de seguridad (patrón usado en otros proyectos de Netxia)
    allow_dangerous_ops: bool = False  # se auto-deshabilita en producción

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/0"

    @property
    def rabbitmq_url(self) -> str:
        return (
            f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}"
            f"@{self.rabbitmq_host}:{self.rabbitmq_port}/"
        )

    def model_post_init(self, __context) -> None:
        # Nunca permitir operaciones peligrosas fuera de dev/staging
        if self.environment == "production" and self.allow_dangerous_ops:
            object.__setattr__(self, "allow_dangerous_ops", False)


settings = Settings()
