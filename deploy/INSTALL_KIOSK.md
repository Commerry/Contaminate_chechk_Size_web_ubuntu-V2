# PSE Vision — ติดตั้งให้เปิดหน้าเว็บอัตโนมัติตอนบูต (Kiosk) บน Ubuntu/Linux

เอกสารนี้ทำให้เครื่อง Ubuntu **เปิดเว็บ PSE Vision เต็มจออัตโนมัติทันทีที่เปิดเครื่อง**
โดยไม่ต้องแตะคีย์บอร์ด/เมาส์

## สถาปัตยกรรม (พอร์ตเดียว)
- **Backend** (systemd service) รัน `python_scripts/backend_server.py` ซึ่งเสิร์ฟทั้ง
  **หน้าเว็บ (frontend/dist) + REST API + Socket.IO บนพอร์ตเดียว** (ค่าเริ่มต้น 64020)
- **Kiosk browser** (Chromium autostart) เปิด `http://localhost:64020` เต็มจอเมื่อเข้าเดสก์ท็อป
- **Auto-login** ทำให้เดสก์ท็อปเริ่มเองโดยไม่ต้องกรอกรหัส → browser จึง autostart

> ไม่ต้องรัน Vite/Node ตอนใช้งานจริง — ใช้ Node แค่ตอน **build ครั้งเดียว**

---

## 0) ตั้งค่าตัวแปร (แก้ให้ตรงเครื่องคุณ)
รันทุกคำสั่งด้านล่างในเทอร์มินัลเดียวกันต่อเนื่อง (ตัวแปรจะถูกใช้ซ้ำ)

```bash
# ผู้ใช้ที่ล็อกอินเดสก์ท็อป (ปกติคือผู้ใช้ปัจจุบัน)
export PSE_USER="$USER"
# โฟลเดอร์รากของโปรเจค (โฟลเดอร์ที่มี python_scripts/ และ frontend/)
export PSE_HOME="/opt/pse-vision"
# พอร์ตที่จะเปิดเว็บ
export PSE_PORT="64020"
```

## 1) วางโปรเจคไว้ที่ PSE_HOME
```bash
sudo mkdir -p "$PSE_HOME"
sudo chown -R "$PSE_USER":"$PSE_USER" "$PSE_HOME"
# คัดลอกไฟล์โปรเจค (โฟลเดอร์ที่มี python_scripts/, frontend/, deploy/) ไปไว้ที่ $PSE_HOME
# เช่น: rsync -a /path/to/Contaminate_chechk_Size_web_ubuntu-main/  "$PSE_HOME"/
```

## 2) ติดตั้ง system dependencies
```bash
sudo apt update
sudo apt install -y python3-venv python3-pip curl chromium-browser
# Node.js 20 (สำหรับ build frontend ครั้งเดียว) — apt ของ Ubuntu มักเก่าเกินไป
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```
> บางรุ่นแพ็กเกจชื่อ `chromium` แทน `chromium-browser` — สคริปต์ kiosk รองรับทั้งคู่

## 3) สร้าง Python venv + ติดตั้ง backend
```bash
cd "$PSE_HOME"
python3 -m venv venv
./venv/bin/pip install --upgrade pip
# ใช้ requirements ของฝั่ง Ubuntu (มี depthai สำหรับกล้อง OAK)
./venv/bin/pip install -r python_scriptsUB/backend_requirements.txt
```
> ถ้าเครื่อง **ไม่มีกล้อง OAK** ก็ยังรันได้ (backend ข้าม depthai อัตโนมัติ) —
> ถ้า `pip install depthai` ล้มเหลว ให้ลบบรรทัด depthai ออกก่อน แล้วค่อยติดตั้งทีหลัง

## 4) Build frontend (ครั้งเดียว → ได้ frontend/dist)
```bash
cd "$PSE_HOME/frontend"
npm ci        # หรือ: npm install
npm run build
cd "$PSE_HOME"
```

## 5) ติดตั้ง systemd service ของ backend
```bash
sed -e "s#__PSE_USER__#$PSE_USER#g" \
    -e "s#__PSE_HOME__#$PSE_HOME#g" \
    -e "s#__PSE_PORT__#$PSE_PORT#g" \
    "$PSE_HOME/deploy/pse-vision.service" | sudo tee /etc/systemd/system/pse-vision.service

sudo systemctl daemon-reload
sudo systemctl enable --now pse-vision.service
# ตรวจสถานะ + ดู log
systemctl status pse-vision.service --no-pager
curl -sf "http://localhost:$PSE_PORT/api/camera/status" && echo "  <-- backend OK"
```

## 6) ติดตั้ง Kiosk autostart (เปิด browser เต็มจอตอนเข้าเดสก์ท็อป)
```bash
chmod +x "$PSE_HOME/deploy/start-kiosk.sh"
mkdir -p "$HOME/.config/autostart"
sed -e "s#__PSE_HOME__#$PSE_HOME#g" \
    "$PSE_HOME/deploy/pse-vision-kiosk.desktop" > "$HOME/.config/autostart/pse-vision-kiosk.desktop"
# ตั้ง URL ให้ตรงพอร์ต (เผื่อเปลี่ยนพอร์ต)
echo "PSE_URL=http://localhost:$PSE_PORT" | sudo tee /etc/environment.d/pse-vision.conf >/dev/null 2>&1 || true
```
> ถ้าเปลี่ยนพอร์ตจาก 64020 ให้แก้ `PSE_URL` ใน `deploy/start-kiosk.sh` ด้วย

## 7) เปิด Auto-login (เดสก์ท็อปเริ่มเองไม่ต้องกรอกรหัส)
**วิธี GUI:** Settings → Users → ปลดล็อก → เปิด **Automatic Login**

**วิธีไฟล์ (GNOME/gdm3):**
```bash
sudo sed -i 's/^#\?\s*AutomaticLoginEnable.*/AutomaticLoginEnable=true/' /etc/gdm3/custom.conf
sudo sed -i "s/^#\?\s*AutomaticLogin=.*/AutomaticLogin=$PSE_USER/" /etc/gdm3/custom.conf
# ถ้าไม่มีบรรทัดใน [daemon] ให้เพิ่มเอง:
grep -q "AutomaticLogin=" /etc/gdm3/custom.conf || \
  sudo sed -i "/^\[daemon\]/a AutomaticLoginEnable=true\nAutomaticLogin=$PSE_USER" /etc/gdm3/custom.conf
```

## 8) (แนะนำ) ปิดการหรี่/ดับจอ + sleep
```bash
gsettings set org.gnome.desktop.session idle-delay 0
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'
gsettings set org.gnome.desktop.screensaver lock-enabled false
```

## 9) (ถ้ามีกล้อง OAK ต่อ USB) ติดตั้ง udev rules
```bash
echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="03e7", MODE="0666"' | \
  sudo tee /etc/udev/rules.d/80-movidius.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
sudo usermod -aG plugdev "$PSE_USER"
```
> กล้องแบบ **PoE/Network** ไม่ต้องทำ udev — ตั้ง IP กล้องผ่านหน้า Settings ในเว็บแทน

## 10) รีบูตทดสอบ
```bash
sudo reboot
```
เปิดเครื่องมาควรเห็นหน้าเว็บ PSE Vision **เต็มจออัตโนมัติ**

---

## การใช้งาน / ดูแล
```bash
# ดู log backend สด
journalctl -u pse-vision.service -f
# รีสตาร์ท backend หลังอัปเดตโค้ด
sudo systemctl restart pse-vision.service
# อัปเดตหน้าเว็บหลังแก้ frontend
cd "$PSE_HOME/frontend" && npm run build && sudo systemctl restart pse-vision.service
```

## ออกจากโหมด Kiosk (ชั่วคราว)
- กด **Ctrl+W** หรือ **Alt+F4** ปิด browser
- ปิดถาวร: `rm ~/.config/autostart/pse-vision-kiosk.desktop`

## แก้ปัญหาเบื้องต้น
| อาการ | ตรวจ/แก้ |
|------|----------|
| หน้าเว็บไม่ขึ้น | `systemctl status pse-vision` + `curl localhost:$PSE_PORT` |
| Backend ไม่ start | `journalctl -u pse-vision -n 50` (มัก path/venv ผิด) |
| Browser ไม่เด้ง | เช็ค auto-login เปิดจริงไหม + ไฟล์ `~/.config/autostart/pse-vision-kiosk.desktop` |
| ไม่เจอ chromium | `sudo apt install -y chromium-browser` (หรือ `chromium`) |
| จอดับเอง | ทำข้อ 8 ซ้ำ |
| กล้องไม่ต่อ | ข้อ 9 (udev) + เสียบ USB3 / ตั้ง IP กล้อง PoE ในเว็บ |

## ถอนการติดตั้ง
```bash
sudo systemctl disable --now pse-vision.service
sudo rm /etc/systemd/system/pse-vision.service && sudo systemctl daemon-reload
rm ~/.config/autostart/pse-vision-kiosk.desktop
```
