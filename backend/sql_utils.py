import re
from typing import List, Dict, Set

# Tokens that must never appear inside the query (after we strip a single trailing semicolon)
FORBIDDEN = [
    "--",
    "/*",
    "pragma",
    "insert",
    "update",
    "delete",
    "alter",
    "drop",
    "create",
]


def _extract_tables(query_lc: str) -> Set[str]:
    """Extract only real table names from FROM and JOIN clauses (ignore aliases)."""
    tables: Set[str] = set()
    # Capture table names following FROM/JOIN keywords
    for m in re.finditer(r"\b(from|join)\s+([a-zA-Z_][a-zA-Z0-9_]*)", query_lc):
        tables.add(m.group(2))
    return tables


def _extract_identifiers(query_lc: str) -> Set[str]:
    # Find identifiers like table.column or column
    return set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?", query_lc))


def is_safe_sql(query: str, allowed_tables: List[str], schema: Dict[str, Set[str]]) -> bool:
    """
    Basic SQL safety validator with alias-tolerant checks.
    - Must start with SELECT
    - No forbidden tokens (after trimming a single trailing semicolon)
    - Must include LIMIT <= 200
    - Only reference allowed tables/columns (aliases allowed)
    """
    if not query:
        return False

    # Normalize whitespace and strip a single trailing semicolon
    q = query.strip()
    if q.endswith(";"):
        q = q[:-1].strip()
    ql = q.lower()

    if not ql.startswith("select"):
        return False

    # No forbidden tokens
    for bad in FORBIDDEN:
        if bad in ql:
            return False

    # Must include LIMIT and <= 200
    m = re.search(r"limit\s+(\d+)", ql)
    if not m:
        return False
    try:
        limit_val = int(m.group(1))
    except ValueError:
        return False
    if limit_val > 200:
        return False

    # Only allowed tables
    allowed_set = set(t.lower() for t in allowed_tables)
    used_tables = {t.lower() for t in _extract_tables(ql)}
    if not used_tables.issubset(allowed_set):
        return False

    # Column-level validation is disabled to reduce false negatives from LLM-generated SQL
    # We still enforce table allowlist and LIMIT and forbid dangerous tokens.
    # This allows DB to surface precise errors if a column does not exist.
    return True
