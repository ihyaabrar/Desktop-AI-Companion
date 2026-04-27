"""Runtime configuration loaded from environment / .env."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Sidecar settings.

    All fields are overridable via environment variables (and the .env file in dev).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    llm_provider: str = "ollama"
    llm_model: str = "ollama/qwen2.5:7b"
    ollama_api_base: str = "http://127.0.0.1:11434"

    # Optional cloud keys (LiteLLM picks them up from env directly, listed here for completeness)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None

    # Server
    sidecar_host: str = "127.0.0.1"
    sidecar_port: int = 8765

    # Generation
    max_tokens: int = 1024
    temperature: float = 0.7


settings = Settings()
