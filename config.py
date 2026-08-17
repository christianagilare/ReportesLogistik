import os
import logging
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

logger = logging.getLogger(__name__)


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("true", "1", "yes", "on")


def parse_new_collaborators(raw: str | None) -> list[dict]:
    """
    Formato: EMPRESA|NOMBRE|CEDULA;EMPRESA|NOMBRE|CEDULA
    Ejemplo: LOGIZTIK|Joffre Paul Castillo Andino|1710964295
    """
    if not raw or not raw.strip():
        return []

    collaborators = []
    for entry in raw.split(";"):
        entry = entry.strip()
        if not entry:
            continue
        parts = [part.strip() for part in entry.split("|")]
        if len(parts) != 3:
            logger.warning("Formato invalido en NEW_COLLABORATORS (use EMPRESA|NOMBRE|CEDULA): %s", entry)
            continue
        try:
            cedula = int(parts[2].strip())
        except ValueError:
            logger.warning("Cedula invalida en NEW_COLLABORATORS: %s", parts[2])
            continue
        collaborators.append({
            "empresa": parts[0],
            "nombre": parts[1],
            "cedula": cedula,
        })
    return collaborators


class Config:
    # ─── TrackingTime ───────────────────────────────────────
    TT_TOKEN = os.getenv("TT_TOKEN")
    TT_BASE_URL = os.getenv("TT_BASE_URL", "https://api.trackingtime.co/api/v4")
    TT_DATE_FROM = os.getenv("TT_DATE_FROM")
    TT_DATE_TO = os.getenv("TT_DATE_TO")

    # ─── Azure DevOps ────────────────────────────────────────
    ADO_TOKEN = os.getenv("ADO_TOKEN")
    ADO_ORG = os.getenv("ADO_ORG")
    ADO_PROJECT_ID = os.getenv("ADO_PROJECT_ID")
    ADO_QUERY_ID = os.getenv("ADO_QUERY_ID")
    ADO_BASE_URL = os.getenv("ADO_BASE_URL", "https://dev.azure.com")

    # ─── Nuevos colaboradores ────────────────────────────────
    AUTO_ADD_COLLABORATORS = _parse_bool(os.getenv("AUTO_ADD_COLLABORATORS"))
    NEW_COLLABORATORS = parse_new_collaborators(os.getenv("NEW_COLLABORATORS"))

def validate_config():
    """Valida que todas las variables de entorno requeridas estén presentes."""
    required_vars = [
        "TT_TOKEN", "TT_DATE_FROM", "TT_DATE_TO",
        "ADO_TOKEN", "ADO_ORG", "ADO_PROJECT_ID", "ADO_QUERY_ID"
    ]
    
    missing = [var_name for var_name in required_vars if not getattr(Config, var_name)]
    
    if missing:
        raise ValueError(f"Faltan las siguientes variables de entorno en el archivo .env: {', '.join(missing)}")

# Validar al cargar el módulo
validate_config()
