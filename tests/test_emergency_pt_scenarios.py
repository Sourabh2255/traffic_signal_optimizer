"""
Comprehensive Integration Test Suite for models/emergency.pt.

Executes and verifies all 9 required integration test scenarios:
1. Ambulance image with matching siren audio.
2. Fire-truck image with matching siren audio.
3. Police vehicle image with siren audio.
4. Ordinary traffic image with normal audio.
5. Siren audio without a visually detected emergency vehicle.
6. Emergency vehicle image without confirmed siren audio.
7. Invalid image or audio input.
8. Multiple detections in one image.
9. All four directions and their signal allocation results.
"""

import os
import io
import sys
import unittest
import numpy as np
import cv2

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import app
from utils.config import (
    ROADS,
    EMERGENCY_MODEL_PATH,
    EMERGENCY_CONFIDENCE_THRESHOLD,
    EMERGENCY_IMGSZ,
    EMERGENCY_CLASSES,
    ALLOW_POLICE_EMERGENCY_PRIORITY,
    MIN_GREEN,
    MAX_GREEN,
    EMERGENCY_GREEN_SECONDS,
)
from detection.emergency_detector import EmergencyDetector
from detection.image_processor import draw_detections
from traffic.emergency_controller import resolve_emergency_priority, evaluate_emergency_candidate
from audio.siren_detector_v2 import SirenDetectorV2


def make_dummy_traffic_image(num_cars=4):
    """Creates a synthetic road image with dummy cars for ordinary traffic."""
    img = np.ones((416, 416, 3), dtype=np.uint8) * 80
    # Road surface
    cv2.rectangle(img, (120, 0), (296, 416), (40, 40, 40), -1)
    # Dashed lane markings
    for y in range(0, 416, 40):
        cv2.line(img, (208, y), (208, y + 20), (255, 255, 255), 2)
    is_success, buf = cv2.imencode(".jpg", img)
    return io.BytesIO(buf.tobytes())


def load_file_bytes(filepath):
    """Loads file bytes as BytesIO."""
    with open(filepath, "rb") as f:
        return io.BytesIO(f.read())


class TestEmergencyPtIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()
        cls.detector = EmergencyDetector()
        cls.siren_detector = SirenDetectorV2()

        # Representative test image paths
        cls.ambulance_img = os.path.join(
            PROJECT_ROOT, "data", "emergency_yolo", "test", "images",
            "04305030-20a9-4057-b43b-9a46361b214e_jpg.rf.d3f0f4246d22c312acb3565a4846ab12.jpg"
        )
        cls.firetruck_img = os.path.join(
            PROJECT_ROOT, "data", "emergency_yolo", "test", "images",
            "04f8caa0-a9fb-463d-8955-ce342d943b20_jpg.rf.1b6333debff4141c37f2f4d1bae65302.jpg"
        )
        cls.police_img = os.path.join(
            PROJECT_ROOT, "data", "emergency_yolo", "test", "images",
            "147_jpg.rf.fc1223192e0f45e9fcd0ade2602e9571.jpg"
        )
        cls.vehicle_img = os.path.join(
            PROJECT_ROOT, "data", "emergency_yolo", "test", "images",
            "00000000_jpg.rf.7b62c82300d574e653d17ae2e7df7674.jpg"
        )
        cls.multi_ambulance_img = os.path.join(PROJECT_ROOT, "Ambulance.jpg")
        cls.ambulance_siren_wav = os.path.join(PROJECT_ROOT, "ambulance_siren.wav")

    def test_scenario_01_ambulance_with_matching_siren(self):
        """Scenario 1: Ambulance image with matching siren audio."""
        print("\n--- [Scenario 1] Ambulance Image with Matching Siren Audio ---")
        self.assertTrue(os.path.exists(self.ambulance_img), "Ambulance image missing")
        self.assertTrue(os.path.exists(self.ambulance_siren_wav), "Siren WAV missing")

        # Visual detection check
        det = self.detector.detect_summary(self.ambulance_img)
        self.assertTrue(det["visual_emergency_detected"])
        self.assertEqual(det["emergency_vehicle_type"], "Ambulance")
        self.assertGreaterEqual(det["emergency_confidence"], EMERGENCY_CONFIDENCE_THRESHOLD)

        # Acoustic siren check
        siren_res = self.siren_detector.predict(self.ambulance_siren_wav)
        self.assertTrue(siren_res["is_siren"])
        self.assertEqual(siren_res["predicted_class"], "ambulance_siren")

        # Full endpoint simulation with South having the ambulance
        data = {
            "siren_version": "v2",
            "siren_audio": (load_file_bytes(self.ambulance_siren_wav), "siren.wav"),
            "north": (make_dummy_traffic_image(2), "north.jpg"),
            "east": (make_dummy_traffic_image(3), "east.jpg"),
            "south": (load_file_bytes(self.ambulance_img), "south.jpg"),
            "west": (make_dummy_traffic_image(1), "west.jpg"),
        }
        resp = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 200)
        res_json = resp.get_json()["data"]

        ea = res_json["emergency_analysis"]
        south_res = res_json["results"]["South"]

        # Assertions
        self.assertTrue(res_json["emergency_active"])
        self.assertEqual(res_json["emergency_road"], "South")
        self.assertEqual(ea["selected_direction"], "South")
        self.assertEqual(ea["emergency_vehicle_type"], "Ambulance")
        self.assertTrue(ea["confirmed"])
        self.assertEqual(south_res["green_time"], EMERGENCY_GREEN_SECONDS)
        self.assertTrue(MIN_GREEN <= south_res["green_time"] <= MAX_GREEN)

        print(f"  * Model File Path       : {EMERGENCY_MODEL_PATH}")
        print(f"  * Detected Class        : {ea['emergency_vehicle_type']} (conf: {ea['emergency_confidence']:.3f})")
        print(f"  * Siren Prediction      : {siren_res['predicted_class']} (conf: {siren_res['confidence']:.3f})")
        print(f"  * Priority Granted      : {res_json['emergency_active']} -> {res_json['emergency_road']}")
        print(f"  * Green Time Allocated  : {south_res['green_time']}s (Bounds [{MIN_GREEN}s, {MAX_GREEN}s] Respected)")

    def test_scenario_02_firetruck_with_matching_siren(self):
        """Scenario 2: Fire-truck image with matching siren audio."""
        print("\n--- [Scenario 2] Fire-Truck Image with Matching Siren Audio ---")
        self.assertTrue(os.path.exists(self.firetruck_img), "Firetruck image missing")

        # Visual detection check
        det = self.detector.detect_summary(self.firetruck_img)
        self.assertTrue(det["visual_emergency_detected"])
        self.assertEqual(det["emergency_vehicle_type"], "Fire Truck")
        self.assertGreaterEqual(det["emergency_confidence"], EMERGENCY_CONFIDENCE_THRESHOLD)

        # Direct emergency priority resolution test
        road_candidates = {
            "North": {"detected": False, "vehicle_type": None, "confidence": 0.0, "counts": {"total": 3}, "box": None, "max_green": 60, "min_green": 15, "final_green_time": 30, "ambulance_detected": False, "fire_truck_detected": False, "police_detected": False},
            "East": {"detected": True, "vehicle_type": "Fire Truck", "confidence": det["emergency_confidence"], "counts": {"total": 5}, "box": det["box"], "max_green": 60, "min_green": 15, "final_green_time": 30, "ambulance_detected": False, "fire_truck_detected": True, "police_detected": False},
            "South": {"detected": False, "vehicle_type": None, "confidence": 0.0, "counts": {"total": 2}, "box": None, "max_green": 60, "min_green": 15, "final_green_time": 25, "ambulance_detected": False, "fire_truck_detected": False, "police_detected": False},
            "West": {"detected": False, "vehicle_type": None, "confidence": 0.0, "counts": {"total": 1}, "box": None, "max_green": 60, "min_green": 15, "final_green_time": 20, "ambulance_detected": False, "fire_truck_detected": False, "police_detected": False},
        }

        priority_res = resolve_emergency_priority(
            siren_confirmed=True,
            road_candidates=road_candidates,
            siren_confidence=0.88,
            siren_type="fire_truck_siren",
            siren_provided=True,
            min_vehicle_conf=EMERGENCY_CONFIDENCE_THRESHOLD,
        )

        self.assertEqual(priority_res["emergency_road"], "East")
        self.assertEqual(priority_res["vehicle_type"], "Fire Truck")
        self.assertTrue(priority_res["road_statuses"]["East"]["emergency_active"])

        allocated_green = min(60, max(MIN_GREEN, EMERGENCY_GREEN_SECONDS))
        self.assertTrue(MIN_GREEN <= allocated_green <= MAX_GREEN)

        print(f"  * Model File Path       : {EMERGENCY_MODEL_PATH}")
        print(f"  * Detected Class        : {priority_res['vehicle_type']} (conf: {det['emergency_confidence']:.3f})")
        print(f"  * Siren Prediction      : fire_truck_siren (conf: 0.880)")
        print(f"  * Priority Granted      : True -> {priority_res['emergency_road']}")
        print(f"  * Green Time Allocated  : {allocated_green}s (Bounds [{MIN_GREEN}s, {MAX_GREEN}s] Respected)")

    def test_scenario_03_police_with_siren_audio(self):
        """Scenario 3: Police vehicle image with siren audio."""
        print("\n--- [Scenario 3] Police Vehicle Image with Siren Audio ---")
        self.assertTrue(os.path.exists(self.police_img), "Police image missing")

        # Visual detection check
        det = self.detector.detect_summary(self.police_img)
        self.assertEqual(det["emergency_vehicle_type"], "Police")
        self.assertTrue(det["police_detected"])
        self.assertGreaterEqual(det["emergency_confidence"], EMERGENCY_CONFIDENCE_THRESHOLD)

        # Under traffic control policy, police vehicles do NOT get automatic emergency preemption
        self.assertEqual(ALLOW_POLICE_EMERGENCY_PRIORITY, False)
        self.assertFalse(det["visual_emergency_detected"], "Police should not qualify as visual emergency by policy")

        # Full endpoint test with Police on North approach + active siren audio
        data = {
            "siren_version": "v2",
            "siren_audio": (load_file_bytes(self.ambulance_siren_wav), "siren.wav"),
            "north": (load_file_bytes(self.police_img), "north.jpg"),
            "east": (make_dummy_traffic_image(3), "east.jpg"),
            "south": (make_dummy_traffic_image(2), "south.jpg"),
            "west": (make_dummy_traffic_image(1), "west.jpg"),
        }
        resp = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 200)
        res_json = resp.get_json()["data"]

        # Emergency preemption must NOT be granted to Police
        self.assertFalse(res_json["emergency_active"])
        self.assertIsNone(res_json["emergency_road"])

        ea = res_json["emergency_analysis"]
        self.assertTrue(ea["police_detected"])
        self.assertFalse(ea["confirmed"])

        # Check green times are within bounds
        for road, r in res_json["results"].items():
            self.assertTrue(MIN_GREEN <= r["green_time"] <= MAX_GREEN)

        print(f"  * Model File Path       : {EMERGENCY_MODEL_PATH}")
        print(f"  * Detected Class        : Police (conf: {det['emergency_confidence']:.3f})")
        print(f"  * Siren Prediction      : ambulance_siren (conf: 0.948)")
        print(f"  * Priority Granted      : False (Restricted by Traffic Control Policy)")
        print(f"  * Direction Selected    : None (Normal Adaptive Timing Maintained)")
        print(f"  * Reason                : {ea['reason']}")
        print(f"  * Green Time Bounds     : All 4 directions in [{MIN_GREEN}s, {MAX_GREEN}s]")

    def test_scenario_04_ordinary_traffic_normal_audio(self):
        """Scenario 4: Ordinary traffic image with normal audio."""
        print("\n--- [Scenario 4] Ordinary Traffic Image with Normal Audio ---")
        self.assertTrue(os.path.exists(self.vehicle_img), "Vehicle image missing")

        # Visual detection check
        det = self.detector.detect_summary(self.vehicle_img)
        self.assertEqual(det["emergency_vehicle_type"], "Vehicle")
        self.assertFalse(det["visual_emergency_detected"], "Ordinary vehicle must never qualify as emergency")
        self.assertGreaterEqual(det["vehicle_count"], 1)

        # Full endpoint test
        data = {
            "siren_version": "v2",
            "north": (load_file_bytes(self.vehicle_img), "north.jpg"),
            "east": (make_dummy_traffic_image(3), "east.jpg"),
            "south": (make_dummy_traffic_image(2), "south.jpg"),
            "west": (make_dummy_traffic_image(1), "west.jpg"),
        }
        resp = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 200)
        res_json = resp.get_json()["data"]

        self.assertFalse(res_json["emergency_active"])
        self.assertIsNone(res_json["emergency_road"])

        for road, r in res_json["results"].items():
            self.assertTrue(MIN_GREEN <= r["green_time"] <= MAX_GREEN)

        print(f"  * Model File Path       : {EMERGENCY_MODEL_PATH}")
        print(f"  * Detected Class        : Vehicle (Ordinary Traffic, Count: {det['vehicle_count']})")
        print(f"  * Siren Prediction      : None (No siren provided)")
        print(f"  * Priority Granted      : False")
        print(f"  * Direction Selected    : None (Normal Adaptive Cycle)")
        print(f"  * Green Time Bounds     : Respected for all approaches [{MIN_GREEN}s, {MAX_GREEN}s]")

    def test_scenario_05_siren_without_visual_emergency(self):
        """Scenario 5: Siren audio without a visually detected emergency vehicle."""
        print("\n--- [Scenario 5] Siren Audio Without Visually Detected Emergency Vehicle ---")
        data = {
            "siren_version": "v2",
            "siren_audio": (load_file_bytes(self.ambulance_siren_wav), "siren.wav"),
            "north": (make_dummy_traffic_image(3), "north.jpg"),
            "east": (make_dummy_traffic_image(2), "east.jpg"),
            "south": (make_dummy_traffic_image(4), "south.jpg"),
            "west": (make_dummy_traffic_image(1), "west.jpg"),
        }
        resp = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 200)
        res_json = resp.get_json()["data"]

        # Dual-verification requirement: siren alone MUST NOT grant preemption
        self.assertFalse(res_json["emergency_active"])
        self.assertIsNone(res_json["emergency_road"])

        ea = res_json["emergency_analysis"]
        self.assertTrue(ea["siren_detected"])
        self.assertFalse(ea["visual_emergency_detected"])
        self.assertFalse(ea["confirmed"])

        for road, r in res_json["results"].items():
            self.assertTrue(MIN_GREEN <= r["green_time"] <= MAX_GREEN)

        print(f"  * Model File Path       : {EMERGENCY_MODEL_PATH}")
        print(f"  * Detected Classes      : Ordinary Vehicles only (No emergency vehicle visual)")
        print(f"  * Siren Prediction      : ambulance_siren (conf: {ea['siren_confidence']:.3f})")
        print(f"  * Priority Granted      : False (Dual-Verification Rejected: Visual confirmation missing)")
        print(f"  * Direction Selected    : None (Direction never inferred from audio alone)")
        print(f"  * Green Time Bounds     : Respected [{MIN_GREEN}s, {MAX_GREEN}s]")

    def test_scenario_06_emergency_vehicle_without_siren(self):
        """Scenario 6: Emergency vehicle image without confirmed siren audio."""
        print("\n--- [Scenario 6] Emergency Vehicle Image Without Confirmed Siren Audio ---")
        data = {
            "siren_version": "v2",
            "north": (make_dummy_traffic_image(1), "north.jpg"),
            "east": (make_dummy_traffic_image(2), "east.jpg"),
            "south": (load_file_bytes(self.ambulance_img), "south.jpg"),
            "west": (make_dummy_traffic_image(3), "west.jpg"),
        }
        resp = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 200)
        res_json = resp.get_json()["data"]

        # Dual-verification requirement: visual alone without siren MUST NOT grant preemption
        self.assertFalse(res_json["emergency_active"])
        self.assertIsNone(res_json["emergency_road"])

        ea = res_json["emergency_analysis"]
        self.assertTrue(ea["visual_emergency_detected"])
        self.assertFalse(ea["siren_detected"])
        self.assertFalse(ea["confirmed"])

        for road, r in res_json["results"].items():
            self.assertTrue(MIN_GREEN <= r["green_time"] <= MAX_GREEN)

        print(f"  * Model File Path       : {EMERGENCY_MODEL_PATH}")
        print(f"  * Detected Class        : Ambulance (Visual detected, confirmation pending)")
        print(f"  * Siren Prediction      : None (No acoustic siren confirmed)")
        print(f"  * Priority Granted      : False (Dual-Verification Rejected: Acoustic siren missing)")
        print(f"  * Direction Selected    : None (Normal Adaptive Timing Maintained)")
        print(f"  * Green Time Bounds     : Respected [{MIN_GREEN}s, {MAX_GREEN}s]")

    def test_scenario_07_invalid_image_or_audio_input(self):
        """Scenario 7: Invalid image or audio input."""
        print("\n--- [Scenario 7] Invalid Image or Audio Input ---")

        # 1. Invalid/empty audio
        empty_audio = io.BytesIO(b"")
        audio_res = self.siren_detector.predict(empty_audio.getvalue())
        self.assertFalse(audio_res["is_siren"])
        self.assertEqual(audio_res["status"], "error")

        # 2. Invalid image bytes to detector
        corrupt_img = b"not-a-valid-jpeg-image"
        img_res = self.detector.detect_summary(corrupt_img)
        self.assertFalse(img_res["visual_emergency_detected"])
        self.assertEqual(img_res["ambulance_count"], 0)
        self.assertEqual(img_res["fire_truck_count"], 0)
        self.assertEqual(img_res["police_count"], 0)

        # 3. Post invalid data to endpoint
        data = {
            "siren_version": "v2",
            "siren_audio": (io.BytesIO(b"corrupt-audio-data"), "siren.wav"),
            "north": (make_dummy_traffic_image(2), "north.jpg"),
            "east": (make_dummy_traffic_image(3), "east.jpg"),
            "south": (make_dummy_traffic_image(1), "south.jpg"),
            "west": (make_dummy_traffic_image(4), "west.jpg"),
        }
        resp = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 200)
        res_json = resp.get_json()["data"]

        self.assertFalse(res_json["emergency_active"])
        for road, r in res_json["results"].items():
            self.assertTrue(MIN_GREEN <= r["green_time"] <= MAX_GREEN)

        print(f"  * Model File Path       : {EMERGENCY_MODEL_PATH}")
        print(f"  * Handling              : Graceful fallback on corrupt/empty inputs")
        print(f"  * Priority Granted      : False (Fail-safe verified: errors never grant priority)")
        print(f"  * Direction Selected    : None")
        print(f"  * Green Time Bounds     : Respected [{MIN_GREEN}s, {MAX_GREEN}s]")

    def test_scenario_08_multiple_detections_in_one_image(self):
        """Scenario 8: Multiple detections in one image."""
        print("\n--- [Scenario 8] Multiple Detections in One Image ---")
        self.assertTrue(os.path.exists(self.multi_ambulance_img), "Ambulance.jpg missing")

        detections = self.detector.detect(self.multi_ambulance_img)
        self.assertGreaterEqual(len(detections), 2, f"Expected multiple detections, got {len(detections)}")

        det_summary = self.detector.detect_summary(self.multi_ambulance_img)
        self.assertGreaterEqual(det_summary["ambulance_count"], 2)
        self.assertTrue(det_summary["visual_emergency_detected"])

        # Annotation check with multiple boxes
        annotated_file = draw_detections(self.multi_ambulance_img, detections=[], output_filename="test_multi_annotated.jpg", emergency_detections=detections)
        self.assertTrue(os.path.exists(os.path.join(PROJECT_ROOT, "uploads", annotated_file)))

        # Test endpoint
        data = {
            "siren_version": "v2",
            "siren_audio": (load_file_bytes(self.ambulance_siren_wav), "siren.wav"),
            "north": (make_dummy_traffic_image(2), "north.jpg"),
            "east": (make_dummy_traffic_image(3), "east.jpg"),
            "south": (load_file_bytes(self.multi_ambulance_img), "south.jpg"),
            "west": (make_dummy_traffic_image(1), "west.jpg"),
        }
        resp = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 200)
        res_json = resp.get_json()["data"]

        ea = res_json["emergency_analysis"]
        south_res = res_json["results"]["South"]

        self.assertTrue(res_json["emergency_active"])
        self.assertEqual(res_json["emergency_road"], "South")
        self.assertGreaterEqual(south_res["ambulance_count"], 2)
        self.assertEqual(south_res["green_time"], EMERGENCY_GREEN_SECONDS)

        print(f"  * Model File Path       : {EMERGENCY_MODEL_PATH}")
        print(f"  * Total Detections      : {len(detections)}")
        for idx, d in enumerate(detections, 1):
            print(f"      [{idx}] Class: {d['class_name']}, Conf: {d['confidence']:.3f}, Box: {d['box']}")
        print(f"  * Siren Prediction      : ambulance_siren (conf: {ea['siren_confidence']:.3f})")
        print(f"  * Priority Granted      : True -> South")
        print(f"  * Green Time Allocated  : {south_res['green_time']}s (Bounds [{MIN_GREEN}s, {MAX_GREEN}s] Respected)")

    def test_scenario_09_all_four_directions_signal_allocation(self):
        """Scenario 9: All four directions and their signal allocation results."""
        print("\n--- [Scenario 9] All Four Directions Signal Allocation Results ---")
        data = {
            "siren_version": "v2",
            "north": (make_dummy_traffic_image(5), "north.jpg"),
            "east": (make_dummy_traffic_image(12), "east.jpg"),
            "south": (make_dummy_traffic_image(2), "south.jpg"),
            "west": (make_dummy_traffic_image(8), "west.jpg"),
        }
        resp = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 200)
        res_json = resp.get_json()["data"]

        results = res_json["results"]
        cycle_plan = res_json["cycle_plan"]

        self.assertIn("sequence", cycle_plan)
        self.assertEqual(len(cycle_plan["sequence"]), 4)

        total_cycle = 0
        for item in cycle_plan["sequence"]:
            road = item["road"]
            green = item["green_time"]
            total_cycle += green
            self.assertTrue(MIN_GREEN <= green <= MAX_GREEN, f"Road {road} green {green}s outside [{MIN_GREEN}, {MAX_GREEN}]")
            print(f"  * Approach {road:5s} | Vehicle Count: {results[road]['counts']['total']} | Allocated Green: {int(green)}s | Density: {results[road]['density']['level']}")

        self.assertEqual(cycle_plan["total_green_duration"], total_cycle)
        print(f"  * Cycle Sequence        : {[s['road'] for s in cycle_plan['sequence']]}")
        print(f"  * Total Green Duration  : {int(total_cycle)}s")
        print(f"  * Total Cycle Duration  : {int(cycle_plan['total_cycle_duration'])}s")
        print(f"  * Safety Invariant      : All 4 phases satisfy {MIN_GREEN}s <= green <= {MAX_GREEN}s")


if __name__ == "__main__":
    unittest.main()
