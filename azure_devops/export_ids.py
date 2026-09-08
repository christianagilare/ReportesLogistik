import logging
from typing import Any, Dict, List, Sequence

from .client import AzureDevOpsClient
from .wiql import (
    MODE_SAVED_QUERY,
    MODE_WIQL_ENV,
    extract_changed_date_bounds,
    normalize_export_mode,
    rewrite_changed_date_bounds,
    to_ado_changed_date_literal,
)

logger = logging.getLogger(__name__)


def fetch_work_item_ids(
    client: AzureDevOpsClient,
    mode: str,
    query_id: str,
    date_from: str | None = None,
    date_to: str | None = None,
) -> List[int]:
    """Return work item IDs using either the saved query or WIQL rewritten from .env dates."""
    resolved_mode = normalize_export_mode(mode)

    if resolved_mode == MODE_SAVED_QUERY:
        logger.info("Modo saved_query: ejecutando el query guardado (fechas definidas en Azure DevOps).")
        wiql_url = client.get_query_wiql_url(query_id)
        logger.info("WIQL URL obtenida exitosamente desde metadata.")
        return client.execute_wiql(wiql_url)

    if resolved_mode != MODE_WIQL_ENV:
        raise ValueError(f"Modo de exportacion ADO no soportado: {resolved_mode}")

    if not date_from or not date_to:
        raise ValueError("El modo wiql_env requiere TT_DATE_FROM y TT_DATE_TO.")

    logger.info(
        "Modo wiql_env: obteniendo WIQL del query guardado y aplicando fechas de .env (%s .. %s).",
        date_from,
        date_to,
    )
    original_wiql = client.get_query_wiql(query_id)
    original_from, original_to = extract_changed_date_bounds(original_wiql)
    rewritten_wiql = rewrite_changed_date_bounds(original_wiql, date_from, date_to)
    logger.info(
        "System.ChangedDate reescrito: %s .. %s -> %s .. %s",
        original_from,
        original_to,
        to_ado_changed_date_literal(date_from),
        to_ado_changed_date_literal(date_to),
    )
    logger.debug("WIQL reescrita: %s", rewritten_wiql)
    return client.execute_wiql_query(rewritten_wiql)


def diff_id_sets(saved_query_ids: Sequence[int], wiql_env_ids: Sequence[int]) -> Dict[str, Any]:
    saved_set = set(saved_query_ids)
    env_set = set(wiql_env_ids)
    only_saved = sorted(saved_set - env_set)
    only_env = sorted(env_set - saved_set)
    return {
        "saved_query_count": len(saved_set),
        "wiql_env_count": len(env_set),
        "saved_query_ids": sorted(saved_set),
        "wiql_env_ids": sorted(env_set),
        "equal": saved_set == env_set,
        "only_in_saved_query": only_saved,
        "only_in_wiql_env": only_env,
    }


def compare_export_modes(
    client: AzureDevOpsClient,
    query_id: str,
    date_from: str,
    date_to: str,
) -> Dict[str, Any]:
    original_wiql = client.get_query_wiql(query_id)
    original_from, original_to = extract_changed_date_bounds(original_wiql)

    saved_ids = fetch_work_item_ids(client, MODE_SAVED_QUERY, query_id)
    env_ids = fetch_work_item_ids(
        client,
        MODE_WIQL_ENV,
        query_id,
        date_from=date_from,
        date_to=date_to,
    )
    result = diff_id_sets(saved_ids, env_ids)
    result.update(
        {
            "query_id": query_id,
            "env_date_from": date_from,
            "env_date_to": date_to,
            "saved_query_changed_date_from": original_from,
            "saved_query_changed_date_to": original_to,
            "rewritten_changed_date_from": to_ado_changed_date_literal(date_from),
            "rewritten_changed_date_to": to_ado_changed_date_literal(date_to),
        }
    )
    return result


def format_compare_report(result: Dict[str, Any], max_diff_ids: int = 50) -> str:
    equal_label = "SI" if result["equal"] else "NO"
    lines = [
        "=== Comparacion de modos Azure DevOps ===",
        f"Query ID: {result.get('query_id', '')}",
        f"Fechas .env (wiql_env): {result.get('env_date_from')} .. {result.get('env_date_to')}",
        (
            "Fechas en query Azure (saved_query): "
            f"{result.get('saved_query_changed_date_from')} .. {result.get('saved_query_changed_date_to')}"
        ),
        (
            "Fechas reescritas (wiql_env): "
            f"{result.get('rewritten_changed_date_from')} .. {result.get('rewritten_changed_date_to')}"
        ),
        f"saved_query: {result['saved_query_count']} work items",
        f"wiql_env:    {result['wiql_env_count']} work items",
        f"conjuntos iguales: {equal_label}",
    ]

    def _preview(label: str, ids: Sequence[int]) -> None:
        if not ids:
            lines.append(f"{label}: (ninguno)")
            return
        shown = list(ids[:max_diff_ids])
        suffix = "" if len(ids) <= max_diff_ids else f" ... ({len(ids) - max_diff_ids} mas)"
        lines.append(f"{label} ({len(ids)}): {shown}{suffix}")

    _preview("solo en saved_query", result.get("only_in_saved_query") or [])
    _preview("solo en wiql_env", result.get("only_in_wiql_env") or [])
    return "\n".join(lines)
