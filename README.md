# AI Littering Detection CCTV System

An AI-powered CCTV prototype that automatically detects, tracks, and documents people dropping trash/litter in real-time. The system utilizes **YOLOv8** for object detection and **ByteTrack** for persistent tracking, combined with a **stateful trajectory-association engine** and a **rule-based event detector** to capture photographic and video evidence of violations.

---

## Features

1. **Persistent Person & Object Tracking**: Identifies and tracks people and 30+ portable classes of potential litter concurrently.
2. **Trajectory-Based Re-Association**: Solves tracking ID switching (link breaking) when objects are dropped and change orientation. If an object is lost and detected as a new ID on the ground, the system checks historical walking trails to re-link ownership.
3. **Littering Event Detection**: Evaluates violation conditions:
   * Object was carried by a person.
   * Object is dropped and remains stationary for $\ge 3$ seconds.
   * The owner walks away ($\ge 150$ pixels away or exits frame).
   * Automatically resets if the object is picked up again.
4. **Evidence Collection**: Creates date-organized folders (`Violations/YYYY-MM-DD/`) containing:
   * **Snapshots**: A JPEG image of the violation moment.
   * **Replay Clips**: A 10-second MP4 video clip containing the 5 seconds *before* the drop and 5 seconds *after* the trigger.
   * **Metadata**: A structured `metadata.json` logging event details.

---

## File Structure

* `yolo_detector.py` – Encapsulates model loading and multi-class tracking.
* `association.py` – Trajectory history mapping and object-person linkage.
* `event_detector.py` – State machine analyzing drops, stationary times, and walk-away distances.
* `evidence_collector.py` – Manages buffered video recording, image snapshot saves, and daily JSON logs.
* `main_tracking.py` – Entry script connecting webcam streams, drawing visual overlay bounding boxes, and displaying FPS.
* `README.md` – Setup and execution guide.

---

## Installation & Setup

### 1. Copy Files
Copy the python script files (`yolo_detector.py`, `association.py`, `event_detector.py`, `evidence_collector.py`, and `main_tracking.py`) into your project folder.

### 2. Set Up Virtual Environment (venv)
Open PowerShell (or CMD) in the project directory and run:
```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
Install the required packages in your active virtual environment:
```powershell
pip install ultralytics opencv-python numpy lap
```
*(Note: `lap` is required by Ultralytics for the linear assignment tracking algorithms).*

---

## How to Run

Activate your virtual environment and run `main_tracking.py`.

### 1. Run on Default Built-in Webcam (Index 0)
```powershell
python main_tracking.py --camera 0
```

### 2. Run on External USB Webcam (Index 1)
```powershell
python main_tracking.py --camera 1
```

### 3. Run on a Video File (For Testing)
```powershell
python main_tracking.py --camera path/to/littering_test.mp4
```

### 4. Advanced Run (GPU Optimized & High Sensitivity)
To run with a larger, more accurate model (`yolov8s.pt`) and low detection threshold (`0.12`) to capture flat/distant items on your USB camera:
```powershell
python main_tracking.py --camera 1 --model yolov8s.pt --conf 0.12
```

---

## Configuration Flags

| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--camera` | `str` | `0` | Camera index (e.g. `0`, `1`, `2`) or path to video file (`.mp4`, `.avi`). |
| `--model` | `str` | `yolov8s.pt` | YOLOv8 model weight filename (`yolov8n.pt`, `yolov8s.pt`, `yolov8m.pt`). |
| `--conf` | `float` | `0.20` | Detection confidence threshold (lower value makes it more sensitive). |

---

## Controls & Outputs

* **Focus Window**: Click on the webcam visual display.
* **Exit**: Press **'q'** on your keyboard to close streams and shut down.
* **Evidence Directory**: Open the generated `Violations/` folder to view recorded events.
