import os
import pytest
from backend.services.geocode import Geocode

def test_geocode_single_location():
    """✅ Test Geocode().get_or_create_location() directly."""
    geocoder = Geocode()
    result = geocoder.get_or_create_location(None, "Chicago, Illinois, USA")
    assert result is not None
    assert result.latitude is not None
    assert result.longitude is not None
    assert hasattr(result, "confidence_label")
    assert hasattr(result, "confidence_score")


def test_list_trees(client):
    """✅ Check if /api/trees/ returns 200 and list."""
    print("💥 BEFORE request")
    resp = client.get("/api/trees/")
    print("📬 AFTER request")
    print("📦 STATUS:", resp.status_code)

    try:
        content_type = resp.headers.get("Content-Type")
        print("🧪 Content-Type:", content_type)

        if "application/json" in content_type:
            data = resp.get_json()
            print("📦 JSON:", data)
            assert isinstance(data.get("trees"), list)
        else:
            print("❌ Not JSON, raw body:")
            print(resp.data.decode("utf-8"))
            assert False, "Non-JSON response returned"

    except Exception as e:
        print("❌ Failed to parse response:", e)
        print("🧾 Raw Body:", resp.data.decode("utf-8"))
        assert False, "Failed to fetch valid /api/trees/ response"
