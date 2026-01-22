from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    """Application settings"""
    host: str = "0.0.0.0"
    port: int = 8000
    archive_path: Path = Path("./dicom_archive")
    upload_path: Path = Path("./uploads")
    max_file_size: int = 50_000_000  # 50MB

    class Config:
        env_file = ".env"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories if they don't exist
        self.archive_path.mkdir(parents=True, exist_ok=True)
        self.upload_path.mkdir(parents=True, exist_ok=True)

settings = Settings()
