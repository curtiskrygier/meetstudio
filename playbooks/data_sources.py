# ═══════════════════════════════════════════════════════════════════════════
# STAGED FILE — destination: playbooks/data_sources.py (REPLACES existing)
#
# Round 3 additions:
#   - Real `rest` source (was stubbed) — shared httpx.AsyncClient hot-pool +
#     per-request timeout override, with _json_path / _apply_map /
#     _interpolate_url helpers around it.
#   - `_json_path(obj, path)` — tiny walker supporting `.foo`, `.foo[]`,
#     `.foo[0]`, `.foo[].bar`. NOT a full JSONPath library — deliberate.
#   - `_apply_map(data, mapping)` — flat key-projection only. NOT a computed-
#     expression engine — deliberate.
#   - `_interpolate_url(url, context)` — {{key}} from slide_cfg; lists join CSV.
#   - Cache key now (space_id, slide_id, data_key) for multi-tenant isolation.
#
# ## TODO before apply
#   - The cache key migration drops all currently-cached values (different
#     shape). Acceptable — cache is unbounded and uvicorn restart clears it
#     anyway. Next refresh fetches fresh.
#   - bigquery / yahoo_finance still stubbed. Wire when needed; the rest
#     pattern is the template.
#   - The shared httpx client is module-level. v1 might need per-host
#     connection-pool limits if you start hitting wildly different domains.
#     v0 burns a single pool across whatever you fetch — fine for now.
# ═══════════════════════════════════════════════════════════════════════════
"""Data resolution substrate for the YAML playbook layer.

Per-slide YAML `data:` declares one entry per key, with:
    source:     literal | yaml | rest | bigquery | yahoo_finance
    refresh:    static | on_fire | "<N>s" — when to re-fetch (default on_fire)
    fallback:   shown if source fetch fails
    (source-specific keys: query, path, url, symbol, json_path, map, ...)

Resolver is the only async layer. Templates receive a plain {key: value} dict
and don't know how the values got there."""

import asyncio
import os
import re
import time
from typing import Any

import httpx
import yaml


# ────────────────────────────────────────────────────────────────────────────
# Cache — keyed by (space_id, slide_id, data_key) for multi-tenant isolation.
# Two presenters in different Meet rooms firing the same playbook get
# independent cache entries; their data does NOT leak across rooms.
#
# Value: (resolved_value, last_fetched_unix_ts).
# v0 has no eviction — restart clears it. For v1: periodic sweep that drops
# entries with ts older than max(refresh_period * 5, 600s); evict oldest 25%
# when len() exceeds 5000.
# ────────────────────────────────────────────────────────────────────────────
_DATA_CACHE: dict[tuple[str, str, str], tuple[Any, float]] = {}


# ────────────────────────────────────────────────────────────────────────────
# Shared httpx client — hot connection pool across tick cycles.
# Per-fetch construction at 2s polling would burn DNS + TLS handshake every
# tick, causing visible jitter (~300ms) on flip-card animations. Single
# module-level client keeps the pool warm; per-request timeout overrides via
# kwargs at invocation so heterogeneous sources stay correct.
# ────────────────────────────────────────────────────────────────────────────
_SHARED_CLIENT: httpx.AsyncClient | None = None


def _get_rest_client() -> httpx.AsyncClient:
    """Lazy module-level shared httpx.AsyncClient. Generous default timeout;
    per-request timeout overrides via the call site."""
    global _SHARED_CLIENT
    if _SHARED_CLIENT is None or _SHARED_CLIENT.is_closed:
        _SHARED_CLIENT = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
    return _SHARED_CLIENT


# ────────────────────────────────────────────────────────────────────────────
# Helper — tiny JSONPath walker.
#
# Supports (deliberately small grammar):
#   ".foo"          → obj["foo"]
#   ".foo.bar"      → obj["foo"]["bar"]
#   ".[0].bar"      → obj[0]["bar"]
#   ".foo[]"        → obj["foo"]            (list passes through, subsequent
#                                            tokens map across each item)
#   ".foo[].bar"    → [item["bar"] for item in obj["foo"]]
#
# Does NOT support: filter predicates `[?id=="x"]`, wildcards `*`, recursive
# descent `..`, slice `[1:5]`. That's a deliberate substrate constraint — if
# a real use case needs those, we add a sibling helper, not a heavier engine.
# ────────────────────────────────────────────────────────────────────────────
_JSONPATH_TOKEN_RE = re.compile(r"[\w$_]+|\[\]|\[\d+\]")


def _json_path(obj: Any, path: str) -> Any:
    """Walk a tiny JSONPath. Returns None on miss; caller falls back."""
    if not path or path == ".":
        return obj
    cur = obj
    for token in _JSONPATH_TOKEN_RE.findall(path):
        if token == "[]":
            if not isinstance(cur, list):
                return None
            # leave as list; subsequent tokens map across it
            continue
        if token.startswith("[") and token.endswith("]"):
            idx = int(token[1:-1])
            if not isinstance(cur, list) or idx >= len(cur):
                return None
            cur = cur[idx]
            continue
        # name token
        if isinstance(cur, list):
            cur = [c.get(token) if isinstance(c, dict) else None for c in cur]
        elif isinstance(cur, dict):
            cur = cur.get(token)
        else:
            return None
    return cur


# ────────────────────────────────────────────────────────────────────────────
# Helper — flat key-projection map for normalizing source schemas.
#
# YAML authoring surface:
#     map: { symbol: symbol, price: regularMarketPrice, change: regularMarketChangePercent }
#         ↑ target key      ↑ source key in upstream payload
#
# Operates on a list of dicts (most common — list of records) OR a single dict.
# Anything else passes through (scalars, mixed types — map doesn't apply).
#
# Deliberately NOT a computed-expression engine. No "is_up: change >= 0" —
# derivation belongs in templates, not in data normalization.
# ────────────────────────────────────────────────────────────────────────────
def _apply_map(data: Any, mapping: dict) -> Any:
    """Project a list of dicts (or a single dict) onto a target schema.
    Missing source keys → None; downstream renders as '—' via fallback."""
    if isinstance(data, list):
        return [
            {tgt: (item.get(src) if isinstance(item, dict) else None)
             for tgt, src in mapping.items()}
            for item in data
        ]
    if isinstance(data, dict):
        return {tgt: data.get(src) for tgt, src in mapping.items()}
    return data  # scalar / other — map doesn't apply, pass through


# ────────────────────────────────────────────────────────────────────────────
# Helper — {{key}} URL interpolation against sibling slide_cfg keys.
#
# YAML authoring surface:
#     symbols: [AAPL, TSLA, NVDA]
#     data:
#       quotes:
#         source: rest
#         url: "https://.../quote?symbols={{symbols}}"
#               → fetched as "https://.../quote?symbols=AAPL,TSLA,NVDA"
#
# Lists join with comma — the only encoding most REST APIs accept for array
# params. Scalars str()-cast. Missing keys leave the token visible (so the
# author sees the unresolved name in logs instead of silently broken URLs).
#
# DELIBERATE non-feature: does NOT read from `data:` (other resolved values).
# That would introduce inter-source dependencies and require DAG ordering. If
# a downstream call needs an upstream result, build a backend proxy that
# normalizes the chain server-side.
# ────────────────────────────────────────────────────────────────────────────
_INTERP_RE = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")
_ENV_RE    = re.compile(r"\$\{(\w+)\}")


def _interpolate_url(url: str, context: dict) -> str:
    """Replace {{key}} in the URL with values from context['slide_cfg'] AND
    ${ENV_VAR} with values from os.environ.

    Lists join CSV; scalars str()-cast; missing slide_cfg keys leave token
    visible (so the author sees the miss in logs). Missing env vars resolve
    to empty string — failing the fetch with a 401/403 rather than silently
    succeeding with the placeholder embedded in the URL.

    The two-step order (slide_cfg first, env vars second) is deliberate so a
    slide_cfg key called `{{TWELVE_DATA_API_KEY}}` can't accidentally shadow
    the env var of the same name."""
    if "{{" not in url and "${" not in url:
        return url
    cfg = context.get("slide_cfg") or {}
    def sub_token(m: re.Match) -> str:
        key = m.group(1).strip()
        if key not in cfg:
            return m.group(0)
        val = cfg[key]
        if isinstance(val, list):
            return ",".join(str(v) for v in val)
        return str(val)
    url = _INTERP_RE.sub(sub_token, url)
    url = _ENV_RE.sub(lambda m: os.environ.get(m.group(1), ""), url)
    return url


def _resolve_env_in_headers(headers: dict | None) -> dict:
    """Apply ${ENV_VAR} substitution to header values. Header keys (like
    'Authorization') stay literal; values can carry env-var tokens so the
    actual secret never lives in YAML committed to git."""
    if not headers:
        return {}
    return {
        k: _ENV_RE.sub(lambda m: os.environ.get(m.group(1), ""), str(v))
        for k, v in headers.items()
    }


# ────────────────────────────────────────────────────────────────────────────
# Per-source fetchers.
# Add a new source by writing one async fn here + one elif in `resolve()`.
# ────────────────────────────────────────────────────────────────────────────

async def _fetch_literal(decl: dict, context: dict) -> Any:
    """Literal value embedded in YAML. Always returns decl['value']."""
    return decl.get("value")


async def _fetch_yaml(decl: dict, context: dict) -> Any:
    """Read a YAML file relative to the playbooks/ directory."""
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, decl["path"])
    with open(path) as f:
        return yaml.safe_load(f)


async def _fetch_rest(decl: dict, context: dict) -> Any:
    """Generic REST fetcher.

    decl keys:
        url            required — endpoint; supports {{key}} interpolation
                       against sibling slide_cfg keys (lists join CSV) AND
                       ${ENV_VAR} substitution from os.environ.
        json_path      optional — pluck a subtree before returning.
        values         optional bool — if True and result is a dict, take
                       list(data.values()). Needed for APIs like Twelve Data
                       that return dict-keyed-by-symbol on multi-symbol calls.
                       Applied between json_path and map.
        map            optional — flat key-projection on the result.
        headers        optional — dict of HTTP headers. Values carry
                       ${ENV_VAR} substitution (Authorization tokens).
        timeout        optional — seconds; default 4.0; per-request override
                                  on the shared client.
        method         optional — 'GET' (default) or 'POST'.
        body           optional — JSON body for POST.
    """
    url = _interpolate_url(decl["url"], context)
    headers = _resolve_env_in_headers(decl.get("headers"))
    timeout = float(decl.get("timeout", 4.0))
    method = (decl.get("method", "GET") or "GET").upper()

    client = _get_rest_client()
    if method == "POST":
        r = await client.post(url, headers=headers, json=decl.get("body"),
                              timeout=timeout)
    else:
        r = await client.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    data = r.json()

    if (jp := decl.get("json_path")):
        data = _json_path(data, jp)
    if decl.get("values") and isinstance(data, dict):
        # Dict-of-records → list-of-records. Twelve Data's multi-symbol /quote
        # response shape; presumably others. Applied before map so the same
        # `map:` projection works whether the upstream returns a list or a dict.
        data = list(data.values())
    if (m := decl.get("map")):
        data = _apply_map(data, m)
    return data


async def _fetch_bigquery(decl: dict, context: dict) -> Any:
    """BigQuery source — stub. Wire via google.cloud.bigquery when needed.

    Pattern, when wired:
        from google.cloud import bigquery
        client = bigquery.Client(project=os.environ.get("GEMINI_PROJECT"))
        rows = list(client.query(decl["query"]).result())
        if not rows: return None
        # honour optional `column` or default to first column of first row
        col = decl.get("column")
        return rows[0][col] if col else list(rows[0].values())[0]
    """
    raise NotImplementedError("bigquery source not yet wired — using fallback")


async def _fetch_yahoo(decl: dict, context: dict) -> Any:
    """yahoo_finance source — stub. Probably unnecessary now that `rest` is
    real (yahoo's unofficial quote endpoint is just a REST URL). Kept as a
    placeholder if domain-specific syntactic sugar earns its keep later."""
    raise NotImplementedError("yahoo_finance source not yet wired — use rest")


# ────────────────────────────────────────────────────────────────────────────
# Public API — used by yaml_loader, never imported by templates.
# ────────────────────────────────────────────────────────────────────────────

async def resolve(decl: dict, context: dict) -> Any:
    """Source-agnostic resolver. Always returns a value — falls back
    gracefully on any error so the show keeps going."""
    src = decl.get("source")
    try:
        if src == "literal":       return await _fetch_literal(decl, context)
        if src == "yaml":          return await _fetch_yaml(decl, context)
        if src == "rest":          return await _fetch_rest(decl, context)
        if src == "bigquery":      return await _fetch_bigquery(decl, context)
        if src == "yahoo_finance": return await _fetch_yahoo(decl, context)
        raise ValueError(f"unknown source: {src!r}")
    except Exception:
        # Always fall back gracefully — demo > correctness for one tick.
        # If you want louder failure during dev, wrap call sites in
        # yaml_loader and inspect there.
        return decl.get("fallback", "—")


def should_refresh(space_id: str, slide_id: str, key: str,
                   decl: dict, tick: int) -> bool:
    """Decide whether to re-fetch this data on this tick, based on the
    slide's declared refresh policy.
        static:   one-shot — fetched on first access, never again
        on_fire:  default — fetched at tick 0 of each fire
        '<N>s':   every N seconds (via tick loop)
    """
    refresh = decl.get("refresh", "on_fire")
    cached = _DATA_CACHE.get((space_id, slide_id, key))

    if refresh == "static":
        return cached is None
    if refresh == "on_fire":
        return tick == 0
    if isinstance(refresh, str) and refresh.endswith("s"):
        try:
            period = float(refresh.rstrip("s"))
        except ValueError:
            return tick == 0
        if cached is None:
            return True
        return (time.time() - cached[1]) >= period
    return tick == 0


async def resolve_slide_data(slide_id: str, data_decls: dict | None,
                             context: dict, tick: int) -> dict:
    """Walk a slide's `data:` declarations, refresh only what policy demands,
    return a flat {key: resolved_value} dict ready for the template.

    context MUST include:
        space_id        — for multi-tenant cache isolation
        playbook_name   — for endpoint URL construction in templates
        slide_cfg       — sibling slide-config keys for {{ }} interpolation
                          in REST URLs (Round 3)
    """
    if not data_decls:
        return {}
    space_id = context.get("space_id", "default")
    out: dict[str, Any] = {}
    for key, decl in data_decls.items():
        if should_refresh(space_id, slide_id, key, decl, tick):
            value = await resolve(decl, context)
            _DATA_CACHE[(space_id, slide_id, key)] = (value, time.time())
            out[key] = value
        else:
            cached = _DATA_CACHE.get((space_id, slide_id, key))
            out[key] = cached[0] if cached else decl.get("fallback", "—")
    return out


def slide_has_refresh_ticks(data_decls: dict | None) -> bool:
    """True iff any data declaration uses a periodic refresh (`<N>s`).
    yaml_loader uses this to set `Slide.ticks=True` automatically."""
    if not data_decls:
        return False
    for decl in data_decls.values():
        refresh = decl.get("refresh", "on_fire")
        if isinstance(refresh, str) and refresh.endswith("s"):
            try:
                float(refresh.rstrip("s"))
                return True
            except ValueError:
                pass
    return False
