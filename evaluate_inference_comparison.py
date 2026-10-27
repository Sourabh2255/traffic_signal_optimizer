"""
Inference Configuration Evaluation and Comparison Script.

Evaluates the trained emergency vehicle YOLO model (models/best_emergency_vehicle.pt)
across multiple image sizes (640, 960) and confidence thresholds (0.10, 0.15, 0.25)
on a small, balanced, representative validation subset without retraining.
"""

import time
import csv
from pathlib import Path
from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parent
MODEL_PATH = PROJECT_ROOT / "models" / "best_emergency_vehicle.pt"
SUBSET_YAML_PATH = PROJECT_ROOT / "data" / "emergency_yolo_subset" / "data.yaml"
ORIGINAL_YAML_PATH = PROJECT_ROOT / "data" / "emergency_yolo" / "data.yaml"

OUTPUT_TXT = PROJECT_ROOT / "inference_comparison.txt"
OUTPUT_CSV = PROJECT_ROOT / "inference_comparison.csv"

# Configurations to test
CONFIGS = [
    {"imgsz": 640, "conf": 0.10, "label": "Baseline (640, conf=0.10)"},
    {"imgsz": 640, "conf": 0.15, "label": "Config 2 (640, conf=0.15)"},
    {"imgsz": 640, "conf": 0.25, "label": "Config 3 (640, conf=0.25)"},
    {"imgsz": 960, "conf": 0.10, "label": "Config 4 (960, conf=0.10)"},
    {"imgsz": 960, "conf": 0.15, "label": "Config 5 (960, conf=0.15)"},
    {"imgsz": 960, "conf": 0.25, "label": "Config 6 (960, conf=0.25)"},
]

def main():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model not found at: {MODEL_PATH}")
    if not SUBSET_YAML_PATH.exists():
        raise FileNotFoundError(f"Subset data.yaml not found at: {SUBSET_YAML_PATH}")

    print("=" * 80)
    print("YOLO INFERENCE CONFIGURATION COMPARISON (REPRESENTATIVE SUBSET: 60 IMAGES)")
    print("=" * 80)
    print(f"Model:                {MODEL_PATH.name} (read-only)")
    print(f"Subset Dataset YAML:  {SUBSET_YAML_PATH}")
    print(f"Configurations to run: {len(CONFIGS)}")
    print("=" * 80)

    # 1. Inspect duplicate annotation warnings in validation dataset
    original_val_labels = PROJECT_ROOT / "data" / "emergency_yolo" / "valid" / "labels"
    dup_details = []
    if original_val_labels.exists():
        for txt_file in original_val_labels.glob("*.txt"):
            lines = [l.strip() for l in txt_file.read_text(encoding="utf-8").splitlines() if l.strip()]
            seen = set()
            file_dups = 0
            for l in lines:
                parts = l.split()
                if len(parts) >= 5:
                    cls_id = parts[0]
                    coords = tuple(round(float(x), 4) for x in parts[1:5])
                    key = (cls_id, coords)
                    if key in seen:
                        file_dups += 1
                    seen.add(key)
            if file_dups > 0:
                dup_details.append((txt_file.name, len(lines), file_dups))

    print(f"\n[Dataset Inspection] Found {len(dup_details)} files in 'valid/labels' with duplicate bounding boxes.")
    print("Ultralytics automatically filters these exact duplicate labels out during validation scanning.")
    print("Per instructions, original dataset labels are kept completely unmodified.\n")

    # 2. Load model (read-only)
    model = YOLO(str(MODEL_PATH))

    results = []

    for idx, cfg in enumerate(CONFIGS, 1):
        imgsz = cfg["imgsz"]
        conf = cfg["conf"]
        label = cfg["label"]

        print("-" * 80)
        print(f"Running [{idx}/{len(CONFIGS)}]: {label} (imgsz={imgsz}, conf={conf:.2f})...")
        t0 = time.time()

        metrics = model.val(
            data=str(SUBSET_YAML_PATH),
            split="val",
            imgsz=imgsz,
            conf=conf,
            batch=4,
            device="cpu",
            plots=False,
            verbose=False,
        )

        elapsed = time.time() - t0
        ms_per_img = (elapsed / 60) * 1000  # 60 images

        # Overall metrics
        mp = float(metrics.box.mp)
        mr = float(metrics.box.mr)
        map50 = float(metrics.box.map50)
        map50_95 = float(metrics.box.map)

        # Per-class metrics
        class_metrics = {}
        for c_id, c_name in model.names.items():
            c_p = float(metrics.box.p[c_id]) if hasattr(metrics.box, "p") and len(metrics.box.p) > c_id else 0.0
            c_r = float(metrics.box.r[c_id]) if hasattr(metrics.box, "r") and len(metrics.box.r) > c_id else 0.0
            c_ap50 = float(metrics.box.ap50[c_id]) if hasattr(metrics.box, "ap50") and len(metrics.box.ap50) > c_id else 0.0
            c_map = float(metrics.box.maps[c_id]) if hasattr(metrics.box, "maps") and len(metrics.box.maps) > c_id else 0.0
            class_metrics[c_name] = {
                "precision": c_p,
                "recall": c_r,
                "map50": c_ap50,
                "map50_95": c_map,
            }

        res_item = {
            "config": label,
            "imgsz": imgsz,
            "conf": conf,
            "elapsed_sec": elapsed,
            "ms_per_img": ms_per_img,
            "precision": mp,
            "recall": mr,
            "map50": map50,
            "map50_95": map50_95,
            "ambulance": class_metrics.get("ambulance", {}),
            "fire_truck": class_metrics.get("fire_truck", {}),
        }
        results.append(res_item)

        print(f"Done in {elapsed:.1f}s ({ms_per_img:.1f} ms/img) | "
              f"P: {mp:.4f}, R: {mr:.4f}, mAP50: {map50:.4f}, mAP50-95: {map50_95:.4f}")

    print("\n" + "=" * 80)
    print("ALL 6 CONFIGURATIONS COMPLETED!")
    print("=" * 80)

    # 3. Save to CSV
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "configuration", "imgsz", "conf", "elapsed_sec", "ms_per_image",
            "overall_precision", "overall_recall", "overall_map50", "overall_map50_95",
            "amb_precision", "amb_recall", "amb_map50", "amb_map50_95",
            "fire_precision", "fire_recall", "fire_map50", "fire_map50_95"
        ])
        for r in results:
            writer.writerow([
                r["config"], r["imgsz"], r["conf"],
                f"{r['elapsed_sec']:.2f}", f"{r['ms_per_img']:.1f}",
                f"{r['precision']:.4f}", f"{r['recall']:.4f}", f"{r['map50']:.4f}", f"{r['map50_95']:.4f}",
                f"{r['ambulance']['precision']:.4f}", f"{r['ambulance']['recall']:.4f}",
                f"{r['ambulance']['map50']:.4f}", f"{r['ambulance']['map50_95']:.4f}",
                f"{r['fire_truck']['precision']:.4f}", f"{r['fire_truck']['recall']:.4f}",
                f"{r['fire_truck']['map50']:.4f}", f"{r['fire_truck']['map50_95']:.4f}",
            ])
    print(f"[SUCCESS] CSV written to: {OUTPUT_CSV.resolve()}")

    # 4. Save to TXT with comparative analysis
    baseline = results[0]
    total_val_images = 1490

    with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
        f.write("=" * 90 + "\n")
        f.write("YOLO INFERENCE CONFIGURATION COMPARISON REPORT (REPRESENTATIVE SUBSET: 60 IMAGES)\n")
        f.write("=" * 90 + "\n")
        f.write(f"Model: {MODEL_PATH.name} (read-only, no retraining)\n")
        f.write(f"Subset Size: 60 images (22 fire trucks, 28 ambulances, 10 backgrounds)\n")
        f.write(f"Tested Configurations: 6 (imgsz in [640, 960], conf in [0.10, 0.15, 0.25])\n\n")

        f.write("DUPLICATE ANNOTATION WARNING INSPECTION:\n")
        f.write("-" * 90 + "\n")
        f.write(f"Total files in valid/labels with duplicate bounding boxes: {len(dup_details)}\n")
        f.write("Sample affected files:\n")
        for fname, tot, dups in dup_details[:8]:
            f.write(f"  - {fname}: {tot} total annotations, {dups} exact duplicate(s)\n")
        f.write("Root Cause: Bounding boxes with identical class ID and coordinates exist in Roboflow export.\n")
        f.write("Resolution: Ultralytics validator automatically dedupes identical boxes during validation scanning;\n")
        f.write("dataset files are left intact per project instructions.\n\n")

        f.write("OVERALL INFERENCE COMPARISON TABLE:\n")
        f.write("-" * 90 + "\n")
        f.write(f"{'Configuration':<28}{'imgsz':<8}{'conf':<8}{'ms/img':<10}{'Precision':<12}{'Recall':<10}{'mAP50':<10}{'mAP50-95':<10}\n")
        f.write("-" * 90 + "\n")
        for r in results:
            f.write(f"{r['config']:<28}{r['imgsz']:<8}{r['conf']:<8.2f}{r['ms_per_img']:<10.1f}{r['precision']:<12.4f}{r['recall']:<10.4f}{r['map50']:<10.4f}{r['map50_95']:<10.4f}\n")
        f.write("-" * 90 + "\n\n")

        f.write("PER-CLASS BREAKDOWN (AMBULANCE vs FIRE TRUCK):\n")
        f.write("-" * 90 + "\n")
        f.write(f"{'Configuration':<28}{'Class':<12}{'Precision':<12}{'Recall':<10}{'mAP50':<10}{'mAP50-95':<10}\n")
        f.write("-" * 90 + "\n")
        for r in results:
            amb = r['ambulance']
            fire = r['fire_truck']
            f.write(f"{r['config']:<28}{'ambulance':<12}{amb['precision']:<12.4f}{amb['recall']:<10.4f}{amb['map50']:<10.4f}{amb['map50_95']:<10.4f}\n")
            f.write(f"{'':<28}{'fire_truck':<12}{fire['precision']:<12.4f}{fire['recall']:<10.4f}{fire['map50']:<10.4f}{fire['map50_95']:<10.4f}\n")
            f.write("-" * 90 + "\n")
        f.write("\n")

        f.write("COMPARATIVE ANALYSIS & RUNTIME ESTIMATION FOR FULL VALIDATION SET (1,490 IMAGES):\n")
        f.write("-" * 90 + "\n")
        for r in results:
            est_sec = (r['ms_per_img'] * total_val_images) / 1000
            est_min = est_sec / 60
            delta_map50 = r['map50'] - baseline['map50']
            delta_p = r['precision'] - baseline['precision']
            delta_r = r['recall'] - baseline['recall']
            f.write(f"[{r['config']}]\n")
            f.write(f"  - Latency: {r['ms_per_img']:.1f} ms/image | Est. Full Val (1,490 imgs) Runtime: ~{est_min:.1f} minutes ({est_sec:.0f}s)\n")
            f.write(f"  - Precision vs Baseline: {delta_p:+.4f} ({r['precision']*100:.2f}% vs {baseline['precision']*100:.2f}%)\n")
            f.write(f"  - Recall vs Baseline:    {delta_r:+.4f} ({r['recall']*100:.2f}% vs {baseline['recall']*100:.2f}%)\n")
            f.write(f"  - mAP50 vs Baseline:     {delta_map50:+.4f} ({r['map50']*100:.2f}% vs {baseline['map50']*100:.2f}%)\n\n")

        f.write("=" * 90 + "\n")
    print(f"[SUCCESS] TXT report written to: {OUTPUT_TXT.resolve()}")
    print("=" * 80)

if __name__ == "__main__":
    main()
