"""
Normalize, classify, and (when possible) geocode raw place strings
coming from GEDCOM uploads.

Handles:
   • manual overrides
   • fuzzy-alias typo cleanup
   • RapidFuzz auto-corrections
   • vague state + county centroids
   • historical beat lookup
   • DB session fuzzy match
   • retry-safe TTL cache in Geocoder
   • unresolved logging
"""
from __future__ import annotations
from backend.config import settings, DATA_DIR
from pathlib import Path
import json
import os
from datetime import datetime, timezone
from typing import Dict, Optional, Any

from rapidfuzz import process as fuzz

from backend.utils.helpers import normalize_location
from backend.utils.logger import get_file_logger
from backend.models.location_models import LocationOut
from backend.services.geocode import Geocode

logger = get_file_logger("location_processor")

# ────────────── File & Data Paths ──────────────
DATA_DIR = Path(DATA_DIR)
DATA_DIR.mkdir(exist_ok=True, parents=True)

MANUAL_FIXES_PATH   = DATA_DIR / "manual_place_fixes.json"
FUZZY_ALIASES_PATH  = DATA_DIR / "fuzzy_aliases.json"
UNRESOLVED_LOG_PATH = DATA_DIR / "unresolved_locations.json"
HISTORICAL_DIR      = DATA_DIR / "historical_places"
HISTORICAL_DIR.mkdir(exist_ok=True, parents=True)

GEOCODER = Geocode(api_key=settings.GEOCODE_API_KEY)
logger.info("🧪 Using GEOCODE_API_KEY = %s", (settings.GEOCODE_API_KEY[:6] + "...") if settings.GEOCODE_API_KEY else "None")

_SEEN_UNRESOLVED: set[str] = set()

# ────── JSON helpers ──────

def _safe_load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        logger.warning("⚠️ %s not found.", path.name)
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("❌ Failed loading %s: %s", path, e)
        return default

MANUAL_FIXES_RAW: Dict[str, Dict[str, Any]] = _safe_load_json(MANUAL_FIXES_PATH, {})
FUZZY_ALIASES_RAW: Dict[str, str] = _safe_load_json(FUZZY_ALIASES_PATH, {})

# All keys normalized!
MANUAL_FIXES: Dict[str, Dict[str, Any]] = {
    normalize_location(k): v for k, v in MANUAL_FIXES_RAW.items()
}
FUZZY_ALIASES: Dict[str, str] = {
    normalize_location(k): normalize_location(v) for k, v in FUZZY_ALIASES_RAW.items()
}

# Build a list of “known good” names for fuzzy search
_KNOWN_LOCATIONS: list[str] = list(MANUAL_FIXES.keys()) + list(FUZZY_ALIASES.values())

# ────── Vague state + county fallbacks ──────
STATE_VAGUE: Dict[str, tuple[float, float]] = {
    "mississippi": (32.7364, -89.6678),
    "arkansas": (34.7990, -92.1990),
    "tennessee": (35.5175, -86.5804),
    "alabama": (32.8067, -86.7911),
    "louisiana": (30.9843, -91.9623),
    "illinois": (40.6331, -89.3985),
    "ohio": (40.4173, -82.9071),
}

COUNTY_VAGUE: Dict[str, tuple[float, float]] = {
    "sunflower county": (33.5000, -90.5500),
    "leflore county": (33.5519, -90.3084),
    "bolivar county": (33.7188, -91.0160),
    "tallahatchie county": (33.9508, -90.1889),
    "washington county ms": (33.2993, -91.0387),
}

# ────── Historical places loader ──────
HISTORICAL_LOOKUP: dict[str, tuple[float, float, str]] = {}

def _load_historical_places() -> None:
    if not HISTORICAL_DIR.exists():
        logger.info("🕰️  No historical_places/ folder found at %s.", HISTORICAL_DIR)
        return
    count = 0
    for fname in os.listdir(HISTORICAL_DIR):
        if not fname.endswith(".json"):
            continue
        path = HISTORICAL_DIR / fname
        data = _safe_load_json(path, {})
        for raw_key, rec in data.items():
            norm_key = normalize_location(raw_key)
            HISTORICAL_LOOKUP[norm_key] = (
                rec["lat"],
                rec["lng"],
                rec.get("modern_equivalent", norm_key),
            )
            count += 1
    logger.info("🗺️  Loaded %d historical place records.", count)

_load_historical_places()

_KNOWN_LOCATIONS.extend(list(HISTORICAL_LOOKUP.keys()))
_KNOWN_LOCATIONS.extend(list(COUNTY_VAGUE.keys()))
_KNOWN_LOCATIONS = list(set(_KNOWN_LOCATIONS))  # dedupe

# ────── Unresolved logger helper ──────

def _log_unresolved_once(raw: str, reason: str, tree_id: Optional[str]) -> None:
    key = f"{raw}|{reason}|{tree_id}"
    if key in _SEEN_UNRESOLVED:
        return
    _SEEN_UNRESOLVED.add(key)

    entry = {
        "raw_name": raw,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "status": "manual_fix_pending",
        # stringify the UUID so json.dump won’t freak out
        "tree_id": str(tree_id) if tree_id is not None else None,
    }
    try:
        data = []
        if UNRESOLVED_LOG_PATH.exists():
            with open(UNRESOLVED_LOG_PATH, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    logger.warning("⚠️ Corrupt unresolved log; starting fresh")
                    data = []
        data.append(entry)
        with open(UNRESOLVED_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.warning("📝 unresolved logged: %s", entry)
    except Exception as e:
        logger.error("❌ failed to write unresolved_location for '%s': %s", raw, e)

# ────── Main processor ──────

def process_location(
    raw_place: str,
    source_tag: str = "",
    event_year: Optional[int] = None,
    tree_id: Optional[str] = None,
    db_session=None,
    geocoder: Optional[Geocode] = None,
) -> LocationOut:
    """Primary resolver used by parser & API."""
    now = datetime.now(timezone.utc).isoformat()
    norm = normalize_location(raw_place)
    geo_service = geocoder or GEOCODER

    logger.info(
        "🌍 process_location: raw='%s' | norm='%s' | tag=%s | yr=%s",
        raw_place,
        norm,
        source_tag,
        event_year,
    )

    # 1. empty / nonsense — BUT keep one-word state / county names
    if not norm:
        raw_lower = raw_place.strip().lower()
        if raw_lower in STATE_VAGUE:
            norm = raw_lower
            logger.info("🕳️ single-state fallback '%s' → '%s'", raw_place, norm)
        elif raw_lower in COUNTY_VAGUE:
            norm = raw_lower
            logger.info("🏛️ single-county fallback '%s' → '%s'", raw_place, norm)
        else:
            logger.warning("⛔ Dropped empty-norm '%s'", raw_place)
            _log_unresolved_once(raw_place, "empty_after_normalise", tree_id)
            return LocationOut(
                raw_name=raw_place,
                normalized_name="",
                latitude=None,
                longitude=None,
                confidence_score=0.0,
                status="unresolved",
                source="normalize",
                timestamp=now,
            )

    # 2. manual fixes
    if norm in MANUAL_FIXES:
        fix = MANUAL_FIXES[norm]
        logger.info("🔧 manual_fix '%s' → '%s'", raw_place, norm)
        return LocationOut(
            raw_name=fix.get("raw_name", raw_place),
            normalized_name=fix.get("normalized_name", norm),
            latitude=fix.get("lat") or fix.get("latitude"),
            longitude=fix.get("lng") or fix.get("longitude"),
            confidence_score=float(fix.get("confidence", 1.0)),
            status="manual_fix",
            source="manual",
            timestamp=now,
        )

    # 3. alias table (one-step recurse)
    if norm in FUZZY_ALIASES:
        aliased = FUZZY_ALIASES[norm]
        logger.info("🔁 alias_fix '%s' → '%s'", raw_place, aliased)
        return process_location(aliased, source_tag, event_year, tree_id, db_session, geocoder)

    # 4. RapidFuzz auto-fix
    if _KNOWN_LOCATIONS:
        match, score, _ = fuzz.extractOne(norm, _KNOWN_LOCATIONS)
        if score >= 85:
            logger.info("✨ RapidFuzz %d%% '%s' → '%s'", score, raw_place, match)
            return process_location(match, source_tag, event_year, tree_id, db_session, geocoder)

    # 5. vague county fallback
    if norm in COUNTY_VAGUE:
        lat, lng = COUNTY_VAGUE[norm]
        logger.info("🏛️ vague_county '%s' (%s,%s)", raw_place, lat, lng)
        return LocationOut(
            raw_name=raw_place,
            normalized_name=norm,
            latitude=lat,
            longitude=lng,
            confidence_score=0.35,
            status="vague_county",
            source="fallback",
            timestamp=now,
        )

    # 6. vague state fallback
    if norm in STATE_VAGUE:
        lat, lng = STATE_VAGUE[norm]
        logger.info("🕳️ vague_state '%s' (%s,%s)", raw_place, lat, lng)
        return LocationOut(
            raw_name=raw_place,
            normalized_name=norm,
            latitude=lat,
            longitude=lng,
            confidence_score=0.4,
            status="vague_state",
            source="fallback",
            timestamp=now,
        )

    # 7. historical lookup
    if norm in HISTORICAL_LOOKUP:
        lat, lng, modern = HISTORICAL_LOOKUP[norm]
        logger.info("📜 historical '%s' → '%s' (%s,%s)", raw_place, modern, lat, lng)
        return LocationOut(
            raw_name=raw_place,
            normalized_name=modern,
            latitude=lat,
            longitude=lng,
            confidence_score=0.9,
            status="historical",
            source="historical",
            timestamp=now,
        )

    # 8. API geocode / DB fuzzy
    geo = geo_service.get_or_create_location(db_session, raw_place)
    if geo and geo.latitude is not None and geo.longitude is not None:
        if (
            geo.latitude == 0.0
            and geo.longitude == 0.0
            and event_year is not None
            and event_year < 1890
        ):
            logger.info("🟠 0,0 coords pre-1890 → vague_state_pre1890")
            geo.status = "vague_state_pre1890"
        else:
            geo.status = geo.status or "ok"
        geo.timestamp = now
        return geo

    # 9. unresolved
    logger.error("❌ unresolved '%s'", raw_place)
    _log_unresolved_once(raw_place, "api_failed", tree_id)
    return LocationOut(
        raw_name=raw_place,
        normalized_name=norm,
        latitude=None,
        longitude=None,
        confidence_score=0.0,
        status="unresolved",
        source="api",
        timestamp=now,
    )

# alias for import-compat
log_unresolved_location = _log_unresolved_once
