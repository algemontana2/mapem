import os
import json
import time
import requests
import logging
from datetime import datetime
from urllib.parse import urlencode
from typing import Optional, Dict, Any
from backend.models.location_models import LocationOut

from pathlib import Path
from pydantic import BaseModel

from backend import models
from backend.utils.helpers import normalize_location, calculate_name_similarity

logger = logging.getLogger("backend.services.geocode")
logger.setLevel(logging.DEBUG)

# ─── Return model (Pydantic, exportable) ───────────

def classify_location_failure(raw_name):
    generic = {"mississippi", "usa", "tennessee", "louisiana", "unknown"}
    normalized = raw_name.lower().strip()
    if normalized in generic:
        return "too_vague", None
    if ", ," in raw_name or raw_name.startswith(",") or raw_name.endswith(","):
        return "format_error", None
    if "boliver" in normalized:
        return "typo_or_misspelling", "Bolivar County, Mississippi, USA"
    if "moorehead" in normalized:
        return "typo_or_misspelling", "Moorhead, Sunflower, Mississippi, USA"
    return "geocode_failed", None

DEFAULT_CACHE_PATH = Path(
    os.getenv(
        "GEOCODE_CACHE_FILE",
        Path(__file__).resolve().parent.parent / "geocode_cache.json",
    )
)


class Geocode:
    def __init__(
        self,
        api_key=None,
        cache_file: Optional[str | Path] = None,
        use_cache: bool = True,
        manual_fixes=None,
        historical_lookup=None,
    ):
        self.api_key = api_key
        self.cache_file = Path(cache_file or DEFAULT_CACHE_PATH)
        self.cache_enabled = use_cache
        self.cache = self._load_cache() if use_cache else {}
        self.manual_fixes = manual_fixes or {}
        self.historical_lookup = historical_lookup or {}

    def _load_cache(self):
        if self.cache_file.exists():
            try:
                with self.cache_file.open('r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning("⚠️ Cache file corrupted, starting fresh.")
                return {}
        return {}

    def _save_cache(self):
        if self.cache_enabled:
            with self.cache_file.open('w') as f:
                json.dump(self.cache, f, indent=2)

    def _normalize_key(self, place):
        norm = normalize_location(place.strip())
        if not norm:
            logger.warning(f"⚠️ normalize_location failed for '{place}' — using fallback")
            return place.strip().lower()
        return norm.lower()
    def _retry_request(self, func, *args, retries=2, backoff=1, **kwargs):
        for attempt in range(1, retries + 1):
            try:
                return func(*args, **kwargs)
            except requests.RequestException as e:
                logger.warning(f"⚠️ Request failed (attempt {attempt}/{retries}): {e}")
                time.sleep(backoff * attempt)
        return None

    def _google_geocode(self, location):
        base_url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"address": location, "key": self.api_key}
        url = f"{base_url}?{urlencode(params)}"
        def call():
            return requests.get(url, timeout=5)
        resp = self._retry_request(call)
        if not resp or resp.status_code != 200:
            logger.error(f"❌ Google geocode error: status {resp.status_code if resp else 'no response'}")
            return None, None, None, None
        data = resp.json()
        if data.get("status") != "OK" or not data.get("results"):
            logger.error(f"❌ Google geocode status={data.get('status')} for '{location}'")
            return None, None, None, None
        result = data['results'][0]
        loc = result['geometry']['location']
        location_type = result['geometry'].get('location_type', '')
        confidence = 1.0 if location_type.upper() == "ROOFTOP" else 0.75
        normalized_name = result.get('formatted_address', location)
        return loc['lat'], loc['lng'], normalized_name, confidence

    def _nominatim_geocode(self, location):
        base_url = "https://nominatim.openstreetmap.org/search"
        headers = {"User-Agent": "GenealogyMapper"}
        params = {"q": location, "format": "json", "limit": 1}
        def call(p):
            return requests.get(base_url, params=p, headers=headers, timeout=10)
        resp = self._retry_request(call, params)
        if resp and resp.status_code == 200:
            data = resp.json()
            if data:
                lat = float(data[0]['lat'])
                lon = float(data[0]['lon'])
                name = data[0]['display_name']
                return lat, lon, name, 0.8
        city = location.split(",")[0].strip()
        logger.info(f"🪃 Falling back to city-only geocode: '{city}'")
        params["q"] = city
        resp = self._retry_request(call, params)
        if resp and resp.status_code == 200:
            data = resp.json()
            if data:
                lat = float(data[0]['lat'])
                lon = float(data[0]['lon'])
                name = data[0]['display_name']
                return lat, lon, name, 0.7
        return None, None, None, None

    def get_or_create_location(self, session, location_name) -> Optional[LocationOut]:
        logger.debug(f"Geocode called with place='{location_name}'")

        if not location_name:
            logger.warning("⚠️ Empty location_name provided.")
            return None

        raw_name = location_name.strip().replace(",,", ",").replace("  ", " ")
        low = raw_name.lower()

        # ─── Vague blocklist FIRST ────────────────────
        if low in {"mississippi", "usa", "unknown"}:
            logger.info(f"🟫 Too vague to geocode: '{raw_name}'")
            return None

        # ─── Normalize key ────────────────────────────
        key = self._normalize_key(raw_name)
        if key is None:
            return None

        # ─── Manual override ──────────────────────────
        if key in self.manual_fixes:
            override = self.manual_fixes[key]
            logger.info(f"🟢 Manual override hit for '{raw_name}' → {override}")
            if override.get("lat") and override.get("lng"):
                return LocationOut(
                    raw_name=raw_name,
                    normalized_name=override.get("modern_equivalent", raw_name),
                    latitude=override["lat"],
                    longitude=override["lng"],
                    confidence_score=1.0,
                    status="manual",
                    source="manual",
                    timestamp=datetime.now().isoformat(),
                )
            return None

        # ─── Historical lookup ────────────────────────
        hist_key = f"sunflower:{low}"
        if hist_key in self.historical_lookup:
            hp = self.historical_lookup[hist_key]
            logger.info(f"🟡 Historical lookup hit for '{raw_name}' → {hp}")
            if hp.get("lat") and hp.get("lng"):
                return LocationOut(
                    raw_name=raw_name,
                    normalized_name=hp.get("modern_equivalent", raw_name),
                    latitude=hp["lat"],
                    longitude=hp["lng"],
                    confidence_score=1.0,
                    status="historical",
                    source="historical",
                    timestamp=datetime.now().isoformat(),
                )
            return None

        # Vague blocklist
        if raw_name.lower() in {"mississippi", "usa", "unknown"}:
            logger.info(f"🟫 Too vague to geocode: '{raw_name}'")
            return None

        # Cache hit
        if self.cache_enabled and key in self.cache:
            lat, lng, norm, conf = self.cache[key]
            if lat is not None and lng is not None:
                logger.info(f"🟦 Cache hit for '{raw_name}'")
                return LocationOut(
                    raw_name=raw_name,
                    normalized_name=norm,
                    latitude=lat,
                    longitude=lng,
                    confidence_score=float(conf or 0.0),
                    status="ok",
                    source="cache",
                    timestamp=datetime.now().isoformat(),
                )
            logger.warning(f"⚠️ Cache miss or incomplete for '{raw_name}'")
            return None

        # Fuzzy DB match
        if session:
            for loc in session.query(models.Location).all():
                compare_to = loc.normalized_name or loc.raw_name
                sim = calculate_name_similarity(compare_to, raw_name)
                if sim >= 90 and loc.latitude and loc.longitude:
                    logger.info(f"🟪 Fuzzy DB match for '{raw_name}' → {compare_to}")
                    return LocationOut(
                        raw_name=raw_name,
                        normalized_name=compare_to,
                        latitude=loc.latitude,
                        longitude=loc.longitude,
                        confidence_score=float(loc.confidence_score or 0.0),
                        status="ok",
                        source="db",
                        timestamp=datetime.now().isoformat(),
                    )

        # External geocode (Google first, then Nominatim fallback)
        lat, lng, norm, conf = None, None, None, None
        source = "nominatim"
        if self.api_key:
            lat, lng, norm, conf = self._google_geocode(raw_name)
            source = "google"
            if lat is None or lng is None:
                logger.warning(f"[Geocode] Google miss on '{raw_name}', switching to Nominatim")
                lat, lng, norm, conf = self._nominatim_geocode(raw_name)
                source = "nominatim"
        else:
            lat, lng, norm, conf = self._nominatim_geocode(raw_name)

        # Safe-check the returned normalized name
        norm = norm or raw_name  # if external returns None, default to raw_name
        norm = norm.strip()
        if not norm:
            logger.warning("⚠️ Geocode returned empty normalized name for '%s'", raw_name)
            norm = raw_name  # final fallback

        if lat is None or lng is None:
            cat, suggestion = classify_location_failure(raw_name)
            logger.warning(f"❌ FINAL FAIL: '{raw_name}' could not be geocoded (cat={cat}, suggestion={suggestion})")
            return None

        # Save cache on success
        if self.cache_enabled:
            self.cache[key] = (lat, lng, norm, conf)
            self._save_cache()

        logger.info(f"✅ Geocode SUCCESS: '{raw_name}' → ({lat}, {lng}) | {norm}")
        return LocationOut(
            raw_name=raw_name,
            normalized_name=norm,
            latitude=lat,
            longitude=lng,
            confidence_score=float(conf or 0.0),
            status="ok",
            source=source,
            timestamp=datetime.now().isoformat(),
        )

# Export the return model for your tests and routes
__all__ = ["Geocode", "LocationOut"]
