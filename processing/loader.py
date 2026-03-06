import pandas as pd
import logging
from config import Config

logger = logging.getLogger(__name__)

def parse_completed_work(val):
    if pd.isna(val) or str(val).strip() == "":
        return 0.0
    try:
        # El CSV usa coma como separador de miles si locale es en-US. 
        # Intentar remover coma y convertir a float.
        val_str = str(val).replace(",", "")
        return float(val_str)
    except ValueError:
        return 0.0

def load_data(output_dir: str, docs_dir: str):
    logger.info("Cargando datos para Fase 2...")
    date_suffix = f"{Config.TT_DATE_FROM.replace('-', '')}_{Config.TT_DATE_TO.replace('-', '')}"
    
    azure_path = f"{output_dir}/azure_devops_unified_{date_suffix}.csv"
    tracking_path = f"{output_dir}/trackingtime_unified_{date_suffix}.csv"
    codigos_path = f"{docs_dir}/CodigosProyectos.csv"
    equipo_path = f"{docs_dir}/Equipo.csv"
    
    # 1. Load Azure DevOps (,)
    logger.info(f"Cargando Azure DevOps desde {azure_path}")
    df_azure = pd.read_csv(azure_path, sep=",")
    
    # Cast tipos
    df_azure["ID"] = df_azure["ID"].fillna(0).astype(int)
    
    # Parse Completed Work
    df_azure["Completed Work"] = df_azure["Completed Work"].apply(parse_completed_work)
    
    # El resto str
    str_cols = [c for c in df_azure.columns if c not in ["ID", "Completed Work"]]
    for c in str_cols:
        df_azure[c] = df_azure[c].astype(str).replace('nan', '')
        
    # 2. Load TrackingTime (,)
    logger.info(f"Cargando TrackingTime desde {tracking_path}")
    df_tracking = pd.read_csv(tracking_path, sep=",")
    
    # Cast tipos
    df_tracking["Project"] = df_tracking["Project"].astype(str).replace('nan', '')
    df_tracking["User"] = df_tracking["User"].astype(str).replace('nan', '')
    
    # Handle CSV using european decimal comma
    if "Hours" in df_tracking.columns:
        df_tracking["Hours"] = df_tracking["Hours"].astype(str).str.replace(",", ".").astype(float)
        
    # 3. Load CodigosProyectos.csv (;)
    logger.info(f"Cargando CodigosProyectos desde {codigos_path}")
    df_codigos = pd.read_csv(codigos_path, sep=";")
    
    # Eliminar espacios de columnas
    df_codigos.columns = df_codigos.columns.str.strip()
    
    # Cast % to float (e.g. "25%" -> 0.25)
    pct_cols = ["ECU", "COL", "USA", "NL"]
    for col in pct_cols:
        if col in df_codigos.columns:
            df_codigos[col] = (
                df_codigos[col]
                .astype(str)
                .str.replace("%", "")
                .replace('nan', '0')
                .astype(float) / 100.0
            )
            
    # 4. Load Equipo.csv (;)
    logger.info(f"Cargando Equipo desde {equipo_path}")
    df_equipo = pd.read_csv(equipo_path, sep=";")
    
    # Eliminar espacios de nombres de columnas
    df_equipo.columns = df_equipo.columns.str.strip()
    
    logger.info("Carga de datos completada.")
    
    return df_azure, df_tracking, df_codigos, df_equipo