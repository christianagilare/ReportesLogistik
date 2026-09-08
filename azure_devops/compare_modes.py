import logging
import sys

from config import Config, validate_config

from .client import AzureDevOpsClient
from .export_ids import compare_export_modes, format_compare_report


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def run_compare() -> dict:
    validate_config()
    client = AzureDevOpsClient(
        token=Config.ADO_TOKEN,
        base_url=Config.ADO_BASE_URL,
        org=Config.ADO_ORG,
        project_id=Config.ADO_PROJECT_ID,
    )
    return compare_export_modes(
        client,
        query_id=Config.ADO_QUERY_ID,
        date_from=Config.TT_DATE_FROM,
        date_to=Config.TT_DATE_TO,
    )


def main() -> int:
    setup_logging()
    logger = logging.getLogger(__name__)
    try:
        result = run_compare()
    except Exception as exc:
        logger.error("Fallo al comparar modos de exportacion ADO: %s", exc, exc_info=True)
        return 1

    report = format_compare_report(result)
    print(report)
    if result["equal"]:
        logger.info("Los conjuntos de work item IDs coinciden entre saved_query y wiql_env.")
        return 0

    logger.error("Los conjuntos de work item IDs NO coinciden entre modos.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
