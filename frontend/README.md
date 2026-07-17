# 🌐 Admin Web Interface (Vue.js 3)

**PSE Vision CM4 - Web-based Administration Panel**

---

## 📋 สารบัญ (Table of Contents)

1. [ภาพรวม (Overview)](#-ภาพรวม-overview)
2. [โครงสร้างโปรเจค (Project Structure)](#-โครงสร้างโปรเจค-project-structure)
3. [การติดตั้ง (Installation)](#-การติดตั้ง-installation)
4. [การพัฒนา (Development)](#-การพัฒนา-development)
5. [Components](#-components)
6. [State Management](#-state-management)

---

## 📖 ภาพรวม (Overview)

Admin Web เป็นส่วนหน้าบ้าน (Frontend) ของ PSE Vision CM4 ที่พัฒนาด้วย **Vue.js 3 Composition API** ใช้สำหรับ:

- 📊 **Dashboard** - แสดงสถิติแบบ Real-time (Pass/Fail counts, FPS, etc.)
- 📷 **Live Camera Feed** - แสดงภาพจากกล้องแบบ Real-time (70% viewport)
- 📸 **Captured Images** - แสดงภาพที่ถ่ายพร้อม ROI marker
- 📝 **System Logs** - แสดง Log messages แบบ Color-coded
- ⚙️ **Settings Panel** - จัดการ PLC, Machines, Configurations, LOTs
- 🎯 **Industrial HMI UI** - ออกแบบสไตล์ Purple/Indigo Gradient

---

## 🖼️ UI Design

### Layout (3-Panel Grid)

```
┌────────────────────────────────────────────────────────┐
│  [Logo]  Camera: ●  PLC: ●  Stats  [Buttons]          │ ← Navbar
├────────────────────────────────┬───────────────────────┤
│                                │  📸 Last Captured    │
│      📷 Live Camera Feed       │                       │
│         (70% Width)            │                       │
│                                ├───────────────────────┤
│                                │  📝 System Logs      │
│                                │                       │
└────────────────────────────────┴───────────────────────┘
```

### Color Theme

- **Background:** Deep indigo gradient (#1e1b4b → #312e81 → #1e293b)
- **Primary:** Purple (#9333ea) / Indigo (#6366f1)
- **Accent:** Orange (#f59e0b) for Debug mode
- **Success:** Green (#10b981)
- **Error:** Red (#ef4444)

---

## 📂 โครงสร้างโปรเจค (Project Structure)

```
frontend/
│
├── src/
│   ├── App.vue                    # ✨ Main Application
│   ├── main.js                    # Entry point
│   ├── style.css                  # Global styles
│   │
│   ├── components/                # Vue Components
│   │   ├── CalibrationModal.vue   # Camera calibration
│   │   ├── CameraView.vue         # Camera display
│   │   ├── ConfigurationManager.vue  # Configurations CRUD
│   │   ├── DatabaseControl.vue    # Database operations
│   │   ├── DatabaseSettings.vue   # DB config
│   │   ├── IconSvg.vue            # ⭐ SVG Icons
│   │   ├── LoadingSpinner.vue     # Loading indicator
│   │   ├── LOTManager.vue         # LOT management
│   │   ├── MachineManager.vue     # Machine CRUD
│   │   ├── MeasurementDisplay.vue # Show measurement results
│   │   ├── PLCSettings.vue        # ⭐ PLC control panel
│   │   ├── SettingsDropdown.vue   # Settings menu
│   │   ├── SettingsPanel.vue      # Settings container
│   │   ├── Sidebar.vue            # Navigation sidebar
│   │   ├── ToastNotification.vue  # Toast messages
│   │   └── UnifiedManagementModal.vue  # ⭐ Settings modal
│   │
│   ├── composables/               # Composable functions
│   │   └── useToast.js            # Toast notifications
│   │
│   ├── services/                  # API Services
│   │   └── measurementService.js  # Measurement API calls
│   │
│   ├── stores/                    # Pinia Stores
│   │   └── measurementStore.js    # Measurement state
│   │
│   └── utils/                     # Utilities
│       └── debugFileInput.js      # Debug file upload
│
├── public/                        # Static Assets
│   └── Icon/
│       └── LOGO-NEW.png           # PSE Vision logo (80px)
│
├── dist/                          # ⚙️ Built files (production)
├── package.json                   # npm dependencies
├── vite.config.js                 # Vite configuration
└── README.md                      # This file
```

---

## 🚀 การติดตั้ง (Installation)

### Prerequisites

- **Node.js** 16+ (แนะนำ v20 LTS)
- **npm** 7+ (มากับ Node.js)

### Install Dependencies

```bash
cd frontend

# Install packages
npm install

# Build for production
npm run build
```

**Output:** `dist/` folder

---

## 💻 การพัฒนา (Development)

### Dev Server (Hot Reload)

```bash
cd frontend

# Start dev server
npm run dev
```

**Dev server:** `http://localhost:5173/`  
**Backend API:** `http://localhost:64020`

**Features:**
- ✅ Hot Module Replacement (HMR)
- ✅ Fast refresh
- ✅ Source maps

---

### Build for Production

```bash
npm run build
```

**Output:** `dist/` folder  
**Size:** ~500KB (gzipped)

---

### Preview Production Build

```bash
npm run preview
```

**Preview server:** `http://localhost:4173/`

---

## 🧩 Components

### Core Components

#### `App.vue` (Main Application)

**Lines:** ~1,000 lines  
**Purpose:** Main application with 3-panel layout

**Features:**
- Navbar with logo, status indicators, statistics, action buttons
- Live camera feed (70% left panel)
- Last captured image with ROI (top-right 30%)
- System logs panel (bottom-right 30%)
- Socket.IO connection for real-time updates
- PLC mode switch button (Debug ↔ Production)

**Socket Events:**
```javascript
socket.on('frame_update', (data) => { ... })
socket.on('measurement_result', (data) => { ... })
socket.on('plc_status', (data) => { ... })
socket.on('log_message', (data) => { ... })
```

---

#### `PLCSettings.vue` (PLC Control Panel)

**Lines:** 292 lines  
**Purpose:** PLC configuration and control

**Features:**
- PLC status card (pulse animation when connected)
- Connect/Disconnect buttons
- Debug trigger button
- Mode selector (Debug/Production)
- IP address and DB number inputs
- Real-time status polling (every 5s)

---

#### `UnifiedManagementModal.vue` (Settings Modal)

**Lines:** ~400 lines  
**Purpose:** Tabbed settings modal

**Tabs:**
1. **PLC** - PLC settings and control (default)
2. **Machines** - Machine management
3. **Configurations** - Measurement configurations
4. **LOTs** - LOT management

---

#### `IconSvg.vue` (SVG Icon Library)

**Available Icons:**
- `settings`, `camera`, `image`, `upload`, `download`
- `trash`, `edit`, `save`, `close`
- `bug` 🐞 - Debug mode icon
- `cpu` 💻 - PLC mode icon
- `zap` ⚡ - Trigger icon

**Usage:**
```vue
<IconSvg name="settings" :size="24" />
```

---

## 🗄️ State Management

### Pinia Store: `measurementStore.js`

**State:**
```javascript
{
  measurements: [],
  currentMeasurement: null,
  statistics: {
    totalPass: 0,
    totalFail: 0
  }
}
```

---

## 🎨 Styling

### Key Colors

```css
:root {
  --color-background: #1e1b4b;
  --color-primary: #9333ea;
  --color-success: #10b981;
  --color-error: #ef4444;
  --color-warning: #f59e0b;
}
```

---

## 📦 Dependencies

```json
{
  "vue": "^3.4.0",
  "pinia": "^2.1.7",
  "socket.io-client": "^4.8.3",
  "axios": "^1.6.5"
}
```

---

## 🐛 Troubleshooting

### Build Failed

```bash
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
npm run build
```

### Dev Server Not Starting

```bash
# Check port
lsof -i :5173  # Linux/Mac
netstat -ano | findstr :5173  # Windows

# Kill process
kill -9 <PID>
```

---

## 📞 Support

- **Documentation:** [../docs/README.md](../docs/README.md)
- **Backend API:** [../python_scripts/README.md](../python_scripts/README.md)

---

**Made with ❤️ by PSE Vision Team**
