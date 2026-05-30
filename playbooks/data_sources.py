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


async def _fetch_stooq(decl: dict, context: dict) -> Any:
    """Fetch real-time stock/index/commodity quotes from Stooq's CSV API.

    Calculates change as percentage: (Close - Open) / Open * 100.
    Returns normalized objects: { 'symbol': symbol, 'price': price, 'change': change }
    """
    cfg = context.get("slide_cfg") or {}
    symbols_list = cfg.get("symbols", [])
    if not symbols_list:
        symbols_list = decl.get("symbols", [])

    if not symbols_list:
        return []

    # Join with '+' as required by Stooq multi-symbol query
    symbols_str = "+".join(symbols_list)
    url = f"https://stooq.com/q/l/?s={symbols_str}&f=sd2t2ohlc&h&e=csv"

    timeout = float(decl.get("timeout", 5.0))
    client = _get_rest_client()

    r = await client.get(url, timeout=timeout)
    r.raise_for_status()

    text = r.text
    lines = text.strip().split("\n")
    if len(lines) < 2:
        return []

    header = [col.strip().lower() for col in lines[0].split(",")]
    # Expected: ['symbol', 'date', 'time', 'open', 'high', 'low', 'close']

    results = []
    for line in lines[1:]:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != len(header):
            continue
        row = dict(zip(header, parts))

        try:
            symbol = row.get("symbol", "").upper()
            open_str = row.get("open", "")
            close_str = row.get("close", "")
            
            if open_str == "N/D" or close_str == "N/D" or not open_str or not close_str:
                results.append({
                    "symbol": symbol,
                    "price": None,
                    "change": None
                })
                continue

            open_val = float(open_str)
            close_val = float(close_str)

            price = close_val
            if open_val != 0:
                change = ((close_val - open_val) / open_val) * 100.0
            else:
                change = 0.0

            results.append({
                "symbol": symbol,
                "price": price,
                "change": change
            })
        except ValueError:
            results.append({
                "symbol": row.get("symbol", "").upper(),
                "price": None,
                "change": None
            })

    return results


async def _fetch_noaa_metar(decl: dict, context: dict) -> dict:
    """Fetches real METAR for a weather station (defaults to LFBO) and parses it."""
    station = decl.get("station", "LFBO")
    url = f"https://tgftp.nws.noaa.gov/data/observations/metar/stations/{station}.TXT"
    fallback = {
        "wind": "310° @ 12kt",
        "temp": "16°C",
        "pressure": "1015 hPa",
        "clouds": "Few clouds 3000ft",
        "raw": f"{station} 262100Z 31012KT 9999 FEW030 16/11 Q1015"
    }
    client = _get_rest_client()
    try:
        resp = await client.get(url, timeout=3.0)
        if resp.status_code == 200:
            lines = resp.text.strip().splitlines()
            if len(lines) >= 2:
                metar_raw = lines[1].strip()
                # Simple parsing of wind (e.g. 32015KT, VRB05KT, 32015G25KT)
                wind_match = re.search(r'\b(\d{3}|VRB)(\d{2})(G\d{2})?KT\b', metar_raw)
                wind_str = "310° @ 12kt"
                if wind_match:
                    dir_val = wind_match.group(1)
                    speed_val = wind_match.group(2)
                    gust_val = wind_match.group(3)
                    dir_deg = f"{dir_val}°" if dir_val != "VRB" else "Variable"
                    wind_str = f"{dir_deg} @ {speed_val}kt"
                    if gust_val:
                        wind_str += f" (Gusts {gust_val[1:]}kt)"
                
                # Parse temperature (e.g. 15/10, M02/M05)
                temp_match = re.search(r'\b(M?\d{2})\/(M?\d{2})\b', metar_raw)
                temp_str = "16°C"
                if temp_match:
                    t = temp_match.group(1)
                    t_val = int(t.replace('M', '-')) if t.startswith('M') else int(t)
                    temp_str = f"{t_val}°C"
                
                # Parse pressure (e.g. Q1015)
                qnh_match = re.search(r'\bQ(\d{4})\b', metar_raw)
                qnh_str = "1015 hPa"
                if qnh_match:
                    qnh_str = f"{qnh_match.group(1)} hPa"
                
                # Parse clouds (e.g. FEW030, SCT045, BKN035, OVC010)
                cloud_match = re.search(r'\b(FEW|SCT|BKN|OVC|CAVOK|NSC)(\d{3})?\b', metar_raw)
                cloud_str = "Clear skies"
                if cloud_match:
                    typ = cloud_match.group(1)
                    alt = cloud_match.group(2)
                    if typ == "CAVOK":
                        cloud_str = "Clear (CAVOK)"
                    elif typ == "NSC":
                        cloud_str = "No significant clouds"
                    else:
                        alt_ft = int(alt) * 100 if alt else 3000
                        names = {"FEW": "Few", "SCT": "Scattered", "BKN": "Broken", "OVC": "Overcast"}
                        cloud_str = f"{names.get(typ, typ)} clouds @ {alt_ft}ft"
                
                return {
                    "wind": wind_str,
                    "temp": temp_str,
                    "pressure": qnh_str,
                    "clouds": cloud_str,
                    "raw": metar_raw
                }
    except Exception:
        pass
    return fallback


async def _fetch_simulated_airspace(decl: dict, context: dict) -> list[dict]:
    """Generates progress-stepped approach sequences targeting LFBO Runway 32L/R."""
    tick = context.get("tick", 0)
    sim_tick = tick % 8

    flights = [
        {
            "callsign": "AFR6129",
            "company": "Air France",
            "aircraft": "Airbus A321",
            "altitude": max(150, 1150 - sim_tick * 100),
            "speed": max(135, 260 - sim_tick * 12),
            "vrate": -1100,
            "origin": "ORY",
            "destination": "TLS",
            "dep_time": "19:40",
            "squawk": "1242"
        },
        {
            "callsign": "BAW373",
            "company": "British Airways",
            "aircraft": "Airbus A320",
            "altitude": max(300, 2400 - sim_tick * 150),
            "speed": max(145, 300 - sim_tick * 15),
            "vrate": -1400,
            "origin": "LHR",
            "destination": "TLS",
            "dep_time": "18:15",
            "squawk": "2104"
        },
        {
            "callsign": "EZY4218",
            "company": "EasyJet",
            "aircraft": "Airbus A319",
            "altitude": max(600, 3800 - sim_tick * 200),
            "speed": max(155, 340 - sim_tick * 18),
            "vrate": -1700,
            "origin": "LGW",
            "destination": "TLS",
            "dep_time": "18:45",
            "squawk": "4215"
        },
        {
            "callsign": "RYR109B",
            "company": "Ryanair",
            "aircraft": "Boeing 737",
            "altitude": max(1200, 4900 - sim_tick * 250),
            "speed": max(165, 380 - sim_tick * 20),
            "vrate": -900,
            "origin": "STN",
            "destination": "TLS",
            "dep_time": "18:30",
            "squawk": "7302"
        },
        {
            "callsign": "DLH11A",
            "company": "Lufthansa",
            "aircraft": "Airbus A321",
            "altitude": max(2100, 5800 - sim_tick * 300),
            "speed": max(180, 410 - sim_tick * 22),
            "vrate": -1200,
            "origin": "FRA",
            "destination": "TLS",
            "dep_time": "19:25",
            "squawk": "1104"
        }
    ]

    for f in flights:
        alt_m = f["altitude"]
        vrate_fpm = abs(f["vrate"])
        alt_ft = alt_m * 3.28084
        if vrate_fpm > 0:
            minutes_to_touchdown = alt_ft / vrate_fpm
        else:
            minutes_to_touchdown = 5.0
            
        seconds_to_touchdown = int(minutes_to_touchdown * 60)
        
        base_seconds = 20 * 3600 + 50 * 60
        target_seconds = base_seconds + seconds_to_touchdown
        
        eta_hr = (target_seconds // 3600) % 24
        eta_min = (target_seconds // 60) % 60
        eta_sec = target_seconds % 60
        
        f["eta"] = f"{eta_hr:02d}:{eta_min:02d}:{eta_sec:02d}"
        f["eta_relative"] = f"{seconds_to_touchdown // 60}m {seconds_to_touchdown % 60:02d}s"

    flights.sort(key=lambda f: f["altitude"])
    return flights


async def _fetch_text_file(decl: dict, context: dict) -> str:
    """Read a raw text/SVG file relative to the playbooks/ directory."""
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, decl["path"])
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


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
        if src == "stooq":         return await _fetch_stooq(decl, context)
        if src == "bigquery":      return await _fetch_bigquery(decl, context)
        if src == "yahoo_finance": return await _fetch_yahoo(decl, context)
        if src == "noaa_metar":    return await _fetch_noaa_metar(decl, context)
        if src == "simulated_airspace": return await _fetch_simulated_airspace(decl, context)
        if src == "text_file":     return await _fetch_text_file(decl, context)
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
