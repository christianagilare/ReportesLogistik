import datetime
from pathlib import Path

from config import Config

REPORTS_BASE_DIR = "Informes"


def get_date_suffix(date_from: str | None = None, date_to: str | None = None) -> str:
    date_from = date_from or Config.TT_DATE_FROM
    date_to = date_to or Config.TT_DATE_TO
    return f"{date_from.replace('-', '')}_{date_to.replace('-', '')}"


def get_period_dir(date_from: str | None = None) -> Path:
    date_from = date_from or Config.TT_DATE_FROM
    dt = datetime.datetime.strptime(date_from, "%Y-%m-%d")
    return Path(REPORTS_BASE_DIR) / str(dt.year) / f"{dt.month:02d}-{dt.strftime('%B').upper()}"


def get_anexos_dir(date_from: str | None = None) -> Path:
    return get_period_dir(date_from) / "ANEXOS"


def get_report_paths(date_from: str | None = None, date_to: str | None = None) -> dict[str, Path]:
    period_dir = get_period_dir(date_from)
    anexos_dir = get_anexos_dir(date_from)
    date_suffix = get_date_suffix(date_from, date_to)

    return {
        "period_dir": period_dir,
        "anexos_dir": anexos_dir,
        "report_path": period_dir / f"Reporte_{date_suffix}.xlsx",
        "azure_csv": anexos_dir / f"azure_devops_unified_{date_suffix}.csv",
        "tracking_csv": anexos_dir / f"trackingtime_unified_{date_suffix}.csv",
    }


def ensure_period_dirs(date_from: str | None = None, date_to: str | None = None) -> dict[str, Path]:
    paths = get_report_paths(date_from, date_to)
    paths["period_dir"].mkdir(parents=True, exist_ok=True)
    paths["anexos_dir"].mkdir(parents=True, exist_ok=True)
    return paths
