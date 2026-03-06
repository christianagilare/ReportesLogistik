import os
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

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
