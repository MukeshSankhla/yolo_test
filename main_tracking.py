import cv2
import time
import argparse
from yolo_detector import YOLODetector
from association import LitterAssociator
from event_detector import LitterEventDetector
from evidence_collector import EvidenceCollector

def main():
    # Set up command-line arguments to allow selecting different cameras, models, or confidence thresholds
    parser = argparse.ArgumentParser(description="AI Littering CCTV System")
    parser.add_argument(
        "--camera", 
        type=str, 
        default="0", 
        help="Webcam index (e.g. 0, 1, 2) or path to a video file (e.g. path/to/video.mp4)"
    )
    parser.add_argument(
        "--model", 
        type=str, 
        default="yolov8s.pt", 
        help="YOLOv8 model weight file (default: yolov8s.pt for higher accuracy)"
    )
    parser.add_argument(
        "--conf", 
        type=float, 
        default=0.20, 
        help="Detection confidence threshold (default: 0.20)"
    )
    args = parser.parse_args()
    
    # Parse source: if it's a number, convert to int for OpenCV camera index, otherwise keep as string path
    try:
        camera_source = int(args.camera)
        print(f"Using camera index: {camera_source}")
    except ValueError:
        camera_source = args.camera
        print(f"Using video file source: {camera_source}")
        
    # Initialize the custom YOLO detector with custom model and confidence threshold
    detector = YOLODetector(model_path=args.model, conf=args.conf)
    
    # Initialize the Litter Associator
    associator = LitterAssociator(distance_threshold=120, max_stale_frames=100)
    
    # Initialize the Litter Event Detector
    event_detector = LitterEventDetector(stationary_time_threshold=3.0, walk_away_distance=150)
    
    # Initialize the Evidence Collector
    evidence_collector = EvidenceCollector(pre_event_frames=75, post_event_frames=75, default_fps=10.0)
    
    print(f"Opening video source: {camera_source}...")
    cap = cv2.VideoCapture(camera_source)
    
    if not cap.isOpened():
        print(f"Error: Could not open source {camera_source}. If using an external USB webcam, try --camera 1 or --camera 2.")
        return
        
    print("Video source successfully opened. Press 'q' in the window to quit.")
    
    prev_time = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to grab frame or reached end of video stream.")
            break
            
        # Run detection and tracking
        tracked_persons, tracked_litter = detector.track_frame(frame)
        
        # Run association logic (Phase 3)
        tracked_litter = associator.associate(tracked_persons, tracked_litter)
        
        # Run event detection logic (Phase 4)
        tracked_litter, violations = event_detector.update(tracked_persons, tracked_litter)
        
        # Create a copy of the frame to draw all annotations on
        annotated_frame = frame.copy()
        
        # Calculate FPS
        curr_time = time.time()
        fps = 1.0 / (curr_time - prev_time) if prev_time > 0 else 0.0
        prev_time = curr_time
        cv2.putText(annotated_frame, f"System FPS: {fps:.1f}", (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
        # Map person IDs to their info for quick lookup when drawing lines
        person_map = {p["id"]: p for p in tracked_persons if p["id"] is not None}
        
        # Check if any active violation exists to display screen warning banner
        any_violation = any(l.get("event_status") == "violation" for l in tracked_litter)
        if any_violation:
            # Flashing visual warning banner on top
            overlay = annotated_frame.copy()
            cv2.rectangle(overlay, (0, 0), (annotated_frame.shape[1], 50), (0, 0, 255), -1)
            cv2.addWeighted(overlay, 0.4, annotated_frame, 0.6, 0, annotated_frame)
            
            if int(time.time() * 2) % 2 == 0:
                cv2.putText(annotated_frame, "WARNING: LITTERING DETECTED", (annotated_frame.shape[1] // 2 - 190, 35), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
        
        # Draw blinking [REC] indicator if evidence recording is active
        if evidence_collector.is_recording:
            if int(time.time() * 2) % 2 == 0:
                cv2.putText(annotated_frame, "REC", (annotated_frame.shape[1] - 70, 35), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)
                cv2.circle(annotated_frame, (annotated_frame.shape[1] - 90, 27), 6, (0, 0, 255), -1)
                
        # 1. Draw detected/tracked persons (Green boxes)
        for person in tracked_persons:
            bbox = person["bbox"]
            track_id = person["id"]
            conf = person["confidence"]
            
            x1, y1, x2, y2 = bbox
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            label = f"Person #{track_id}" if track_id is not None else "Person (Detecting...)"
            label += f" ({conf:.2f})"
            
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(annotated_frame, (x1, y1 - 22), (x1 + w + 4, y1), (0, 255, 0), -1)
            cv2.putText(annotated_frame, label, (x1 + 2, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
            
        # 2. Draw detected/tracked litter and association lines
        for litter in tracked_litter:
            bbox = litter["bbox"]
            track_id = litter["id"]
            conf = litter["confidence"]
            class_name = litter["class_name"]
            
            associated_person_id = litter.get("associated_person_id")
            owner_person_id = litter.get("owner_person_id")
            event_status = litter.get("event_status", "unknown")
            time_since_drop = litter.get("time_since_drop", 0.0)
            
            lx1, ly1, lx2, ly2 = bbox
            lcx = (lx1 + lx2) // 2
            lcy = (ly1 + ly2) // 2
            
            if event_status == "violation":
                box_color = (0, 0, 255)
                label = f"LITTER VIOLATION! by #{owner_person_id}"
            elif event_status == "carrying":
                box_color = (255, 255, 0)
                label = f"{class_name} #{track_id} (held by #{associated_person_id})"
            elif event_status == "dropped":
                box_color = (0, 165, 255)
                label = f"{class_name} #{track_id} (dropped by #{owner_person_id}) - {time_since_drop:.1f}s"
            else:
                box_color = (128, 128, 128)
                label = f"{class_name} #{track_id}"
                
            label += f" ({conf:.2f})"
            
            # Draw litter box
            cv2.rectangle(annotated_frame, (lx1, ly1), (lx2, ly2), box_color, 2)
            
            # Draw label banner
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(annotated_frame, (lx1, ly1 - 22), (lx1 + w + 4, ly1), box_color, -1)
            cv2.putText(annotated_frame, label, (lx1 + 2, ly1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
            
            # Draw association lines
            target_owner_id = associated_person_id if associated_person_id is not None else owner_person_id
            if target_owner_id is not None and target_owner_id in person_map:
                p_bbox = person_map[target_owner_id]["bbox"]
                px1, py1, px2, py2 = p_bbox
                pcx = (px1 + px2) // 2
                pcy = (py1 + py2) // 2
                
                line_color = box_color
                if event_status == "carrying":
                    cv2.line(annotated_frame, (lcx, lcy), (pcx, pcy), line_color, 1, cv2.LINE_AA)
                else:
                    dist = math.sqrt((lcx - pcx) ** 2 + (lcy - pcy) ** 2)
                    steps = int(dist / 10)
                    if steps > 0:
                        for step in range(0, steps, 2):
                            t1 = step / steps
                            t2 = min(1.0, (step + 1) / steps)
                            x_start = int(lcx + t1 * (pcx - lcx))
                            y_start = int(lcy + t1 * (pcy - lcy))
                            x_end = int(lcx + t2 * (pcx - lcx))
                            y_end = int(lcy + t2 * (pcy - lcy))
                            cv2.line(annotated_frame, (x_start, y_start), (x_end, y_end), line_color, 1, cv2.LINE_AA)
            
        # Feed the fully annotated frame to the evidence collector rolling buffer
        evidence_collector.add_frame(annotated_frame)
        
        # Trigger evidence collection for any newly reported violations
        for violation in violations:
            local_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(violation["timestamp"]))
            print(f"\n[ALERT] !!! LITTERING VIOLATION DETECTED !!!")
            print(f"Time: {local_time}")
            print(f"Offender: Person #{violation['owner_id']}")
            print(f"Object: {violation['class_name']} #{violation['litter_id']}")
            print(f"Location bbox: {violation['bbox']}")
            print("-" * 35)
            
            evidence_collector.trigger_violation(violation, annotated_frame)
            
        # Display window
        cv2.imshow("AI Littering CCTV - Person & Garbage Tracking", annotated_frame)
        
        # Quit if 'q' key is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    # Clean up resources
    cap.release()
    cv2.destroyAllWindows()
    print("CCTV Tracking stopped. Webcam and windows closed.")

import math

if __name__ == "__main__":
    main()
