import os
import cv2
import json
import time
from collections import deque

class EvidenceCollector:
    """
    Handles saving evidence (snapshots, video clips, and metadata logs)
    when a littering violation occurs. Maintains a rolling frame buffer to capture
    the action leading up to the violation.
    """
    def __init__(self, violations_dir="Violations", pre_event_frames=75, post_event_frames=75, default_fps=10.0):
        self.violations_dir = violations_dir
        self.pre_event_frames = pre_event_frames
        self.post_event_frames = post_event_frames
        self.default_fps = default_fps
        
        # Rolling buffer for pre-event frames
        self.frame_buffer = deque(maxlen=self.pre_event_frames)
        
        # Recording state
        self.is_recording = False
        self.frames_to_record = 0
        self.video_writer = None
        self.current_event_id = None
        self.current_date_str = None
        self.current_metadata = None

    def add_frame(self, frame):
        """
        Adds the current frame to the rolling buffer.
        If a recording is active, writes the frame to the video file.
        """
        # Store a copy in the rolling buffer
        self.frame_buffer.append(frame.copy())
        
        if self.is_recording and self.video_writer is not None:
            self.video_writer.write(frame)
            self.frames_to_record -= 1
            
            if self.frames_to_record <= 0:
                self._stop_recording()

    def trigger_violation(self, violation_info, current_frame):
        """
        Triggers evidence collection for a violation.
        Saves a JPEG snapshot and starts recording the MP4 clip (pre-event + post-event).
        """
        if self.is_recording:
            # Already recording an event; ignore new triggers until complete
            return
            
        self.current_date_str = time.strftime("%Y-%m-%d")
        daily_dir = os.path.join(self.violations_dir, self.current_date_str)
        os.makedirs(daily_dir, exist_ok=True)
        
        # 1. Determine next incremental event ID (event_001, event_002, etc.)
        event_num = 1
        if os.path.exists(daily_dir):
            files = [f for f in os.listdir(daily_dir) if f.startswith("event_") and f.endswith(".jpg")]
            if files:
                nums = []
                for f in files:
                    try:
                        # Extract number from "event_001.jpg" -> 1
                        num_part = f.split("_")[1].split(".")[0]
                        nums.append(int(num_part))
                    except (IndexError, ValueError):
                        continue
                if nums:
                    event_num = max(nums) + 1
                    
        self.current_event_id = f"event_{event_num:03d}"
        
        # 2. Save the JPEG snapshot of the violation detection moment
        snapshot_path = os.path.join(daily_dir, f"{self.current_event_id}.jpg")
        cv2.imwrite(snapshot_path, current_frame)
        print(f"\n[EVIDENCE] Saved violation snapshot to: {snapshot_path}")
        
        # 3. Initialize video recording (MP4)
        video_path = os.path.join(daily_dir, f"{self.current_event_id}.mp4")
        height, width = current_frame.shape[:2]
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.video_writer = cv2.VideoWriter(video_path, fourcc, self.default_fps, (width, height))
        
        if not self.video_writer.isOpened():
            print(f"[EVIDENCE ERROR] Could not open VideoWriter for {video_path}")
            self.video_writer = None
            return
            
        # Write pre-event frames from rolling buffer
        print(f"[EVIDENCE] Writing {len(self.frame_buffer)} pre-event buffer frames to video...")
        for buffered_frame in self.frame_buffer:
            self.video_writer.write(buffered_frame)
            
        # Set up state to record post-event frames
        self.is_recording = True
        self.frames_to_record = self.post_event_frames
        
        # Store metadata to save when recording completes
        self.current_metadata = {
            "event_id": self.current_event_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(violation_info["timestamp"])),
            "offender_id": int(violation_info["owner_id"]),
            "item_class": violation_info["class_name"],
            "litter_track_id": int(violation_info["litter_id"]),
            "snapshot_file": f"{self.current_event_id}.jpg",
            "video_file": f"{self.current_event_id}.mp4"
        }

    def _stop_recording(self):
        """
        Releases the VideoWriter and appends the metadata to the daily JSON file.
        """
        if self.video_writer is not None:
            self.video_writer.release()
            self.video_writer = None
            
        self.is_recording = False
        print(f"[EVIDENCE] Finished recording clip for event: {self.current_event_id}")
        
        if self.current_metadata is not None:
            daily_dir = os.path.join(self.violations_dir, self.current_date_str)
            metadata_path = os.path.join(daily_dir, "metadata.json")
            
            # Read existing metadata list or start a new one
            data = {"events": []}
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, "r") as f:
                        data = json.load(f)
                except Exception as e:
                    print(f"[EVIDENCE WARNING] Failed to read existing metadata.json: {e}")
                    
            # Append new event metadata
            data["events"].append(self.current_metadata)
            
            # Write back to metadata.json
            try:
                with open(metadata_path, "w") as f:
                    json.dump(data, f, indent=4)
                print(f"[EVIDENCE] Saved metadata to: {metadata_path}\n")
            except Exception as e:
                print(f"[EVIDENCE ERROR] Failed to write metadata.json: {e}")
                
        # Reset state
        self.current_event_id = None
        self.current_metadata = None
