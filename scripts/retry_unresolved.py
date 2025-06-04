import os
import sys
import json
import logging
from sqlalchemy.orm import sessionmaker
from backend.db import get_engine
from backend.models.location import Location
from backend.services.geocode import Geocode

# ───────────────────────────────────────────────
# Setup path + logging
# ───────────────────────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(PROJECT_ROOT)

UNRESOLVED_PATH = os.path.join(PROJECT_ROOT, "backend", "data", "unresolved_locations.json")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger("retry_unresolved")

# ───────────────────────────────────────────────
# Load unresolved from JSON
# ───────────────────────────────────────────────
def load_unresolved_locations():
    if not os.path.exists(UNRESOLVED_PATH):
        log.error("❌ unresolved_locations.json not found.")
        return []

    with open(UNRESOLVED_PATH, "r") as f:
        data = json.load(f)

    log.info(f"📦 Loaded {len(data)} unresolved entries from JSON")
    return data

# ───────────────────────────────────────────────
# Main Retry Script
# ───────────────────────────────────────────────
def main():
    log.info("🚀 Starting unresolved location retry script")
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    session = Session()

    unresolved = load_unresolved_locations()
    if not unresolved:
        log.warning("🟡 No unresolved entries found. Exiting early.")
        return

    geocoder = Geocode(api_key=os.getenv("GEOCODE_API_KEY"))
    retried = 0
    skipped = 0

    for idx, entry in enumerate(unresolved, start=1):
        raw = entry.get("raw_name") or entry.get("place")
        if not raw:
            log.warning(f"⚠️ Entry #{idx} missing 'raw_name'. Skipping: {entry}")
            continue

        log.info(f"\n🧩 ({idx}/{len(unresolved)}) Retrying: {raw}")
        match = session.query(Location).filter_by(raw_name=raw).first()

        if not match:
            log.warning(f"🔍 No DB match found for raw_name='{raw}'")
            skipped += 1
            continue

        log.debug(f"🔎 Existing DB location → ID: {match.id}, Lat: {match.latitude}, Lng: {match.longitude}, Status: {match.status}")

        try:
            result = geocoder.get_or_create_location(session, raw)
        except Exception as e:
            log.error(f"💥 Geocoder crashed for '{raw}': {e}")
            skipped += 1
            continue

        if result and result.latitude is not None:
            log.info(
                f"✅ Geocode success: {result.raw_name} → ({result.latitude}, {result.longitude})"
            )
            match.latitude = result.latitude
            match.longitude = result.longitude
            match.status = getattr(result, "status", "geocoded")
            session.add(match)
            retried += 1
        else:
            log.error(f"❌ Still unresolved: {raw}")
            skipped += 1

    session.commit()
    log.info("\n🏁 Finished retry process.")
    log.info(f"🔄 Total retried + updated: {retried}")
    log.info(f"⏭️  Skipped (missing or unresolved): {skipped}")
    log.info(f"📊 Total attempted: {retried + skipped}")

if __name__ == "__main__":
    main()
