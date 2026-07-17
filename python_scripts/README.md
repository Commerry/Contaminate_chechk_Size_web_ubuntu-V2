# 🐍 Backend Server (Python/Flask)

**PSE Vision CM4 - Backend Server with Camera & PLC Integration**

---

## 📋 สารบัญ (Table of Contents)

1. [ภาพรวม (Overview)](#-ภาพรวม-overview)
2. [โครงสร้างไฟล์ (File Structure)](#-โครงสร้างไฟล์-file-structure)
3. [การติดตั้ง (Installation)](#-การติดตั้ง-installation)
4. [การใช้งาน (Usage)](#-การใช้งาน-usage)
5. [API Endpoints](#-api-endpoints)
6. [Configuration](#-configuration)
7. [PLC Integration](#-plc-integration)

---

## 📖 ภาพรวม (Overview)

Backend Server เป็นหัวใจหลักของระบบ PSE Vision CM4 ที่รับผิดชอบ:

- 📷 **Camera Control** - ควบคุมกล้อง OAK-D (DepthAI) และประมวลผลภาพ
- 📏 **Measurement** - วัดขนาดวัตถุ (Area, Width, Height) อัตโนมัติ
- 🔌 **PLC Communication** - เชื่อมต่อ PLC Siemens ผ่าน Snap7
- 🌐 **REST API** - Endpoints สำหรับ Frontend
- ⚡ **WebSocket** - Real-time communication (Socket.IO)
- 💾 **Data Storage** - บันทึกข้อมูลการวัดและรูปภาพ

---

## 📂 โครงสร้างไฟล์ (File Structure)

```
python_scripts/
│
├── backend_server.py              # ✨ Main Flask Server
├── backend_extension.py           # Extensions & Utilities
├── backend_requirements.txt       # Python dependencies
│
├── config.json                    # 🔧 Main Configuration
├── configurations.json            # Measurement configurations
├── lots.json                      # LOT management
├── machines.json                  # Machine list
│
├── system_config.py               # System settings module
├── measurement_utils.py           # Measurement algorithms
├── check_config.py                # Config validation
├── reset_camera.py                # Camera reset utility
│
├── plc/                           # 🔌 PLC Integration
│   ├── __init__.py
│   ├── plc_production.py          # Real PLC (Snap7)
│   └── plc_debug.py               # Debug mode (simulated)
│
└── database/                      # 💾 Database Models
    ├── __init__.py
    ├── db_config.py               # Database connection
    ├── db_service.py              # Database operations
    └── measurement_session.py     # Measurement data model
```

---

## 🚀 การติดตั้ง (Installation)

### Quick Install

```bash
# 1. Create virtual environment
python3.12 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\Activate.ps1  # Windows

# 2. Install dependencies
pip install -r backend_requirements.txt

# 3. Configure settings
cp config.example.json config.json
nano config.json  # Edit camera IP, PLC settings

# 4. Run server
python backend_server.py
```

### Dependencies

**Main packages:**
- `flask` (3.0.0) - Web framework
- `flask-socketio` (5.3.6) - WebSocket support
- `flask-cors` (4.0.0) - CORS support
- `depthai` (2.27.0.0) - OAK camera SDK
- `opencv-contrib-python` (4.10.0.84) - Image processing
- `numpy` (1.26.4) - Numerical computing
- `python-snap7` (≥1.3) - PLC communication

**Full list:** [backend_requirements.txt](backend_requirements.txt)

---

## 💻 การใช้งาน (Usage)

### Start Server

```bash
# Activate virtual environment
source venv/bin/activate

# Run backend server
python backend_server.py
```

**Server will start on:** `http://0.0.0.0:64020`

### Environment Variables

```bash
# Optional: Override config
export BACKEND_PORT=64020
export CAMERA_IP=10.2.100.51
export PLC_MODE=debug  # or production

python backend_server.py
```

### Production Mode

```bash
# Using PM2
pm2 start ecosystem.config.js

# Using Systemd
sudo systemctl start pse-vision-backend
```

---

## 🌐 API Endpoints

### Camera Endpoints

```http
GET  /api/camera/status           # Get camera status
POST /api/camera/connect          # Connect camera
POST /api/camera/disconnect       # Disconnect camera
POST /api/camera/capture          # Manual capture
GET  /api/camera/settings         # Get camera settings
POST /api/camera/settings         # Update camera settings
```

### PLC Endpoints

```http
GET  /api/plc/status              # Get PLC status
POST /api/plc/connect             # Connect to PLC
POST /api/plc/disconnect          # Disconnect PLC
POST /api/plc/trigger-debug       # Manual trigger (debug mode)
POST /api/plc/mode                # Switch PLC mode (debug/production)
GET  /api/plc/config              # Get PLC configuration
POST /api/plc/config              # Update PLC configuration
```

### Measurement Endpoints

```http
GET  /api/measurements            # Get measurement history
GET  /api/measurements/:id        # Get specific measurement
POST /api/measurements/clear      # Clear history
```

### Configuration Endpoints

```http
GET  /api/configurations          # Get all configurations
GET  /api/configurations/:id      # Get specific config
POST /api/configurations          # Create configuration
PUT  /api/configurations/:id      # Update configuration
DELETE /api/configurations/:id    # Delete configuration
```

### Machine Endpoints

```http
GET  /api/machines                # Get all machines
POST /api/machines                # Create machine
PUT  /api/machines/:id            # Update machine
DELETE /api/machines/:id          # Delete machine
```

### System Endpoints

```http
GET  /api/status                  # System status
GET  /api/stats                   # Statistics
POST /api/system/restart          # Restart backend
```

**📖 Full API Documentation:** [../docs/API_REFERENCE.md](../docs/API_REFERENCE.md)

---

## ⚙️ Configuration

### Main Config: `config.json`

```json
{
  "camera_active": 1,
  "network_camera_ip": "10.2.100.51",
  "camera_fps": 15,
  "frame_skip_rate": 4,
  "rubber_type": "white",
  "zoom_level": 1.0,
  
  "plc_enabled": true,
  "plc_mode": "debug",
  "plc_address": "192.168.1.100",
  "plc_db_num": 100,
  "plc_rack": 0,
  "plc_slot": 1,
  
  "backend_port": 64020,
  "debug": false,
  "log_level": "INFO"
}
```

### Camera Settings

| Key | Type | Description | Default |
|-----|------|-------------|---------|
| `camera_active` | int | Enable camera (0=off, 1=on) | 1 |
| `network_camera_ip` | string | OAK camera IP (for PoE) | "10.2.100.51" |
| `camera_fps` | int | Frame rate (5-30) | 15 |
| `frame_skip_rate` | int | Send 1 frame per N frames | 4 |
| `rubber_type` | string | "white" or "black" | "white" |
| `zoom_level` | float | Digital zoom (0.5-2.0) | 1.0 |

### PLC Settings

| Key | Type | Description | Default |
|-----|------|-------------|---------|
| `plc_enabled` | bool | Enable PLC integration | true |
| `plc_mode` | string | "debug" or "production" | "debug" |
| `plc_address` | string | PLC IP address | "192.168.1.100" |
| `plc_db_num` | int | Data Block number | 100 |
| `plc_rack` | int | PLC rack number | 0 |
| `plc_slot` | int | PLC slot number | 1 |

---

## 🔌 PLC Integration

### Debug Mode (ไม่ต้องมี PLC จริง)

```json
{
  "plc_enabled": true,
  "plc_mode": "debug"
}
```

**Features:**
- ✅ ไม่ต้องเชื่อมต่อ PLC จริง
- ✅ Auto-trigger ทุก 10 วินาที
- ✅ Manual trigger ผ่าน API
- ✅ Log แสดง [DEBUG] prefix

**Use case:** Development, Testing

---

### Production Mode (ต่อ PLC จริง)

```json
{
  "plc_enabled": true,
  "plc_mode": "production",
  "plc_address": "192.168.1.100",
  "plc_db_num": 100
}
```

**Features:**
- ✅ เชื่อมต่อ PLC Siemens S7-1200/1500
- ✅ อ่าน Trigger จาก PLC (DB Offset 0.0)
- ✅ เขียนผลการวัดกลับไป PLC
  - Offset 2: Area (REAL)
  - Offset 4: Width (REAL)
  - Offset 8: Height (REAL)
  - Offset 12: Status (INT)
  - Offset 16: Camera Status (INT)

**Use case:** Production Line

---

## 🐛 Troubleshooting

### Camera Not Detected

```bash
# Check USB connection
lsusb | grep Myriad

# Fix permissions
sudo usermod -aG plugdev $USER
sudo udevadm control --reload-rules
sudo reboot
```

### Port Already in Use

```bash
# Find and kill process
sudo lsof -i :64020
sudo kill -9 <PID>
```

### Module Not Found

```bash
# Make sure venv is activated
source venv/bin/activate

# Reinstall dependencies
pip install --force-reinstall -r backend_requirements.txt
```

### PLC Connection Failed

```bash
# Check network
ping 192.168.1.100

# Test Snap7
python -c "import snap7; print('Snap7 OK')"

# Use debug mode first
# Edit config.json: "plc_mode": "debug"
```

**📖 More solutions:** [../docs/TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md)

---

## 📞 Support

- **Documentation:** [../docs/README.md](../docs/README.md)
- **API Reference:** [../docs/API_REFERENCE.md](../docs/API_REFERENCE.md)
- **Issues:** https://github.com/pse/pse-vision-cm4/issues

---

**Made with ❤️ by PSE Vision Team**
