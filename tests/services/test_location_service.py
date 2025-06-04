import json
import pytest
from datetime import datetime, timezone
from pathlib import Path
import os  # ← needed by test_override_applies_before_geocoder


from backend.services.location_service import LocationService
from backend.models.location_models import LocationOut


def fake_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────────
#  TEST DATA SET-UP
# ─────────────────────────────
@pytest.fixture(autouse=True)
def patch_data_files(tmp_path: Path, monkeypatch):
    """
    Create throw-away manual & historical data the real service loader can see.
    IMPORTANT: keys must be  *lat* / *lng*  because LocationService
    uses manual_hit.get("lat") / .get("lng")
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # manual overrides
    (data_dir / "manual_place_fixes.json").write_text(json.dumps({
        "test_city_tc": {
            "lat": 1.1, "lng": 2.2,
            "status": "manual", "source": "manual"
        }
    }))

    # historical look-ups
    hist_dir = data_dir / "historical_places"
    hist_dir.mkdir()
    (data_dir / "historical_places/delta.json").write_text(json.dumps({
        "oldtown_ot": {
            "lat": 3.3, "lng": 4.4,
            "status": "historical", "source": "history"
        }
    }))

    # Make LocationService load from this tmp directory
    monkeypatch.setenv("MAPEM_DATA_DIR", str(data_dir))


# ─────────────────────────────
#  SERVICE FIXTURE
# ─────────────────────────────
@pytest.fixture
def service(monkeypatch) -> LocationService:
    # --- dummy geocoder ----------------------------------------------------
    class DummyGeocode:
        def get_or_create_location(self, _raw, normalized_name):
            """
            Return fake geocode hits only for the names we care about.
            Anything else returns None so the code drops to the fallback path.
            """
            if normalized_name == "realcity_rc":
                return LocationOut(
                    raw_name="RealCity, RC",
                    normalized_name="realcity_rc",
                    latitude=5.5,
                    longitude=6.6,
                    confidence_score=0.9,
                    status="ok",
                    source="external",
                    timestamp=fake_timestamp(),
                )
            if normalized_name == "mississippi":
                return LocationOut(
                    raw_name="Mississippi",
                    normalized_name="mississippi",
                    latitude=0,
                    longitude=0,
                    confidence_score=0.5,
                    status="vague_state_pre1890",
                    source="vague",
                    timestamp=fake_timestamp(),
                )
            return None

    monkeypatch.setattr(
        "backend.services.location_service.Geocode",
        lambda *a, **kw: DummyGeocode(),
    )

    # --- stub process_location --------------------------------------------
    def mock_process_location(raw_place, event_year, source_tag="", tree_id=None):
        name = (raw_place or "").lower()
        ts = fake_timestamp()

        if "test city" in name:
            return LocationOut(
                raw_name=raw_place,
                normalized_name="test_city_tc",
                latitude=1.1,
                longitude=2.2,
                confidence_score=1.0,
                status="manual",
                source="manual",
                timestamp=ts,
            )
        if "oldtown" in name:
            return LocationOut(
                raw_name=raw_place,
                normalized_name="oldtown_ot",
                latitude=3.3,
                longitude=4.4,
                confidence_score=1.0,
                status="historical",
                source="history",
                timestamp=ts,
            )
        if "realcity" in name:
            # Let the geocoder supply lat/lng; only return the normalised name
            return LocationOut(
                raw_name=raw_place,
                normalized_name="realcity_rc",
                latitude=None,
                longitude=None,
                confidence_score=0.0,
                status="needs_geocode",
                source="raw",
                timestamp=ts,
            )
        if "mississippi" in name and event_year < 1890:
            return LocationOut(
                raw_name=raw_place,
                normalized_name="mississippi",
                latitude=0,
                longitude=0,
                confidence_score=0.5,
                status="vague_state_pre1890",
                source="vague",
                timestamp=ts,
            )
        if not raw_place or not raw_place.strip():
            return LocationOut(
                raw_name="",
                normalized_name="",
                latitude=None,
                longitude=None,
                confidence_score=0.0,
                status="empty",
                source="none",
                timestamp=ts,
            )
        # default unresolved
        return LocationOut(
            raw_name=raw_place,
            normalized_name="",
            latitude=None,
            longitude=None,
            confidence_score=0.0,
            status="unresolved",
            source="none",
            timestamp=ts,
        )

    monkeypatch.setattr(
        "backend.services.location_service.process_location",
        mock_process_location,
    )

    # --- spin up the real service (it will read our tmp data) -------------
    return LocationService(api_key="DUMMY")


# ─────────────────────────────
#  TESTS
# ─────────────────────────────
def test_manual_override(service):
    out = service.resolve_location("Test City, TC", event_year=1950)
    assert out.latitude == 1.1
    assert out.status == "manual"


def test_historical_lookup(service):
    out = service.resolve_location("OldTown, OT", event_year=1900)
    assert out.latitude == 3.3
    assert out.status == "historical"   # comes through the same override path


def test_external_geocode_success(service):
    out = service.resolve_location("RealCity, RC", event_year=2000)
    assert out.latitude == 5.5
    assert out.status == "ok"
    assert out.source == "external"


def test_vague_state_pre1890(service):
    out = service.resolve_location("Mississippi", event_year=1880)
    assert out.status.startswith("vague_state")
    assert out.latitude == 0


def test_unresolved_fallback(service):
    out = service.resolve_location("NoWhereLand", event_year=2020)
    assert out.status == "unresolved"
    assert out.latitude is None


def test_blank_input(service):
    out = service.resolve_location("", event_year=1900)
    assert out.status == "empty"
    assert out.latitude is None


def test_nonsense_input(service):
    out = service.resolve_location("(*&@#Y$(*&Y$)", event_year=2000)
    assert out.status == "unresolved"
    assert out.latitude is None

def test_loader_respects_env_dir(tmp_path):
    """If we point MAPEM_DATA_DIR at tmp_path the service should load from it."""
    (tmp_path / "manual_place_fixes.json").write_text(
        json.dumps({"sample_town": {"lat": 9.9, "lng": 8.8}})
    )
    service = LocationService(data_dir=str(tmp_path))
    assert "sample_town" in service.manual_fixes           # key is normalized later


def test_override_applies_before_geocoder(service, monkeypatch):
    """
    Ensure that an override short-circuits the external geocoder.
    We monkey-patch DummyGeocode to raise if it’s called for 'test_city_tc'.
    """
    class BoomGeocode:
        def get_or_create_location(self, *_a, **_k):
            raise RuntimeError("should not be reached")

    monkeypatch.setattr("backend.services.location_service.Geocode", lambda *a, **k: BoomGeocode())

    svc = LocationService(api_key="X", data_dir=os.getenv("MAPEM_DATA_DIR"))
    out = svc.resolve_location("Test City, TC", event_year=2000)
    assert out.latitude == 1.1 and out.status.startswith("manual")
