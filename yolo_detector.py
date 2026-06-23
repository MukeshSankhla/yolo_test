import numpy as np

class YOLODetector:
    """
    A wrapper class for YOLOv8 object detection and tracking.
    Enables persistent tracking of specified classes (e.g. persons, bottles, cups)
    using ByteTrack.
    """
    def __init__(self, model_path="yolov8n.pt", person_class_ids=None, litter_class_ids=None, conf=0.25):
        from ultralytics import YOLO
        print(f"Initializing YOLO model with weights from: {model_path}")
        self.model = YOLO(model_path)
        self.conf = conf
        
        # Default COCO dataset classes:
        # 0: person
        # Portable items (litter classes):
        # 24: backpack, 25: umbrella, 26: handbag, 27: tie, 28: suitcase, 32: sports ball,
        # 39: bottle, 41: cup, 42: fork, 43: knife, 44: spoon, 45: bowl,
        # 46: banana, 47: apple, 48: sandwich, 49: orange, 50: broccoli, 51: carrot,
        # 52: hot dog, 53: pizza, 54: donut, 55: cake, 67: cell phone, 73: book,
        # 74: clock, 75: vase, 76: scissors, 77: teddy bear, 78: hair drier, 79: toothbrush
        self.person_class_ids = person_class_ids if person_class_ids is not None else [0]
        self.litter_class_ids = litter_class_ids if litter_class_ids is not None else [
            24, 25, 26, 27, 28, 32, 39, 41, 42, 43, 44, 45, 46, 47, 48, 49,
            50, 51, 52, 53, 54, 55, 67, 73, 74, 75, 76, 77, 78, 79
        ]
        
        self.all_classes = self.person_class_ids + self.litter_class_ids
        print(f"Tracking Person classes: {self.person_class_ids}")
        print(f"Tracking Litter classes: {self.litter_class_ids}")

    def track_frame(self, frame):
        """
        Runs tracking on a single frame.
        
        Args:
            frame: opencv BGR image frame
            
        Returns:
            tracked_persons: List of dicts representing detected people
            tracked_litter: List of dicts representing detected litter items
        """
        # Run tracking using ByteTrack
        # persist=True ensures tracking states are maintained across frames
        results = self.model.track(
            source=frame, 
            persist=True, 
            classes=self.all_classes, 
            tracker="bytetrack.yaml", 
            conf=self.conf,
            verbose=False
        )
        
        tracked_persons = []
        tracked_litter = []
        
        if not results or len(results) == 0:
            return tracked_persons, tracked_litter
            
        r = results[0]
        if r.boxes is None or len(r.boxes) == 0:
            return tracked_persons, tracked_litter
            
        names = self.model.names
        
        xyxy = r.boxes.xyxy.cpu().numpy()
        cls = r.boxes.cls.cpu().numpy().astype(int)
        conf = r.boxes.conf.cpu().numpy()
        
        # Extract tracking IDs. Under some circumstances (e.g. first frame or low confidence), 
        # boxes.id might not contain IDs yet.
        if r.boxes.id is not None:
            track_ids = r.boxes.id.cpu().numpy().astype(int)
        else:
            track_ids = [None] * len(cls)
            
        for i in range(len(cls)):
            class_id = cls[i]
            class_name = names.get(class_id, f"class_{class_id}")
            track_id = track_ids[i]
            bbox = tuple(map(int, xyxy[i]))  # (x1, y1, x2, y2)
            confidence = float(conf[i])
            
            detection = {
                "id": track_id,
                "bbox": bbox,
                "confidence": confidence,
                "class_name": class_name,
                "class_id": class_id
            }
            
            if class_id in self.person_class_ids:
                tracked_persons.append(detection)
            elif class_id in self.litter_class_ids:
                tracked_litter.append(detection)
                
        return tracked_persons, tracked_litter
