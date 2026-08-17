import logging# [COMENTADO TEMPORALMENTE: INTEGRACION TRACKINGTIME]
# Para volver a integrar TrackingTime, descomentar la siguiente linea:
# from trackingtime.exporter import run_trackingtime_export
from azure_devops.exporter import run_azure_devops_export
from config import validate_config, Config
from report_paths import ensure_period_dirs, get_report_paths

from processing import (
    load_data,
    transform_azure_devops,
    transform_trackingtime,
    build_tables,
    build_presentation_table,
    add_new_collaborators,
    generate_excel_report
)

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("INICIO FASE 1: Extraccion de datos")
    
    try:
        # Asegura que las configuraciones esten presentes
        validate_config()
    except Exception as e:
        logger.error(f"Error de configuracion: {e}")
        return

    # [COMENTADO TEMPORALMENTE: INTEGRACION TRACKINGTIME]
    # Para volver a integrar TrackingTime, descomentar el siguiente bloque:
    # logger.info("--- Ejecutando extraccion de TrackingTime ---")
    # try:
    #     run_trackingtime_export()
    # except Exception as e:
    #     logger.error(f"Error critico en modulo TrackingTime: {e}", exc_info=True)
        
    logger.info("--- Ejecutando extraccion de Azure DevOps ---")
    try:
        run_azure_devops_export()
    except Exception as e:
        logger.error(f"Error critico en modulo Azure DevOps: {e}", exc_info=True)
        
    logger.info("FIN FASE 1")
    
    logger.info("INICIO FASE 2: Transformacion y Reporte")

    paths = ensure_period_dirs()
    docs_dir = "Documentos"

    # 1. Load data
    try:
        df_azure_raw, df_tracking_raw, df_codigos, df_equipo = load_data(docs_dir)
    except Exception as e:
        logger.error(f"Error al cargar datos para Fase 2: {e}", exc_info=True)
        return
        
    # 2. Transformations
    df_azure_clean = transform_azure_devops(df_azure_raw)
    df_tracking_clean = transform_trackingtime(df_tracking_raw)
    
    # 3. Build derived tables
    tables = build_tables(df_azure_clean, df_tracking_clean, df_codigos, df_equipo)
    horas_az = tables["horas_azure"]
    horas_tr = tables["horas_tracking"]
    total_horas_combinado = tables["total_horas_combinado"]
    
    # 4. Presentation matrix
    presentacion = build_presentation_table(horas_az, horas_tr, total_horas_combinado)

    if Config.AUTO_ADD_COLLABORATORS:
        logger.info("Agregando registros de nuevos colaboradores...")
        presentacion = add_new_collaborators(presentacion, Config.NEW_COLLABORATORS)
    
    # 5. Generate Excel
    output_path = str(paths["report_path"])
    generate_excel_report(
        presentacion=presentacion,
        codigos_df=df_codigos,
        azure_df=df_azure_clean,
        tracking_df=df_tracking_clean,
        output_path=output_path,
        start_date=Config.TT_DATE_FROM,
        end_date=Config.TT_DATE_TO
    )
    
    logger.info(f"FIN FASE 2. Archivo procesado en: {output_path}")

if __name__ == "__main__":
    main()
