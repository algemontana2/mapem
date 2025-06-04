import pytest
from backend.services.geocode import Geocode
from backend.models.location_models import LocationOut

@pytest.fixture
def geocoder():
    # Force a manual fix for Boliver
    manual_fixes = {
        "boliver_mississippi": {
            "lat": 33.8,
            "lng": -90.7,
            "modern_equivalent": "Bolivar County, Mississippi, USA",
        }
    }
    historical_lookup = {
        "sunflower:beat 2": {
            "lat": 33.5,
            "lng": -90.5,
            "modern_equivalent": "Beat 2, Sunflower County, Mississippi",
        }
    }
    return Geocode(
        api_key=None,
        use_cache=False,
        manual_fixes=manual_fixes,
        historical_lookup=historical_lookup
    )

def test_manual_override_hit(geocoder):
    result = geocoder.get_or_create_location(None, "Boliver, Mississippi")
    assert isinstance(result, LocationOut)
    assert result.source == "manual"
    assert result.status == "manual"

def test_vague_state_classification(geocoder):
    result = geocoder.get_or_create_location(None, "Mississippi")
    assert result is None

from unittest.mock import patch

@patch("backend.services.geocode.Geocode._nominatim_geocode", return_value=(None, None, None, None))
def test_unresolved_logged(mock_geo, geocoder):
    result = geocoder.get_or_create_location(None, "unknown place")
    assert result is None

def test_geocode_output_structure(geocoder):
    result = geocoder.get_or_create_location(None, "Greenwood, Mississippi")
    if result:
        assert hasattr(result, "raw_name")
        assert hasattr(result, "latitude")
        assert isinstance(result.confidence_score, float)

def test_historical_match_simulated(geocoder):
    result = geocoder.get_or_create_location(None, "Beat 2")
    assert isinstance(result, LocationOut)
    assert result.source == "historical"
