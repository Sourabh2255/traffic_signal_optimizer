"""
Evaluate Trained Emergency Vehicle YOLO Detection Model.

Evaluates models/best_emergency_vehicle.pt on the validation dataset
with imgsz=640 and conf=0.10 without retraining.
"""

from pathlib import Path
import csv
import yaml
from ultralytics import YOLO

# 1. Project paths
PROJECT_ROOT = Path(__file__).resolve().parent
MODEL_PATH = PROJECT_ROOT / "models" / "best_emergency_vehicle.pt"
YAML_PATH = PROJECT_ROOT / "data" / "emergency_yolo" / "data.yaml"
OUTPUT_TXT_PATH = PROJECT_ROOT / "emergency_model_val_results.txt"
OUTPUT_CSV_PATH = PROJECT_ROOT / "emergency_model_val_results.csv"

# 2. Verification
if not MODEL_PATH.exists():
    raise FileNotFoundError(f"Trained model not found at: {MODEL_PATH}")

if not YAML_PATH.exists():
    raise FileNotFoundError(f"Dataset YAML configuration not found at: {YAML_PATH}")

print("=" * 70)
print("EMERGENCY VEHICLE DETECTION MODEL EVALUATION")
print("=" * 70)
print(f"Model Path:      {MODEL_PATH}")
print(f"Dataset Config:  {YAML_PATH}")
print(f"Target Split:    val")
print(f"Image Size:      640")
print(f"Confidence:      0.10")
print(f"Mode:            Validation only (no retraining)")
print("=" * 70)

# 3. Load trained model (read-only)
model = YOLO(str(MODEL_PATH))
print(f"Loaded classes: {model.names}")

# 4. Run single evaluation with imgsz=640, conf=0.10 on 'val' split
print("\nRunning evaluation on validation split (imgsz=640, conf=0.10)... Please wait.")
metrics = model.val(
    data=str(YAML_PATH),
    split="val",
    imgsz=640,
    conf=0.10,
    batch=4,
    device="cpu",
    plots=True,
    verbose=True,
)

# 5. Extract metrics
precision = float(metrics.box.mp)
recall = float(metrics.box.mr)
map50 = float(metrics.box.map50)
map50_95 = float(metrics.box.map)

print("\n" + "=" * 70)
print("OVERALL VALIDATION RESULTS (conf=0.10, imgsz=640)")
print("=" * 70)
print(f"Precision:        {precision:.4f} ({precision * 100:.2f}%)")
print(f"Recall:           {recall:.4f} ({recall * 100:.2f}%)")
print(f"mAP@50:           {map50:.4f} ({map50 * 100:.2f}%)")
print(f"mAP@50-95:        {map50_95:.4f} ({map50_95 * 100:.2f}%)")

per_class_results = []
print("\nPER-CLASS BREAKDOWN:")
print("-" * 70)
print(f"{'Class ID':<10}{'Class Name':<16}{'Precision':<14}{'Recall':<14}{'mAP@50':<14}{'mAP@50-95':<14}")
print("-" * 70)

for idx, class_name in model.names.items():
    cls_p = float(metrics.box.p[idx]) if hasattr(metrics.box, 'p') and len(metrics.box.p) > idx else 0.0
    cls_r = float(metrics.box.r[idx]) if hasattr(metrics.box, 'r') and len(metrics.box.r) > idx else 0.0
    cls_ap50 = float(metrics.box.ap50[idx]) if hasattr(metrics.box, 'ap50') and len(metrics.box.ap50) > idx else 0.0
    cls_map = float(metrics.box.maps[idx]) if hasattr(metrics.box, 'maps') and len(metrics.box.maps) > idx else 0.0
    per_class_results.append({
        "class_id": idx,
        "class_name": class_name,
        "precision": cls_p,
        "recall": cls_r,
        "map50": cls_ap50,
        "map50_95": cls_map,
    })
    print(f"{idx:<10}{class_name:<16}{cls_p:<14.4f}{cls_r:<14.4f}{cls_ap50:<14.4f}{cls_map:<14.4f}")
print("-" * 70)

# 6. Save results to text file
with open(OUTPUT_TXT_PATH, "w", encoding="utf-8") as f:
    f.write("======================================================================\n")
    f.write("EMERGENCY VEHICLE YOLO DETECTION EVALUATION REPORT\n")
    f.write("======================================================================\n")
    f.write(f"Model:           {MODEL_PATH.name}\n")
    f.write(f"Dataset Split:   Validation (split='val')\n")
    f.write(f"Image Size:      640\n")
    f.write(f"Confidence:      0.10\n\n")
    f.write("OVERALL METRICS:\n")
    f.write(f"Precision:       {precision:.4f} ({precision * 100:.2f}%)\n")
    f.write(f"Recall:          {recall:.4f} ({recall * 100:.2f}%)\n")
    f.write(f"mAP@50:          {map50:.4f} ({map50 * 100:.2f}%)\n")
    f.write(f"mAP@50-95:       {map50_95:.4f} ({map50_95 * 100:.2f}%)\n\n")
    f.write("PER-CLASS METRICS:\n")
    f.write(f"{'Class ID':<10}{'Class Name':<16}{'Precision':<14}{'Recall':<14}{'mAP@50':<14}{'mAP@50-95':<14}\n")
    f.write("-" * 70 + "\n")
    for r in per_class_results:
        f.write(f"{r['class_id']:<10}{r['class_name']:<16}{r['precision']:<14.4f}{r['recall']:<14.4f}{r['map50']:<14.4f}{r['map50_95']:<14.4f}\n")
    f.write("======================================================================\n")

print(f"\n[SUCCESS] Detailed text report saved to: {OUTPUT_TXT_PATH.resolve()}")

# 7. Save results to CSV file
with open(OUTPUT_CSV_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["category", "class_id", "class_name", "imgsz", "conf", "precision", "recall", "map50", "map50_95"])
    writer.writerow(["overall", "all", "all_classes", 640, 0.10, f"{precision:.4f}", f"{recall:.4f}", f"{map50:.4f}", f"{map50_95:.4f}"])
    for r in per_class_results:
        writer.writerow(["per_class", r["class_id"], r["class_name"], 640, 0.10, f"{r['precision']:.4f}", f"{r['recall']:.4f}", f"{r['map50']:.4f}", f"{r['map50_95']:.4f}"])

print(f"[SUCCESS] Structured CSV report saved to: {OUTPUT_CSV_PATH.resolve()}")
print("=" * 70)
