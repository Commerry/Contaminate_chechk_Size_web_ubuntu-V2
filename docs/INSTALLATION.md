# 📦 PSE Vision CM4 - Installation Guide

**คู่มือติดตั้งระบบสำหรับ Raspberry Pi CM4 / Ubuntu Server**

---

## 📋 สารบัญ (Table of Contents)

1. [ความต้องการของระบบ (System Requirements)](#-ความต้องการของระบบ-system-requirements)
2. [การติดตั้งอัตโนมัติ (Automatic Installation)](#-การติดตั้งอัตโนมัติ-automatic-installation)
3. [การติดตั้งแบบ Manual (Manual Installation)](#-การติดตั้งแบบ-manual-manual-installation)
4. [การตั้งค่าหลังติดตั้ง (Post-Installation Setup)](#-การตั้งค่าหลังติดตั้ง-post-installation-setup)
5. [การทดสอบระบบ (System Testing)](#-การทดสอบระบบ-system-testing)
6. [แก้ปัญหาที่พบบ่อย (Common Issues)](#-แก้ปัญหาที่พบบ่อย-common-issues)

---

## 🖥️ ความต้องการของระบบ (System Requirements)

### Hardware
- **Raspberry Pi CM4** (แนะนำ 4GB RAM ขึ้นไป) หรือ **Ubuntu Server**
- **OAK-D Camera** (Luxonis OAK-D, OAK-D-S2, OAK-D-POE)
  - เชื่อมต่อผ่าน USB 3.0 หรือ Network (PoE)
- **Storage:** 16GB ขึ้นไป (แนะนำ 32GB สำหรับ production)
- **Network:** Ethernet (แนะนำสำหรับ stability)

### Software
- **OS:** Ubuntu 20.04+ / Raspberry Pi OS (64-bit)
- **Python:** 3.8+ (จะติดตั้งอัตโนมัติ)
- **Node.js:** 16+ (จะติดตั้งอัตโนมัติ)

### Optional (สำหรับ PLC Integration)
- **PLC Siemens S7-1200/1500** (ถ้าใช้งานร่วมกับ PLC)
- **python-snap7** library (ติดตั้งอัตโนมัติ)

---

## 🚀 การติดตั้งอัตโนมัติ (Automatic Installation)

### วิธีที่ 1: One-Click Installation (แนะนำ)

```bash
# 1. Clone repository
git clone https://github.com/pse/pse-vision-cm4.git
cd pse-vision-cm4

# 2. รันสคริปต์ติดตั้งอัตโนมัติ
chmod +x scripts/install/install_all.sh
sudo ./scripts/install/install_all.sh
```

**สคริปต์จะทำ:**
- ✅ ติดตั้ง Python 3.12 + pip + dependencies
- ✅ ติดตั้ง Node.js 20 LTS + npm
- ✅ ติดตั้ง dependencies (Flask, DepthAI, OpenCV, etc.)
- ✅ Build Frontend (Vue.js Admin Web)
- ✅ ตั้งค่า Systemd service (auto-start on boot)
- ✅ ตั้งค่า PM2 process manager
- ✅ ทดสอบระบบเบื้องต้น

**ระยะเวลาติดตั้ง:** ~15-20 นาที (ขึ้นอยู่กับความเร็วอินเทอร์เน็ต)

---

### วิธีที่ 2: Step-by-Step Installation

#### Step 1: Install System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install basic dependencies
sudo apt install -y git curl wget build-essential

# Install Python 3.12
sudo apt install -y python3.12 python3.12-venv python3-pip

# Install Node.js 20 LTS
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

#### Step 2: Install Python Dependencies

```bash
cd pse-vision-cm4

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install Python packages
pip install -r python_scripts/backend_requirements.txt
```

**หมายเหตุ:** ถ้าติดตั้ง depthai ไม่ได้ให้ใช้:
```bash
pip install depthai --no-cache-dir
```

#### Step 3: Install Frontend Dependencies

```bash
cd frontend
npm install
npm run build
cd ..
```

#### Step 4: Setup Configuration

```bash
# Copy example config
cp python_scripts/config.example.json python_scripts/config.json

# Edit config (ตั้งค่า Camera IP, PLC settings)
nano python_scripts/config.json
```

#### Step 5: Test Backend Server

```bash
# Run backend server (test mode)
python python_scripts/backend_server.py
```

**ถ้าสำเร็จจะเห็น:**
```
============================================================
OAK Camera Object Measurement System - Backend Server
============================================================

Server starting on http://localhost:64020
Camera: OAK-D-S2-POE Connected ✓
```

**เปิดเบราว์เซอร์:** http://localhost:64020

---

## 🔧 การติดตั้งแบบ Manual (Manual Installation)

### 1. Backend Setup

```bash
# 1. Navigate to project
cd pse-vision-cm4

# 2. Create Python virtual environment
python3.12 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install flask==3.0.0
pip install flask-socketio==5.3.6
pip install flask-cors==4.0.0
pip install depthai==2.27.0.0
pip install opencv-contrib-python==4.10.0.84
pip install numpy==1.26.4
pip install python-snap7>=1.3  # Optional: for PLC

# 4. Test import
python -c "import depthai; print('DepthAI OK')"
python -c "import cv2; print('OpenCV OK')"
```

### 2. Frontend Setup

```bash
cd frontend

# Install npm dependencies
npm install

# Build for production
npm run build

# Output: frontend/dist/
```

### 3. Configure Database (Optional)

```bash
# Install PostgreSQL (if using database)
sudo apt install -y postgresql postgresql-contrib

# Create database
sudo -u postgres createdb pse_vision
sudo -u postgres psql pse_vision < config/database/schema.sql
```

---

## ⚙️ การตั้งค่าหลังติดตั้ง (Post-Installation Setup)

### 1. Setup Systemd Service (Auto-start on Boot)

```bash
# Copy service file
sudo cp scripts/setup/pse-vision-backend.service /etc/systemd/system/

# Edit service file (update paths)
sudo nano /etc/systemd/system/pse-vision-backend.service

# Enable and start service
sudo systemctl enable pse-vision-backend
sudo systemctl start pse-vision-backend

# Check status
sudo systemctl status pse-vision-backend
```

### 2. Setup PM2 (Process Manager)

```bash
# Install PM2 globally
sudo npm install -g pm2

# Start backend with PM2
pm2 start ecosystem.config.js

# Save PM2 startup
pm2 save
pm2 startup

# View logs
pm2 logs pse-vision-backend
```

### 3. Setup Auto-Login (for CM4 Kiosk Mode)

```bash
# Run auto-login setup
sudo ./scripts/setup/setup_autologin.sh
```

### 4. Network Configuration

```bash
# Set static IP (edit netplan)
sudo nano /etc/netplan/01-netcfg.yaml
```

**Example netplan config:**
```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    eth0:
      dhcp4: no
      addresses:
        - 10.2.100.94/24
      gateway4: 10.2.100.1
      nameservers:
        addresses: [8.8.8.8, 8.8.4.4]
```

```bash
# Apply netplan
sudo netplan apply
```

---

## ✅ การทดสอบระบบ (System Testing)

### Test 1: Camera Connection

```bash
# Test OAK camera detection
python python_scripts/test_camera.py
```

**Expected output:**
```
Found 1 OAK camera(s):
  Device: OAK-D-S2-POE
  ID: 19443010219C811300
  Status: Connected ✓
```

### Test 2: Backend API

```bash
# Start backend
python python_scripts/backend_server.py

# In another terminal, test API
curl http://localhost:64020/api/status
```

**Expected response:**
```json
{
  "status": "ok",
  "camera_active": true,
  "version": "1.0.0"
}
```

### Test 3: PLC Connection (if enabled)

```bash
# Test PLC connection (debug mode)
curl -X POST http://localhost:64020/api/plc/connect
```

### Test 4: Full System Test

```bash
# Run comprehensive test
./scripts/utils/test_system.sh
```

---

## 🐛 แก้ปัญหาที่พบบ่อย (Common Issues)

### ❌ Camera Not Detected

**ปัญหา:** `No OAK devices found`

**แก้ไข:**
```bash
# Check USB connection
lsusb | grep Myriad

# Check USB permissions
sudo usermod -aG plugdev $USER
sudo udevadm control --reload-rules
sudo udevadm trigger

# Reboot
sudo reboot
```

### ❌ Port Already in Use

**ปัญหา:** `Address already in use: port 64020`

**แก้ไข:**
```bash
# Find process using port
sudo lsof -i :64020

# Kill process
sudo kill -9 <PID>
```

### ❌ Python Import Error

**ปัญหา:** `ModuleNotFoundError: No module named 'depthai'`

**แก้ไข:**
```bash
# Activate virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install --force-reinstall depthai
```

### ❌ Frontend Build Failed

**ปัญหา:** `npm ERR! code ELIFECYCLE`

**แก้ไข:**
```bash
cd frontend

# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
npm run build
```

### ❌ Service Won't Start

**ปัญหา:** `systemctl status pse-vision-backend` shows `failed`

**แก้ไข:**
```bash
# Check logs
sudo journalctl -u pse-vision-backend -n 50

# Fix permissions
sudo chown -R $USER:$USER /path/to/pse-vision-cm4

# Restart service
sudo systemctl restart pse-vision-backend
```

---

## 📞 ต้องการความช่วยเหลือ?

- **Documentation:** [docs/README.md](README.md)
- **Troubleshooting:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **GitHub Issues:** https://github.com/pse/pse-vision-cm4/issues

---

## ✅ Installation Checklist

- [ ] Python 3.12+ installed
- [ ] Node.js 20+ installed
- [ ] OAK Camera connected and detected
- [ ] Backend dependencies installed
- [ ] Frontend built successfully
- [ ] Backend server starts without errors
- [ ] Admin Web accessible at http://localhost:64020
- [ ] Camera live feed working
- [ ] Systemd service configured (optional)
- [ ] PM2 process manager setup (optional)

**ถ้าทั้งหมด ✓ แสดงว่าติดตั้งสำเร็จแล้ว!** 🎉

---

**Next Steps:**  
→ อ่าน [USER_GUIDE.md](USER_GUIDE.md) เพื่อเริ่มใช้งานระบบ  
→ อ่าน [CONFIGURATION.md](CONFIGURATION.md) เพื่อตั้งค่าระบบ
