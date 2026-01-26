from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path
from typing import List
import json

# Settings file path for runtime configuration
SETTINGS_FILE = Path("./d2d_settings.json")

class Settings(BaseSettings):
    """Application settings"""
    host: str = "0.0.0.0"
    port: int = 8000
    archive_path: Path = Path("./dicom_archive")
    upload_path: Path = Path("./uploads")
    qr_storage_path: Path = Path("./qr_storage")
    max_file_size: int = 50_000_000  # 50MB

    # Query/Retrieve Storage SCP settings
    qr_scp_ae_title: str = "D2D_STORE"
    qr_scp_port: int = 11113

    # API Security Settings (can be overridden by environment variables)
    require_api_key: bool = Field(default=True, description="Whether API key authentication is required")
    api_keys: str = Field(default="vrg-api-key-2026-secure-change-me", description="Comma-separated list of valid API keys")
    deployment_timestamp: str = Field(default="", description="Last deployment or code update timestamp")

    class Config:
        env_file = ".env"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories if they don't exist
        self.archive_path.mkdir(parents=True, exist_ok=True)
        self.upload_path.mkdir(parents=True, exist_ok=True)
        self.qr_storage_path.mkdir(parents=True, exist_ok=True)
        # Load runtime settings from file
        self._load_runtime_settings()

    def _load_runtime_settings(self):
        """Load runtime settings from JSON file if it exists"""
        if SETTINGS_FILE.exists():
            try:
                data = json.loads(SETTINGS_FILE.read_text())
                if "require_api_key" in data:
                    object.__setattr__(self, "require_api_key", data["require_api_key"])
                if "api_keys" in data:
                    object.__setattr__(self, "api_keys", data["api_keys"])
            except Exception:
                pass  # Use defaults if file is invalid

    def save_runtime_settings(self, require_api_key: bool = None, api_keys: str = None):
        """Save runtime settings to JSON file"""
        data = {}
        if SETTINGS_FILE.exists():
            try:
                data = json.loads(SETTINGS_FILE.read_text())
            except Exception:
                data = {}

        if require_api_key is not None:
            data["require_api_key"] = require_api_key
            object.__setattr__(self, "require_api_key", require_api_key)
        if api_keys is not None:
            data["api_keys"] = api_keys
            object.__setattr__(self, "api_keys", api_keys)

        SETTINGS_FILE.write_text(json.dumps(data, indent=2))

    def get_api_keys_list(self) -> List[str]:
        """Get list of valid API keys"""
        return [k.strip() for k in self.api_keys.split(",") if k.strip()]

settings = Settings()
