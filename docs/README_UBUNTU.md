# PSE Vision - Ubuntu Deployment Guide

## 📋 ภาพรวม

คู่มือนี้สำหรับติดตั้ง PSE Vision บน Ubuntu Desktop/Server

## 🚀 Quick Start

### วิธีที่ 1: Deploy จาก Windows (แนะนำ)

จากเครื่อง Windows ที่มีโค้ดอยู่:

```powershell
# PowerShell
.\deploy.ps1

# หรือถ้ามี WSL/Git Bash
./deploy.sh
```

Script จะ:
- ✅ Build frontend
- ✅ Upload ไฟล์ทั้งหมดไปที่ Ubuntu server
- ✅ ตั้งค่า permissions
- ✅ แสดงขั้นตอนติดตั้งต่อ

### วิธีที่ 2: ติดตั้งโดยตรงบน Ubuntu

```bash
# 1. Clone หรือ copy โปรเจคไปที่ Ubuntu

# 2. เข้าไปในโฟลเดอร์
cd /path/to/pse-vision

# 3. ทำให้ scripts executable
chmod +x *.sh

# 4. รันการติดตั้ง
./install.sh
```

---

## 📦 การติดตั้งระบบ

### ขั้นตอนบน Ubuntu Server

หลังจาก deploy แล้ว ให้ SSH เข้าไปและรันคำสั่งต่อไปนี้:

```bash
# SSH เข้าไปยัง server
ssh adminpse@10.1.100.78

# เข้าไปในโฟลเดอร์โปรเจค
cd ~/pse-vision

# ติดตั้งระบบ (ใช้เวลา 5-10 นาที)
./install.sh
```

Script จะติดตั้ง:
- ✅ Python packages (Flask, OpenCV, DepthAI, etc.)
- ✅ System dependencies สำหรับ OAK-D camera
- ✅ Node.js packages
- ✅ Build frontend
- ✅ Camera permissions (udev rules)

---

## 💻 การใช้งาน

### 1. รัน Backend + Admin Web

```bash
# เริ่มระบบ
./start.sh

# เข้าใช้งาน Admin Web ที่:
# http://localhost:64020
# หรือ http://10.1.100.78:64020 (จากเครื่องอื่น)
```

### 2. รัน Worker Mode (สำหรับคนงาน)

```bash
# เริ่ม Worker Mode
./start_worker.sh

# จะเปิด Desktop App (ถ้า build แล้ว)
```

### 3. Development Mode

```bash
# รัน Backend + Frontend แบบ dev
./dev.sh

# Frontend จะรันที่ port 64021
```

---

## 🔧 การ Build Desktop App

Build Desktop App สำหรับ Ubuntu:

```bash
cd user_display

# Build AppImage
npm run dist:linux

# ไฟล์จะอยู่ที่:
# dist-installer/PSE Vision Worker Display-1.0.0.AppImage
```

รันแอป:

```bash
cd dist-installer
chmod +x *.AppImage
./PSE*.AppImage
```

---

## ⚙️ Auto-Start บน Ubuntu

### ติดตั้ง systemd service

```bash
# ติดตั้ง auto-start service
./setup_service.sh

# Backend จะเริ่มอัตโนมัติทุกครั้งที่ boot
```

### จัดการ Service

```bash
# ตรวจสอบสถานะ
sudo systemctl status pse-vision-backend

# หยุด service
sudo systemctl stop pse-vision-backend

# เริ่ม service
sudo systemctl start pse-vision-backend

# Restart
sudo systemctl restart pse-vision-backend

# ดู logs แบบ realtime
sudo journalctl -u pse-vision-backend -f

# ปิด auto-start
sudo systemctl disable pse-vision-backend
```

### ถอนการติดตั้ง Service

```bash
./remove_service.sh
```

---

## 🎥 OAK-D Camera บน Ubuntu

### ตรวจสอบ Camera

```bash
# ตรวจสอบว่า camera เชื่อมต่ออยู่
lsusb | grep 03e7

# ถ้าเจอจะแสดง:
# Bus 001 Device 005: ID 03e7:2485 Intel Movidius MyriadX
```

### แก้ไขปัญหา Permissions

ถ้า camera ไม่ทำงาน:

```bash
# ตรวจสอบ udev rules
cat /etc/udev/rules.d/80-movidius.rules

# ถ้าไม่มี ให้สร้าง:
echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="03e7", MODE="0666"' | sudo tee /etc/udev/rules.d/80-movidius.rules

# Reload rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# ถอดและเสียบ camera ใหม่
```

---

## 🔍 การแก้ไขปัญหา

### Backend ไม่เริ่ม

```bash
# ตรวจสอบ logs
cd python_scripts
python3 backend_server.py

# หรือถ้าใช้ systemd
sudo journalctl -u pse-vision-backend -n 50
```

### Port ถูกใช้งานอยู่

```bash
# หา process ที่ใช้ port 64020
sudo lsof -i:64020

# หรือ
sudo netstat -tulpn | grep 64020

# Kill process
sudo kill -9 <PID>
```

### Python Packages ติดตั้งไม่สำเร็จ

```bash
# ติดตั้ง dependencies ที่จำเป็น
sudo apt update
sudo apt install python3-dev python3-pip
sudo apt install libusb-1.0-0-dev libopencv-dev

# ติดตั้งใหม่
cd python_scripts
pip3 install -r backend_requirements.txt --user
```

### Frontend Build ล้มเหลว

```bash
cd frontend

# ลบ node_modules และติดตั้งใหม่
rm -rf node_modules package-lock.json
npm install

# Build
npm run build
```

---

## 📁 โครงสร้างไฟล์บน Ubuntu

```
~/pse-vision/
├── install.sh              ← ติดตั้งระบบ
├── start.sh                ← เริ่มระบบ
├── start_worker.sh         ← Worker mode
├── dev.sh                  ← Development mode
├── build_desktop.sh        ← Build Desktop App
├── setup_service.sh        ← ติดตั้ง auto-start
├── remove_service.sh       ← ถอนการติดตั้ง service
├── deploy.sh               ← Deploy script
├── pse-vision-backend.service  ← Systemd service file
│
├── python_scripts/         ← Backend
├── frontend/               ← Admin Web
├── user_display/           ← Desktop App
└── config/                 ← Configurations
```

---

## 🌐 Network Access

### เข้าใช้งานจากเครื่องอื่น

```bash
# หา IP ของ Ubuntu server
ip addr show | grep inet

# เข้าใช้งาน Admin Web จากเครื่องอื่น:
http://<ubuntu-ip>:64020

# ตัวอย่าง:
http://10.1.100.78:64020
```

### เปิด Firewall (ถ้าจำเป็น)

```bash
# Ubuntu ใช้ ufw
sudo ufw allow 64020/tcp
sudo ufw status
```

---

## 🔄 การอัพเดทระบบ

### อัพเดทจาก Windows

```powershell
# แก้ไขโค้ดบน Windows แล้ว deploy ใหม่
.\deploy.ps1
```

### อัพเดทบน Server

```bash
# SSH เข้าไป
ssh adminpse@10.1.100.78

cd ~/pse-vision

# Pull/sync โค้ดใหม่
# (หรือรัน deploy.ps1 จาก Windows)

# Restart service
sudo systemctl restart pse-vision-backend

# หรือถ้าไม่ใช้ systemd
pkill -f backend_server.py
./start.sh
```

---

## 📊 System Requirements

### ขั้นต่ำ:
- Ubuntu 20.04+ (Desktop หรือ Server)
- Python 3.8+
- Node.js 16+
- RAM 4GB
- Storage 10GB

### แนะนำ:
- Ubuntu 22.04 LTS
- Python 3.10+
- Node.js 18+
- RAM 8GB+
- SSD Storage 20GB+

### USB Requirements:
- USB 3.0 port สำหรับ OAK-D camera
- USB Type-C port (ถ้าใช้ OAK-D Pro)

---

## 📞 Support

เมื่อพบปัญหา:

1. ตรวจสอบ logs:
   ```bash
   sudo journalctl -u pse-vision-backend -f
   ```

2. ตรวจสอบ camera:
   ```bash
   lsusb | grep 03e7
   ```

3. ตรวจสอบ port:
   ```bash
   sudo lsof -i:64020
   ```

4. Restart service:
   ```bash
   sudo systemctl restart pse-vision-backend
   ```

---

## ✅ Checklist หลังติดตั้ง

- [ ] Backend เริ่มได้ (`./start.sh`)
- [ ] เข้า Admin Web ได้ (`http://localhost:64020`)
- [ ] Camera ตรวจจับได้ (`lsusb | grep 03e7`)
- [ ] Frontend แสดงผลถูกต้อง
- [ ] Desktop App build ได้ (ถ้าต้องการ)
- [ ] Auto-start ทำงาน (ถ้าติดตั้ง)
- [ ] เข้าถึงจากเครื่องอื่นได้

---

## 🎯 Quick Commands

```bash
# ติดตั้ง
./install.sh

# เริ่มระบบ
./start.sh

# Worker mode
./start_worker.sh

# Dev mode
./dev.sh

# Auto-start
./setup_service.sh

# ตรวจสอบสถานะ
sudo systemctl status pse-vision-backend

# ดู logs
sudo journalctl -u pse-vision-backend -f

# Restart
sudo systemctl restart pse-vision-backend

# หยุด
sudo systemctl stop pse-vision-backend
```

---

**PSE Vision Team**  
Version 1.0.0 | Ubuntu Edition
