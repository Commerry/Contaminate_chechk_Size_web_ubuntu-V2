<template>
  <div class="app-container">
    <!-- Mobile Menu Button -->
    <button class="mobile-menu-btn" @click="toggleSidebar">
      <IconSvg name="menu" :size="24" />
    </button>

    <!-- Sidebar Overlay -->
    <div class="sidebar-overlay" :class="{ 'active': sidebarOpen }" @click="toggleSidebar"></div>

    <!-- Sidebar -->
    <Sidebar 
      :isConnected="isConnected"
      :isOpen="sidebarOpen"
      :isCameraActive="isCameraActive"
      :isPredicting="isPredicting"
      :isContourDetecting="isContourDetecting"
      :fps="currentFps"
      :objectCount="currentObjectCount"
      @toggle-camera="toggleCamera"
      @toggle-contour="toggleContour"
      @capture-image="captureImage"
      @open-settings="showSettings = true"
      @open-calibration="showCalibration = true"
      @open-machines="showMachines = true"
      @open-lots="showLots = true"
      @update:contrast="handleContrastChange"
      @update:colorSchemeChange="handleColorSchemeChange"
      @close="closeSidebar"
    />

    <!-- Main Content Area -->
    <main class="main-content">
      <!-- Header -->
      <header class="header">
        <div class="header-left">
          <h1 class="header-title">
            Object Measurement System
          </h1>
          <span v-if="isConnected" class="badge badge-success pulse">
            <span class="status-dot"></span>
            Connected
          </span>
          <span v-else class="badge badge-danger">
            <span class="status-dot"></span>
            Disconnected
          </span>
        </div>
        <div class="header-right">
          <SettingsDropdown
            @open-settings="showSettings = true"
            @open-calibration="showCalibration = true"
            @open-database="showDatabase = true"
            @open-machines="showMachines = true"
            @open-lots="showLots = true"
          />
          <IconSvg name="clock" :size="16" style="margin-right: 8px; opacity: 0.7;" />
          <span class="timestamp">{{ currentTime }}</span>
        </div>
      </header>

      <!-- Main Grid Layout -->
      <div class="content-grid">
        <!-- Camera View -->
        <div class="camera-section">
          <CameraView 
            :isActive="isCameraActive"
            :isConnected="isConnected"
            :isPredicting="isPredicting"
            :isContourDetecting="isContourDetecting"
            :threeZoneMode="threeZoneMode"
            :detections="detections"
            :frameData="currentFrame"
            :statusMessage="cameraStatusMessage"
          />
        </div>

        <!-- Measurement Display -->
        <div class="measurement-section">
          <MeasurementDisplay 
            ref="measurementDisplayRef"
            :measurements="currentMeasurements"
            :zoneMeasurements="zoneMeasurements"
            :threeZoneMode="threeZoneMode"
            :contrastFrame="contrastFrame"
            :depthFrame="depthFrame"
            :contourMask="contourMask"
            :depthColorScheme="depthColorScheme"
            :detectionStats="detectionStats"
          :activeSetup="activeSetup"
          />
          
          <!-- Database Control -->
          <DatabaseControl />
        </div>
      </div>
    </main>

    <!-- Settings Panel (Overlay) -->
    <SettingsPanel 
      v-if="showSettings"
      :settings="settings"
      @close="showSettings = false"
      @update-settings="updateSettings"
    />

    <!-- Calibration Modal -->
    <CalibrationModal 
      v-if="showCalibration"
      @close="showCalibration = false"
      @calibration-complete="handleCalibrationComplete"
    />

    <!-- Machine Manager -->
    <MachineManager
      v-if="showMachines"
      @close="showMachines = false"
      @updated="handleMachinesUpdated"
    />

    <!-- LOT Manager -->
    <div v-if="showLots" class="modal-overlay" @click.self="showLots = false">
      <div class="modal-panel">
        <div class="modal-header">
          <h2 class="modal-title">
            <IconSvg name="package" :size="24" />
            LOT Management
            <span class="subtitle">จัดการ LOT</span>
          </h2>
          <button class="close-btn" @click="showLots = false">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        <div class="modal-content">
          <LOTManager @updated="handleLotsUpdated" />
        </div>
      </div>
    </div>

    <!-- Database Settings Modal -->
    <div v-if="showDatabase" class="modal-overlay" @click.self="showDatabase = false">
      <div class="modal-panel">
        <div class="modal-header">
          <h2 class="modal-title">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
              <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path>
              <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path>
            </svg>
            Database Connection
            <span class="subtitle">การเชื่อมต่อฐานข้อมูล</span>
          </h2>
          <button class="close-btn" @click="showDatabase = false">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        <div class="modal-content">
          <DatabaseSettings />
        </div>
      </div>
    </div>

    <!-- Toast Notifications (มุมขวาล่าง) -->
    <div class="toast-container">
      <ToastNotification
        v-for="toast in toasts"
        :key="toast.id"
        :message="toast.message"
        :type="toast.type"
        :duration="toast.duration"
        @close="removeToast(toast.id)"
      />
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import { io } from 'socket.io-client'  // 🔥 Import SocketIO
import Sidebar from './components/Sidebar.vue'
import CameraView from './components/CameraView.vue'
import MeasurementDisplay from './components/MeasurementDisplay.vue'
import SettingsPanel from './components/SettingsPanel.vue'
import SettingsDropdown from './components/SettingsDropdown.vue'
import CalibrationModal from './components/CalibrationModal.vue'
import DatabaseControl from './components/DatabaseControl.vue'
import DatabaseSettings from './components/DatabaseSettings.vue'
import MachineManager from './components/MachineManager.vue'
import LOTManager from './components/LOTManager.vue'
import IconSvg from './components/IconSvg.vue'
import ToastNotification from './components/ToastNotification.vue'
import { useMeasurementStore } from './stores/measurementStore'
import { useToast } from './composables/useToast'
import measurementService from './services/measurementService'

// 🌐 Dynamic server URL - works for localhost AND remote machines
const apiBaseUrl = window.location.origin  // e.g. http://10.2.110.89:64020

const store = useMeasurementStore()
const { toasts, removeToast, success, error, warning, info } = useToast()

const isConnected = ref(false)
const isCameraActive = ref(false)
const isPredicting = ref(false)
const isContourDetecting = ref(false)  // ✅ Contour detection state
const showDatabase = ref(false)  // 🗄️ Database settings modal
const showSettings = ref(false)
const showMachines = ref(false)
const showLots = ref(false)  // 🎯 LOT management modal
const showCalibration = ref(false)
const currentTime = ref('')
const MOBILE_BREAKPOINT = 1024
const isMobileViewport = ref(typeof window !== 'undefined' ? window.innerWidth <= MOBILE_BREAKPOINT : false)
const sidebarOpen = ref(!isMobileViewport.value)
const detections = ref([])
const currentFrame = ref(null)
const cameraStatusMessage = ref('Click "Start Camera" to begin')
const contrastFrame = ref(null)
const depthFrame = ref(null)
const contourMask = ref(null)  // เพิ่ม contour mask
const threeZoneMode = ref(false)  // 🎯 3-zone detection mode
const zoneMeasurements = ref({ 1: null, 2: null, 3: null })  // 🎯 measurements แยกตาม zone
const currentFps = ref(0)  // ✅ FPS tracking
const currentObjectCount = ref(0)  // ✅ Object count tracking
const detectionStats = ref({  // ✅ สถิติการตรวจจับ (3-tier system)
  total: 0,
  inRange: 0,
  outRange: 0,
  pass: 0,
  nearPass: 0,
  fail: 0,
  smallest: 0,
  largest: 0
})
const activeSetup = ref({  // ✅ การตั้งค่าที่เลือกบนหน้าโปรแกรม
  machineId: null,
  machineName: '',
  lotId: null,
  lotName: '',
  config: null
})
const currentMeasurements = ref({
  width: 0,
  height: 0,
  depth: 0,
  volume: 0,
  hasObject: false
})

// Image enhancement settings
const contrastEnabled = ref(false)
const depthColorScheme = ref('gray')
const measurementDisplayRef = ref(null)

// 🔥 SocketIO instance
let socket = null

// Helper function to add log
const addLog = (message, type = 'info') => {
  if (measurementDisplayRef.value && measurementDisplayRef.value.addLog) {
    measurementDisplayRef.value.addLog(message, type)
  }
}

// Database session helper
const sendToDatabaseSession = async (detections) => {
  if (!detections || detections.length === 0) return
  
  try {
    // Check if session is active
    const statusResponse = await axios.get('/api/database/session/status')
    if (!statusResponse.data.success || !statusResponse.data.active) {
      return // No active session, skip
    }
    
    const session = statusResponse.data.session
    
    // Find the largest object to send (or use first detection)
    let objectToSend = detections[0]
    if (detections.length > 1) {
      // Find object with maximum size
      objectToSend = detections.reduce((max, det) => {
        const maxSize = (max.width_mm || 0) + (max.height_mm || 0)
        const detSize = (det.width_mm || 0) + (det.height_mm || 0)
        return detSize > maxSize ? det : max
      })
    }
    
    // Calculate size (average of width and height)
    const size = ((objectToSend.width_mm || 0) + (objectToSend.height_mm || 0)) / 2
    
    // Send to session
    const response = await axios.post('/api/database/session/add', {
      object_name: session.object_name, // Use session's locked object name
      size: size
    })
    
    if (response.data.success) {
      console.log(`[Database] Measurement added: ${size.toFixed(2)}mm (${response.data.current_count}/${session.max_triggers})`)
      
      // If session completed
      if (response.data.is_complete) {
        addLog(`Session completed! Saved max: ${response.data.max_measurement.size.toFixed(2)}mm`, 'success')
      }
    }
  } catch (error) {
    // Silently handle errors (don't disturb the UI)
    if (error.response?.status !== 400) {
      console.warn('[Database] Failed to send measurement:', error.message)
    }
  }
}

const settings = ref({
  minDepth: 300,
  maxDepth: 3000,
  confidenceThreshold: 0.5,
  measurementUnit: 'mm',
  autoCapture: true,
  showDepthMap: false
})

// Handle contrast and color scheme updates from Sidebar
const handleContrastChange = (enabled) => {
  contrastEnabled.value = enabled
  console.log('Contrast enabled:', enabled)
}

const handleColorSchemeChange = (scheme) => {
  depthColorScheme.value = scheme
  console.log('Color scheme changed to:', scheme)
}

// Update current time
const updateTime = () => {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('th-TH')
}

// Toggle camera on/off
const toggleCamera = async () => {
  console.log('🎥 Toggle camera clicked, current state:', isCameraActive.value)
  isCameraActive.value = !isCameraActive.value
  if (isCameraActive.value) {
    console.log('📹 Starting camera...')
    addLog('Starting camera...', 'info')
    await startCamera()
    focusMainContentOnMobile()
  } else {
    console.log('⏹️ Stopping camera...')
    addLog('Camera stopped', 'warning')
    stopCamera()
    focusMainContentOnMobile()
  }
}

// REMOVED: togglePrediction - prediction mode has been removed from the system

const toggleContour = async () => {
  if (!isCameraActive.value) {
    alert('⚠️ Please start the camera first')
    return
  }
  
  try {
    if (isContourDetecting.value) {
      // Stop contour detection + multi-object
      const response = await axios.post(`${apiBaseUrl}/api/camera/contour/stop`)
      if (response.data.success) {
        isContourDetecting.value = false
        // 🔢 Also stop Multi-Object Detection
        try { await axios.post(`${apiBaseUrl}/api/camera/multi-object/stop`) } catch (e) {}
        // ✅ ล้างกรอบ ROI และ stats ทันที
        detections.value = []
        currentObjectCount.value = 0
        detectionStats.value = {
          total: 0,
          inRange: 0,
          outRange: 0,
          smallest: 0,
          largest: 0
        }
        currentMeasurements.value = {
          width: 0,
          height: 0,
          depth: 0,
          volume: 0,
          hasObject: false
        }
        console.log('✅ Contour detection stopped - ROI and stats cleared')
        focusMainContentOnMobile()
      }
    } else {
      // Start contour detection
      const response = await axios.post(`${apiBaseUrl}/api/camera/contour/start`)
      if (response.data.success) {
        isContourDetecting.value = true
        isPredicting.value = false  // ปิด prediction mode
        // 🔢 Also enable Multi-Object Detection for multi-contour
        try {
          await axios.post(`${apiBaseUrl}/api/camera/multi-object/start`)
          console.log('✅ Multi-Object Detection enabled with contour')
        } catch (e) {
          console.warn('⚠️ Multi-object start failed:', e.message)
        }
        console.log('✅ Contour detection started (background subtraction mode)')
        focusMainContentOnMobile()
      } else {
        alert(response.data.message || 'Failed to start contour detection')
      }
    }
  } catch (error) {
    console.error('Error toggling contour detection:', error)
    alert('❌ Failed to toggle contour detection: ' + (error.response?.data?.message || error.message))
  }
}

const captureImage = async () => {
  if (!isCameraActive.value) {
    alert('Please start the camera first')
    return
  }
  
  try {
    console.log('Capturing image...')
    const response = await axios.post(`${apiBaseUrl}/api/camera/capture`)
    console.log('Capture response:', response.data)
    
    if (response.data.success) {
      console.log('Image captured successfully, saving to disk...')
      // Save to backend
      const saveResponse = await axios.post(`${apiBaseUrl}/api/camera/save-capture`, {
        image: response.data.image
      })
      console.log('Save response:', saveResponse.data)
      
      if (saveResponse.data.success) {
        alert(`✓ Image saved successfully!\nFile: ${saveResponse.data.filename}\nLocation: captures/`)
      } else {
        alert(`Failed to save image: ${saveResponse.data.message}`)
      }
    } else {
      alert(`Failed to capture image: ${response.data.message || 'Unknown error'}`)
    }
  } catch (error) {
    console.error('Capture failed:', error)
    alert(`Failed to capture image: ${error.response?.data?.message || error.message}`)
  }
}

// Start camera and begin receiving data
const startCamera = async () => {
  try {
    console.log('📡 Connecting to backend camera API...')
    addLog('Connecting to camera...', 'info')
    // Connect to backend API
    const result = await store.connectCamera()
    console.log('📡 Backend response:', result)
    
    if (result.success) {
      console.log('✅ Camera connection successful!')
      addLog('Camera connected successfully', 'success')
      isConnected.value = true
      cameraStatusMessage.value = 'Camera connected. Waiting for live frames...'
      // Start polling for frames and measurements immediately
      // Backend will initialize camera in background
      startDataPolling()
      
      // Wait a bit for camera to initialize
      setTimeout(() => {
        console.log('✅ Camera should be ready now')
        addLog('Camera ready', 'success')
      }, 3000)
    } else {
      // Connection failed
      console.error('❌ Camera connection failed:', result.message)
      addLog(`Camera connection failed: ${result.message}`, 'error')
      isConnected.value = false
      isCameraActive.value = false
      cameraStatusMessage.value = result.message || 'Failed to initialize camera'
      alert('Failed to connect to camera: ' + result.message)
    }
  } catch (error) {
    console.error('❌ Failed to start camera:', error)
    isConnected.value = false
    isCameraActive.value = false
    cameraStatusMessage.value = 'No OAK camera detected or backend connection failed'
    alert('Error connecting to camera. Please ensure the backend server is running and an OAK camera is connected.')
  }
}

// Stop camera - explicitly disconnect from backend
const stopCamera = async () => {
  try {
    await axios.post(`${apiBaseUrl}/api/camera/disconnect`)
    console.log('📹 Camera explicitly stopped')
  } catch (error) {
    console.error('Failed to stop camera:', error)
  }
  
  isConnected.value = false
  cameraStatusMessage.value = 'Camera stopped'
  stopDataPolling()
}

// Update settings
const updateSettings = (newSettings) => {
  settings.value = { ...settings.value, ...newSettings }
  store.updateSettings(newSettings)
  // ✅ แสดง notification เมื่อบันทึกการตั้งค่า
  success('บันทึกการตั้งค่าเรียบร้อยแล้ว')
}

const syncResponsiveLayout = () => {
  const mobile = window.innerWidth <= MOBILE_BREAKPOINT
  isMobileViewport.value = mobile
  sidebarOpen.value = !mobile
}

const focusMainContentOnMobile = () => {
  if (isMobileViewport.value) {
    sidebarOpen.value = false
  }
}

// Toggle sidebar for mobile
const toggleSidebar = () => {
  sidebarOpen.value = !sidebarOpen.value
}

// Close sidebar
const closeSidebar = () => {
  sidebarOpen.value = false
}

// Handle calibration completion
const handleCalibrationComplete = (calibrationData) => {
  console.log('Calibration completed:', calibrationData)
  showCalibration.value = false
  
  // Update settings with new calibration factor
  if (calibrationData.calibrationFactor) {
    settings.value.calibrationFactor = calibrationData.calibrationFactor
    store.updateSettings({ calibrationFactor: calibrationData.calibrationFactor })
    // ✅ แสดง notification เมื่อ calibration สำเร็จ
    success('ปรับเทียบกล้องสำเร็จแล้ว')
  }
}

// Handle machines updated
const handleMachinesUpdated = () => {
  console.log('Machines updated')
  success('อัปเดตเครื่องจักรสำเร็จ')
}

const handleLotsUpdated = () => {
  console.log('LOTs updated')
  success('อัปเดต LOTs สำเร็จ')
}

// Polling intervals
let pollingInterval = null
let stateSyncInterval = null // ใหม่: สำหรับ sync state
let frameCount = 0
let lastFpsUpdate = Date.now()

const startDataPolling = () => {
  // Clear any existing interval
  stopDataPolling()
  
  // ✅ เริ่ม State Sync Polling (ทุก 2 วินาที)
  startStateSyncPolling()
  
  // 🔥 MODIFIED: Polling only for PREVIEW FRAMES (contrast/depth/contour mask)
  // SocketIO handles main frame + detections + measurements
  pollingInterval = setInterval(async () => {
    // Only poll if camera is active
    if (!isCameraActive.value) {
      return
    }
    
    try {
      // Pass image enhancement options to backend
      const options = {
        contrast: contrastEnabled.value,
        colorScheme: depthColorScheme.value
      }
      
      const data = await store.getMeasurementData(options)
      
      // ✅ Update FPS calculation (based on SocketIO frame_update events)
      frameCount++
      const now = Date.now()
      const elapsed = (now - lastFpsUpdate) / 1000
      if (elapsed >= 1.0) {
        currentFps.value = Math.round(frameCount / elapsed)
        frameCount = 0
        lastFpsUpdate = now
      }
      
      // ❌ REMOVED: Main frame update (SocketIO handles this)
      // if (data.frame) {
      //   currentFrame.value = data.frame
      // }
      
      // ✅ Update PREVIEW frames (contrast/depth) - not handled by SocketIO
      console.log('📊 API Response - contrastFrame:', data.contrastFrame ? 'RECEIVED' : 'NULL')
      console.log('📊 API Response - depthFrame:', data.depthFrame ? 'RECEIVED' : 'NULL')
      
      if (data.contrastFrame) {
        contrastFrame.value = data.contrastFrame
        console.log('✅ Contrast frame updated')
      }
      if (data.depthFrame) {
        depthFrame.value = data.depthFrame
        console.log('✅ Depth frame updated')
      }
      
      // ✅ Fetch contour mask if contour detection is active (not handled by SocketIO)
      if (isContourDetecting.value) {
        try {
          const contourResponse = await axios.get(`${apiBaseUrl}/api/camera/contour/mask`)
          if (contourResponse.data.success && contourResponse.data.mask) {
            contourMask.value = { image: contourResponse.data.mask }
            console.log('✅ Contour mask updated')
          }
        } catch (error) {
          // Ignore 404 errors (no mask available yet)
          if (error.response?.status !== 404) {
            console.warn('Failed to fetch contour mask:', error)
          }
        }
      } else {
        contourMask.value = null
      }
      
      // ❌ REMOVED: Measurements/detections update (SocketIO handles this)
      // All detection data now comes from socket.on('frame_update')
      
    } catch (error) {
      // Silently handle errors to avoid console spam
      // Only log if it's not a connection/network error
      if (error.code !== 'ERR_NETWORK' && error.response?.status !== 400) {
        console.error('Failed to get preview data:', error.message)
      }
    }
  }, 1000) // 1 FPS for preview frames only
}

const stopDataPolling = () => {
  if (pollingInterval) {
    clearInterval(pollingInterval)
    pollingInterval = null
  }
  stopStateSyncPolling()
  // ✅ Reset FPS และ object count เมื่อหยุดกล้อง
  currentFps.value = 0
  currentObjectCount.value = 0
  frameCount = 0
  lastFpsUpdate = Date.now()
}

// ✅ State Sync Functions - ทำให้ทุกเครื่อง sync state แบบ real-time
const startStateSyncPolling = () => {
  stopStateSyncPolling()
  
  stateSyncInterval = setInterval(async () => {
    try {
      const response = await axios.get(`${apiBaseUrl}/api/camera/status`)
      const status = response.data
      
      // Sync camera state
      if (status.camera_active !== isCameraActive.value) {
        console.log('🔄 Camera state changed:', status.camera_active)
        isCameraActive.value = status.camera_active
        
        if (!status.camera_active) {
          isContourDetecting.value = false
          detections.value = []
          currentObjectCount.value = 0
        }
      }
      
      // Sync contour detection state
      if (status.contour_detection_active !== isContourDetecting.value) {
        console.log('🔄 Contour detection state changed:', status.contour_detection_active)
        isContourDetecting.value = status.contour_detection_active
        
        if (!status.contour_detection_active) {
          detections.value = []
          currentObjectCount.value = 0
          detectionStats.value = {
            total: 0,
            inRange: 0,
            outRange: 0,
            smallest: 0,
            largest: 0
          }
        }
      }
      
      // 🔄 Sync measurement session state (from Desktop App)
      // Note: Admin Web doesn't have measurement UI, but we can log it
      if (status.measurement_running !== undefined) {
        if (status.measurement_running) {
          console.log('🔄 Measurement running on another client:', {
            machine: status.active_machine_id,
            config: status.active_config?.name
          })
        }
      }
      
      isConnected.value = status.connected || false
      if (!status.camera_active) {
        cameraStatusMessage.value = 'Click "Start Camera" to begin'
      } else if (!status.hasDevice) {
        cameraStatusMessage.value = 'No OAK camera detected. Check USB, power, or network camera IP.'
      } else if (!status.has_frames) {
        cameraStatusMessage.value = 'Camera connected. Waiting for frames...'
      } else if (!status.frames_fresh) {
        cameraStatusMessage.value = 'Camera connected but frames are stale. Reconnecting...'
      } else {
        cameraStatusMessage.value = 'Live camera feed active'
      }
      
    } catch (error) {
      // Silent fail
    }
  }, 2000) // Every 2 seconds
  
  console.log('✅ Real-time state sync enabled')
}

const stopStateSyncPolling = () => {
  if (stateSyncInterval) {
    clearInterval(stateSyncInterval)
    stateSyncInterval = null
  }
}

// Check camera status and reconnect if needed
const checkCameraStatus = async () => {
  try {
    const response = await axios.get(`${apiBaseUrl}/api/camera/status`)
    const status = response.data
    
    console.log('📹 Camera status from server:', status)
    
    // Sync all states from backend
    if (status.camera_active) {
      isCameraActive.value = true
      isConnected.value = true
      isContourDetecting.value = status.contour_detection_active || false
      if (!status.hasDevice) {
        cameraStatusMessage.value = 'No OAK camera detected. Check USB, power, or network camera IP.'
      } else if (!status.has_frames) {
        cameraStatusMessage.value = 'Camera connected. Waiting for frames...'
      } else {
        cameraStatusMessage.value = 'Live camera feed active'
      }
      
      // 🔧 Seed activeSetup from server state (measurement may already be running)
      if (status.measurement_running && status.active_config) {
        activeSetup.value = {
          machineId: status.active_machine_id || null,
          machineName: status.active_machine_name || '',
          lotId: status.active_lot_id || null,
          lotName: status.active_lot_name || '',
          config: status.active_config || null
        }
        isPredicting.value = true
        isContourDetecting.value = true
        console.log('🔧 Seeded activeSetup from server:', activeSetup.value)
      }
      
      // Resume data polling
      startDataPolling()
      
      console.log('✅ Synced with server state:')
      console.log(`  Camera: ${status.camera_active ? 'ON' : 'OFF'}`)
      console.log(`  Contour Detection: ${status.contour_detection_active ? 'ON' : 'OFF'}`)
      console.log(`  Connected: ${status.connected ? 'YES' : 'NO'}`)
    } else {
      // Camera not active on server
      isCameraActive.value = false
      isContourDetecting.value = false
      isConnected.value = false
      cameraStatusMessage.value = 'No OAK camera detected. Connect the device, then press Start Camera.'
      console.log('ℹ️ Camera is not active on server')
    }
  } catch (error) {
    console.log('⚠️ Backend not ready yet or connection failed:', error.message)
    isConnected.value = false
    cameraStatusMessage.value = 'Backend not ready or camera unavailable'
  }
}

// Lifecycle hooks
onMounted(() => {
  updateTime()
  setInterval(updateTime, 1000)
  syncResponsiveLayout()
  window.addEventListener('resize', syncResponsiveLayout)
  
  // 🔥 Initialize Socket.IO connection (use dynamic server URL for multi-client support)
  const serverUrl = window.location.origin  // e.g. http://10.2.110.89:64020
  socket = io(serverUrl, {
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionAttempts: Infinity,
    reconnectionDelay: 1000
  })

  // ✅ Socket connection events
  socket.on('connect', () => {
    isConnected.value = true
    if (!isCameraActive.value) {
      cameraStatusMessage.value = 'Backend connected. Click "Start Camera" to begin.'
    }
    console.log('✅ SocketIO connected to backend')
    success('เชื่อมต่อ backend สำเร็จ')
  })

  socket.on('disconnect', () => {
    isConnected.value = false
    cameraStatusMessage.value = 'Backend disconnected'
    console.log('❌ SocketIO disconnected from backend')
    warning('ขาดการเชื่อมต่อ backend')
  })

  socket.on('connect_error', (err) => {
    isConnected.value = false
    cameraStatusMessage.value = 'Unable to connect to backend'
    console.error('❌ SocketIO connection error:', err.message)
    error('ไม่สามารถเชื่อมต่อ backend: ' + err.message)
  })

  socket.on('error', (err) => {
    console.error('❌ SocketIO error:', err)
    error('เกิดข้อผิดพลาดในการเชื่อมต่อ')
  })

  // 📡 Listen to frame updates (real-time frame streaming)
  socket.on('frame_update', (payload) => {
    console.log('📡 Received frame_update:', {
      hasFrame: !!payload?.frame,
      measurementsCount: payload?.measurements?.length || 0,
      statistics: payload?.statistics
    })
    
    if (payload?.frame) {
      // Update main frame - wrap in { image } object as expected by CameraView
      currentFrame.value = { image: payload.frame }
      cameraStatusMessage.value = 'Live camera feed active'
      
      // Update detections from measurements
      if (Array.isArray(payload.measurements)) {
        detections.value = payload.measurements
        currentObjectCount.value = payload.measurements.length
        
        // ✅ ใช้ session statistics จาก backend (แทนการคำนวณเอง)
        if (payload.statistics) {
          detectionStats.value = {
            total: payload.statistics.total || 0,
            inRange: (payload.statistics.pass || 0) + (payload.statistics.near_pass || 0),
            outRange: payload.statistics.fail || 0,
            pass: payload.statistics.pass || 0,
            nearPass: payload.statistics.near_pass || 0,
            fail: payload.statistics.fail || 0,
            smallest: 0,  // ไม่ได้ใช้ในการแสดงผล
            largest: 0    // ไม่ได้ใช้ในการแสดงผล
          }
        } else if (payload.measurements.length === 0) {
          // ถ้าไม่มี statistics และไม่มีวัตถุ ให้ reset
          detectionStats.value = {
            total: 0,
            inRange: 0,
            outRange: 0,
            pass: 0,
            nearPass: 0,
            fail: 0,
            smallest: 0,
            largest: 0
          }
        }
        
        // Update active setup info from frame_update
        if (payload.active_setup) {
          const s = payload.active_setup
          activeSetup.value = {
            machineId: s.machine_id || null,
            machineName: s.machine_name || '',
            lotId: s.lot_id || null,
            lotName: s.lot_name || '',
            config: s.config || null
          }
        }
      }
    }
  })

  // 🔄 Listen to measurement state changes (button sync)
  socket.on('measurement_state_changed', (payload) => {
    console.log('🔄 Measurement state changed:', payload)
    
    if (payload.running) {
      // Measurement started from another client (Desktop App)
      isPredicting.value = true
      isContourDetecting.value = true
      // Update active setup from event
      activeSetup.value = {
        machineId: payload.machine_id || null,
        machineName: payload.machine_name || '',
        lotId: payload.lot_id || null,
        lotName: payload.lot_name || '',
        config: payload.config || null
      }
      console.log('✅ Auto-synced: Measurement started from another client')
    } else {
      // Measurement stopped from another client
      isPredicting.value = false
      isContourDetecting.value = false
      activeSetup.value = { machineId: null, machineName: '', lotId: null, lotName: '', config: null }
      console.log('✅ Auto-synced: Measurement stopped from another client')
    }
  })

  // 🔄 Listen to contour state changes
  socket.on('contour_state_changed', (payload) => {
    console.log('🔄 Contour state changed:', payload)
    isContourDetecting.value = payload.active || false
  })

  // 🔄 Listen to multi-object state changes
  socket.on('multi_object_state_changed', (payload) => {
    console.log('🔄 Multi-object state changed:', payload)
    // Already handled by measurement state
  })

  // 🔄 Listen to camera state changes
  socket.on('camera_state_changed', (payload) => {
    console.log('🔄 Camera state changed:', payload)
    isCameraActive.value = payload.active || false
    if (payload.active) {
      console.log('✅ Auto-synced: Camera started from another client')
    } else {
      console.log('✅ Auto-synced: Camera stopped from another client')
    }
  })
  
  // Check if camera was already running
  checkCameraStatus()
})

onUnmounted(() => {
  window.removeEventListener('resize', syncResponsiveLayout)
  // Disconnect socket
  if (socket) {
    socket.disconnect()
    console.log('🔌 SocketIO disconnected')
  }
  
  // DON'T stop camera on unmount - keep it running in backend
  stopDataPolling() // Only stop polling, camera stays active
  console.log('Page unloaded - camera stays active in backend')
})
</script>

<style scoped>
.app-container {
  display: flex;
  width: 100vw;
  height: 100vh;
  background: var(--bg-dark);
  position: relative;
}

/* Mobile Menu Button */
.mobile-menu-btn {
  display: none;
  position: fixed;
  top: 50%;
  left: 8px;
  transform: translateY(-50%);
  z-index: 1001;
  width: 36px;
  height: 36px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  cursor: pointer;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 0;
  box-shadow: var(--shadow-md);
  transition: all 0.3s ease;
  opacity: 0.8;
}

.mobile-menu-btn:hover {
  background: var(--bg-card-hover);
  border-color: var(--primary-color);
  box-shadow: 0 0 15px rgba(139, 92, 246, 0.3);
  opacity: 1;
  transform: translateY(-50%) scale(1.05);
}

.hamburger-line {
  width: 18px;
  height: 2px;
  background: var(--text-primary);
  border-radius: 1px;
  transition: all 0.3s ease;
}

.mobile-menu-btn.active .hamburger-line:nth-child(1) {
  transform: translateY(6px) rotate(45deg);
}

.mobile-menu-btn.active .hamburger-line:nth-child(2) {
  opacity: 0;
}

.mobile-menu-btn.active .hamburger-line:nth-child(3) {
  transform: translateY(-6px) rotate(-45deg);
}

/* Sidebar Overlay */
.sidebar-overlay {
  display: none;
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.5);
  z-index: 998;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.3s ease;
}

.sidebar-overlay.active {
  opacity: 1;
  pointer-events: auto;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 30px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-color);
  animation: slideInFromLeft 0.6s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(10px);
  position: relative;
  z-index: 100000;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-title {
  font-size: 32px;
  font-weight: 800;
  display: flex;
  align-items: center;
  gap: 12px;
  background: linear-gradient(135deg, #8b5cf6 0%, #a855f7 50%, #6d28d9 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.5px;
  text-transform: uppercase;
  position: relative;
  font-family: 'Poppins', sans-serif;
}

.title-logo {
  width: 40px;
  height: 40px;
  object-fit: contain;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
}

.icon {
  font-size: 28px;
}

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  margin-right: 4px;
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  box-shadow: 0 0 8px currentColor;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.timestamp {
  font-size: 14px;
  color: var(--text-secondary);
  font-family: 'Courier New', monospace;
}

.content-grid {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr minmax(350px, 400px);
  gap: 20px;
  padding: 20px 30px;
  overflow: hidden;
}

.camera-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow: hidden;
}

.measurement-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow-y: auto;
}

@media (max-width: 1400px) {
  .content-grid {
    grid-template-columns: 1fr 350px;
    gap: 16px;
    padding: 16px 20px;
  }
}

@media (max-width: 1024px) {
  .mobile-menu-btn {
    display: flex;
  }
  
  .sidebar-overlay {
    display: block;
  }
  
  .main-content {
    margin-left: 0;
    width: 100%;
  }
  
  .header {
    padding: 16px 20px;
    padding-left: 60px;
  }
  
  .header-title {
    font-size: 20px;
  }
  
  .content-grid {
    grid-template-columns: 1fr;
    grid-template-rows: 1fr auto;
    gap: 16px;
    padding: 16px;
  }
  
  .measurement-section {
    max-height: 350px;
  }
}

@media (max-width: 768px) {
  .mobile-menu-btn {
    top: 12px;
    left: 12px;
    width: 44px;
    height: 44px;
  }
  
  .header {
    padding: 12px 16px;
    padding-left: 70px;
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
  
  .header-left {
    width: 100%;
    justify-content: space-between;
  }
  
  .header-title {
    font-size: 18px;
    gap: 8px;
  }
  
  .header-right {
    width: 100%;
  }
  
  .content-grid {
    padding: 12px;
    gap: 12px;
  }
  
  .measurement-section {
    max-height: 300px;
  }
}

@media (max-width: 480px) {
  .mobile-menu-btn {
    top: 10px;
    left: 10px;
    width: 40px;
    height: 40px;
  }
  
  .hamburger-line {
    width: 20px;
    height: 2px;
  }
  
  .header {
    padding: 10px 12px;
    padding-left: 60px;
  }
  
  .header-title {
    font-size: 16px;
    gap: 6px;
  }
  
  .content-grid {
    padding: 10px;
    gap: 10px;
  }
  
  .measurement-section {
    max-height: 250px;
  }
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  animation: fadeIn 0.3s;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-container {
  position: relative;
  width: 95%;
  max-width: 1000px;
  max-height: 90vh;
  overflow-y: auto;
  animation: slideUp 0.3s;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.modal-close-btn {
  position: absolute;
  top: -45px;
  right: 0;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 2px solid rgba(255, 255, 255, 0.4);
  font-size: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s;
  backdrop-filter: blur(10px);
}

.modal-close-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.6);
  transform: rotate(90deg);
}

/* Model Config Panel */
.modal-container.model-config {
  max-width: 900px;
}

.config-panel {
  background: white;
  border-radius: 12px;
  overflow: hidden;
}

.config-header {
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
  color: white;
  padding: 32px;
  text-align: center;
}

.config-header .header-icon {
  margin-bottom: 12px;
}

.config-header h2 {
  margin: 0 0 8px 0;
  font-size: 28px;
}

.config-header .subtitle {
  margin: 0;
  opacity: 0.9;
  font-size: 14px;
}

/* ============================================
   📱 RESPONSIVE DESIGN - รองรับทุกขนาดหน้าจอ
   ============================================ */

/* Tablet (768px - 1024px) */
@media (max-width: 1024px) {
  .mobile-menu-btn {
    display: flex; /* ✅ แสดงปุ่มเมนูในจอเล็ก */
  }
  
  .main-content {
    margin-left: 0;
    width: 100%;
    padding-top: 70px; /* ✅ เผื่อที่สำหรับปุ่มเมนู */
  }
  
  .content-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
  
  .measurement-section {
    order: 2;
  }
  
  .camera-section {
    order: 1;
  }
}

/* Mobile (< 768px) */
@media (max-width: 768px) {
  .header {
    padding: 12px 16px;
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  
  .header-title {
    font-size: 18px;
  }
  
  .header-right {
    width: 100%;
    justify-content: space-between;
  }
  
  .time-display {
    font-size: 14px;
  }
  
  .content-grid {
    padding: 12px;
    gap: 12px;
  }
  
  .card {
    padding: 14px;
  }
  
  .card-title {
    font-size: 16px;
  }
  
  /* Detection Summary - 2 columns on mobile */
  .stats-grid {
    grid-template-columns: 1fr 1fr;
    gap: 8px; /* ✅ ลดจาก 10px */
    padding: 10px; /* ✅ ลดจาก 12px */
  }
  
  .stat-card {
    padding: 8px 10px; /* ✅ ลดจาก 10px 12px */
    gap: 8px;
  }
  
  .stat-icon {
    width: 32px;
    height: 32px;
  }
  
  .stat-icon svg {
    width: 16px;
    height: 16px;
  }
  
  .stat-value {
    font-size: 14px; /* ✅ ลดจาก 16px */
    letter-spacing: -0.5px;
  }
  
  .stat-label {
    font-size: 7px; /* ✅ ลดจาก 8px */
    letter-spacing: 0.2px;
  }
  
  /* Modal adjustments */
  .modal-container {
    width: 98%;
    max-height: 95vh;
  }
}

/* Small Mobile (< 480px) */
@media (max-width: 480px) {
  .mobile-menu-btn {
    top: 12px;
    left: 12px;
    width: 44px;
    height: 44px;
  }
  
  .main-content {
    padding-top: 65px;
  }
  
  .header-title {
    font-size: 16px;
  }
  
  .badge {
    font-size: 10px;
    padding: 4px 8px;
  }
  
  .camera-section {
    min-height: 300px;
  }
  
  /* Single column for stats on very small screens */
  .stats-grid {
    grid-template-columns: 1fr;
    gap: 8px;
    padding: 8px;
  }
  
  .stat-card {
    padding: 10px 12px; /* ✅ เพิ่มพื้นที่สำหรับ 1 column */
  }
  
  .stat-icon {
    width: 36px; /* ✅ เพิ่มขึ้นเล็กน้อยสำหรับ 1 column */
    height: 36px;
  }
  
  .stat-icon svg {
    width: 18px;
    height: 18px;
  }
  
  .stat-value {
    font-size: 16px; /* ✅ เพิ่มขึ้นสำหรับ 1 column */
  }
  
  .stat-label {
    font-size: 8px; /* ✅ เพิ่มขึ้นสำหรับ 1 column */
  }
}

/* Landscape Mobile */
@media (max-height: 600px) and (orientation: landscape) {
  .content-grid {
    grid-template-columns: 1fr 1fr;
  }
  
  .camera-section {
    min-height: 250px;
  }
}

/* ✅ Toast Notification Container (มุมขวาล่าง) */
.toast-container {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9999;
  display: flex;
  flex-direction: column-reverse; /* ใหม่ล่างสุด */
  gap: 12px;
  pointer-events: none;
}

.toast-container > * {
  pointer-events: all;
}

/* Toast transitions */
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.toast-enter-from {
  transform: translateX(100%);
  opacity: 0;
}

.toast-leave-to {
  transform: translateY(20px);
  opacity: 0;
}

/* Mobile responsive */
@media (max-width: 768px) {
  .toast-container {
    bottom: 16px;
    right: 16px;
    left: 16px;
    max-width: calc(100vw - 32px);
  }
}

/* LOT Management Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100001;
  animation: fadeIn 0.2s ease-out;
}

.modal-panel {
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  width: 90%;
  max-width: 900px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: slideUp 0.3s ease-out;
  border: 1px solid #e5e7eb;
}

.modal-header {
  padding: 24px 32px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f9fafb;
}

.modal-title {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0;
  color: #111827;
  font-size: 24px;
  font-weight: 600;
}

.subtitle {
  font-size: 14px;
  font-weight: 400;
  color: #6b7280;
  margin-left: 4px;
}

.close-btn {
  padding: 8px;
  background: transparent;
  border: none;
  border-radius: 8px;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  background: #fee2e2;
  color: #dc2626;
}

.modal-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
  background: white;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes slideUp {
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

</style>
