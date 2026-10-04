from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Synapic"
    app_env: str = "production"
    host: str = "0.0.0.0"
    port: int = 8000
    max_upload_mb: int = 15
    ocr_dpi: int = 300
    tesseract_cmd: str = "tesseract"
    translation_provider: str = "google"
    libretranslate_url: str = "https://libretranslate.com"
    libretranslate_api_key: str = ""
    translation_api_key: str = ""
    translation_base_url: str = "https://api.openai.com/v1"
    translation_model: str = ""
    storage_dir: str = "./storage"
    allowed_origins: str = "*"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def storage_path(self) -> Path:
        path = Path(self.storage_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def cors_origins(self) -> list[str]:
        if self.allowed_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
