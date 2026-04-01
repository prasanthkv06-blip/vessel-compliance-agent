from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    app_name: str = "Vessel Compliance Agent"
    app_version: str = "1.0.0"

    # API Keys (loaded from .env)
    marine_traffic_api_key: Optional[str] = None
    spire_api_key: Optional[str] = None
    equasis_username: Optional[str] = None
    equasis_password: Optional[str] = None

    # Sanctions data paths
    ofac_sdn_path: str = "data/sanctions/ofac_sdn.xml"
    eu_sanctions_path: str = "data/sanctions/eu_consolidated.xml"
    uk_sanctions_path: str = "data/sanctions/uk_sanctions.csv"

    # Flag risk data
    paris_mou_path: str = "data/flags/paris_mou.json"
    uscg_targeted_path: str = "data/flags/uscg_targeted.json"
    itf_foc_path: str = "data/flags/itf_foc.json"

    # Report settings
    report_output_dir: str = "reports/"
    investigation_months: int = 24

    # Database
    database_url: str = "sqlite+aiosqlite:///data/vessel_compliance.db"

    class Config:
        env_file = ".env"

settings = Settings()
