import cv2
from ultralytics import YOLO

def main():
    # Load the YOLO model (YOLOv8 Nano is lightweight and fast for webcam)
    print("Loading YOLOv8 model...")
    model = YOLO("yolov8n.pt")
    
    # Open the webcam (0 is usually the default built-in webcam)
    print("Opening webcam...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open webcam. Make sure your webcam is connected and not in use by another program.")
        return
        
    print("Webcam successfully opened. Press 'q' to quit.")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to grab frame.")
            break
            
        # Run inference on the current frame.
        # Filter classes=[0] to only detect 'person'.
        # stream=True is used for memory efficiency when processing webcam/video streams.
        results = model(frame, classes=[0], stream=True)
        
        # Plot the detection results on the frame
        annotated_frame = frame.copy()
        for r in results:
            annotated_frame = r.plot()
            
        # Display the frame in a window
        cv2.imshow("YOLOv8 Webcam Person Detection", annotated_frame)
        
        # Break the loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    # Clean up and release the webcam
    cap.release()
    cv2.destroyAllWindows()
    print("Webcam released and windows closed.")

if __name__ == "__main__":
    main()
