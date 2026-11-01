import os
from pathlib import Path
import yaml
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

def load_settings():
    """Loads environment variables and YAML configuration."""
    # Load .env
    env_path = BASE_DIR / ".env"
    load_dotenv(dotenv_path=env_path)

    # Load config.yaml
    config_path = BASE_DIR / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Missing config.yaml at {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f) or {}

    smtp_host = (os.getenv("SMTP_HOST") or "smtp.gmail.com").strip()
    raw_port = os.getenv("SMTP_PORT")
    try:
        smtp_port = int(raw_port.strip()) if raw_port and raw_port.strip() else 587
    except ValueError:
        smtp_port = 587

    smtp_user = (os.getenv("SMTP_USER") or "").strip()
    smtp_password = (os.getenv("SMTP_PASSWORD") or "").replace(" ", "").strip()

    sender_name = (os.getenv("SENDER_NAME") or "Job Applicant").strip()
    sender_phone = (os.getenv("SENDER_PHONE") or "").strip()
    sender_linkedin = (os.getenv("SENDER_LINKEDIN") or "").strip()
    sender_github = (os.getenv("SENDER_GITHUB") or "").strip()
    sender_portfolio = (os.getenv("SENDER_PORTFOLIO") or "").strip()

    return {
        "base_dir": BASE_DIR,
        "smtp": {
            "host": smtp_host,
            "port": smtp_port,
            "user": smtp_user,
            "password": smtp_password,
        },
        "sender": {
            "name": sender_name,
            "phone": sender_phone,
            "linkedin": sender_linkedin,
            "github": sender_github,
            "portfolio": sender_portfolio,
        },
        "campaign": config_data.get("campaign", {}),
        "attachments": config_data.get("attachments", {}),
        "safety": config_data.get("safety", {}),
        "paths": config_data.get("paths", {}),
    }
