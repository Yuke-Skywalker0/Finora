from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    mongodb_uri: str
    mongodb_db: str = "finora"
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str
    jwt_secret: str
    data_encryption_key: str
    user_index_secret: str
    cookie_secure: bool = True
    cookie_samesite: str = "lax"
    access_token_minutes: int = 10080

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
