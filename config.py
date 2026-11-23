"""Central configuration, read from environment variables (.env)."""
import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()


def _build_database_url() -> str:
    explicit = os.getenv("DATABASE_URL")  # handy for tests
    if explicit:
        return explicit
    user = quote_plus(os.getenv("MYSQL_USER", "root"))
    password = quote_plus(os.getenv("MYSQL_PASSWORD", ""))
    host = os.getenv("MYSQL_HOST", "localhost")
    port = os.getenv("MYSQL_PORT", "3306")
    name = os.getenv("MYSQL_DATABASE", "price_tracker")
    return f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{name}"


DATABASE_URL = _build_database_url()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "60"))
REQUEST_DELAY_RANGE = (
    int(os.getenv("MIN_DELAY_SECONDS", "5")),
    int(os.getenv("MAX_DELAY_SECONDS", "12")),
)
HEADLESS = os.getenv("HEADLESS", "true").lower() != "false"

CURRENCY = "₹"
