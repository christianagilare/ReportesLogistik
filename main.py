import argparse
import logging
import sys

# [COMENTADO TEMPORALMENTE: INTEGRACION TRACKINGTIME]
# Para volver a integrar TrackingTime, descomentar la siguiente linea:
# from trackingtime.exporter import run_trackingtime_export
from azure_devops.compare_modes import run_compare, format_compare_report
from azure_devops.exporter import run_azure_devops_export
from azure_devops.wiql import VALID_EXPORT_MODES
from config import validate_config, Config
from report_paths import ensure_period_dirs

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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extrae datos de Azure DevOps (y TrackingTime) y genera el informe Excel."
    )
    parser.add_argument(
        "--ado-export-mode",
        choices=list(VALID_EXPORT_MODES),
        default=None,
        help=(
            "Modo de exportacion de Azure DevOps. "
            "wiql_env (default) usa TT_DATE_FROM/TT_DATE_TO; "
            "saved_query usa las fechas embebidas en el query de Azure. "
            "Si se omite, se usa ADO_EXPORT_MODE del .env (default: wiql_env)."
        ),
    )
    parser.add_argument(
        "--compare-modes",
        action="store_true",
        help=(
            "Ejecuta saved_query y wiql_env contra el mismo query, compara los conjuntos "
            "de work item IDs y termina sin generar el Excel."
        ),
    )
    return parser.parse_args(argv)

def main(argv: list[str] | None = None):
    args = parse_args(argv)
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Asegura que las configuraciones esten presentes
        validate_config()
    except Exception as e:
        logger.error(f"Error de configuracion: {e}")
        return 1

    if args.compare_modes:
        logger.info("Comparando modos de exportacion Azure DevOps (saved_query vs wiql_env)...")
        try:
            result = run_compare()
        except Exception as e:
            logger.error(f"Error al comparar modos Azure DevOps: {e}", exc_info=True)
            return 1
        print(format_compare_report(result))
        if result["equal"]:
            logger.info("Los conjuntos de work item IDs coinciden.")
            return 0
        logger.error("Los conjuntos de work item IDs NO coinciden.")
        return 1

    logger.info("INICIO FASE 1: Extraccion de datos")

    # [COMENTADO TEMPORALMENTE: INTEGRACION TRACKINGTIME]
    # Para volver a integrar TrackingTime, descomentar el siguiente bloque:
    # logger.info("--- Ejecutando extraccion de TrackingTime ---")
    # try:
    #     run_trackingtime_export()
    # except Exception as e:
    #     logger.error(f"Error critico en modulo TrackingTime: {e}", exc_info=True)
        
    logger.info("--- Ejecutando extraccion de Azure DevOps ---")
    try:
        run_azure_devops_export(mode=args.ado_export_mode)
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
        return 1
        
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
    return 0

if __name__ == "__main__":
    sys.exit(main() or 0)
