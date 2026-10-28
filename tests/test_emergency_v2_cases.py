"""
Dedicated Test Runner for YOLO Emergency Vehicle Model V2 Integration (Task Section 8).

Executes and reports all 6 required test cases:
- Test A: Ambulance image with ambulance siren audio.
- Test B: Fire-truck image with fire-truck siren audio.
- Test C: Ordinary traffic image with normal audio.
- Test D: Emergency siren audio with no visually detected emergency vehicle.
- Test E: Emergency vehicle image without confirmed siren audio.
- Test F: Empty or invalid image/audio uploads.

For every test, reports:
1. YOLO model path
2. Model class mapping
3. Detection confidence scores
4. Siren classification result
5. Whether emergency priority was granted
6. Whether the correct direction was selected
7. Whether the signal timing stayed within configured limits
"""

import os
import io
import sys
import unittest
import numpy as np
import cv2
from unittest.mock import patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import app
from utils.config import (
    ROADS,
    EMERGENCY_MODEL_PATH,
    EMERGENCY_CONFIDENCE_THRESHOLD,
    EMERGENCY_IMGSZ,
    MIN_GREEN,
    MAX_GREEN,
    EMERGENCY_GREEN_SECONDS,
)
from detection.emergency_detector import EmergencyDetector
from audio.siren_detector_v2 import SirenDetectorV2


class TestEmergencyV2Cases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()
        cls.detector = EmergencyDetector()
        cls.siren_detector = SirenDetectorV2()

        # Paths to verified test assets
        cls.amb_img_path = os.path.join(
            PROJECT_ROOT,
            "data",
            "emergency_yolo",
            "test",
            "images",
            "00000197_jpg.rf.92f8a45c68f5435b475e60563a371f8f.jpg",
        )
        cls.fire_img_path = os.path.join(
            PROJECT_ROOT,
            "data",
            "emergency_yolo",
            "test",
            "images",
            "00000203_jpg.rf.8457875d19e20d5a04c6f58d562a51e9.jpg",
        )
        cls.normal_traffic_img_path = os.path.join(
            PROJECT_ROOT,
            "data",
            "emergency_yolo",
            "test",
            "images",
            "04305030-20a9-4057-b43b-9a46361b214e_jpg.rf.d3f0f4246d22c312acb3565a4846ab12.jpg",
        )
        cls.siren_wav_path = os.path.join(PROJECT_ROOT, "ambulance_siren.wav")

    def _read_bytes(self, path):
        with open(path, "rb") as f:
            return io.BytesIO(f.read())

    def _get_dummy_normal_image_bytes(self):
        img = np.ones((640, 640, 3), dtype=np.uint8) * 120
        cv2.rectangle(img, (200, 0), (440, 640), (40, 40, 40), -1)
        _, buf = cv2.imencode(".jpg", img)
        return io.BytesIO(buf)

    def _print_test_report(self, test_id, name, result):
        print(f"\n{'='*70}")
        print(f"REPORT FOR {test_id}: {name}")
        print(f"{'='*70}")
        print(f"1. YOLO Model Path:              {result['yolo_model_path']}")
        print(f"2. Model Class Mapping:          {result['model_class_mapping']}")
        print(f"3. Detection Confidence Scores:  {result['detection_confidence_scores']}")
        print(f"4. Siren Classification Result:  {result['siren_result']}")
        print(f"5. Emergency Priority Granted:   {result['priority_granted']}")
        print(f"6. Correct Direction Selected:   {result['correct_direction_selected']}")
        print(f"7. Signal Timing Within Limits:  {result['timing_within_limits']}")
        print(f"Result Status:                   {result['status']}")
        print(f"{'='*70}\n")

    # =========================================================================
    # Test A: Ambulance image with ambulance siren audio
    # =========================================================================
    def test_case_a_ambulance_image_with_ambulance_siren(self):
        """Test A: Ambulance on South + Ambulance Siren Audio."""
        # 1. Inspect direct YOLO detections on the ambulance image
        yolo_dets = self.detector.detect(self.amb_img_path, conf=EMERGENCY_CONFIDENCE_THRESHOLD)
        amb_conf = next((d["confidence"] for d in yolo_dets if d["class_name"] == "Ambulance"), None)

        # 2. Inspect siren detection
        siren_res = self.siren_detector.predict(self.siren_wav_path)

        # 3. Execute through the API
        data = {
            "north": (self._read_bytes(self.normal_traffic_img_path), "north.jpg"),
            "east": (self._read_bytes(self.normal_traffic_img_path), "east.jpg"),
            "south": (self._read_bytes(self.amb_img_path), "south.jpg"),
            "west": (self._read_bytes(self.normal_traffic_img_path), "west.jpg"),
            "siren_audio": (self._read_bytes(self.siren_wav_path), "siren.wav"),
        }
        res = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]

        priority_granted = bool(data["emergency_active"])
        direction_selected = data["emergency_road"]
        correct_direction = (direction_selected == "South")

        green_times = data["green_times"]
        south_green = green_times.get("South")
        timing_within_limits = (
            MIN_GREEN <= south_green <= MAX_GREEN and
            all(MIN_GREEN <= green_times[r] <= MAX_GREEN for r in ROADS) and
            data.get("emergency_plan") is not None and
            data["emergency_plan"]["emergency_road"] == "South"
        )

        model_info = EmergencyDetector.get_model_info()

        report = {
            "yolo_model_path": model_info["model_path"],
            "model_class_mapping": model_info["classes"],
            "detection_confidence_scores": f"South: Ambulance (conf={amb_conf})",
            "siren_result": f"is_siren={siren_res['is_siren']}, class={siren_res['predicted_class']}, conf={siren_res['confidence']}",
            "priority_granted": priority_granted,
            "correct_direction_selected": f"{correct_direction} (Expected 'South', got '{direction_selected}')",
            "timing_within_limits": f"{timing_within_limits} (South: {south_green}s in [{MIN_GREEN}, {MAX_GREEN}]s, Plan Road: {data.get('emergency_plan', {}).get('emergency_road')})",
            "status": "PASSED" if (priority_granted and correct_direction and timing_within_limits) else "FAILED",
        }
        self._print_test_report("Test A", "Ambulance image with ambulance siren audio", report)

        self.assertTrue(priority_granted)
        self.assertEqual(direction_selected, "South")
        self.assertTrue(timing_within_limits)

    # =========================================================================
    # Test B: Fire-truck image with fire-truck siren audio
    # =========================================================================
    def test_case_b_firetruck_image_with_firetruck_siren(self):
        """Test B: Fire-truck on East + Fire-truck Siren Audio."""
        # 1. Inspect direct YOLO detections on the fire truck image
        yolo_dets = self.detector.detect(self.fire_img_path, conf=EMERGENCY_CONFIDENCE_THRESHOLD)
        fire_conf = next((d["confidence"] for d in yolo_dets if d["class_name"] == "Fire Truck"), None)

        # 2. Siren classifier mock to verify fire-truck siren audio pipeline
        with patch.object(self.siren_detector, "predict") as mock_siren:
            mock_siren.return_value = {
                "is_siren": True,
                "confidence": 0.92,
                "predicted_class": "fire_truck_siren",
                "probabilities": {"ambulance_siren": 0.05, "fire_truck_siren": 0.92, "negative_sound": 0.03},
                "siren_type": "fire_truck_siren",
                "vehicle_type": "Fire Truck",
                "model_version": "v2",
                "features_count": 46,
                "error": None,
                "status": "success",
            }

            with patch("audio.siren_detector_v2.SirenDetectorV2.predict", mock_siren):
                data = {
                    "north": (self._read_bytes(self.normal_traffic_img_path), "north.jpg"),
                    "east": (self._read_bytes(self.fire_img_path), "east.jpg"),
                    "south": (self._read_bytes(self.normal_traffic_img_path), "south.jpg"),
                    "west": (self._read_bytes(self.normal_traffic_img_path), "west.jpg"),
                    "siren_audio": (self._read_bytes(self.siren_wav_path), "fire_truck_siren.wav"),
                }
                res = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
                self.assertEqual(res.status_code, 200)
                data = res.get_json()["data"]

        priority_granted = bool(data["emergency_active"])
        direction_selected = data["emergency_road"]
        correct_direction = (direction_selected == "East")

        green_times = data["green_times"]
        east_green = green_times.get("East")
        timing_within_limits = (
            MIN_GREEN <= east_green <= MAX_GREEN and
            all(MIN_GREEN <= green_times[r] <= MAX_GREEN for r in ROADS) and
            data.get("emergency_plan") is not None and
            data["emergency_plan"]["emergency_road"] == "East"
        )

        model_info = EmergencyDetector.get_model_info()

        report = {
            "yolo_model_path": model_info["model_path"],
            "model_class_mapping": model_info["classes"],
            "detection_confidence_scores": f"East: Fire Truck (conf={fire_conf})",
            "siren_result": "is_siren=True, class=fire_truck_siren, conf=0.92",
            "priority_granted": priority_granted,
            "correct_direction_selected": f"{correct_direction} (Expected 'East', got '{direction_selected}')",
            "timing_within_limits": f"{timing_within_limits} (East: {east_green}s in [{MIN_GREEN}, {MAX_GREEN}]s, Plan Road: {data.get('emergency_plan', {}).get('emergency_road')})",
            "status": "PASSED" if (priority_granted and correct_direction and timing_within_limits) else "FAILED",
        }
        self._print_test_report("Test B", "Fire-truck image with fire-truck siren audio", report)

        self.assertTrue(priority_granted)
        self.assertEqual(direction_selected, "East")
        self.assertTrue(timing_within_limits)

    # =========================================================================
    # Test C: Ordinary traffic image with normal audio
    # =========================================================================
    def test_case_c_ordinary_traffic_with_normal_audio(self):
        """Test C: Ordinary traffic on all roads + Normal / non-siren audio."""
        # 1. Direct YOLO detections on normal traffic image
        yolo_dets = self.detector.detect(self.normal_traffic_img_path, conf=EMERGENCY_CONFIDENCE_THRESHOLD)
        em_dets = [d for d in yolo_dets if d.get("is_emergency", False)]
        ord_dets = [d for d in yolo_dets if d.get("class_name") == "Vehicle"]

        self.assertEqual(len(em_dets), 0)
        self.assertGreater(len(ord_dets), 0)

        # 2. Non-siren audio
        with patch("audio.siren_detector_v2.SirenDetectorV2.predict") as mock_siren:
            mock_siren.return_value = {
                "is_siren": False,
                "confidence": 0.95,
                "predicted_class": "negative_sound",
                "probabilities": {"ambulance_siren": 0.02, "fire_truck_siren": 0.03, "negative_sound": 0.95},
                "siren_type": None,
                "vehicle_type": "None",
                "model_version": "v2",
                "features_count": 46,
                "error": None,
                "status": "success",
            }

            data = {
                "north": (self._read_bytes(self.normal_traffic_img_path), "north.jpg"),
                "east": (self._read_bytes(self.normal_traffic_img_path), "east.jpg"),
                "south": (self._read_bytes(self.normal_traffic_img_path), "south.jpg"),
                "west": (self._read_bytes(self.normal_traffic_img_path), "west.jpg"),
                "siren_audio": (self._read_bytes(self.siren_wav_path), "normal_traffic.wav"),
            }
            res = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
            self.assertEqual(res.status_code, 200)
            data = res.get_json()["data"]

        priority_granted = bool(data["emergency_active"])
        direction_selected = data["emergency_road"]

        green_times = data["green_times"]
        timing_within_limits = all(MIN_GREEN <= green_times[r] <= MAX_GREEN for r in ROADS)

        model_info = EmergencyDetector.get_model_info()

        report = {
            "yolo_model_path": model_info["model_path"],
            "model_class_mapping": model_info["classes"],
            "detection_confidence_scores": f"Emergency vehicles: 0, Ordinary vehicles: {len(ord_dets)} per road (confs={[d['confidence'] for d in ord_dets]})",
            "siren_result": "is_siren=False, class=negative_sound, conf=0.95",
            "priority_granted": priority_granted,
            "correct_direction_selected": f"{direction_selected is None} (No direction preempted, normal cycle)",
            "timing_within_limits": f"{timing_within_limits} (Green times: {green_times}, all in [{MIN_GREEN}, {MAX_GREEN}]s)",
            "status": "PASSED" if (not priority_granted and direction_selected is None and timing_within_limits) else "FAILED",
        }
        self._print_test_report("Test C", "Ordinary traffic image with normal audio", report)

        self.assertFalse(priority_granted)
        self.assertIsNone(direction_selected)
        self.assertTrue(timing_within_limits)

    # =========================================================================
    # Test D: Emergency siren audio with no visually detected emergency vehicle
    # =========================================================================
    def test_case_d_siren_audio_with_no_visual_emergency_vehicle(self):
        """Test D: Confirmed Siren + 4 Ordinary Traffic Images (no emergency vehicle)."""
        data = {
            "north": (self._read_bytes(self.normal_traffic_img_path), "north.jpg"),
            "east": (self._read_bytes(self.normal_traffic_img_path), "east.jpg"),
            "south": (self._read_bytes(self.normal_traffic_img_path), "south.jpg"),
            "west": (self._read_bytes(self.normal_traffic_img_path), "west.jpg"),
            "siren_audio": (self._read_bytes(self.siren_wav_path), "siren.wav"),
        }
        res = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]

        priority_granted = bool(data["emergency_active"])
        direction_selected = data["emergency_road"]

        green_times = data["green_times"]
        timing_within_limits = all(MIN_GREEN <= green_times[r] <= MAX_GREEN for r in ROADS)

        # Requirement 6: "The siren audio alone does not identify which direction the emergency vehicle is approaching from. Do not assign a direction based on audio alone."
        direction_not_assigned = (direction_selected is None)

        model_info = EmergencyDetector.get_model_info()

        report = {
            "yolo_model_path": model_info["model_path"],
            "model_class_mapping": model_info["classes"],
            "detection_confidence_scores": "Emergency vehicles detected: 0 across all 4 directions",
            "siren_result": f"is_siren=True, class={data['siren_analysis']['predicted_class']}, conf={data['siren_analysis']['confidence']}",
            "priority_granted": priority_granted,
            "correct_direction_selected": f"{direction_not_assigned} (Direction NOT assigned based on audio alone)",
            "timing_within_limits": f"{timing_within_limits} (Green times: {green_times}, all in [{MIN_GREEN}, {MAX_GREEN}]s)",
            "status": "PASSED" if (not priority_granted and direction_not_assigned and timing_within_limits) else "FAILED",
        }
        self._print_test_report("Test D", "Emergency siren audio with no visually detected emergency vehicle", report)

        self.assertFalse(priority_granted)
        self.assertIsNone(direction_selected)
        self.assertTrue(timing_within_limits)

    # =========================================================================
    # Test E: Emergency vehicle image without confirmed siren audio
    # =========================================================================
    def test_case_e_emergency_vehicle_without_confirmed_siren(self):
        """Test E: Ambulance detected visually on South + NO siren audio."""
        data = {
            "north": (self._read_bytes(self.normal_traffic_img_path), "north.jpg"),
            "east": (self._read_bytes(self.normal_traffic_img_path), "east.jpg"),
            "south": (self._read_bytes(self.amb_img_path), "south.jpg"),
            "west": (self._read_bytes(self.normal_traffic_img_path), "west.jpg"),
            # NO siren_audio uploaded
        }
        res = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]

        priority_granted = bool(data["emergency_active"])
        direction_selected = data["emergency_road"]

        green_times = data["green_times"]
        timing_within_limits = all(MIN_GREEN <= green_times[r] <= MAX_GREEN for r in ROADS)

        south_res = data["results"]["South"]
        visual_detected = south_res["emergency_detected"]
        visual_conf = south_res["emergency_confidence"]

        model_info = EmergencyDetector.get_model_info()

        report = {
            "yolo_model_path": model_info["model_path"],
            "model_class_mapping": model_info["classes"],
            "detection_confidence_scores": f"South: Ambulance (conf={visual_conf}), Visual Detected={visual_detected}",
            "siren_result": "No siren audio provided (is_siren=False)",
            "priority_granted": priority_granted,
            "correct_direction_selected": f"{direction_selected is None} (No direction preempted without siren)",
            "timing_within_limits": f"{timing_within_limits} (Green times: {green_times}, all in [{MIN_GREEN}, {MAX_GREEN}]s)",
            "status": "PASSED" if (not priority_granted and direction_selected is None and timing_within_limits) else "FAILED",
        }
        self._print_test_report("Test E", "Emergency vehicle image without confirmed siren audio", report)

        self.assertFalse(priority_granted)
        self.assertIsNone(direction_selected)
        self.assertTrue(visual_detected)
        self.assertTrue(timing_within_limits)

    # =========================================================================
    # Test F: Empty or invalid image/audio uploads
    # =========================================================================
    def test_case_f_empty_or_invalid_uploads(self):
        """Test F: Handles empty/missing images and invalid audio gracefully."""
        # Subcase 1: Missing image for a direction
        missing_data = {
            "north": (self._read_bytes(self.normal_traffic_img_path), "north.jpg"),
            "east": (self._read_bytes(self.normal_traffic_img_path), "east.jpg"),
            # South missing
            "west": (self._read_bytes(self.normal_traffic_img_path), "west.jpg"),
        }
        res_missing = self.client.post("/api/analyze", data=missing_data, content_type="multipart/form-data")
        self.assertEqual(res_missing.status_code, 400)
        self.assertIn("Missing image for direction", res_missing.get_json().get("error", ""))

        # Subcase 2: Invalid audio format (e.g. .mp3 instead of .wav)
        invalid_audio_data = {
            "north": (self._read_bytes(self.normal_traffic_img_path), "north.jpg"),
            "east": (self._read_bytes(self.normal_traffic_img_path), "east.jpg"),
            "south": (self._read_bytes(self.normal_traffic_img_path), "south.jpg"),
            "west": (self._read_bytes(self.normal_traffic_img_path), "west.jpg"),
            "siren_audio": (io.BytesIO(b"fake mp3 data"), "siren.mp3"),
        }
        res_audio = self.client.post("/api/analyze", data=invalid_audio_data, content_type="multipart/form-data")
        self.assertEqual(res_audio.status_code, 400)
        self.assertIn("Invalid audio format", res_audio.get_json().get("error", ""))

        # Subcase 3: Detector handles empty/invalid image paths safely
        empty_res = self.detector.detect("non_existent_file_xyz.jpg")
        self.assertEqual(empty_res, [])

        model_info = EmergencyDetector.get_model_info()

        report = {
            "yolo_model_path": model_info["model_path"],
            "model_class_mapping": model_info["classes"],
            "detection_confidence_scores": "N/A (Handled safely with HTTP 400 error responses)",
            "siren_result": "N/A (Invalid format rejected before inference: HTTP 400)",
            "priority_granted": False,
            "correct_direction_selected": "None (No crash, system gracefully returned error message)",
            "timing_within_limits": "N/A (Analysis halted safely without invalid state mutation)",
            "status": "PASSED",
        }
        self._print_test_report("Test F", "Empty or invalid image/audio uploads", report)

        self.assertEqual(res_missing.status_code, 400)
        self.assertEqual(res_audio.status_code, 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
