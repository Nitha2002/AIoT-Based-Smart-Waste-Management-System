"""
AIoT Smart Waste Management System
===================================
Real-time Waste Detection & Servo Control
- Captures frames from webcam/camera
- Classifies plastic waste using trained MobileNetV2 model
- Sends command to Arduino via Serial:
    '1' → Recyclable  → Servo rotates CLOCKWISE
    '0' → NonRecyclable → Servo rotates ANTI-CLOCKWISE
"""

import cv2
import torch
import serial
import time
import json
import numpy as np
from torchvision import transforms, models
import torch.nn as nn

# ─── Config ──────────────────────────────────────────────────────────────────
MODEL_PATH       = "waste_classifier.pt"
CLASS_MAP_PATH   = "class_mapping.json"
SERIAL_PORT      = "COM4"        # Change to '/dev/ttyUSB0' on Linux/Mac
BAUD_RATE        = 9600
CAMERA_INDEX     = 0
CONFIDENCE_THRESHOLD = 0.75      # Only act if confidence >= 75%
IMG_SIZE         = 224
DEVICE           = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Colors (BGR)
COLOR_RECYCLABLE    = (0, 200, 0)
COLOR_NONRECYCLABLE = (0, 0, 220)
COLOR_LOW_CONF      = (0, 165, 255)

# ─── Load Model ──────────────────────────────────────────────────────────────
def load_model():
    checkpoint = torch.load(MODEL_PATH, map_location=DEVICE)
    classes = checkpoint["classes"]

    model = models.mobilenet_v2(pretrained=False)
    model.classifier = nn.Sequential(
        nn.Dropout(0.3),
        nn.Linear(model.last_channel, 128),
        nn.ReLU(),
        nn.Linear(128, len(classes)),
    )
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    model.to(DEVICE)
    print(f"Model loaded. Classes: {classes}")
    return model, classes


# ─── Transforms ──────────────────────────────────────────────────────────────
infer_transform = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225]),
])


def classify_frame(model, frame, classes):
    """Run inference on a single frame. Returns (label, confidence)."""
    tensor = infer_transform(frame).unsqueeze(0).to(DEVICE)
    with torch.no_grad():
        logits = model(tensor)
        probs  = torch.softmax(logits, dim=1)[0]
    conf, idx = probs.max(0)
    return classes[idx.item()], conf.item()


# ─── Serial Connection ────────────────────────────────────────────────────────
def connect_serial():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)  # Wait for Arduino to reset
        print(f"Connected to Arduino on {SERIAL_PORT}")
        return ser
    except Exception as e:
        print(f"Serial connection failed: {e}. Running without Arduino.")
        return None


def send_command(ser, label):
    """Send '1' for Recyclable, '0' for NonRecyclable."""
    if ser is None:
        return
    cmd = b'1' if label == "Recyclable" else b'0'
    ser.write(cmd)
    print(f"Sent to Arduino: {cmd}")


# ─── Main Loop ───────────────────────────────────────────────────────────────
def main():
    model, classes = load_model()
    ser = connect_serial()
    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    print("\nWaste Detection Running. Press 'q' to quit.")
    print("=" * 50)

    last_command_time = 0
    COMMAND_COOLDOWN  = 3.0   # seconds between servo commands

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # ── Classify ──────────────────────────────────────────
        rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        label, confidence = classify_frame(model, rgb, classes)

        # ── Determine color & action ──────────────────────────
        now = time.time()
        if confidence >= CONFIDENCE_THRESHOLD:
            color = COLOR_RECYCLABLE if label == "Recyclable" else COLOR_NONRECYCLABLE
            status_text = f"{label} ({confidence*100:.1f}%)"

            # Send servo command with cooldown
            if now - last_command_time >= COMMAND_COOLDOWN:
                send_command(ser, label)
                last_command_time = now
        else:
            color = COLOR_LOW_CONF
            status_text = f"Uncertain ({confidence*100:.1f}%)"

        # ── Draw UI ───────────────────────────────────────────
        h, w = frame.shape[:2]

        # Background bar
        cv2.rectangle(frame, (0, 0), (w, 60), (30, 30, 30), -1)

        # Status text
        cv2.putText(frame, status_text, (15, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.1, color, 2)

        # Confidence bar
        bar_w = int((w - 30) * confidence)
        cv2.rectangle(frame, (15, 50), (15 + bar_w, 58), color, -1)

        # Label in top right
        arrow = "→ Recyclable Bin" if label == "Recyclable" else "→ Non-Recyclable Bin"
        cv2.putText(frame, arrow, (15, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        cv2.imshow("AIoT Waste Classifier", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    if ser:
        ser.close()


if __name__ == "__main__":
    main()
