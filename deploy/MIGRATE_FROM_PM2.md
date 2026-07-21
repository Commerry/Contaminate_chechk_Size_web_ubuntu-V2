# ย้ายจากระบบเก่า (pm2) มาเป็น PSE Vision Kiosk บน Ubuntu Server

เอกสารนี้ช่วย **ลบ startup เดิมที่ตั้งด้วย pm2** ให้หมด แล้วตั้งค่าใหม่ให้
**เปิดเครื่องมาหน้าเว็บเด้งเต็มจออัตโนมัติ (kiosk)**

> ⚠️ Kiosk ต้องมี **หน้าจอ + Desktop Environment (GNOME ฯลฯ)** บนเครื่องนั้น
> ถ้าเป็น Ubuntu Server แบบ headless (ไม่มี GUI) ให้ดูหัวข้อ "กรณี Server ไม่มี GUI" ท้ายเอกสาร

---

## ส่วน A — ลบ startup เดิม (pm2)

### A1. ดูของเดิมก่อน
```bash
pm2 list                      # โปรแกรมที่ pm2 รันอยู่
systemctl list-unit-files | grep -i pm2   # service ที่ pm2 สร้างตอนบูต
sudo ss -tlnp | grep -E '64020|64021'     # ดูว่ามีอะไรจับพอร์ตของเราอยู่
```

### A2. หยุด + ลบโปรเซสของ pm2 ทั้งหมด
```bash
pm2 stop all
pm2 delete all
pm2 save --force              # ล้างรายการที่ pm2 จำไว้ (dump)
```

### A3. ลบ "ตัวสั่งให้ pm2 เริ่มตอนบูต" (สำคัญที่สุด)
```bash
# วิธีมาตรฐาน: สั่ง unstartup แล้วรันคำสั่ง sudo ที่มันพิมพ์ออกมา
pm2 unstartup systemd

# หรือสั่งตรงๆ (แทน $USER/$HOME ด้วยผู้ใช้จริง):
sudo env PATH=$PATH:/usr/bin pm2 unstartup systemd -u $USER --hp $HOME
```

### A4. ยืนยันว่า service pm2 หายจริง + เก็บกวาด
```bash
systemctl list-unit-files | grep -i pm2   # ควรไม่เหลือ pm2-xxx
sudo systemctl disable pm2-$USER 2>/dev/null
sudo systemctl stop pm2-$USER 2>/dev/null
sudo rm -f /etc/systemd/system/pm2-$USER.service
sudo systemctl daemon-reload
pm2 kill                      # ปิด daemon ของ pm2 (ถ้ายังค้าง)
```

### A5. เช็ค startup อื่นๆ ที่ของเก่าอาจแอบตั้งไว้
```bash
# systemd services ที่ enable อยู่ (หาชื่อของเก่า เช่น node/electron/vision/web/kiosk/chrom)
systemctl list-unit-files --state=enabled | grep -iE 'node|electron|vision|pse|web|kiosk|chrom'

# crontab @reboot
crontab -l 2>/dev/null | grep -i reboot
sudo crontab -l 2>/dev/null | grep -i reboot

# desktop autostart (โปรแกรมเก่าอาจตั้งให้เปิด browser ตอน login)
ls -la ~/.config/autostart/
```
พบของเก่าตัวไหน ให้ปิด/ลบ:
```bash
sudo systemctl disable --now <ชื่อ-service-เก่า>
sudo rm -f /etc/systemd/system/<ชื่อ-service-เก่า>.service && sudo systemctl daemon-reload
rm -f ~/.config/autostart/<ไฟล์เก่า>.desktop        # ลบ autostart เก่า
# ลบบรรทัด @reboot ออกจาก crontab: crontab -e
```

### A6. ยืนยันว่าพอร์ตว่างแล้ว
```bash
sudo ss -tlnp | grep -E '64020|64021'    # ควรไม่มีอะไรค้าง
```

---

## ส่วน B — ตั้ง Kiosk ใหม่ (เด้งเต็มจอตอนบูต)

ทำตาม `deploy/INSTALL_KIOSK.md` ข้อ 0–10 โดยย่อคือ:

```bash
export PSE_USER="$USER"; export PSE_HOME="/opt/pse-vision"; export PSE_PORT="64020"

# ติดตั้ง deps + build frontend (ครั้งเดียว)
sudo apt install -y python3-venv chromium-browser curl
cd "$PSE_HOME" && python3 -m venv venv && ./venv/bin/pip install -r python_scriptsUB/backend_requirements.txt
cd frontend && npm ci && npm run build && cd "$PSE_HOME"

# 1) Backend เป็น systemd service (แทน pm2 เดิม)
sed -e "s#__PSE_USER__#$PSE_USER#g" -e "s#__PSE_HOME__#$PSE_HOME#g" -e "s#__PSE_PORT__#$PSE_PORT#g" \
    deploy/pse-vision.service | sudo tee /etc/systemd/system/pse-vision.service
sudo systemctl daemon-reload && sudo systemctl enable --now pse-vision.service
curl -sf "http://localhost:$PSE_PORT/api/camera/status" && echo "  <-- backend OK"

# 2) Kiosk autostart (เปิด browser เต็มจอตอนเข้าเดสก์ท็อป)
chmod +x deploy/start-kiosk.sh
mkdir -p ~/.config/autostart
sed "s#__PSE_HOME__#$PSE_HOME#g" deploy/pse-vision-kiosk.desktop > ~/.config/autostart/pse-vision-kiosk.desktop

# 3) เปิด Auto-login (เดสก์ท็อปเริ่มเองไม่ต้องกรอกรหัส) — GNOME/gdm3
sudo sed -i 's/^#\?\s*AutomaticLoginEnable.*/AutomaticLoginEnable=true/' /etc/gdm3/custom.conf
sudo sed -i "s/^#\?\s*AutomaticLogin=.*/AutomaticLogin=$PSE_USER/" /etc/gdm3/custom.conf

sudo reboot
```

เปิดเครื่องมาต้องเห็นหน้าเว็บ PSE Vision **เต็มจออัตโนมัติ** และ backend รันเป็น systemd (`pse-vision.service`) แทน pm2

---

## กรณี Server ไม่มี GUI (headless) — ต้องมีจอถึงจะ kiosk ได้
ถ้าเครื่องเป็น Ubuntu Server ล้วน ไม่มีเดสก์ท็อป ต้องเลือกอย่างใดอย่างหนึ่ง:

**ตัวเลือก 1 — ลง desktop เต็ม (ง่ายสุด):**
```bash
sudo apt install -y ubuntu-desktop chromium-browser
sudo systemctl set-default graphical.target
# แล้วทำ "ส่วน B" ตามปกติ
```

**ตัวเลือก 2 — kiosk เบาๆ ไม่ต้องลง desktop เต็ม (cage compositor):**
```bash
sudo apt install -y cage chromium-browser
# สร้าง service ให้รัน cage + chromium kiosk บน tty1 (auto-login tty ก่อน)
```
> ถ้าจะใช้ตัวเลือก 2 บอกผมได้ เดี๋ยวผมทำ service ไฟล์ `cage` ให้

---

## สรุปสั้น: ทำไมเปลี่ยนจาก pm2 → systemd
- pm2 เหมาะกับ Node process — แต่ backend เราเป็น **Python** และเสิร์ฟหน้าเว็บ+API ในพอร์ตเดียว
- systemd เป็นระบบ startup มาตรฐานของ Ubuntu เสถียรกว่า, restart อัตโนมัติ, และไม่ต้องพึ่ง Node ตอนรัน
