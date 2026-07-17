# PSE Vision - Remote Access & Auto Power-On Guide
**Date:** May 8, 2026  
**Server:** Ubuntu 26.04 at 10.1.100.78  
**User:** adminpse

---

## 📡 Remote Desktop Access

### 🖥️ Method 1: xRDP (Recommended for Windows)

**ติดตั้งแล้ว:** ✅ xRDP Server พร้อมใช้งาน

**การเชื่อมต่อจาก Windows:**
1. เปิด **Remote Desktop Connection** (mstsc.exe)
2. Computer: `10.1.100.78:3389`
3. Username: `adminpse`
4. Password: `Abc123**`
5. คลิก **Connect**

**หรือใช้ Command Line:**
```cmd
mstsc /v:10.1.100.78
```

**พอร์ต:** 3389 (TCP)  
**สถานะ:** ✅ Active และ Auto-start enabled

---

### 🔒 Method 2: VNC (Alternative)

**ติดตั้งแล้ว:**
- ✅ TigerVNC Server
- ✅ x11vnc

**การเชื่อมต่อ VNC:**

#### A. ใช้ TigerVNC:
1. บน Ubuntu: `vncserver :1 -geometry 1920x1080 -depth 24`
2. ดาวน์โหลด **TigerVNC Viewer** สำหรับ Windows
   - https://github.com/TigerVNC/tigervnc/releases
3. เชื่อมต่อ: `10.1.100.78:5901`

#### B. ใช้ x11vnc (Share existing desktop):
```bash
x11vnc -display :0 -auth guess -forever -loop -noxdamage -repeat -rfbauth ~/.vnc/passwd -rfbport 5900 -shared
```

**VNC Viewer สำหรับ Windows:**
- **TigerVNC Viewer**: https://tigervnc.org/
- **RealVNC Viewer**: https://www.realvnc.com/en/connect/download/viewer/
- **UltraVNC**: https://uvnc.com/downloads/ultravnc.html
- **TightVNC**: https://www.tightvnc.com/download.php

**พอร์ต:** 
- 5900 (VNC default)
- 5901 (TigerVNC :1)

---

## 🌐 Firewall Configuration

```bash
sudo ufw allow 3389/tcp comment 'xRDP'
sudo ufw allow 5900/tcp comment 'VNC'
sudo ufw status
```

---

## ⚡ Auto Power-On Methods

### 🔌 Method 1: Wake-on-LAN (WOL) - แนะนำที่สุด

**ข้อมูลเครือข่าย:**
- **Interface:** enp0s31f6
- **MAC Address:** `c0:25:a5:ce:74:1a`
- **IP Address:** 10.1.100.78

#### ตั้งค่า WOL บน Ubuntu:
```bash
# 1. ติดตั้ง tools
sudo apt install -y ethtool wakeonlan

# 2. เช็คสถานะ WOL
sudo ethtool enp0s31f6 | grep Wake-on

# 3. เปิด WOL
sudo ethtool -s enp0s31f6 wol g

# 4. ตั้งค่าให้เปิด WOL ทุกครั้งที่ boot
echo '[Unit]
Description=Configure Wake On LAN for enp0s31f6
After=network.target

[Service]
Type=oneshot
ExecStart=/sbin/ethtool -s enp0s31f6 wol g

[Install]
WantedBy=basic.target' | sudo tee /etc/systemd/system/wol.service

sudo systemctl enable wol.service
sudo systemctl start wol.service
```

#### เปิดเครื่องจาก Windows:

**A. ใช้ PowerShell:**
```powershell
# ติดตั้ง WOL module
Install-Module -Name WakeOnLan -Force

# ส่ง Magic Packet
Send-WOL -MacAddress "C0:25:A5:CE:74:1A" -IPAddress "10.1.100.255"
```

**B. ใช้ WakeMeOnLan (GUI):**
1. ดาวน์โหลด: https://www.nirsoft.net/utils/wake_on_lan.html
2. เพิ่ม Computer:
   - IP: 10.1.100.78
   - MAC: C0:25:A5:CE:74:1A
3. คลิก "Wake Up Selected Computers"

**C. ใช้ Command Line:**
```cmd
# ดาวน์โหลด wolcmd.exe จาก https://www.depicus.com/wake-on-lan/wake-on-lan-cmd
wolcmd C0:25:A5:CE:74:1A 10.1.100.255 255.255.255.0 9
```

#### เปิดเครื่องจากมือถือ:
- **Android:** Wake On Lan (by Mike Webb)
- **iOS:** Mocha WOL

---

### ⏰ Method 2: BIOS/UEFI Auto Power-On

**เหมาะสำหรับ:** ตั้งเวลาเปิดเครื่องทุกวัน

**วิธีตั้งค่า:**
1. กด **F2** หรือ **Del** เมื่อเปิดเครื่อง → เข้า BIOS/UEFI
2. ไปที่ **Power Management** หรือ **Advanced**
3. หา **Wake on RTC** หรือ **Resume by Alarm**
4. ตั้ง:
   - Enable: **Yes**
   - Time: เวลาที่ต้องการ (เช่น 07:00)
   - Days: ทุกวัน หรือเฉพาะวันจันทร์-ศุกร์
5. Save & Exit

---

### 📅 Method 3: RTC Wake (Linux)

**เหมาะสำหรับ:** ตั้งเวลาเปิดครั้งเดียวหรือตามกำหนด

```bash
# ตั้งเวลาเปิดเครื่อง (ครั้งเดียว)
sudo rtcwake -m off -l -t $(date -d 'tomorrow 07:00' +%s)

# ตั้งเวลาเปิดจาก script (ทุกวัน 07:00)
echo '#!/bin/bash
# Set RTC wake for next day at 07:00
sudo rtcwake -m off -l -t $(date -d "tomorrow 07:00" +%s)
' | sudo tee /usr/local/bin/schedule-wake.sh

sudo chmod +x /usr/local/bin/schedule-wake.sh
```

---

## 🚀 Auto-Start Configuration (สำหรับเครื่องที่เปิดแล้ว)

**ตั้งค่าแล้ว:** ✅

### 1. Auto-Login
- GDM3 configured for `adminpse`
- ไม่ต้องใส่รหัสผ่านเมื่อบูต

### 2. Backend Auto-Start
- PM2 systemd service: `pm2-adminpse.service`
- Backend starts on boot: `pse-vision-backend`

### 3. Desktop App Auto-Start
- Wrapper script: `~/start-pse-display.sh`
- XDG autostart: `~/.config/autostart/pse-vision-display.desktop`

---

## 🔧 Wake-on-LAN Setup Script

สร้างไฟล์ `setup_wol.sh` บน Ubuntu:

```bash
#!/bin/bash
# PSE Vision - Wake-on-LAN Setup Script

INTERFACE="enp0s31f6"
MAC="c0:25:a5:ce:74:1a"

echo "=== Setting up Wake-on-LAN ==="
echo ""

# Install tools
echo "1. Installing ethtool..."
sudo apt install -y ethtool

# Enable WOL
echo "2. Enabling WOL on $INTERFACE..."
sudo ethtool -s $INTERFACE wol g

# Create systemd service
echo "3. Creating systemd service..."
cat <<EOF | sudo tee /etc/systemd/system/wol.service
[Unit]
Description=Configure Wake On LAN for $INTERFACE
After=network.target

[Service]
Type=oneshot
ExecStart=/sbin/ethtool -s $INTERFACE wol g

[Install]
WantedBy=basic.target
EOF

# Enable service
echo "4. Enabling WOL service..."
sudo systemctl enable wol.service
sudo systemctl start wol.service

# Verify
echo "5. Verifying WOL status..."
sudo ethtool $INTERFACE | grep Wake-on

echo ""
echo "✅ Wake-on-LAN setup complete!"
echo ""
echo "MAC Address: $MAC"
echo "IP Address: $(ip -4 addr show $INTERFACE | grep -oP '(?<=inet\s)\d+(\.\d+){3}')"
echo ""
echo "Use this MAC address to wake the computer from another device."
```

---

## 💻 Windows WOL PowerShell Script

สร้างไฟล์ `wake_pse_server.ps1` บน Windows:

```powershell
# PSE Vision Server - Wake-on-LAN Script
# MAC Address ของ Ubuntu server

$MAC = "C0:25:A5:CE:74:1A"
$IP = "10.1.100.255"  # Broadcast address

Write-Host "🔌 Sending Magic Packet to PSE Vision Server..." -ForegroundColor Cyan
Write-Host "   MAC: $MAC" -ForegroundColor White
Write-Host "   IP:  $IP" -ForegroundColor White

# Convert MAC to byte array
$MacByteArray = $MAC -split '[:-]' | ForEach-Object { [Byte] "0x$_" }

# Create Magic Packet (6 bytes of FF + 16 repetitions of MAC)
$MagicPacket = [Byte[]](,0xFF * 6) + ($MacByteArray * 16)

# Send UDP packet
$UdpClient = New-Object System.Net.Sockets.UdpClient
$UdpClient.Connect($IP, 9)
$UdpClient.Send($MagicPacket, $MagicPacket.Length) | Out-Null
$UdpClient.Close()

Write-Host "✅ Magic Packet sent successfully!" -ForegroundColor Green
Write-Host "⏰ Server should wake up in 5-10 seconds..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Waiting 10 seconds before testing connection..." -ForegroundColor Gray

Start-Sleep -Seconds 10

Write-Host "Testing connection..." -ForegroundColor Cyan
if (Test-Connection -ComputerName "10.1.100.78" -Count 2 -Quiet) {
    Write-Host "✅ Server is online!" -ForegroundColor Green
    Write-Host "You can now connect via Remote Desktop or SSH." -ForegroundColor White
} else {
    Write-Host "⏰ Server is still booting... Please wait 30 seconds and try again." -ForegroundColor Yellow
}
```

**วิธีใช้:**
```powershell
.\wake_pse_server.ps1
```

---

## 📱 Quick Reference

### Remote Desktop (Windows → Ubuntu)
```
Address: 10.1.100.78:3389
User: adminpse
Pass: Abc123**
```

### SSH Access
```
ssh adminpse@10.1.100.78
```

### Wake Computer
```powershell
# PowerShell
.\wake_pse_server.ps1
```

### VNC Access
```
Address: 10.1.100.78:5900
```

---

## 🔍 Troubleshooting

### Remote Desktop ไม่ได้:
```bash
# เช็คสถานะ xRDP
sudo systemctl status xrdp

# Restart xRDP
sudo systemctl restart xrdp

# เช็ค firewall
sudo ufw status
```

### Wake-on-LAN ไม่ทำงาน:
1. เช็ค BIOS: WOL ต้องเปิดใน BIOS/UEFI
2. เช็คสถานะ:
   ```bash
   sudo ethtool enp0s31f6 | grep Wake-on
   # ต้องขึ้น: Wake-on: g
   ```
3. เช็ค network cable: ต้องเสียบสาย LAN (WOL ไม่ทำงานกับ WiFi)
4. เช็ค power supply: PSU ต้องเสียบไฟตลอด

### VNC ไม่เชื่อมต่อ:
```bash
# Start VNC server
vncserver :1

# Or start x11vnc
x11vnc -display :0 -forever
```

---

## ✅ Configuration Summary

| Component | Status | Port | Auto-Start |
|-----------|--------|------|------------|
| xRDP | ✅ Active | 3389 | Yes |
| TigerVNC | ✅ Installed | 5901 | Manual |
| x11vnc | ✅ Installed | 5900 | Manual |
| Wake-on-LAN | ⚙️ Setup Required | - | After reboot |
| Backend | ✅ Running | 64020 | Yes (PM2) |
| Desktop App | ✅ Running | - | Yes (XDG) |

---

**Last Updated:** May 8, 2026  
**Maintained by:** PSE Vision System
