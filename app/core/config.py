
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    # Iris AI database
    DB_SERVER: str
    DB_NAME: str
    DB_USERNAME: str
    DB_PASSWORD: str

    DB_DRIVER: str = "ODBC Driver 17 for SQL Server"
    DB_TRUST_SERVER_CERTIFICATE: str = "yes"

    # Existing SafeFare application
    SAFEFARE_DB_NAME: str = "Safe-Fare"
    SAFEFARE_DB_USERNAME: str = "safe-fare"
    SAFEFARE_API_BASE_URL: str = "http://185.193.19.156:9096"

    # Groq AI configuration
    GROQ_API_KEY: str
    GROQ_MODEL: str = "openai/gpt-oss-20b"

    # Application
    APP_NAME: str = "Iris AI"
    DEBUG: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
