# 🎯 PSE Vision CM4

**ระบบตรวจสอบขนาดและคุณภาพวัตถุอัตโนมัติสำหรับ Raspberry Pi CM4**  
*Automated Object Measurement & Quality Inspection System*

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/pse/pse-vision-cm4)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Node](https://img.shields.io/badge/node-20.x-green.svg)](https://nodejs.org/)

---

## 📚 Quick Links

- 🚀 **[Installation Guide](docs/INSTALLATION.md)** - คู่มือติดตั้งแบบละเอียด
- 📖 **[Documentation](docs/README.md)** - เอกสารทั้งหมด
- 🐛 **[Troubleshooting](docs/TROUBLESHOOTING.md)** - แก้ปัญหาที่พบบ่อย
- 🛠️ **[Scripts](scripts/README.md)** - สคริปต์ติดตั้งและ deploy

---

## 🌟 ภาพรวมระบบ (System Overview)

PSE Vision CM4 เป็นระบบตรวจสอบขนาดวัตถุอัตโนมัติที่ออกแบบสำหรับการใช้งานใน **Production Line** รองรับการเชื่อมต่อกับ **PLC Siemens** ผ่าน Snap7 Protocol

### ✨ คุณสมบัติหลัก (Key Features)

- 📷 **Real-time Camera Feed** - กล้อง OAK-D ความละเอียดสูง พร้อม Depth Sensing
- 📏 **Automatic Measurement** - วัดขนาด Area, Width, Height อัตโนมัติ (มม.)
- 🔌 **PLC Integration** - เชื่อมต่อ PLC Siemens S7-1200/1500 ผ่าน Snap7
- 🎯 **Quality Inspection** - ตรวจสอบ Pass/Fail ตามค่ามาตรฐาน
- 📊 **Statistics Dashboard** - แดชบอร์ดแสดงสถิติแบบ Real-time
- 💾 **Data Logging** - บันทึกข้อมูลการวัดทั้งหมด
- 🌐 **Web Interface** - หน้าเว็บจัดการระบบ (Vue.js 3)
- 🚀 **Production Ready** - รองรับ PM2, Systemd, Auto-start

---

## 🚀 Quick Start

### ⚡ One-Command Installation

```bash
# Clone repository
git clone https://github.com/pse/pse-vision-cm4.git
cd pse-vision-cm4

# Install everything (takes ~15-20 minutes)
sudo ./scripts/install/install_all.sh
```

**สคริปต์จะติดตั้ง:**
- ✅ Python 3.12 + Dependencies (Flask, DepthAI, OpenCV, Snap7)
- ✅ Node.js 20 LTS + npm
- ✅ Build Frontend (Vue.js → dist/)
- ✅ Setup Systemd Service (auto-start on boot)
- ✅ Setup PM2 Process Manager

### 🎮 Start System

```bash
# Method 1: Start script (easy)
./start.sh

# Method 2: Systemd Service (production)
sudo systemctl start pse-vision-backend

# Method 3: PM2 (recommended for development)
pm2 start ecosystem.config.js
```

### 🌐 Access Web Interface

```
http://localhost:64020              # Local machine
http://10.2.100.94:64020           # From network
```

**📖 Full installation guide:** [docs/INSTALLATION.md](docs/INSTALLATION.md)

---

## �️ System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   PSE Vision CM4                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐    ┌──────────────┐                 │
│  │  OAK-D Cam   │───▶│   Backend    │                 │
│  │  (USB/PoE)   │    │  Flask API   │                 │
│  └──────────────┘    │  Socket.IO   │                 │
│                      │  (Port 64020)│                 │
│                      └───────┬──────┘                 │
│                              │                         │
│                      ┌───────▼──────┐                 │
│  ┌──────────────┐   │   Admin Web   │                │
│  │  PLC S7-1200 │◀──│   Vue.js 3    │                │
│  │   (Snap7)    │   │   Vite 5.4    │                │
│  └──────────────┘   └──────────────┘                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## � Project Structure

```
pse-vision-cm4/
│
├── 📁 docs/                        # 📚 Documentation
│   ├── README.md                   # Docs index
│   ├── INSTALLATION.md             # Installation guide
│   ├── TROUBLESHOOTING.md          # Problem solving
│   └── API_REFERENCE.md            # API documentation
│
├── 📁 scripts/                     # 🛠️ Installation & Deployment
│   ├── install/                    # Install scripts
│   ├── deploy/                     # Deploy scripts
│   ├── setup/                      # Service setup
│   └── utils/                      # Utilities
│
├── 📁 config/                      # ⚙️ Configuration
│   ├── database/                   # DB schemas
│   └── db_config.json              # DB connection
│
├── 📁 python_scripts/              # 🐍 Backend (Flask)
│   ├── backend_server.py           # Main server
│   ├── config.json                 # Backend config
│   ├── system_config.py            # System settings
│   ├── measurement_utils.py        # Measurement logic
│   ├── plc/                        # PLC integration
│   │   ├── plc_production.py       # Real PLC (Snap7)
│   │   └── plc_debug.py            # Debug mode
│   └── database/                   # Database models
│
├── 📁 frontend/                    # 🌐 Admin Web (Vue.js)
│   ├── src/                        # Source code
│   │   ├── App.vue                 # Main app
│   │   ├── components/             # Vue components
│   │   └── stores/                 # Pinia stores
│   ├── public/                     # Static assets
│   ├── dist/                       # Built files (production)
│   ├── package.json
│   └── vite.config.js
│
├── README.md                       # 📖 This file
├── package.json                    # Dev launcher
├── ecosystem.config.js             # PM2 config
├── start.sh                        # Start script (Linux)
└── config.json                     # Main config
```

---

## ⚙️ Configuration

### Main Config: `python_scripts/config.json`

```json
{
  "camera_active": 1,
  "network_camera_ip": "10.2.100.51",
  "camera_fps": 15,
  "rubber_type": "white",
  
  "plc_enabled": true,
  "plc_mode": "debug",         // "debug" or "production"
  "plc_address": "192.168.1.100",
  "plc_db_num": 100,
  
  "backend_port": 64020,
  "frontend_port": 64021
}
```

### PLC Configuration

**Debug Mode** (ทดสอบโดยไม่ต้องมี PLC จริง):
```json
{
  "plc_enabled": true,
  "plc_mode": "debug"
}
```

**Production Mode** (ต่อ PLC จริง):
```json
{
  "plc_enabled": true,
  "plc_mode": "production",
  "plc_address": "192.168.1.100",
  "plc_db_num": 100,
  "plc_rack": 0,
  "plc_slot": 1
}
```

---

## 🛠️ Development

### Backend Development

```bash
cd python_scripts
source ../venv/bin/activate
python backend_server.py
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev    # Dev server (Vite) port 5173
npm run build  # Build to dist/
```

---

## 🐛 Troubleshooting

### Camera Not Detected?
```bash
lsusb | grep Myriad
sudo usermod -aG plugdev $USER
sudo udevadm control --reload-rules
sudo reboot
```

### Port Already in Use?
```bash
sudo lsof -i :64020
sudo kill -9 <PID>
```

### Module Not Found?
```bash
source venv/bin/activate
pip install -r python_scripts/backend_requirements.txt
```

**📖 More solutions:** [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

---

## 📊 System Requirements

### Minimum
- **CPU:** Raspberry Pi CM4 (4-core ARM) or equivalent
- **RAM:** 2GB
- **Storage:** 16GB
- **Camera:** OAK-D (USB or PoE)

### Recommended
- **CPU:** Raspberry Pi CM4 (8GB) or Intel i5+
- **RAM:** 4GB+
- **Storage:** 32GB SSD
- **Network:** Gigabit Ethernet

---

## 🛠️ Technology Stack

### Backend
- **Python 3.12** - Core language
- **Flask 3.0** - Web framework
- **Flask-SocketIO 5.3** - Real-time WebSocket
- **DepthAI 2.27** - OAK camera SDK
- **OpenCV 4.10** - Image processing
- **python-snap7 ≥1.3** - PLC communication

### Frontend
- **Vue.js 3.4** - UI framework (Composition API)
- **Vite 5.4** - Build tool
- **Socket.IO Client 4.8** - Real-time connection
- **Pinia 2.1** - State management

### Deployment
- **PM2** - Process manager
- **Systemd** - Service management (Linux)

---

## 📞 Support

- **Documentation:** [docs/README.md](docs/README.md)
- **Email:** support@pse-vision.com
- **Issues:** https://github.com/pse/pse-vision-cm4/issues

---

## 📝 License

Copyright © 2026 PSE Vision Team. All rights reserved.

---

**Made with ❤️ by PSE Vision Team**

🚀 **Ready to start?** → [Installation Guide](docs/INSTALLATION.md)

```powershell
cd user_display
npm install
npm start         # Dev mode
npm run dist:win  # Build installer
```

---

## 📊 System Requirements

### เครื่องเซิร์ฟเวอร์ (Backend)
- **OS:** Windows 10/11 (64-bit)
- **CPU:** Intel i5+ (แนะนำ i7+)
- **RAM:** 8 GB+ (แนะนำ 16 GB+)
- **Storage:** 10 GB
- **Camera:** OAK-D Camera (DepthAI)
- **Network:** Ethernet 1 Gbps

### เครื่องคนงาน (Desktop App)
- **OS:** Windows 10/11 (64-bit)
- **CPU:** Intel i3+
- **RAM:** 4 GB+
- **Storage:** 2 GB
- **Network:** LAN connection to Backend

---

## 🔍 Troubleshooting

### Backend รันไม่ได้

```powershell
# ตรวจสอบ Python dependencies
cd python_scripts
pip install -r backend_requirements.txt --upgrade
```

### Frontend Build ล้มเหลว

```powershell
cd frontend
Remove-Item -Recurse -Force node_modules
npm install --legacy-peer-deps
npm run build
```

### Desktop App Build ล้มเหลว

```powershell
cd user_display
Remove-Item -Recurse -Force node_modules
npm install --legacy-peer-deps
npm run dist:win
```

### Port 64020 ถูกใช้งาน

```powershell
# หา process ที่ใช้ port
netstat -ano | findstr :64020
# ปิด process
taskkill /PID [PID-NUMBER] /F
```

---

## 🔐 Security Notes

- Backend รันบน `0.0.0.0:64020` (เปิดให้เครือข่ายเข้าถึงได้)
- ไม่มีระบบ authentication (เหมาะสำหรับเครือข่ายภายใน)
- แนะนำให้ตั้ง Firewall บนเครื่อง Backend
- Database: SQLite (system_config.db)

---

## 📝 API Endpoints

### Backend API (พอร์ต 64020)

**Configurations:**
- `GET /api/configurations` - ดึงรายการ config ทั้งหมด
- `POST /api/configurations` - สร้าง config ใหม่
- `PUT /api/configurations/:id` - แก้ไข config
- `DELETE /api/configurations/:id` - ลบ config

**Machines:**
- `GET /api/machines` - ดึงรายการเครื่องจักร
- `POST /api/machines` - เพิ่มเครื่องจักร

**Measurement:**
- `POST /api/measurement/start` - เริ่มการวัด
- `POST /api/measurement/stop` - หยุดการวัด
- `GET /api/measurement/current-config` - ดู config ปัจจุบัน

**Camera:**
- `GET /api/camera/status` - สถานะกล้อง
- `GET /video_feed` - Video stream

**Socket.IO Events:**
- `measurement_result` - ผลการวัดแบบ Realtime
- `statistics_update` - อัพเดทสถิติ

---

## 📞 Support

หากมีปัญหาในการติดตั้งหรือใช้งาน กรุณาติดต่อทีมพัฒนา

---

## 📄 License

Copyright © 2026 PSE Vision Project  
ระบบนี้พัฒนาสำหรับใช้งานภายใน

---

**เวอร์ชัน:** 1.0.0  
**อัพเดทล่าสุด:** 30 มีนาคม 2026 
