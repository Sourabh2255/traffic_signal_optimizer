
from ultralytics import YOLO

model_path = r"C:\Users\Saurabh\Downloads\traffic-signal-optimizer-FINAL\traffic-signal-optimizer\models\best_emergency_vehicle.pt"

data_yaml = r"C:\Users\Saurabh\Downloads\traffic-signal-optimizer-FINAL\traffic-signal-optimizer\data\emergency_yolo\data.yaml"

model = YOLO(model_path)

for imgsz in [416, 640, 960]:
    for conf in [0.05, 0.10, 0.15, 0.25]:
        metrics = model.val(
            data=data_yaml,
            split="val",
            imgsz=imgsz,
            batch=2,
            device="cpu",
            conf=conf,
            plots=False,
            verbose=False
        )

        print(
            f"imgsz={imgsz}, conf={conf:.2f}, "
            f"Precision={metrics.box.mp:.3f}, "
            f"Recall={metrics.box.mr:.3f}, "
            f"mAP50={metrics.box.map50:.3f}"
        )
