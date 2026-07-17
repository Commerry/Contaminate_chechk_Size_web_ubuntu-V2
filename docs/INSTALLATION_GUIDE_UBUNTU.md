# PSE Vision - คู่มือการติดตั้งและใช้งานบน Ubuntu (ฉบับสมบูรณ์)

## 🚀 Quick Setup (ติดตั้งครบทุกอย่าง)

### หลังจาก Deploy แล้ว ให้รันคำสั่งต่อไปนี้:

```bash
# 1. เข้าสู่ระบบ Ubuntu server
ssh adminpse@10.1.100.78

# 2. เข้าไปในโฟลเดอร์โปรเจค
cd ~/pse-vision

# 3. ติดตั้งระบบทั้งหมด (ใช้เวลา 5-10 นาที)
./install.sh

# 4. Setup PM2 สำหรับ auto-start
./setup_pm2.sh

# 5. (ทางเลือก) Setup auto-login
./setup_autologin.sh
```

---

## 📋 ระบบที่จะได้หลังจากติดตั้ง

### ✅ Backend Server
- Flask API server (port 64020)
- SocketIO สำหรับ realtime updates
- OAK-D camera integration
- SQLite database (local)

### ✅ Admin Web Interface
- เข้าถึงได้ที่: http://localhost:64020
- Configuration management
- Database settings
- Real-time monitoring

### ✅ Desktop App (Worker Display)
- Electron-based application
- Real-time measurement display
- Auto-start on login

### ✅ PM2 Process Manager
- Auto-restart on crash
- Auto-start on boot
- Log management
- Monitoring tools

### ✅ SQLite Database (Local)
- Path: `data/pse_vision.db`
- Auto-created on first run
- สามารถเปลี่ยนเป็น SQL Server ได้ในหน้าเว็บ

---

## 🔧 การใช้งานประจำวัน

### เริ่มระบบ

```bash
# วิธีที่ 1: ใช้ PM2 (แนะนำ)
pm2 start pse-vision-backend

# วิธีที่ 2: ใช้ start script
./start.sh

# วิธีที่ 3: ใช้ systemd (ถ้า setup แล้ว)
sudo systemctl start pse-vision-backend
```

### หยุดระบบ

```bash
# PM2
pm2 stop pse-vision-backend

# systemd
sudo systemctl stop pse-vision-backend
```

### Restart ระบบ

```bash
# PM2
pm2 restart pse-vision-backend

# systemd
sudo systemctl restart pse-vision-backend
```

### ดู Logs

```bash
# PM2 logs
pm2 logs pse-vision-backend

# PM2 logs (realtime)
pm2 logs pse-vision-backend --lines 100

# systemd logs
sudo journalctl -u pse-vision-backend -f
```

### ตรวจสอบสถานะ

```bash
# PM2 status
pm2 status

# PM2 monitoring
pm2 monit

# systemd status
sudo systemctl status pse-vision-backend
```

---

## 💾 การจัดการ Database

### SQLite (Local) - เริ่มต้น

```bash
# ดู database
sqlite3 data/pse_vision.db

# ดูตาราง
.tables

# ดูข้อมูล
SELECT * FROM tbl_measurements LIMIT 10;

# ออกจาก sqlite
.quit
```

### เปลี่ยนเป็น SQL Server

1. เข้าไปที่ Admin Web: http://localhost:64020
2. ไปที่ **Database Settings**
3. เลือก **Database Type**: SQL Server
4. กรอกข้อมูล:
   - Host: your-server-ip
   - Port: 1433
   - Database: your_database_name
   - Username: your_username
   - Password: your_password
5. คลิก **Test Connection**
6. คลิก **Save Settings**

### Backup Database (SQLite)

```bash
# Backup
cp data/pse_vision.db data/pse_vision.db.backup

# Restore
cp data/pse_vision.db.backup data/pse_vision.db
```

---

## 🎨 การปรับแต่ง UI

### เข้าถึง Admin Web

```bash
# จากเครื่องเดียวกัน
http://localhost:64020

# จากเครื่องอื่นในเครือข่าย
http://10.1.100.78:64020
```

### ตั้งค่าที่สำคัญ

1. **Configurations**
   - กำหนดขนาดวัตถุที่ยอมรับได้
   - ตั้งค่า tolerance
   - เลือก camera

2. **Machines**
   - เพิ่มเครื่องจักร
   - กำหนด IP address
   - ระบุ location

3. **Lots**
   - สร้าง lot ใหม่
   - ติดตาม production

4. **Database Settings**
   - เลือกประเภท database
   - ตั้งค่าการเชื่อมต่อ
   - ทดสอบการเชื่อมต่อ

---

## 🖥️ Desktop App (Worker Display)

### Build Desktop App

```bash
cd user_display

# Build AppImage for Linux
npm run dist:linux

# ไฟล์จะอยู่ที่:
# dist-installer/PSE-Vision-Worker-Display-1.0.0.AppImage
```

### ติดตั้ง Desktop App

```bash
cd user_display/dist-installer

# ทำให้ execute ได้
chmod +x PSE-Vision-Worker-Display-*.AppImage

# รันแอป
./PSE-Vision-Worker-Display-*.AppImage
```

### Auto-start Desktop App

Desktop App จะเริ่มอัตโนมัติเมื่อ login (ถ้ารัน `./setup_autologin.sh`)

---

## ⚙️ Auto-Start Configuration

### PM2 Auto-Start (แนะนำ)

```bash
# Setup (รันครั้งเดียว)
./setup_pm2.sh

# PM2 จะ:
# ✅ เริ่ม backend เมื่อ boot
# ✅ Auto-restart เมื่อ crash
# ✅ จัดการ logs
# ✅ Monitoring

# ตรวจสอบ
pm2 status
pm2 logs
```

### Systemd Auto-Start (ทางเลือก)

```bash
# Setup
./setup_service.sh

# ตรวจสอบ
sudo systemctl status pse-vision-backend

# Enable/Disable
sudo systemctl enable pse-vision-backend
sudo systemctl disable pse-vision-backend
```

### Auto-Login + Auto-Start Desktop App

```bash
# Setup auto-login
./setup_autologin.sh

# ระบบจะ:
# ✅ Auto-login เมื่อเปิดเครื่อง
# ✅ เริ่ม Desktop App อัตโนมัติ
# ✅ Backend รันด้วย PM2

# Reboot เพื่อใช้งาน
sudo reboot
```

---

## 🔍 Troubleshooting

### Backend ไม่เริ่ม

```bash
# ดู logs
pm2 logs pse-vision-backend

# หรือ
cd python_scripts
python3 backend_server.py

# ตรวจสอบ dependencies
pip3 list | grep flask
pip3 list | grep depthai
```

### Port ถูกใช้งานอยู่

```bash
# หา process ที่ใช้ port 64020
sudo lsof -i:64020

# Kill process
sudo kill -9 <PID>

# หรือใช้ PM2
pm2 delete pse-vision-backend
pm2 start ecosystem.config.js
```

### Camera ไม่ทำงาน

```bash
# ตรวจสอบ camera
lsusb | grep 03e7

# ถ้าไม่เจอ camera:
# 1. ตรวจสอบสาย USB
# 2. ลองเสียบ USB port อื่น
# 3. Reboot

# แก้ไข permissions
echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="03e7", MODE="0666"' | sudo tee /etc/udev/rules.d/80-movidius.rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### Database ไม่ทำงาน

```bash
# ตรวจสอบ database file
ls -lh data/pse_vision.db

# ถ้าไม่มีไฟล์:
mkdir -p data
python3 -c "import sqlite3; sqlite3.connect('data/pse_vision.db').close()"

# Restart backend
pm2 restart pse-vision-backend
```

### Desktop App ไม่เริ่ม

```bash
# Build ใหม่
cd user_display
rm -rf dist dist-installer
npm run dist:linux

# ตรวจสอบ permissions
chmod +x dist-installer/*.AppImage

# รันใน terminal เพื่อดู error
./dist-installer/PSE-Vision-Worker-Display-*.AppImage
```

### PM2 ไม่ auto-start

```bash
# ตรวจสอบ startup script
pm2 startup

# Run ตามคำสั่งที่แสดง (ต้องใช้ sudo)
# ตัวอย่าง:
sudo env PATH=$PATH:/usr/bin pm2 startup systemd -u adminpse --hp /home/adminpse

# Save process list
pm2 save
```

---

## 🌐 Network Configuration

### เปิด Firewall

```bash
# Ubuntu/UFW
sudo ufw allow 64020/tcp
sudo ufw status

# ตรวจสอบ
sudo netstat -tulpn | grep 64020
```

### เข้าถึงจากเครื่องอื่น

```bash
# หา IP ของ Ubuntu
ip addr show | grep inet

# เข้าใช้งานจากเครื่องอื่น
http://<ubuntu-ip>:64020

# ตัวอย่าง:
http://10.1.100.78:64020
```

---

## 🔄 การอัพเดทระบบ

### อัพเดทจาก Windows

```powershell
# แก้ไขโค้ดบน Windows
# Deploy ใหม่
.\deploy.ps1
```

### อัพเดทบน Ubuntu

```bash
# 1. หยุดระบบ
pm2 stop pse-vision-backend

# 2. Pull/sync โค้ดใหม่
# (หรือรัน deploy.ps1 จาก Windows)

# 3. Build frontend
cd frontend
npm install
npm run build
cd ..

# 4. Restart
pm2 restart pse-vision-backend
```

---

## 📊 System Monitoring

### PM2 Monitoring

```bash
# Dashboard แบบ realtime
pm2 monit

# Logs
pm2 logs pse-vision-backend

# CPU/Memory usage
pm2 describe pse-vision-backend
```

### System Resources

```bash
# CPU และ Memory
top

# Disk usage
df -h

# Network
ifconfig
```

---

## 🎯 Best Practices

### 1. Regular Backups

```bash
# Backup database ทุกวัน
crontab -e

# เพิ่ม:
0 0 * * * cp ~/pse-vision/data/pse_vision.db ~/pse-vision/data/pse_vision.db.$(date +\%Y\%m\%d)
```

### 2. Log Rotation

PM2 จัดการ log rotation อัตโนมัติ แต่สามารถตั้งค่าเพิ่มได้:

```bash
# Install PM2 log rotate
pm2 install pm2-logrotate

# ตั้งค่า
pm2 set pm2-logrotate:max_size 10M
pm2 set pm2-logrotate:retain 7
```

### 3. Monitoring

```bash
# Setup PM2 plus (optional)
pm2 plus

# หรือใช้ tools อื่นเช่น:
# - Grafana
# - Prometheus
# - Netdata
```

---

## ✅ Checklist หลังติดตั้ง

- [ ] Backend เริ่มได้ (`pm2 status`)
- [ ] เข้า Admin Web ได้ (`http://localhost:64020`)
- [ ] Camera ตรวจจับได้ (`lsusb | grep 03e7`)
- [ ] Database ทำงาน (ทดสอบบันทึกข้อมูล)
- [ ] Desktop App build ได้
- [ ] PM2 auto-start ทำงาน (reboot ทดสอบ)
- [ ] Auto-login ทำงาน (ถ้า setup)
- [ ] เข้าถึงจากเครื่องอื่นได้

---

## 📞 Quick Commands Reference

```bash
# ติดตั้ง
./install.sh

# เริ่มระบบ
pm2 start pse-vision-backend

# หยุดระบบ
pm2 stop pse-vision-backend

# Restart
pm2 restart pse-vision-backend

# ดู logs
pm2 logs pse-vision-backend

# ดู status
pm2 status

# Monitor
pm2 monit

# Auto-start setup
./setup_pm2.sh

# Auto-login setup
./setup_autologin.sh

# Build Desktop App
cd user_display && npm run dist:linux

# Database backup
cp data/pse_vision.db data/pse_vision.db.backup

# Check camera
lsusb | grep 03e7

# Check port
sudo lsof -i:64020
```

---

## 📚 เอกสารเพิ่มเติม

- [README.md](README.md) - คู่มือทั่วไป
- [README_UBUNTU.md](README_UBUNTU.md) - คู่มือสำหรับ Ubuntu
- [ecosystem.config.js](ecosystem.config.js) - PM2 configuration
- [pse-vision-backend.service](pse-vision-backend.service) - Systemd service

---

**PSE Vision Team**  
Version 1.0.0 | Ubuntu Edition with PM2 & Auto-Start

เมื่อมีปัญหา:
1. ตรวจสอบ logs ก่อน: `pm2 logs`
2. Restart service: `pm2 restart pse-vision-backend`
3. ตรวจสอบ camera: `lsusb | grep 03e7`
4. ตรวจสอบ port: `sudo lsof -i:64020`
