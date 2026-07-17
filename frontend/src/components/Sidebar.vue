<template>
  <aside class="sidebar" :class="{ 'open': isOpen }">
    <div class="sidebar-header">
      <div class="logo">
        <img src="/Icon/output-onlinepngtools_PSE.png" alt="PSE Logo" class="logo-image" />
      </div>
    </div>

    <nav class="sidebar-nav">
      <!-- ⚠️ DISABLED: Size Mode Selector - ใช้เฉพาะ Small Mode เท่านั้น -->
      <!-- 
      <div class="nav-section size-selector-section">
        <h3 class="nav-section-title">Detection Size Mode</h3>
        <div class="size-toggle-container">
          <span class="size-label" :class="{ active: !isSmallObjectMode }">Large</span>
          <label class="toggle-switch">
            <input 
              type="checkbox" 
              v-model="isSmallObjectMode" 
              @change="toggleSmallObjectMode"
            >
            <span class="toggle-slider"></span>
          </label>
          <span class="size-label" :class="{ active: isSmallObjectMode }">Small</span>
        </div>
      </div>
      -->
      
      <!-- Camera Control -->
      <div class="nav-section">
        <h3 class="nav-section-title">Camera Control</h3>
        <button 
          class="nav-button"
          :class="{ 'active': isCameraActive }"
          @click="$emit('toggle-camera')"
        >
          <IconSvg :name="isCameraActive ? 'pause' : 'play'" :size="20" class="nav-icon" />
          <span>{{ isCameraActive ? 'Stop Camera' : 'Start Camera' }}</span>
        </button>

        <!-- DISABLED: AI Prediction (คอมเมนต์ไว้ - ไม่ใช้งานแล้ว)
        <button 
          class="nav-button"
          :class="{ 'active': isPredicting }"
          :disabled="!isCameraActive"
          @click="$emit('toggle-prediction')"
        >
          <IconSvg name="sparkles" :size="20" class="nav-icon" />
          <span>{{ isPredicting ? 'Stop Prediction' : 'Start Prediction' }}</span>
        </button>
        -->

        <button 
          class="nav-button"
          :class="{ 'active': isContourDetecting }"
          @click="startContourClick"
        >
          <IconSvg name="target" :size="20" class="nav-icon" />
          <span>{{ isContourDetecting ? 'Stop Contour' : 'Start Contour' }}</span>
        </button>

        <!-- ✅ Rubber Type Toggle -->
        <button 
          class="nav-button rubber-type-toggle"
          :class="{ 'white-mode': rubberType === 'white' }"
          :disabled="!isCameraActive || !isContourDetecting"
          @click="toggleRubberType"
          :title="rubberType === 'black' ? 'ยางดำ: พื้นขาว-วัตถุดำ' : 'ยางขาว: พื้นดำ-วัตถุขาว'"
        >
          <svg v-if="rubberType === 'black'" width="20" height="20" viewBox="0 0 24 24" fill="currentColor" class="nav-icon">
            <circle cx="12" cy="12" r="10"/>
          </svg>
          <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="nav-icon">
            <circle cx="12" cy="12" r="10"/>
          </svg>
          <span>{{ rubberType === 'black' ? 'ยางดำ' : 'ยางขาว' }}</span>
        </button>

        <button 
          class="nav-button"
          :class="{ 'active': isMultiObjectActive }"
          :disabled="!isCameraActive || !isContourDetecting"
          @click="toggleMultiObject"
          title="ตรวจจับและแสดงหลายวัตถุพร้อมกัน"
        >
          <IconSvg name="grid" :size="20" class="nav-icon" />
          <span>{{ isMultiObjectActive ? 'Multi: ON' : 'Multi: OFF' }}</span>
        </button>

        <!-- Import image for testing (works without camera) -->
        <!-- Import image panel -->
        <div class="nav-section import-image-section">
          <h3 class="nav-section-title">Import Image (Offline)</h3>
          <div class="import-controls" @dragover.prevent @drop.prevent="onDrop">
            <input id="sidebar-image-input" type="file" accept="image/*" style="display:none" @change="onFileChange" ref="fileInput" />
            <button class="nav-button" @click="chooseFile">
              <IconSvg name="upload" :size="18" class="nav-icon" />
              <span>Choose Image</span>
            </button>

            <div class="calibration-input">
              <label>Calibration (mm):</label>
              <input type="number" v-model.number="calibrationValue" min="0" step="0.1" placeholder="e.g. 100" />
            </div>

            <div class="selected-file" v-if="selectedName">
              <small>{{ selectedName }}</small>
              <div class="preview-container" v-if="previewUrl">
                <img :src="previewUrl" alt="preview" class="preview-image" />
              </div>
              <div class="upload-progress" v-if="uploadProgress > 0 && uploadProgress < 100">
                <div class="progress-bar" :style="{ width: uploadProgress + '%' }"></div>
                <small class="progress-text">Uploading: {{ uploadProgress }}%</small>
              </div>
            </div>

            <div class="import-actions">
              <button class="nav-button" :disabled="!selectedFile || uploadProgress > 0" @click="clearFile">
                <IconSvg name="x" :size="18" class="nav-icon" />
                <span>Clear</span>
              </button>
            </div>
          </div>
        </div>
        
        <!-- Contour Modes Preview -->
        <div class="nav-section contour-modes-section" v-if="Object.keys(contourMasks || {}).length">
          <h3 class="nav-section-title">Contour Modes</h3>
          <div class="contour-thumbs">
            <template v-for="(b64, key) in contourMasks" :key="key">
              <button class="thumb-btn" @click="emitPreviewContour(key, b64)">
                <img :src="'data:image/jpeg;base64,' + b64" :alt="key" class="thumb-image" />
                <small class="thumb-label">{{ key }}</small>
              </button>
            </template>
          </div>
        </div>

        <!-- ⚠️ DISABLED: Large Mode Features (3-Zone Detection) -->
        <!-- 
        <template v-if="!isSmallObjectMode">
          <button 
            class="nav-button"
            :class="{ 'active': isThreeZoneActive }"
            :disabled="!isCameraActive || !isContourDetecting"
            @click="toggleThreeZone"
            title="แบ่งหน้าจอเป็น 3 ช่อง และตรวจจับแยกกัน"
          >
            <IconSvg name="layout" :size="20" class="nav-icon" />
            <span>{{ isThreeZoneActive ? '3-Zone: ON' : '3-Zone: OFF' }}</span>
          </button>
        </template>
        -->
      </div>

      <!-- Status Info -->
      <div class="nav-section">
        <h3 class="nav-section-title">Status</h3>
        <div class="status-card">
          <div class="status-item">
            <span class="status-label">Connection:</span>
            <span class="status-value" :class="isConnected ? 'connected' : 'disconnected'">
              {{ isConnected ? 'Connected' : 'Disconnected' }}
            </span>
          </div>
          <div class="status-item">
            <span class="status-label">FPS:</span>
            <span class="status-value">{{ fps }}</span>
          </div>
          <div class="status-item">
            <span class="status-label">Objects:</span>
            <span class="status-value">{{ objectCount }}</span>
          </div>
        </div>
      </div>
    </nav>

    <div class="sidebar-footer">
      <div class="glove-character">
        <img :src="gloveImage" alt="Glove Character" class="glove-image" />
      </div>
      <div class="version-info">
        <div class="version-text">Version 1.0.0</div>
        <div class="copyright">© 2025 PSE Vision</div>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref, computed } from 'vue'
import IconSvg from './IconSvg.vue'
const gloveImage = '/Icon/glove_character.png'

const props = defineProps({
  isConnected: {
    type: Boolean,
    default: false
  },
  isOpen: {
    type: Boolean,
    default: false
  },
  isCameraActive: {
    type: Boolean,
    default: false
  },
  isPredicting: {
    type: Boolean,
    default: false
  },
  isContourDetecting: {
    type: Boolean,
    default: false
  },
  fps: {
    type: Number,
    default: 0
  },
  objectCount: {
    type: Number,
    default: 0
  }
  ,
  uploadProgress: {
    type: Number,
    default: 0
  }
  ,
  contourMasks: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits([
  'toggle-camera', 
  'toggle-contour', 
  'open-settings', 
  'open-calibration', 
  'open-machines',
  'open-configurations',
  'open-lots',
  'close', 
  'update:contrast', 
  'update:colorScheme', 
  'update:zoom',
  'predict-image',
  'preview-image',
  'preview-contour'
])

const selectedFile = ref(null)
const selectedName = ref('')
const fileInput = ref(null)
const previewUrl = ref(null)
const calibrationValue = ref(null)

const chooseFile = () => {
  if (fileInput.value) fileInput.value.click()
}

const onFileChange = (e) => {
  const f = e.target.files && e.target.files[0]
  if (f) {
    selectedFile.value = f
    selectedName.value = f.name
    // create preview URL
    if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
    // create base64 data URL for CameraView compatibility
    const reader = new FileReader()
    reader.onload = (ev) => {
      previewUrl.value = ev.target.result
      console.log('[Sidebar] emitting preview-image')
      emit('preview-image', previewUrl.value)
    }
    reader.readAsDataURL(f)
  }
}

const onDrop = (e) => {
  const file = e.dataTransfer?.files && e.dataTransfer.files[0]
  if (file) {
    // emulate file input
    selectedFile.value = file
    selectedName.value = file.name
    if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
    const reader = new FileReader()
    reader.onload = (ev) => {
      previewUrl.value = ev.target.result
      console.log('[Sidebar] emitting preview-image (drop)')
      emit('preview-image', previewUrl.value)
    }
    reader.readAsDataURL(file)
  }
}

const clearFile = () => {
  selectedFile.value = null
  selectedName.value = ''
  if (fileInput.value) fileInput.value.value = null
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = null
  }
  emit('preview-image', null)
}

const doPredict = () => {
  if (!selectedFile.value) return
  emit('predict-image', { file: selectedFile.value, calibration: calibrationValue.value })
}

const startContourClick = () => {
  // If a file is selected, ask App to start contour mode using the file
  if (selectedFile.value) {
    emit('toggle-contour', { file: selectedFile.value, calibration: calibrationValue.value })
  } else {
    // No file selected: regular toggle
    emit('toggle-contour')
  }
}

const emitPreviewContour = (key, b64) => {
  if (!b64) return
  // emit data URL for preview
  emit('preview-contour', { mode: key, dataUrl: 'data:image/jpeg;base64,' + b64 })
}

import { onUnmounted } from 'vue'

onUnmounted(() => {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
})

// Image enhancement controls
const contrastEnabled = ref(false)
const selectedColorScheme = ref('gray')
const zoomLevel = ref(1.0)

// ⭐ Multi-object detection control
const isMultiObjectActive = ref(false)
const isThreeZoneActive = ref(false)
const rubberType = ref('black')  // ✅ Rubber type: 'black' or 'white'

// 🌐 Dynamic server URL
const API_BASE = window.location.origin

// Load saved settings from config on mount
const loadConfig = async () => {
  try {
    const response = await fetch(`${API_BASE}/api/config/get`)
    const data = await response.json()
    if (data.success) {
      const config = data.config
      
      // Load all saved settings
      contrastEnabled.value = config.height_on === 1
      selectedColorScheme.value = config.depth_color_scheme || 'gray'
      zoomLevel.value = config.zoom_level || 1.0
      
      // Emit initial values to parent
      emit('update:contrast', contrastEnabled.value)
      emit('update:colorScheme', selectedColorScheme.value)
      emit('update:zoom', zoomLevel.value)
      
      console.log('[Config] ✅ Loaded saved settings:', {
        contrast: contrastEnabled.value,
        colorScheme: selectedColorScheme.value,
        zoom: zoomLevel.value
      })
    }
  } catch (error) {
    console.error('[Config] ❌ Failed to load:', error)
  }
}

// Load rubber type from camera status
const loadRubberType = async () => {
  try {
    const response = await fetch(`${API_BASE}/api/camera/status`)
    const data = await response.json()
    if (data.rubber_type) {
      rubberType.value = data.rubber_type
      console.log('[Rubber Type] Loaded:', rubberType.value)
    }
  } catch (error) {
    console.error('[Rubber Type] Failed to load:', error)
  }
}

// Auto-load config on mount
loadConfig()
loadRubberType()

const toggleContrast = async () => {
  contrastEnabled.value = !contrastEnabled.value
  emit('update:contrast', contrastEnabled.value)
  
  // Save to backend config
  try {
    await fetch(`${API_BASE}/api/config/set`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        key: 'height_on',
        value: contrastEnabled.value ? 1 : 0
      })
    })
  } catch (error) {
    console.error('[Config] Failed to save contrast:', error)
  }
  
  console.log('Contrast enabled:', contrastEnabled.value)
}

const updateColorScheme = async () => {
  emit('update:colorScheme', selectedColorScheme.value)
  
  // Save to backend config
  try {
    await fetch(`${API_BASE}/api/config/set`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        key: 'depth_color_scheme',
        value: selectedColorScheme.value
      })
    })
  } catch (error) {
    console.error('[Config] Failed to save color scheme:', error)
  }
  
  console.log('Color scheme changed to:', selectedColorScheme.value)
}

const updateZoom = async () => {
  emit('update:zoom', zoomLevel.value)
  
  // Save to backend config and apply zoom
  try {
    const response = await fetch(`${API_BASE}/api/camera/zoom`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ zoom: zoomLevel.value })
    })
    const data = await response.json()
    console.log('[Zoom]', data.message)
    
    // Save to config
    await fetch(`${API_BASE}/api/config/set`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        key: 'zoom_level',
        value: zoomLevel.value
      })
    })
    
    // Alert user to restart camera for zoom to take effect
    if (data.message && data.message.includes('restart')) {
      console.warn('⚠️ Please restart camera to apply zoom changes')
    }
  } catch (error) {
    console.error('[Zoom] Failed to update:', error)
  }
}

// ⭐ Toggle multi-object detection mode
const toggleMultiObject = async () => {
  try {
    const response = await fetch(`${API_BASE}/api/camera/multi-object/toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })
    const data = await response.json()
    
    if (data.success) {
      isMultiObjectActive.value = data.active
      console.log('[Multi-Object]', data.message)
    }
  } catch (error) {
    console.error('[Multi-Object] Failed to toggle:', error)
  }
}

// 🎯 Toggle 3-zone detection mode
const toggleThreeZone = async () => {
  try {
    const response = await fetch(`${API_BASE}/api/camera/three-zone/toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })
    const data = await response.json()
    
    if (data.success) {
      isThreeZoneActive.value = data.active
      console.log('[3-Zone]', data.message)
    }
  } catch (error) {
    console.error('[3-Zone] Failed to toggle:', error)
  }
}

// ✅ Toggle rubber type (black/white)
const toggleRubberType = async () => {
  try {
    const response = await fetch(`${API_BASE}/api/rubber/toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })
    const data = await response.json()
    
    if (data.success) {
      rubberType.value = data.rubber_type
      console.log('[Rubber Type]', data.message)
    }
  } catch (error) {
    console.error('[Rubber Type] Failed to toggle:', error)
  }
}

const calibrate = () => {
  emit('open-calibration')
}

const resetMeasurement = () => {
  console.log('Resetting measurements...')
  // TODO: Implement reset
}
</script>

<style scoped>
.sidebar {
  width: 280px;
  background: var(--bg-card);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  flex-shrink: 0;
}

.sidebar:not(.open) {
  width: 0;
  min-width: 0;
  border-right-width: 0;
  overflow: hidden;
}

.sidebar.open {
  width: 280px;
}

.sidebar-header {
  padding: 24px 20px;
  border-bottom: 1px solid var(--border-color);
}

.logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
}

.logo-image {
  width: 120px;
  height: 120px;
  object-fit: contain;
  filter: drop-shadow(0 2px 8px rgba(var(--primary-rgb), 0.3));
  transition: all 0.3s ease;
}

.logo-image:hover {
  filter: drop-shadow(0 4px 12px rgba(var(--primary-rgb), 0.5));
  transform: scale(1.05);
}

.logo-icon {
  width: 48px;
  height: 48px;
  background: var(--gradient-primary);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 16px;
  color: white;
  box-shadow: 0 4px 16px rgba(var(--primary-rgb), 0.3);
  animation: float 3s ease-in-out infinite;
  position: relative;
  overflow: hidden;
}

.logo-icon::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: linear-gradient(45deg, transparent, rgba(255,255,255,0.2), transparent);
  animation: shimmer 3s infinite;
}

.logo-text {
  flex: 1;
}

.logo-title {
  font-size: 18px;
  font-weight: 700;
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--accent-color) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1.2;
}

.logo-subtitle {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.2;
}

.sidebar-nav {
  flex: 1;
  padding: 20px;
}

.nav-section {
  margin-bottom: 28px;
}

.nav-section-title {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.nav-button {
  width: 100%;
  padding: 12px 16px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  margin-bottom: 8px;
  position: relative;
  overflow: hidden;
}

.nav-button::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: var(--gradient-glass);
  transition: left 0.3s ease;
}

.nav-button:hover::before {
  left: 0;
}

.nav-button:hover {
  background: var(--bg-card-hover);
  border-color: var(--primary-color);
  transform: translateX(4px);
  box-shadow: 0 4px 12px rgba(var(--primary-rgb), 0.2);
}

.nav-button.active {
  background: var(--gradient-primary);
  border-color: var(--primary-color);
  color: white;
  box-shadow: 0 4px 16px rgba(var(--primary-rgb), 0.3);
}

/* ✅ Rubber Type Toggle Styles */
.nav-button.rubber-type-toggle {
  background: var(--bg-dark-secondary);
  border: 1px solid var(--border-color);
}

.nav-button.rubber-type-toggle:not(:disabled):hover {
  background: var(--bg-card-hover);
  border-color: var(--border-color-light);
}

.nav-button.rubber-type-toggle.white-mode {
  background: linear-gradient(135deg, rgba(var(--accent-rgb), 0.14), rgba(var(--primary-rgb), 0.14));
  border: 1px solid rgba(var(--primary-rgb), 0.3);
  color: var(--text-primary);
}

.nav-button.rubber-type-toggle.white-mode:not(:disabled):hover {
  background: linear-gradient(135deg, rgba(var(--accent-rgb), 0.22), rgba(var(--primary-rgb), 0.22));
  border-color: rgba(var(--primary-rgb), 0.5);
  color: var(--text-primary);
}

.nav-button:active {
  transform: translateX(2px) scale(0.98);
}

.nav-icon {
  font-size: 18px;
}

.preview-container {
  margin-top: 8px;
  display: flex;
  justify-content: center;
}
.preview-image {
  max-width: 100%;
  max-height: 120px;
  border-radius: 6px;
  object-fit: contain;
  border: 1px solid var(--border-color);
}
.calibration-input {
  margin-top: 8px;
  display: flex;
  gap: 8px;
  align-items: center;
}
.calibration-input label {
  font-size: 12px;
  color: var(--text-secondary);
}
.calibration-input input {
  width: 100%;
  padding: 6px 8px;
  border-radius: 6px;
  border: 1px solid var(--border-color);
  background: transparent;
  color: var(--text-primary);
}
.upload-progress {
  margin-top: 8px;
  position: relative;
  height: 10px;
  background: var(--bg-dark-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  overflow: hidden;
}
.upload-progress .progress-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-color), var(--accent-color));
  transition: width 0.2s ease;
}
.upload-progress .progress-text {
  display: block;
  text-align: center;
  font-size: 11px;
  margin-top: 6px;
  color: var(--text-secondary);
}

/* Contour thumbnails */
.contour-thumbs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.thumb-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 6px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
}
.thumb-image {
  width: 64px;
  height: 48px;
  object-fit: cover;
  border-radius: 4px;
}
.thumb-label {
  font-size: 11px;
  color: var(--text-secondary);
}

.status-card {
  background: var(--bg-dark);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 12px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
}

.status-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.status-item:first-child {
  padding-top: 0;
}

.status-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.status-value {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.status-value.connected {
  color: var(--success-color);
}

.status-value.disconnected {
  color: var(--danger-color);
}

/* Color Scheme Selector */
.color-scheme-selector {
  padding: 12px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

/* Zoom Control */
.zoom-control {
  padding: 12px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 8px;
  border: 1px solid var(--border-color);
  margin-bottom: 12px;
}

.zoom-slider-container {
  margin-top: 8px;
}

.zoom-slider {
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: linear-gradient(90deg, 
    rgba(var(--primary-rgb), 0.3) 0%, 
    rgba(var(--primary-rgb), 0.6) 100%);
  outline: none;
  -webkit-appearance: none;
  appearance: none;
  cursor: pointer;
  transition: all 0.2s ease;
}

.zoom-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--primary-color);
  box-shadow: 0 2px 8px rgba(var(--primary-rgb), 0.5);
  cursor: pointer;
  transition: all 0.2s ease;
}

.zoom-slider::-webkit-slider-thumb:hover {
  background: var(--primary-light);
  box-shadow: 0 4px 12px rgba(var(--primary-rgb), 0.7);
  transform: scale(1.1);
}

.zoom-slider::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--primary-color);
  box-shadow: 0 2px 8px rgba(var(--primary-rgb), 0.5);
  cursor: pointer;
  border: none;
  transition: all 0.2s ease;
}

.zoom-slider::-moz-range-thumb:hover {
  background: var(--primary-light);
  box-shadow: 0 4px 12px rgba(var(--primary-rgb), 0.7);
  transform: scale(1.1);
}

.zoom-slider:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: rgba(100, 116, 139, 0.3);
}

.zoom-slider:disabled::-webkit-slider-thumb {
  background: rgba(100, 116, 139, 0.6);
  box-shadow: none;
  cursor: not-allowed;
}

.zoom-marks {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
  padding: 0 4px;
}

.zoom-marks span {
  font-size: 10px;
  color: var(--text-secondary);
  opacity: 0.7;
}

.selector-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.scheme-select {
  width: 100%;
  padding: 8px 12px;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.scheme-select:hover:not(:disabled) {
  border-color: var(--primary-color);
  background: rgba(var(--primary-rgb), 0.1);
}

.scheme-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.scheme-select option {
  background: #1e293b;
  color: var(--text-primary);
  padding: 8px;
}

.sidebar-footer {
  padding: 20px 20px 20px 20px;
}

.glove-character {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 16px;
  padding: 0;
}

.glove-image {
  max-width: 100%;
  height: auto;
  max-height: 200px;
  object-fit: contain;
  filter: drop-shadow(0 2px 6px rgba(0, 0, 0, 0.08));
  transition: transform 0.3s ease;
}

.glove-image:hover {
  transform: scale(1.05);
}

/* ✨ Size Mode Toggle Switch Styles */
.size-selector-section {
  background: linear-gradient(135deg, rgba(var(--primary-rgb), 0.1), rgba(var(--primary-rgb), 0.1));
  padding: 16px;
  border-radius: 12px;
  border: 1px solid rgba(var(--primary-rgb), 0.2);
  margin-bottom: 20px !important;
}

.size-selector-section .nav-section-title {
  color: var(--primary-color);
  margin-bottom: 16px;
  font-size: 12px;
}

.size-toggle-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 8px 0;
}

.size-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  transition: all 0.3s ease;
  user-select: none;
}

.size-label.active {
  color: var(--primary-color);
  font-size: 14px;
}

/* Toggle Switch */
.toggle-switch {
  position: relative;
  display: inline-block;
  width: 56px;
  height: 28px;
  cursor: pointer;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, #64748b 0%, #475569 100%);
  border-radius: 28px;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.2);
}

.toggle-slider:before {
  content: "";
  position: absolute;
  height: 22px;
  width: 22px;
  left: 3px;
  bottom: 3px;
  background: white;
  border-radius: 50%;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.toggle-switch input:checked + .toggle-slider {
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--accent-color) 100%);
  box-shadow: 0 0 12px rgba(var(--primary-rgb), 0.4);
}

.toggle-switch input:checked + .toggle-slider:before {
  transform: translateX(28px);
  box-shadow: 0 2px 12px rgba(var(--primary-rgb), 0.6);
}

.toggle-switch input:disabled + .toggle-slider {
  opacity: 0.5;
  cursor: not-allowed;
  background: #334155;
}

.size-description {
  text-align: center;
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 12px;
  margin-bottom: 0;
  padding: 6px 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
  font-weight: 500;
}

.version-info {
  text-align: center;
}

.version-text {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.copyright {
  font-size: 11px;
  color: var(--text-secondary);
}

/* Responsive Design */
@media (max-width: 1024px) {
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    height: 100vh;
    width: min(320px, calc(100vw - 32px));
    z-index: 999;
    transform: translateX(-100%);
    box-shadow: 2px 0 20px rgba(0, 0, 0, 0.3);
  }
  
  .sidebar.open {
    width: min(320px, calc(100vw - 32px));
    transform: translateX(0);
  }
  
  .sidebar-header {
    padding: 16px;
  }
  
  .logo-icon {
    width: 40px;
    height: 40px;
    font-size: 16px;
  }
  
  .logo-title {
    font-size: 16px;
  }
  
  .sidebar-nav {
    padding: 16px;
  }

  .sidebar-footer {
    display: none;
  }
  
  .nav-button {
    padding: 10px 12px;
    font-size: 13px;
  }
}

@media (max-width: 768px) {
  .sidebar {
    width: min(300px, calc(100vw - 24px));
  }
  
  .logo-icon {
    width: 36px;
    height: 36px;
    font-size: 14px;
  }
  
  .logo-title {
    font-size: 14px;
  }
  
  .logo-subtitle {
    font-size: 10px;
  }
  
  .nav-button {
    padding: 8px 10px;
    font-size: 12px;
    gap: 8px;
  }
}

@media (max-width: 480px) {
  .sidebar {
    width: min(280px, calc(100vw - 20px));
    max-width: calc(100vw - 20px);
  }
}
</style>
