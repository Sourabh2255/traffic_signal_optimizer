"""
Custom YOLO-based Emergency Vehicle Detector.

Dedicated detection module for identifying emergency vehicles (Ambulance, Fire Truck, Police)
and ordinary Vehicles using the YOLO model (models/emergency.pt).

Key responsibilities:
- Loads the custom model once at application startup (singleton pattern).
- Detects Ambulance (Class 0), Fire_Truck (Class 1), Police (Class 2), and Vehicle (Class 3).
- Returns bounding boxes, class names, confidence scores, and detection status.
- Handles missing model files, unreadable images, and inference errors gracefully.
- Configurable confidence threshold (conf=0.25) and image size (imgsz=416) via utils.config.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from ultralytics import YOLO

from utils.config import (
    EMERGENCY_MODEL_PATH,
    EMERGENCY_CONFIDENCE_THRESHOLD,
    EMERGENCY_IMGSZ,
    EMERGENCY_IOU_THRESHOLD,
    EMERGENCY_CLASSES,
    ALLOW_POLICE_EMERGENCY_PRIORITY,
)

logger = logging.getLogger(__name__)


class EmergencyDetector:
    """
    Singleton wrapper around the custom fine-tuned YOLO emergency vehicle detector.
    Caches the model instance at the class level to avoid expensive reloads per request.
    """

    _model: Optional[YOLO] = None
    _load_attempted: bool = False
    _load_error: Optional[str] = None

    _cached_path: Optional[str] = None

    def __init__(self, model_path: str = EMERGENCY_MODEL_PATH):
        self.model_path = model_path
        if EmergencyDetector._model is None or getattr(EmergencyDetector, "_cached_path", None) != model_path:
            self._load_model()
            EmergencyDetector._cached_path = model_path
        self.model = EmergencyDetector._model

    @classmethod
    def is_available(cls, model_path: str = EMERGENCY_MODEL_PATH) -> bool:
        """Returns True if the custom model weights exist on disk."""
        return os.path.exists(model_path) and os.path.isfile(model_path)

    @classmethod
    def get_model_info(cls) -> Dict[str, Any]:
        """Returns metadata about the loaded emergency model."""
        available = cls.is_available()
        loaded = cls._model is not None
        names = {}
        if loaded and cls._model:
            names = cls._model.names
        elif available:
            names = EMERGENCY_CLASSES

        return {
            "model_path": EMERGENCY_MODEL_PATH,
            "model_name": os.path.basename(EMERGENCY_MODEL_PATH),
            "exists": available,
            "loaded": loaded,
            "classes": names,
            "confidence_threshold": EMERGENCY_CONFIDENCE_THRESHOLD,
            "imgsz": EMERGENCY_IMGSZ,
            "iou": EMERGENCY_IOU_THRESHOLD,
            "error": cls._load_error,
        }

    def _load_model(self) -> None:
        """Attempts to load the custom YOLO model weights once."""
        EmergencyDetector._load_attempted = True
        if not os.path.exists(self.model_path):
            error_msg = f"Custom emergency model file not found at: {self.model_path}"
            logger.warning(error_msg)
            EmergencyDetector._load_error = error_msg
            EmergencyDetector._model = None
            return

        try:
            logger.info(f"Loading custom emergency YOLO model from {self.model_path}...")
            EmergencyDetector._model = YOLO(self.model_path)
            EmergencyDetector._load_error = None
            logger.info("Custom emergency YOLO model loaded successfully.")
        except Exception as e:
            error_msg = f"Failed to load custom emergency model: {e}"
            logger.exception(error_msg)
            EmergencyDetector._load_error = error_msg
            EmergencyDetector._model = None

    def detect(self, image_path: str, conf: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Runs custom emergency YOLO inference on a single image.

        Args:
            image_path: Path to the image file.
            conf: Optional confidence threshold override.

        Returns:
            List of detection dicts:
            [
                {
                    "class_name": "Ambulance" | "Fire Truck" | "Vehicle",
                    "class_id": int,
                    "confidence": float,
                    "box": [x1, y1, x2, y2],
                    "is_emergency": bool (True ONLY for Ambulance & Fire Truck)
                },
                ...
            ]
        """
        if self.model is None:
            if not EmergencyDetector._load_attempted or getattr(EmergencyDetector, "_cached_path", None) != self.model_path:
                self._load_model()
                EmergencyDetector._cached_path = self.model_path
                self.model = EmergencyDetector._model
            if self.model is None:
                logger.warning("EmergencyDetector invoked without an active model. Returning empty detections.")
                return []

        if not os.path.exists(image_path):
            logger.error(f"Image not found for emergency detection: {image_path}")
            return []

        threshold = conf if conf is not None else EMERGENCY_CONFIDENCE_THRESHOLD

        try:
            results = self.model.predict(
                source=image_path,
                conf=threshold,
                iou=EMERGENCY_IOU_THRESHOLD,
                imgsz=EMERGENCY_IMGSZ,
                verbose=False,
            )
        except Exception as e:
            logger.exception(f"Inference error during emergency detection on {image_path}: {e}")
            return []

        if not results:
            return []

        result = results[0]
        detections: List[Dict[str, Any]] = []

        for box in result.boxes:
            class_id = int(box.cls[0].item())
            confidence = round(float(box.conf[0].item()), 3)

            # Map class ID and raw names to standardized display names
            raw_name = str(self.model.names.get(class_id, f"Class_{class_id}")).strip()
            raw_lower = raw_name.lower().replace("-", "_")

            if class_id == 0 or "ambulance" in raw_lower:
                display_name = "Ambulance"
                is_emergency = True
                vehicle_category = "emergency"
            elif class_id == 1 or "fire" in raw_lower:
                display_name = "Fire Truck"
                is_emergency = True
                vehicle_category = "emergency"
            elif class_id == 2 or "police" in raw_lower:
                display_name = "Police"
                is_emergency = bool(ALLOW_POLICE_EMERGENCY_PRIORITY)
                vehicle_category = "police"
            elif class_id == 3 or "vehicle" in raw_lower:
                display_name = "Vehicle"
                is_emergency = False
                vehicle_category = "ordinary"
            else:
                display_name = raw_name.replace("-", " ").replace("_", " ").title()
                is_emergency = False
                vehicle_category = "ordinary"

            xyxy = [round(float(c), 1) for c in box.xyxy[0].tolist()]

            detections.append({
                "class_name": display_name,
                "class_id": class_id,
                "confidence": confidence,
                "box": xyxy,
                "is_emergency": is_emergency,
                "vehicle_category": vehicle_category,
            })

        # Sort detections by confidence descending
        detections.sort(key=lambda d: d["confidence"], reverse=True)
        return detections

    def detect_summary(
        self, image_path: str, conf: Optional[float] = None, road: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Returns a high-level summary of emergency, police, and vehicle detections for a road image.

        Args:
            image_path: Path to the image file.
            conf: Confidence threshold.
            road: Road name (e.g. North, East, South, West).

        Returns:
            dict containing detection status, counts, primary emergency vehicle type,
            highest confidence, bounding box, road direction, and raw detections list.
        """
        detections = self.detect(image_path, conf=conf)

        ambulance_count = sum(1 for d in detections if d["class_name"] == "Ambulance")
        fire_truck_count = sum(1 for d in detections if d["class_name"] in ("Fire Truck", "Fire_Truck"))
        police_count = sum(1 for d in detections if d["class_name"] == "Police")
        vehicle_count = sum(1 for d in detections if d["class_name"] == "Vehicle")

        ambulance_detected = ambulance_count > 0
        fire_truck_detected = fire_truck_count > 0
        police_detected = police_count > 0

        # Only qualifying emergency vehicles trigger visual_emergency_detected
        visual_emergency_detected = ambulance_detected or fire_truck_detected or (police_detected and ALLOW_POLICE_EMERGENCY_PRIORITY)

        # Identify primary emergency detection if any (highest confidence qualifying emergency vehicle)
        emergency_dets = [d for d in detections if d.get("is_emergency", False)]

        if emergency_dets:
            primary_em = emergency_dets[0]
            vehicle_type = primary_em["class_name"]
            class_id = primary_em["class_id"]
            confidence = primary_em["confidence"]
            box = primary_em["box"]
        elif detections:
            primary_em = detections[0]
            vehicle_type = primary_em["class_name"]
            class_id = primary_em["class_id"]
            confidence = primary_em["confidence"]
            box = primary_em["box"]
        else:
            vehicle_type = "None"
            class_id = None
            confidence = None
            box = None

        return {
            "detected": visual_emergency_detected,
            "visual_emergency_detected": visual_emergency_detected,
            "ambulance_detected": ambulance_detected,
            "fire_truck_detected": fire_truck_detected,
            "police_detected": police_detected,
            "ambulance_count": ambulance_count,
            "fire_truck_count": fire_truck_count,
            "police_count": police_count,
            "vehicle_count": vehicle_count,
            "total_detections": len(detections),
            "vehicle_type": vehicle_type,
            "emergency_vehicle_type": vehicle_type,
            "class_id": class_id,
            "confidence": confidence,
            "emergency_confidence": confidence,
            "box": box,
            "road": road,
            "detections": detections,
            "model_available": self.model is not None,
            "error": EmergencyDetector._load_error if self.model is None else None,
        }
