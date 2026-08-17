import pandas as pd
import io
import logging
from config import Config
from report_paths import ensure_period_dirs
from .client import TrackingTimeClient

logger = logging.getLogger(__name__)

def run_trackingtime_export():
    logger.info("Iniciando exportacion de TrackingTime...")
    
    client = TrackingTimeClient(token=Config.TT_TOKEN, base_url=Config.TT_BASE_URL)
    
    try:
        raw_users = client.get_users()
    except Exception as e:
        logger.error(f"Fallo al obtener usuarios: {e}")
        return
        
    # Filtrar usuarios inactivos
    active_users = [u for u in raw_users if not u.get("is_archived")]
    logger.info(f"Se encontraron {len(active_users)} usuarios activos.")
    
    all_dfs = []
    
    for user in active_users:
        user_id = user["id"]
        # Extraer campos basicos para logging
        name = user.get("name", "")
        surname = user.get("surname", "")
        full_name = f"{name} {surname}".strip()
        
        logger.info(f"Exportando eventos para usuario ID: {user_id} - {full_name}")
        
        try:
            csv_data = client.export_events(
                user_id=user_id,
                date_from=Config.TT_DATE_FROM,
                date_to=Config.TT_DATE_TO
            )
            
            # Si devuelve vacio pero 200:
            if not csv_data or not csv_data.strip():
                logger.warning(f"Usuario {user_id} devolvio CSV en blanco. Ignorando.")
                continue
                
            # Leer en pandas df
            df = pd.read_csv(io.StringIO(csv_data))
            
            # Limpiar filas vacias (completamente)
            df.dropna(how='all', inplace=True)
            
            if not df.empty:
                all_dfs.append(df)
            else:
                logger.warning(f"Usuario {user_id} no tiene datos validos despues de limpieza. Ignorando.")
                
        except Exception as e:
            logger.warning(f"Fallo al exportar eventos del usuario {user_id} ({full_name}): {e}. Continuando al siguiente.")
            continue
            
    if all_dfs:
        logger.info(f"Concatenando {len(all_dfs)} dataframes...")
        unified_df = pd.concat(all_dfs, ignore_index=True)

        paths = ensure_period_dirs()
        output_path = paths["tracking_csv"]

        unified_df.to_csv(output_path, index=False)

        logger.info(f"Exportacion de TrackingTime finalizada. Archivo: {output_path}")
    else:
        logger.warning("No se obtuvieron datos de ningun usuario. No se creo el archivo unificado.")
