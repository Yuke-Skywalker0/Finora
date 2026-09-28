from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    mongodb_uri: str
    mongodb_db: str = "finora"
    google_client_id: str
    jwt_secret: str
    data_encryption_key: str
    user_index_secret: str
    frontend_origins: str = "http://localhost:5500"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    access_token_minutes: int = 10080

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def origins(self) -> list[str]:
        return [x.strip() for x in self.frontend_origins.split(",") if x.strip()]

settings = Settings()
