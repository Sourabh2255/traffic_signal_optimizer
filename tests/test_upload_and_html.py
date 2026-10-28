"""
Test script to verify frontend dropzone structure and backend upload API using Flask test_client.
"""

import os
import sys
import io
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app

def test_frontend_html():
    print("[1] Testing Frontend HTML dropzone & input elements...")
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    html = resp.data.decode("utf-8")

    for road in ["north", "east", "south", "west"]:
        assert f'id="file-{road}"' in html, f"file-{road} input missing"
        assert f'for="file-{road}"' in html, f"label for file-{road} missing"
        assert f'id="dropzone-{road}"' in html, f"dropzone-{road} missing"

    assert 'id="file-siren"' in html, "file-siren input missing"
    assert 'for="file-siren"' in html, "label for file-siren missing"
    assert 'id="dropzone-audio"' in html, "dropzone-audio missing"

    print("  -> All 4 road dropzones & siren audio dropzone use correct semantic label-for architecture!")

def test_api_upload_simulation():
    print("[2] Testing /api/analyze with 4 sample images & siren audio...")
    client = app.test_client()
    demo_resp = client.get("/api/demo_samples")
    assert demo_resp.status_code == 200
    demo_meta = demo_resp.get_json()
    assert demo_meta["success"], "Failed to get demo samples"
    
    em_demo = demo_meta["emergency_demo"]
    data = {}

    # Roads
    for road in ["north", "east", "south", "west"]:
        img_url = em_demo[road]
        img_resp = client.get(img_url)
        assert img_resp.status_code == 200, f"Failed to fetch {img_url}"
        data[road] = (io.BytesIO(img_resp.data), f"{road}.jpg")

    # Siren audio
    siren_url = em_demo["siren_audio"]
    siren_resp = client.get(siren_url)
    assert siren_resp.status_code == 200, f"Failed to fetch {siren_url}"
    data["siren_audio"] = (io.BytesIO(siren_resp.data), "siren.wav")
    data["siren_version"] = "v2"

    resp = client.post(
        "/api/analyze",
        data=data,
        content_type="multipart/form-data"
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
    result = resp.get_json()
    assert result["success"] is True, "Analysis returned success=False"
    print("  -> /api/analyze successfully processed 4 uploaded images + siren WAV!")
    print(f"  -> Cycle Number: {result['data']['cycle_number']}")
    print(f"  -> Emergency Active: {result['data']['emergency_active']}")
    print(f"  -> Emergency Road: {result['data']['emergency_road']}")
    print(f"  -> Siren Detected: {result['data']['siren_analysis']['is_siren']}")

if __name__ == "__main__":
    test_frontend_html()
    test_api_upload_simulation()
    print("\nALL UPLOAD VERIFICATION TESTS PASSED SUCCESSFULLY!")

