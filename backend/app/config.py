import os
from dataclasses import dataclass
from pathlib import Path
from typing import List



def _split_csv_env(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./app.db")
    upload_dir: str = os.getenv("UPLOAD_DIR", "./uploads")
    cors_origins_raw: str = os.getenv("CORS_ORIGINS", "http://localhost:4200")
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "120"))
    demo_data_dir: str = os.getenv("DEMO_DATA_DIR", "../demo-data")

    @property
    def cors_origins(self) -> List[str]:
        origins = _split_csv_env(self.cors_origins_raw)
        if "http://localhost:4200" in origins:
            for local_alt in ("http://127.0.0.1:4200", "http://0.0.0.0:4200"):
                if local_alt not in origins:
                    origins.append(local_alt)
        return origins

    @property
    def upload_path(self) -> Path:
        return Path(self.upload_dir).resolve()

    @property
    def demo_data_path(self) -> Path:
        return Path(self.demo_data_dir).resolve()


settings = Settings()
