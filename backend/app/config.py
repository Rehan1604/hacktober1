from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

    llm_provider: str = "ollama"

    llm_model: str = "gemma3:4b"

    ollama_url: str = "http://localhost:11434"

    groq_api_key: str = ""

    groq_model: str = "openai/gpt-oss-20b"

    num_ctx: int = 4096

    db_path: str = "plain_words.db"


settings = Settings()