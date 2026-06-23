# Arduino Q (Debian 13 aarch64) - CCTV Littering Detection Setup & Run Guide

This guide provides step-by-step instructions to install Docker, set up dependencies, copy the project, and run the CCTV littering tracker on the Arduino Q board (Qualcomm Kryo-V2 aarch64 running Debian 13).

---

## 📋 Table of Contents
1. [Prerequisites & Copying Files](#1-prerequisites--copying-files)
2. [Step-by-Step Docker Installation Guide](#2-step-by-step-docker-installation-guide)
3. [Method A: Run using Docker & Docker Compose (Recommended)](#method-a-run-using-docker--docker-compose-recommended)
4. [Method B: Run Natively on the Board (Bare-Metal)](#method-b-run-natively-on-the-board-bare-metal)
5. [Command-Line Arguments & Tuning](#5-command-line-arguments--tuning)

---

## 1. Prerequisites & Copying Files

Before setting up the software, ensure:
- Your Arduino Q is connected to the internet.
- A USB webcam is plugged into the board (usually recognized as `/dev/video0`).

### Transfer the Project Files to the Board
From your host computer, copy the project files to the Arduino Q using `scp` (replace `username` and `board_ip` with your board's credentials):

```bash
# Execute this on your host machine to copy the project
scp -r /path/to/yolo_test username@board_ip:/home/username/yolo_test
```

Then, SSH into your board to continue the setup:
```bash
ssh username@board_ip
cd /home/username/yolo_test
```

---

## 2. Step-by-Step Docker Installation Guide

To run this application via containers, you must install Docker and Docker Compose on the Debian 13 (Trixie) board. Choose **one** of the two installation methods below:

### Option 2.1: Quick Installation via Debian Package Repositories (Simplest)
Debian 13 provides stable, pre-packaged versions of Docker directly in its default package source.

1. **Update package lists & install Docker and Docker Compose**:
   ```bash
   sudo apt-get update
   sudo apt-get install -y docker.io docker-compose-v2
   ```

2. **Start and enable the Docker service**:
   ```bash
   sudo systemctl enable --now docker
   ```

---

### Option 2.2: Official Docker Repository Installation (Latest Stable version)
If you want the official, cutting-edge build directly from Docker, use these steps:

1. **Remove any conflicting packages**:
   ```bash
   for pkg in docker.io docker-doc docker-compose podman-docker containerd runc; do sudo apt-get remove $pkg; done
   ```

2. **Install prerequisite tools**:
   ```bash
   sudo apt-get update
   sudo apt-get install -y ca-certificates curl gnupg
   ```

3. **Add Docker's official GPG key**:
   ```bash
   sudo install -m 0755 -d /etc/apt/keyrings
   sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
   sudo chmod a+r /etc/apt/keyrings/docker.asc
   ```

4. **Add the Docker APT repository**:
   *Note: Since Debian 13 (Trixie) is currently testing, we use the `bookworm` stable repository as a fallback if trixie builds are not yet fully indexed.*
   ```bash
   echo \
     "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
     bookworm stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
   sudo apt-get update
   ```

5. **Install Docker Engine, CLI, Containerd, and Compose Plugin**:
   ```bash
   sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
   ```

---

### 🚨 Critical Step: Run Docker Without Sudo
By default, Docker commands require `sudo`. Run the following to allow your current user to run Docker commands natively:

1. **Add your user to the `docker` group**:
   ```bash
   sudo usermod -aG docker $USER
   ```
2. **Apply the new group membership** (or log out and log back in):
   ```bash
   newgrp docker
   ```
3. **Verify the installation**:
   ```bash
   docker run hello-world
   ```

---

## Method A: Run using Docker & Docker Compose (Recommended)

Docker handles PyTorch compilation, OpenCV dependencies, and tracking requirements internally, ensuring they don't conflict with your board's system files.

### 1. Build and Run the App
From your project directory `/home/username/yolo_test`:

```bash
# Build the Docker image and start the container in the background
docker compose -f arduino_q/docker-compose.yml up --build -d
```
*The image will build on the board, compile `lap`, cache packages, and start running.*

### 2. Monitoring and Troubleshooting
- **View live tracking logs**:
  ```bash
  docker compose -f arduino_q/docker-compose.yml logs -f
  ```
- **Stop the tracker**:
  ```bash
  docker compose -f arduino_q/docker-compose.yml down
  ```

### 3. Customizing the Configuration
- **Camera Selection**: The default configurations mount `/dev/video0`. If your camera index is different, open [docker-compose.yml](file:///c:/Users/mukes/Documents/yolo_test/arduino_q/docker-compose.yml) and update:
  - `devices`: change `/dev/video0:/dev/video0` to `/dev/video1:/dev/video0` (left side is host, right side is container).
- **Evidence Retrieval**: Captured violations are saved directly to the `/home/username/yolo_test/Violations` directory on the host board.

---

## Method B: Run Natively on the Board (Bare-Metal)

If you prefer to run the script outside Docker, run the provided automated setup script.

### 1. Run the Setup Script
From the project folder `/home/username/yolo_test`:
```bash
# Grant execution permissions
chmod +x arduino_q/setup_board.sh

# Run the installation
./arduino_q/setup_board.sh
```
*This installs compiler dependencies (`gcc`, `g++`, `python3-dev`), sets up a virtual environment (`venv`), and runs `pip install`.*

### 2. Run the Application
Activate the virtual environment and execute the script in **headless mode** (required for X11-free terminal sessions):
```bash
source venv/bin/activate
python main_tracking.py --camera 1 --headless
```

---

## 5. Command-Line Arguments & Tuning

You can pass arguments to customize the detection and tracking parameters:

| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--camera` | `str` | `0` | Camera device index (e.g. `0` for `/dev/video0`, `1` for `/dev/video1`) or video file path. |
| `--model` | `str` | `yolov8s.pt` | Model weights: `yolov8n.pt` (faster CPU FPS) or `yolov8s.pt` (higher accuracy). |
| `--conf` | `float`| `0.20` | Confidence threshold for trash/person detections. |
| `--headless`| `bool` | `False` | Must be set to `--headless` when running on the board to prevent GUI crash. |

### Performance Optimization Tip for Embedded CPU
To achieve the maximum possible FPS (frames per second) on the 4-core Qualcomm Kryo CPU, switch from the default `yolov8s.pt` model to the lightweight **YOLOv8 Nano** model:
```bash
# In Native venv
python main_tracking.py --camera 1 --headless --model yolov8n.pt

# If using Docker, edit docker-compose.yml command block:
# command: ["--camera", "1", "--model", "yolov8n.pt"]
```

---

## 🛠️ Troubleshooting: Disk Space Issues ("No space left on device")

On the Arduino Q, the system root partition `/` has only **9.8 GB** (with ~2.7 GB free), whereas `/home/arduino` has **18 GB** (with ~15 GB free). By default, Docker stores all cache, images, and containers in `/var/lib/docker/` (on the root `/` partition), causing package compilation or container builds to crash with:
`ERROR: Could not install packages due to an OSError: [Errno 28] No space left on device`

To fix this, move Docker's storage root to the larger `/home/arduino` partition using these steps:

### Step 1: Stop the Docker Service
```bash
sudo systemctl stop docker docker.socket
```

### Step 2: Create a Storage Directory on the `/home` partition
```bash
sudo mkdir -p /home/arduino/docker
```

### Step 3: Configure Docker to use the new Storage Root
Create or edit the Docker daemon configuration file `/etc/docker/daemon.json`:
```bash
sudo nano /etc/docker/daemon.json
```
Add the following configuration:
```json
{
  "data-root": "/home/arduino/docker"
}
```
*(Save the file and exit: `Ctrl+O`, `Enter`, `Ctrl+X` in nano).*

### Step 4: Sync Existing Docker Data (Optional)
If you want to keep any images/configurations you already downloaded:
```bash
sudo rsync -aP /var/lib/docker/ /home/arduino/docker/
```

### Step 5: Start Docker Service
```bash
sudo systemctl start docker
```

### Step 6: Verify and Clean Up
1. Verify Docker is running on the new path:
   ```bash
   docker info | grep "Docker Root Dir"
   ```
   *It should output: `Docker Root Dir: /home/arduino/docker`*

2. Clean up build caches and unused data to reclaim space on `/`:
   ```bash
   docker builder prune -a -f
   docker system prune -a -f
   ```

3. If everything works, you can safely remove the old directory to free up space on `/`:
   ```bash
   sudo rm -rf /var/lib/docker
   ```

