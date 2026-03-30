# AIoT-Based Smart Waste Management System

A smart waste management system developed as a final year B.Tech project at **Ilahia College of Engineering and Technology**, APJ Abdul Kalam Technological University, Kerala (2024).

> **Published:** "A Comparative Study on AIoT Based Smart Waste Management System" — *Journal of Network and Information Security* (Accepted)

---

## 👥 Team

| Name | Roll No |
|---|---|
| Diya Syam | ICE20CS040 |
| Kiran K Anish | ICE20CS052 |
| Nitha Eldho | ICE20CS073 |
| Shanima V S | ICE20CS085 |

**Guide:** Dr. Sujith Kumar P S, Professor, Dept. of CSE, ICET

---

## 📁 Project Structure

```
aiot-waste-management/
│
├── webapp/
│   └── index.html          ← Web app (User / Worker / Admin portals)
│
├── ml_model/
│   ├── train.py            ← Model training (MobileNetV2)
│   └── detect.py           ← Real-time detection + Arduino serial
│
├── arduino/
│   └── esp32_main.ino      ← ESP32 firmware (sensors + servo + Wi-Fi)
│
├── backend/
│   └── app.py              ← Flask REST API server
│
├── requirements.txt
└── README.md
```

---

## 🚀 How to Run

### Web App
Just open `webapp/index.html` in any browser — no server needed.

**Login credentials:**
- 🛡️ Admin: `admin` / `admin123`
- 👤 User / 🚛 Worker: Register first (Worker code: `WORKER2024`)

### ML Model
```bash
pip install -r requirements.txt
cd ml_model
python train.py      # Train the model
python detect.py     # Run real-time detection
```

### Backend Server
```bash
cd backend
python app.py        # Runs on http://localhost:5000
```

### Arduino
- Open `arduino/esp32_main.ino` in Arduino IDE
- Update `SSID`, `PASSWORD`, `SERVER_URL`
- Select board: **ESP32 Dev Module** → Flash

---

## 🧰 Hardware

| Component | Purpose |
|---|---|
| ESP32 | Wi-Fi + sensor hub |
| Arduino Uno | Servo motor control |
| HC-SR04 Ultrasonic (×2) | Fill level detection |
| HX711 Load Cell | Weight measurement |
| Servo Motor SG90 | Waste segregation |
| Camera | Plastic classification |

---

## 💻 Tech Stack

| Layer | Technology |
|---|---|
| ML Model | Python, PyTorch, MobileNetV2, OpenCV |
| Firmware | Arduino IDE (C++) |
| Backend | Flask, SQLAlchemy, SQLite |
| Web App | HTML, CSS, JavaScript (localStorage) |

---

## 📊 Results

| Metric | Value |
|---|---|
| Model Accuracy | ~90% |
| Data Parsing Speed | 6 GB/min |
| Metadata Query Time | 0.35 sec |
| Alert Threshold (Level) | < 10 cm |
| Alert Threshold (Weight) | > 5 kg |
