# 📁 Scripts Directory

**สคริปต์สำหรับติดตั้ง Setup และจัดการระบบ PSE Vision CM4**

---

## 📂 โครงสร้างโฟลเดอร์ (Directory Structure)

```
scripts/
├── install/          # สคริปต์ติดตั้งระบบ
├── deploy/           # สคริปต์ Deploy to Production  
├── setup/            # สคริปต์ Setup Services
└── utils/            # Utilities และ Helper Scripts
```

---

## 🚀 install/ - สคริปต์ติดตั้ง

### `install_all.sh`
**ติดตั้งระบบทั้งหมดอัตโนมัติ (One-Click Installation)**

```bash
sudo ./scripts/install/install_all.sh
```

**ทำอะไร:**
- ติดตั้ง Python 3.12 + dependencies
- ติดตั้ง Node.js 20 LTS
- ติดตั้ง Backend dependencies (Flask, DepthAI, OpenCV)
- Build Frontend (Vue.js)
- ตั้งค่า Systemd service
- ตั้งค่า PM2 process manager

**ระยะเวลา:** ~15-20 นาที

---

### `install_python.sh`
**ติดตั้ง Python และ dependencies เท่านั้น**

```bash
./scripts/install/install_python.sh
```

**ทำอะไร:**
- ติดตั้ง Python 3.12
- สร้าง virtual environment
- ติดตั้ง requirements: Flask, DepthAI, OpenCV, Snap7

---

### `install_nodejs.sh`
**ติดตั้ง Node.js และ build Frontend**

```bash
./scripts/install/install_nodejs.sh
```

**ทำอะไร:**
- ติดตั้ง Node.js 20 LTS
- ติดตั้ง npm dependencies
- Build frontend → `frontend/dist/`

---

## 🌐 deploy/ - สคริปต์ Deploy

### `deploy.sh`
**Deploy ระบบไปยัง Production Server**

```bash
./scripts/deploy/deploy.sh
```

**ทำอะไร:**
- Pull latest code from Git
- Build frontend
- Restart backend service
- Run health check

---

### `deploy_with_backup.sh`
**Deploy พร้อม Backup ข้อมูลเดิม**

```bash
./scripts/deploy/deploy_with_backup.sh
```

**ทำอะไร:**
- Backup config + database
- Deploy ระบบใหม่
- Rollback อัตโนมัติถ้า deploy ไม่สำเร็จ

---

## ⚙️ setup/ - สคริปต์ Setup Services

### `setup_service.sh`
**ตั้งค่า Systemd Service (Auto-start on Boot)**

```bash
sudo ./scripts/setup/setup_service.sh
```

**ทำอะไร:**
- สร้าง systemd service file
- Enable service
- Start service
- ตรวจสอบ status

**Service name:** `pse-vision-backend.service`

---

### `setup_pm2.sh`
**ตั้งค่า PM2 Process Manager**

```bash
./scripts/setup/setup_pm2.sh
```

**ทำอะไร:**
- ติดตั้ง PM2 globally
- Start backend with PM2
- Setup PM2 startup script
- Save PM2 config

---

### `setup_autologin.sh`
**ตั้งค่า Auto-Login (สำหรับ Kiosk Mode)**

```bash
sudo ./scripts/setup/setup_autologin.sh
```

**ทำอะไร:**
- ตั้งค่า auto-login user
- ปิด screen saver
- ตั้งค่า Chromium kiosk mode (optional)

---

### `remove_service.sh`
**ลบ Systemd Service**

```bash
sudo ./scripts/setup/remove_service.sh
```

**ทำอะไร:**
- Stop service
- Disable service
- ลบ service file

---

## 🛠️ utils/ - Utilities

### `test_system.sh`
**ทดสอบระบบทั้งหมด**

```bash
./scripts/utils/test_system.sh
```

**ทดสอบ:**
- ✅ Python version
- ✅ Node.js version
- ✅ Camera connection
- ✅ Backend API
- ✅ Frontend build
- ✅ Database connection (if enabled)

---

### `backup.sh`
**Backup ข้อมูลระบบ**

```bash
./scripts/utils/backup.sh
```

**Backup:**
- Configuration files (config.json)
- Database (if enabled)
- Logs
- Upload to S3/FTP (optional)

**ตำแหน่ง Backup:** `/var/backups/pse-vision/`

---

### `restore.sh`
**Restore ข้อมูลจาก Backup**

```bash
./scripts/utils/restore.sh <backup-date>
```

**Example:**
```bash
./scripts/utils/restore.sh 2026-06-10
```

---

### `check_health.sh`
**ตรวจสอบสุขภาพระบบ**

```bash
./scripts/utils/check_health.sh
```

**ตรวจสอบ:**
- Service status (running/stopped)
- CPU/Memory usage
- Disk space
- Camera connection
- Network connectivity
- Log errors

---

### `update_system.sh`
**Update ระบบ (Pull latest code + Restart)**

```bash
./scripts/utils/update_system.sh
```

**ทำอะไร:**
- Pull latest code from Git
- Install new dependencies (if any)
- Build frontend
- Restart services
- Run health check

---

### `logs.sh`
**ดู Logs ระบบ**

```bash
# View all logs
./scripts/utils/logs.sh

# View backend logs only
./scripts/utils/logs.sh backend

# View PM2 logs
./scripts/utils/logs.sh pm2

# View systemd logs
./scripts/utils/logs.sh systemd
```

---

### `set_ip.sh`
**ตั้งค่า Static IP (Netplan)**

```bash
sudo ./scripts/utils/set_ip.sh 10.2.100.94 255.255.255.0 10.2.100.1
```

**Arguments:**
- IP Address
- Subnet Mask
- Gateway

---

## 📝 การใช้งานทั่วไป (Common Usage)

### Installation (ครั้งแรก)
```bash
# 1. Clone repository
git clone https://github.com/pse/pse-vision-cm4.git
cd pse-vision-cm4

# 2. ติดตั้งระบบทั้งหมด
sudo ./scripts/install/install_all.sh

# 3. ตั้งค่า service (auto-start)
sudo ./scripts/setup/setup_service.sh

# 4. ทดสอบระบบ
./scripts/utils/test_system.sh
```

### Update System
```bash
# Update code + Restart
./scripts/utils/update_system.sh
```

### Deploy to Production
```bash
# Deploy with backup
./scripts/deploy/deploy_with_backup.sh
```

### Check System Status
```bash
# Health check
./scripts/utils/check_health.sh

# View logs
./scripts/utils/logs.sh
```

### Troubleshooting
```bash
# Restart backend
sudo systemctl restart pse-vision-backend

# View logs
sudo journalctl -u pse-vision-backend -f

# Test camera
python python_scripts/test_camera.py
```

---

## ⚠️ หมายเหตุสำคัญ (Important Notes)

### Permissions
- สคริปต์บางตัวต้องใช้ `sudo` (ติดตั้ง packages, ตั้งค่า services)
- ตรวจสอบว่าสคริปต์มี execute permission: `chmod +x script.sh`

### Virtual Environment
- สคริปต์จะสร้าง Python virtual environment ที่ `venv/`
- ใช้งาน: `source venv/bin/activate`

### Logs Location
- **Backend logs:** `/var/log/pse-vision/backend.log`
- **PM2 logs:** `~/.pm2/logs/`
- **Systemd logs:** `journalctl -u pse-vision-backend`

---

## 🐛 Troubleshooting Scripts

### Script ไม่ทำงาน?

**ตรวจสอบ:**
```bash
# 1. Check execute permission
ls -l scripts/install/install_all.sh

# 2. Add execute permission
chmod +x scripts/install/install_all.sh

# 3. Check script syntax
bash -n scripts/install/install_all.sh
```

### Error: Permission Denied

**แก้ไข:**
```bash
# ใช้ sudo
sudo ./scripts/setup/setup_service.sh
```

### Error: Command Not Found

**แก้ไข:**
```bash
# Install missing dependencies
sudo apt update
sudo apt install -y curl wget git
```

---

## 📞 ต้องการความช่วยเหลือ?

- **Documentation:** [../docs/README.md](../docs/README.md)
- **Troubleshooting:** [../docs/TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md)
- **GitHub Issues:** https://github.com/pse/pse-vision-cm4/issues

---

**Happy Scripting! 🚀**
