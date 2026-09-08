import re

MODE_WIQL_ENV = "wiql_env"
MODE_SAVED_QUERY = "saved_query"
DEFAULT_EXPORT_MODE = MODE_WIQL_ENV
VALID_EXPORT_MODES = (MODE_WIQL_ENV, MODE_SAVED_QUERY)

ADO_DATETIME_SUFFIX = "T00:00:00.0000000"
_DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Only rewrite System.ChangedDate comparison literals, never other date fields.
_GE_PATTERN = re.compile(
    r"(\[\s*System\.ChangedDate\s*\]\s*>=\s*['\"])([^'\"]*)(['\"])",
    re.IGNORECASE,
)
_LE_PATTERN = re.compile(
    r"(\[\s*System\.ChangedDate\s*\]\s*<=\s*['\"])([^'\"]*)(['\"])",
    re.IGNORECASE,
)


def normalize_export_mode(value: str | None) -> str:
    raw = (value or DEFAULT_EXPORT_MODE).strip().lower()
    if not raw:
        return DEFAULT_EXPORT_MODE
    if raw not in VALID_EXPORT_MODES:
        allowed = ", ".join(VALID_EXPORT_MODES)
        raise ValueError(f"Modo de exportacion ADO invalido: {value!r}. Use uno de: {allowed}")
    return raw


def to_ado_changed_date_literal(value: str) -> str:
    literal = (value or "").strip()
    if not literal:
        raise ValueError("La fecha para System.ChangedDate esta vacia.")
    if _DATE_ONLY.fullmatch(literal):
        return f"{literal}{ADO_DATETIME_SUFFIX}"
    return literal


def extract_changed_date_bounds(wiql: str) -> tuple[str | None, str | None]:
    ge_match = _GE_PATTERN.search(wiql or "")
    le_match = _LE_PATTERN.search(wiql or "")
    date_from = ge_match.group(2) if ge_match else None
    date_to = le_match.group(2) if le_match else None
    return date_from, date_to


def rewrite_changed_date_bounds(wiql: str, date_from: str, date_to: str) -> str:
    """Replace [System.ChangedDate] >= / <= literals, leaving every other filter intact."""
    if not wiql or not wiql.strip():
        raise ValueError("El texto WIQL esta vacio.")

    from_literal = to_ado_changed_date_literal(date_from)
    to_literal = to_ado_changed_date_literal(date_to)

    ge_matches = list(_GE_PATTERN.finditer(wiql))
    le_matches = list(_LE_PATTERN.finditer(wiql))
    if not ge_matches:
        raise ValueError(
            "El WIQL no contiene una clausula [System.ChangedDate] >= '...' para reescribir."
        )
    if not le_matches:
        raise ValueError(
            "El WIQL no contiene una clausula [System.ChangedDate] <= '...' para reescribir."
        )

    rewritten = _GE_PATTERN.sub(lambda match: f"{match.group(1)}{from_literal}{match.group(3)}", wiql)
    rewritten = _LE_PATTERN.sub(lambda match: f"{match.group(1)}{to_literal}{match.group(3)}", rewritten)
    return rewritten
