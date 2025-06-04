import logging
import os
from sqlalchemy.orm import sessionmaker

from backend.celery_app import celery_app
from backend.db import get_engine
from backend.models.location import Location
from backend.services.geocode import Geocode

# Set up SQLAlchemy session factory
engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# ⛓️ Load API Key
API_KEY = os.getenv("GEOCODE_API_KEY")
if not API_KEY:
    logging.getLogger(__name__).warning(
        "⚠️ GEOCODE_API_KEY not found in env — geocoder will fallback only."
    )

# 🔧 Geocoder instance
geocoder = Geocode(api_key=API_KEY)

# 📟 Logger for visibility
logger = logging.getLogger("mapem.geocode_tasks")
logger.setLevel(logging.DEBUG)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def geocode_location_task(self, location_id: int):
    with SessionLocal() as session:
        try:
            loc = session.get(Location, location_id)
            if not loc:
                logger.warning(f"[GeocodeTask] Location id={location_id} not found.")
                return

            if loc.latitude is not None and loc.longitude is not None:
                logger.info(f"[GeocodeTask] id={location_id} already geocoded, skipping.")
                return

            # 🔍 Attempt resolution
            result = geocoder.get_or_create_location(None, loc.raw_name)
            if result is None:
                logger.warning(
                    f"[GeocodeTask] Geocoder returned no data for '{loc.raw_name}'"
                )
                return

            # ✅ Apply fields
            loc.latitude = result.latitude
            loc.longitude = result.longitude
            loc.normalized_name = result.normalized_name
            loc.confidence_score = result.confidence_score
            loc.status = result.status
            loc.source = result.source
            loc.geocoded_at = getattr(result, "geocoded_at", None)
            loc.geocoded_by = getattr(result, "geocoded_by", None)

            session.commit()
            logger.info(f"[GeocodeTask] ✅ id={location_id} -> ({loc.latitude}, {loc.longitude})")

        except Exception as err:
            session.rollback()
            logger.exception(f"[GeocodeTask] ❌ Error on id={location_id}, retrying…")
            raise self.retry(exc=err)
