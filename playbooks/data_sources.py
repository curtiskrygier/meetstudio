# ═══════════════════════════════════════════════════════════════════════════
# STAGED FILE — destination: playbooks/data_sources.py (NEW)
#
# ## TODO before apply
#   - v0 cache is unbounded (module-level dict). Acceptable for dev/demo
#     since uvicorn restart clears it. v1 should add TTL-based eviction —
#     see `_DATA_CACHE` comment block below for the hook.
#   - Only `literal` and `yaml` sources are implemented in v0. bigquery,
#     yahoo_finance, rest are stubbed to raise NotImplementedError so the
#     fallback path is exercised cleanly. Wire each up when needed.
#   - Cache key is (slide_id, data_key) — sharing across slides is opt-in
#     (slide A and slide B with the same key get separate cache entries).
# ═══════════════════════════════════════════════════════════════════════════
"""Data resolution substrate for the YAML playbook layer.

Each slide's YAML `data:` section declares one entry per data key, with:
    source:   one of {literal, yaml, bigquery, yahoo_finance, rest, ...}
    refresh:  static | on_fire | "<N>s" — when to re-fetch (default on_fire)
    fallback: shown if source fetch fails
    (source-specific keys: query, path, url, symbol, value, ...)

The resolver is the ONLY async layer. Templates receive a plain dict of
{key: resolved_value} and don't know how the values got there."""

import asyncio
import os
import time
from typing import Any

import yaml


# In-process cache, keyed by (slide_id, data_key).
# Value: (resolved_value, last_fetched_unix_ts).
# v0 has no eviction — restart clears it. For v1, add a periodic sweep that
# drops entries whose ts is older than max(refresh_period * 5, 600s) and
# evicts the oldest 25% when len() exceeds, say, 5000.
_DATA_CACHE: dict[tuple[str, str], tuple[Any, float]] = {}


# ────────────────────────────────────────────────────────────────────────────
# Per-source fetchers — each returns the raw resolved value.
# Add a new source by writing one async fn here + one elif in `resolve()`.
# ────────────────────────────────────────────────────────────────────────────

async def _fetch_literal(decl: dict) -> Any:
    """Literal value embedded in YAML. Always returns decl['value']."""
    return decl.get("value")


async def _fetch_yaml(decl: dict) -> Any:
    """Read a YAML file relative to the playbooks/ directory."""
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, decl["path"])
    with open(path) as f:
        return yaml.safe_load(f)


async def _fetch_bigquery(decl: dict) -> Any:
    """BigQuery source — stub. Wire up via google.cloud.bigquery when needed."""
    # When implementing:
    #   from google.cloud import bigquery
    #   client = bigquery.Client(project=os.environ.get("GEMINI_PROJECT"))
    #   row = next(iter(client.query(decl["query"]).result()), None)
    #   return list(row.values())[0] if row else None
    raise NotImplementedError("bigquery source not yet wired — using fallback")


async def _fetch_yahoo(decl: dict) -> Any:
    """yahoo_finance source — stub. Wire up via yfinance or a free REST API."""
    raise NotImplementedError("yahoo_finance source not yet wired — using fallback")


async def _fetch_rest(decl: dict) -> Any:
    """REST source — stub. Wire up via httpx when needed."""
    raise NotImplementedError("rest source not yet wired — using fallback")


# ────────────────────────────────────────────────────────────────────────────
# Public API — used by yaml_loader, never imported by templates.
# ────────────────────────────────────────────────────────────────────────────

async def resolve(decl: dict, context: dict) -> Any:
    """Source-agnostic resolver. Always returns a value — falls back gracefully
    on any error so the show keeps going."""
    src = decl.get("source")
    try:
        if src == "literal":         return await _fetch_literal(decl)
        if src == "yaml":            return await _fetch_yaml(decl)
        if src == "bigquery":        return await _fetch_bigquery(decl)
        if src == "yahoo_finance":   return await _fetch_yahoo(decl)
        if src == "rest":            return await _fetch_rest(decl)
        raise ValueError(f"unknown source: {src!r}")
    except Exception as e:
        # Log once at debug level, never crash. Demo > correctness here.
        # If you want louder failure during dev, wrap with try/except in
        # yaml_loader and inspect there.
        return decl.get("fallback", "—")


def should_refresh(slide_id: str, key: str, decl: dict, tick: int) -> bool:
    """Decide whether to re-fetch this data on this tick, based on the slide's
    declared refresh policy.
        static:    one-shot — fetched at first ever request, never again
        on_fire:   default — fetched at tick 0 of each fire
        '<N>s':    every N seconds (via tick loop)
    """
    refresh = decl.get("refresh", "on_fire")
    cached  = _DATA_CACHE.get((slide_id, key))

    if refresh == "static":
        return cached is None
    if refresh == "on_fire":
        return tick == 0
    if isinstance(refresh, str) and refresh.endswith("s"):
        try:
            period = float(refresh.rstrip("s"))
        except ValueError:
            return tick == 0  # malformed → safe default
        if cached is None:
            return True
        return (time.time() - cached[1]) >= period
    return tick == 0  # unknown policy → safe default


async def resolve_slide_data(slide_id: str, data_decls: dict | None,
                             context: dict, tick: int) -> dict:
    """Walk a slide's `data:` declarations, refresh only what policy demands,
    return a flat {key: resolved_value} dict ready for the template."""
    if not data_decls:
        return {}
    out: dict[str, Any] = {}
    for key, decl in data_decls.items():
        if should_refresh(slide_id, key, decl, tick):
            value = await resolve(decl, context)
            _DATA_CACHE[(slide_id, key)] = (value, time.time())
            out[key] = value
        else:
            cached = _DATA_CACHE.get((slide_id, key))
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
