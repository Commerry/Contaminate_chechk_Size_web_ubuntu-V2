# 🐛 PSE Vision CM4 - Troubleshooting Guide

**คู่มือแก้ปัญหาที่พบบ่อย**

---

## 📋 สารบัญ

1. [Camera Issues](#-camera-issues)
2. [Backend Issues](#-backend-issues)
3. [Frontend Issues](#-frontend-issues)
4. [PLC Connection Issues](#-plc-connection-issues)
5. [Service & PM2 Issues](#-service--pm2-issues)
6. [Network Issues](#-network-issues)
7. [Performance Issues](#-performance-issues)

---

## 📷 Camera Issues

### ❌ Problem: Camera Not Detected

**Symptoms:**
```
[ERROR] No OAK devices found
[ERROR] Could not connect to camera
```

**Solutions:**

#### 1. Check USB Connection
```bash
# Check if camera is detected
lsusb | grep Myriad

# Should see:
# Bus 001 Device 005: ID 03e7:2485 Intel Movidius MyriadX
```

#### 2. Check USB Permissions
```bash
# Add user to plugdev group
sudo usermod -aG plugdev $USER

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# Log out and log back in (or reboot)
sudo reboot
```

#### 3. Try Different USB Port
- ใช้ USB 3.0 port (สีน้ำเงิน)
- ลองเปลี่ยน USB cable
- หลีกเลี่ยง USB hub

#### 4. Check Power Supply
- กล้อง OAK ต้องการ power 5V/3A
- ตรวจสอบ power supply เพียงพอ

#### 5. Test Camera Standalone
```bash
# Test with depthai demo
python3 -c "import depthai as dai; print(dai.Device.getAllAvailableDevices())"
```

---

### ❌ Problem: Camera Timeout / Disconnects

**Symptoms:**
```
[WARNING] Camera ping missed
[ERROR] Camera disconnected
RuntimeError: Device closed or failed to close
```

**Solutions:**

#### 1. USB Power Management
```bash
# Disable USB autosuspend
echo 'on' | sudo tee /sys/bus/usb/devices/*/power/control

# Make permanent (add to /etc/rc.local):
for dev in /sys/bus/usb/devices/*/power/control; do
    echo 'on' > "$dev"
done
```

#### 2. Increase USB Buffer
```bash
# Add to /boot/cmdline.txt (Raspberry Pi)
dwc_otg.fiq_fsm_mask=0x3

# Reboot
sudo reboot
```

#### 3. Reduce Frame Rate
Edit `python_scripts/config.json`:
```json
{
  "camera_fps": 10,  // ลดจาก 15 → 10
  "frame_skip_rate": 5  // เพิ่มจาก 4 → 5
}
```

---

### ❌ Problem: Low FPS / Laggy Video

**Solutions:**

#### 1. Optimize Frame Skip Rate
```json
// python_scripts/config.json
{
  "frame_skip_rate": 4  // ส่ง 1 ใน 5 frames (5 FPS)
}
```

#### 2. Lower Resolution
```json
{
  "camera_resolution": "720p"  // ใช้ 720p แทน 1080p
}
```

#### 3. Disable Unnecessary Processing
```bash
# Disable depth calculation if not needed
# In backend_server.py, set:
enable_depth = False
```

---

## 🐍 Backend Issues

### ❌ Problem: Module Not Found

**Symptoms:**
```
ModuleNotFoundError: No module named 'depthai'
ModuleNotFoundError: No module named 'flask'
```

**Solutions:**

#### 1. Activate Virtual Environment
```bash
# Check if venv is activated
which python
# Should show: /path/to/pse-vision-cm4/venv/bin/python

# Activate venv
source venv/bin/activate
```

#### 2. Reinstall Dependencies
```bash
# Activate venv first
source venv/bin/activate

# Reinstall all dependencies
pip install -r python_scripts/backend_requirements.txt

# Force reinstall specific package
pip install --force-reinstall depthai
```

#### 3. Check Python Version
```bash
python --version
# Should be Python 3.8+ (recommended 3.12)

# If wrong version, use:
python3.12 -m venv venv
```

---

### ❌ Problem: Port Already in Use

**Symptoms:**
```
OSError: [Errno 98] Address already in use: ('0.0.0.0', 64020)
```

**Solutions:**

#### 1. Find and Kill Process
```bash
# Find process using port 64020
sudo lsof -i :64020

# Kill process
sudo kill -9 <PID>
```

#### 2. Change Port
Edit `python_scripts/config.json`:
```json
{
  "backend_port": 64030  // Change to different port
}
```

#### 3. Stop Service
```bash
# If running as service
sudo systemctl stop pse-vision-backend

# If running with PM2
pm2 stop pse-vision-backend
```

---

### ❌ Problem: Backend Crashes / RuntimeError

**Symptoms:**
```
RuntimeError: cannot join current thread
Traceback ... in stop_oak_camera
```

**Solutions:**

#### 1. Check Logs
```bash
# View backend logs
tail -f /var/log/pse-vision/backend.log

# Or systemd logs
sudo journalctl -u pse-vision-backend -f
```

#### 2. Restart Backend
```bash
# Restart service
sudo systemctl restart pse-vision-backend

# Or PM2
pm2 restart pse-vision-backend
```

#### 3. Fix Camera Thread Issue
The error `cannot join current thread` is fixed in latest version. Update:
```bash
git pull origin main
sudo systemctl restart pse-vision-backend
```

---

## 🌐 Frontend Issues

### ❌ Problem: Frontend Not Building

**Symptoms:**
```
npm ERR! code ELIFECYCLE
npm ERR! errno 1
```

**Solutions:**

#### 1. Clear Cache
```bash
cd frontend

# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

#### 2. Check Node.js Version
```bash
node --version
# Should be v16+ (recommended v20)

# Update Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

#### 3. Build with Verbose Logging
```bash
npm run build --verbose
```

---

### ❌ Problem: Blank Page / White Screen

**Solutions:**

#### 1. Check Browser Console
- Press F12 → Console tab
- Look for JavaScript errors

#### 2. Check Network Tab
- F12 → Network tab
- Refresh page
- Look for 404 errors

#### 3. Rebuild Frontend
```bash
cd frontend
npm run build
```

#### 4. Clear Browser Cache
- Ctrl + Shift + Delete
- Clear cache and cookies

---

## 🔌 PLC Connection Issues

### ❌ Problem: PLC Not Connecting

**Symptoms:**
```
[PLC] Connection timeout
[PLC] Cannot connect to 192.168.1.100
```

**Solutions:**

#### 1. Check Network Connection
```bash
# Ping PLC
ping 192.168.1.100

# Check if port 102 is open (S7 protocol)
telnet 192.168.1.100 102
```

#### 2. Check PLC Settings
```json
// python_scripts/config.json
{
  "plc_enabled": true,
  "plc_mode": "production",  // or "debug"
  "plc_address": "192.168.1.100",
  "plc_db_num": 100,
  "plc_rack": 0,
  "plc_slot": 1
}
```

#### 3. Test Debug Mode First
```json
{
  "plc_mode": "debug"  // Test without real PLC
}
```

#### 4. Install Snap7
```bash
# Install Snap7 library
pip install python-snap7>=1.3

# Test import
python -c "import snap7; print('Snap7 OK')"
```

---

### ❌ Problem: PLC Trigger Not Working

**Solutions:**

#### 1. Enable PLC in Settings
- Open Admin Web → Settings → PLC
- Enable "Enable PLC Integration"
- Select Mode: Debug or Production
- Click "Save Configuration"

#### 2. Connect PLC
- Click "Connect PLC" button
- Check status becomes "Connected" (green)

#### 3. Test Manual Trigger
- In Debug mode, click "Debug Trigger (Manual)"
- Should see measurement result

#### 4. Check Logs
```bash
# Should see:
[PLC] ▶ Trigger received!
[PLC] ✓ Measurement complete: Area=XXX mm²
```

---

## 🔧 Service & PM2 Issues

### ❌ Problem: Service Won't Start

**Symptoms:**
```bash
sudo systemctl status pse-vision-backend
● pse-vision-backend.service - PSE Vision Backend
   Loaded: loaded
   Active: failed (Result: exit-code)
```

**Solutions:**

#### 1. Check Service Logs
```bash
sudo journalctl -u pse-vision-backend -n 50 --no-pager
```

#### 2. Check Service File
```bash
# View service file
cat /etc/systemd/system/pse-vision-backend.service

# Common issues:
# - Wrong paths
# - Wrong user
# - Missing execute permissions
```

#### 3. Fix Permissions
```bash
# Fix ownership
sudo chown -R $USER:$USER /path/to/pse-vision-cm4

# Fix execute permissions
chmod +x /path/to/pse-vision-cm4/start.sh
```

#### 4. Reload Systemd
```bash
sudo systemctl daemon-reload
sudo systemctl restart pse-vision-backend
```

---

### ❌ Problem: PM2 Not Saving

**Symptoms:**
```bash
pm2 list
# No apps listed after reboot
```

**Solutions:**

#### 1. Save PM2 List
```bash
pm2 save
```

#### 2. Setup Startup Script
```bash
pm2 startup
# Copy and run the command it shows
```

#### 3. Verify Startup
```bash
pm2 unstartup
pm2 startup
pm2 save
```

---

## 🌐 Network Issues

### ❌ Problem: Cannot Access from Other Devices

**Symptoms:**
- Can access http://localhost:64020 on server
- Cannot access http://10.2.100.94:64020 from other devices

**Solutions:**

#### 1. Check Firewall
```bash
# Allow port 64020
sudo ufw allow 64020/tcp

# Or disable firewall (testing only)
sudo ufw disable
```

#### 2. Check Backend Binding
```bash
# Backend should bind to 0.0.0.0, not 127.0.0.1
# In backend_server.py:
socketio.run(app, host='0.0.0.0', port=64020)
```

#### 3. Check Network Interface
```bash
# Show IP addresses
ip addr show

# Should show IP: 10.2.100.94 on eth0
```

---

## 🚀 Performance Issues

### ❌ Problem: High CPU Usage

**Solutions:**

#### 1. Reduce Frame Rate
```json
// config.json
{
  "camera_fps": 10,  // Lower FPS
  "frame_skip_rate": 5  // Skip more frames
}
```

#### 2. Disable Contour Detection
```bash
# Only enable when measuring
# Don't run continuously
```

#### 3. Limit Concurrent Measurements
```json
{
  "max_concurrent_measurements": 1
}
```

---

### ❌ Problem: High Memory Usage

**Solutions:**

#### 1. Reduce Image Size
```json
{
  "image_quality": 70,  // Lower JPEG quality
  "max_image_size": "720p"
}
```

#### 2. Clear Old Logs
```bash
# Clear PM2 logs
pm2 flush

# Clear system logs
sudo journalctl --vacuum-time=7d
```

#### 3. Monitor Memory
```bash
# Check memory usage
free -h

# Check per-process
top
# Press M to sort by memory
```

---

## 📞 Still Having Issues?

### 1. Collect Debug Information
```bash
# Run system check
./scripts/utils/check_health.sh > system_info.txt

# Collect logs
./scripts/utils/logs.sh > logs.txt
```

### 2. Check Documentation
- [Installation Guide](INSTALLATION.md)
- [API Reference](API_REFERENCE.md)
- [FAQ](FAQ.md)

### 3. Report Bug
- **GitHub Issues:** https://github.com/pse/pse-vision-cm4/issues
- Include: system_info.txt, logs.txt, error screenshots

---

**Good luck! 🍀**
