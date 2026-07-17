<template>
  <div class="settings-overlay" @click.self="$emit('close')">
    <div class="settings-panel">
      <div class="settings-header">
        <h2 class="settings-title">
          <IconSvg name="settings" :size="28" />
          Settings
        </h2>
        <button class="close-button" @click="$emit('close')">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>

      <div class="settings-content">
        <!-- Connected Cameras (Luxonis) -->
        <div class="settings-section">
          <h3 class="section-title">
            <IconSvg name="camera" :size="18" class="section-icon" />
            Connected Cameras
          </h3>
          
          <div class="camera-list">
            <div v-if="loadingCameras" class="loading-state">
              <div class="spinner"></div>
              <span>Scanning for cameras...</span>
            </div>

            <div v-else-if="cameras.length === 0" class="empty-state">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path>
                <circle cx="12" cy="13" r="4"></circle>
                <line x1="1" y1="1" x2="23" y2="23" stroke="red" stroke-width="2"></line>
              </svg>
              <p>No Luxonis cameras detected</p>
              <button class="btn btn-sm" @click="refreshCameras">
                <IconSvg name="refresh" :size="14" />
                Refresh
              </button>
            </div>

            <div v-else class="camera-items">
              <div 
                v-for="camera in cameras" 
                :key="camera.mxid"
                class="camera-item"
                :class="{ 'active': camera.mxid === currentDeviceId }"
              >
                <div class="camera-icon">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path>
                    <circle cx="12" cy="13" r="4"></circle>
                  </svg>
                </div>
                <div class="camera-info">
                  <div class="camera-name">
                    {{ camera.name }}
                    <span v-if="camera.mxid === currentDeviceId" class="badge-active">Active</span>
                  </div>
                  <div class="camera-details">
                    <span class="camera-id">{{ formatMxId(camera.mxid) }}</span>
                    <span class="camera-protocol">{{ camera.protocol }}</span>
                    <span class="camera-state" :class="'state-' + camera.state.toLowerCase()">
                      {{ camera.state }}
                    </span>
                  </div>
                </div>
              </div>

              <button class="btn btn-secondary btn-sm refresh-btn" @click="refreshCameras">
                <IconSvg name="refresh" :size="14" />
                Refresh List
              </button>
            </div>
          </div>
        </div>

        <!-- Camera Settings -->
        <div class="settings-section">
          <h3 class="section-title">
            <IconSvg name="camera" :size="18" class="section-icon" />
            Camera Settings
          </h3>

          <div class="setting-item">
            <label class="setting-label">
              Resolution
              <span class="setting-description">Camera resolution</span>
            </label>
            <select v-model="localSettings.resolution" class="setting-select">
              <option value="1080p">1920x1080 (1080p)</option>
              <option value="720p">1280x720 (720p)</option>
              <option value="480p">640x480 (480p)</option>
            </select>
          </div>

          <div class="setting-item">
            <label class="setting-label">
              FPS Limit
              <span class="setting-description">Maximum frames per second</span>
            </label>
            <input 
              v-model.number="localSettings.fpsLimit" 
              type="number" 
              min="1" 
              max="60" 
              class="setting-input"
            />
          </div>

          <div class="setting-item">
            <label class="setting-label">
              Show Depth Map
              <span class="setting-description">Display depth map visualization</span>
            </label>
            <label class="toggle-switch">
              <input v-model="localSettings.showDepthMap" type="checkbox" />
              <span class="toggle-slider"></span>
            </label>
          </div>
        </div>

        <!-- Measurement Settings -->
        <div class="settings-section">
          <h3 class="section-title">
            <IconSvg name="ruler" :size="18" class="section-icon" />
            Measurement Settings
          </h3>

          <div class="setting-item">
            <label class="setting-label">
              Measurement Unit
              <span class="setting-description">Unit for displaying measurements</span>
            </label>
            <select v-model="localSettings.measurementUnit" class="setting-select">
              <option value="mm">Millimeters (mm)</option>
              <option value="cm">Centimeters (cm)</option>
              <option value="m">Meters (m)</option>
              <option value="in">Inches (in)</option>
            </select>
          </div>

          <div class="setting-item">
            <label class="setting-label">
              Min Depth (mm)
              <span class="setting-description">Minimum detection depth</span>
            </label>
            <input 
              v-model.number="localSettings.minDepth" 
              type="number" 
              min="100" 
              max="5000" 
              step="100"
              class="setting-input"
            />
          </div>

          <div class="setting-item">
            <label class="setting-label">
              Max Depth (mm)
              <span class="setting-description">Maximum detection depth</span>
            </label>
            <input 
              v-model.number="localSettings.maxDepth" 
              type="number" 
              min="500" 
              max="10000" 
              step="100"
              class="setting-input"
            />
          </div>

          <div class="setting-item">
            <label class="setting-label">
              Auto Capture
              <span class="setting-description">Automatically capture measurements</span>
            </label>
            <label class="toggle-switch">
              <input v-model="localSettings.autoCapture" type="checkbox" />
              <span class="toggle-slider"></span>
            </label>
          </div>
        </div>

        <!-- Detection Settings -->
        <div class="settings-section">
          <h3 class="section-title">
            <IconSvg name="target" :size="18" class="section-icon" />
            Detection Settings
          </h3>

          <div class="setting-item">
            <label class="setting-label">
              Confidence Threshold
              <span class="setting-description">Minimum confidence for object detection ({{ localSettings.confidenceThreshold }})</span>
            </label>
            <input 
              v-model.number="localSettings.confidenceThreshold" 
              type="range" 
              min="0" 
              max="1" 
              step="0.05"
              class="setting-range"
            />
            <div class="range-labels">
              <span>0.0</span>
              <span>1.0</span>
            </div>
          </div>

          <div class="setting-item">
            <label class="setting-label">
              Min Object Size (px)
              <span class="setting-description">Minimum object size to detect</span>
            </label>
            <input 
              v-model.number="localSettings.minObjectSize" 
              type="number" 
              min="10" 
              max="500" 
              step="10"
              class="setting-input"
            />
          </div>

          <div class="setting-item">
            <label class="setting-label">
              Show Bounding Boxes
              <span class="setting-description">Display detection bounding boxes</span>
            </label>
            <label class="toggle-switch">
              <input v-model="localSettings.showBoundingBoxes" type="checkbox" />
              <span class="toggle-slider"></span>
            </label>
          </div>
        </div>



        <!-- ✅ Target Size Configuration Management - COMMENTED OUT -->
        <!-- Use ConfigurationManager component instead (accessible from Sidebar) -->
        <!--
        <div class="settings-section">
          <h3 class="section-title">
            <IconSvg name="list" :size="18" class="section-icon" />
            Target Size Configurations (ตั้งค่าขนาดเป้าหมาย)
          </h3>

          <p class="section-description">
            กำหนดขนาดเป้าหมายสำหรับการตรวจจับวัตถุ (ตรซม.) ซึ่งจะแสดงเป็นตัวเลือกในหน้าโปรแกรม
          </p>

          <div class="config-list">
            <div 
              v-for="config in configurations" 
              :key="config.id"
              class="config-item-compact"
            >
              <div class="config-info">
                <div class="config-name">{{ config.name }}</div>
                <div class="config-range">
                  {{ config.target_area_min }} - {{ config.target_area_max }} mm² 
                  <span class="tolerance-badge">±{{ config.tolerance }}</span>
                </div>
              </div>
              <div class="config-actions-compact">
                <button class="btn-icon-small" @click="editConfiguration(config)" title="แก้ไข">
                  <IconSvg name="edit" :size="14" />
                </button>
                <button class="btn-icon-small danger" @click="deleteConfiguration(config.id)" title="ลบ">
                  <IconSvg name="trash" :size="14" />
                </button>
              </div>
            </div>

            <div v-if="configurations.length === 0" class="empty-message">
              ยังไม่มี Configuration กรุณาเพิ่มขนาดเป้าหมาย
            </div>
          </div>

          <div class="config-form">
            <h4 class="form-subtitle">{{ editingConfigId ? 'แก้ไข' : 'เพิ่ม' }} Configuration</h4>
            
            <div class="setting-item">
              <label class="setting-label">ชื่อ Configuration</label>
              <input 
                v-model="configForm.name" 
                type="text" 
                class="setting-input"
                placeholder="เช่น Very Small (100-500 mm²)"
              />
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
              <div class="setting-item">
                <label class="setting-label">ขนาดต่ำสุด (mm²)</label>
                <input 
                  v-model.number="configForm.target_area_min" 
                  type="number" 
                  min="0"
                  step="10"
                  class="setting-input"
                />
              </div>

              <div class="setting-item">
                <label class="setting-label">ขนาดสูงสุด (mm²)</label>
                <input 
                  v-model.number="configForm.target_area_max" 
                  type="number" 
                  min="0"
                  step="10"
                  class="setting-input"
                />
              </div>
            </div>

            <div class="setting-item">
              <label class="setting-label">Tolerance (±mm²)</label>
              <input 
                v-model.number="configForm.tolerance" 
                type="number" 
                min="0"
                step="5"
                class="setting-input"
              />
            </div>

            <div class="form-actions-compact">
              <button 
                v-if="editingConfigId" 
                class="btn btn-secondary btn-sm" 
                @click="cancelEditConfiguration"
              >
                ยกเลิก
              </button>
              <button 
                class="btn btn-primary btn-sm" 
                @click="saveConfiguration"
                :disabled="!configForm.name || !configForm.target_area_min || !configForm.target_area_max"
              >
                <IconSvg name="check" :size="14" />
                {{ editingConfigId ? 'บันทึก' : 'เพิ่ม Configuration' }}
              </button>
            </div>
          </div>
        </div>
        -->
      </div>

      <div class="settings-footer">
        <button class="btn btn-secondary" @click="resetToDefaults">
          Reset to Defaults
        </button>
        <div class="footer-actions">
          <button class="btn" @click="$emit('close')">
            Cancel
          </button>
          <button class="btn btn-primary" @click="saveSettings">
            Save Settings
          </button>
        </div>
      </div>
    </div>


  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import IconSvg from './IconSvg.vue'
import axios from 'axios'
import { useToast } from '../composables/useToast'

const { showToast } = useToast()

const props = defineProps({
  settings: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['close', 'update-settings'])

// ✅ Configurations Management - COMMENTED OUT
// Use ConfigurationManager component instead
/*
const configurations = ref([])
const editingConfigId = ref(null)
const configForm = ref({
  name: '',
  target_area_min: 100,
  target_area_max: 500,
  tolerance: 30
})

const loadConfigurations = async () => {
  try {
    const response = await axios.get('/api/configurations')
    if (response.data.success) {
      configurations.value = response.data.configurations || []
    }
  } catch (error) {
    console.error('Error loading configurations:', error)
    showToast('โหลด Configurations ไม่สำเร็จ', 'error')
  }
}

const saveConfiguration = async () => {
  if (!configForm.value.name || !configForm.value.target_area_min || !configForm.value.target_area_max) {
    showToast('กรุณากรอกข้อมูลให้ครบ', 'warning')
    return
  }

  try {
    const url = editingConfigId.value 
      ? `/api/configurations/${editingConfigId.value}` 
      : '/api/configurations/create'
    
    const method = editingConfigId.value ? 'PUT' : 'POST'
    
    const response = await axios({
      method,
      url,
      data: configForm.value
    })
    
    if (response.data.success) {
      showToast(
        editingConfigId.value ? 'แก้ไข Configuration สำเร็จ' : 'เพิ่ม Configuration สำเร็จ',
        'success'
      )
      await loadConfigurations()
      cancelEditConfiguration()
    }
  } catch (error) {
    console.error('Error saving configuration:', error)
    showToast('บันทึกไม่สำเร็จ', 'error')
  }
}

const editConfiguration = (config) => {
  editingConfigId.value = config.id
  configForm.value = {
    name: config.name,
    target_area_min: config.target_area_min,
    target_area_max: config.target_area_max,
    tolerance: config.tolerance
  }
}

const cancelEditConfiguration = () => {
  editingConfigId.value = null
  configForm.value = {
    name: '',
    target_area_min: 100,
    target_area_max: 500,
    tolerance: 30
  }
}

const deleteConfiguration = async (configId) => {
  if (!confirm('คุณต้องการลบ Configuration นี้หรือไม่?')) {
    return
  }

  try {
    const response = await axios.delete(`/api/configurations/${configId}`)
    
    if (response.data.success) {
      showToast('ลบ Configuration สำเร็จ', 'success')
      await loadConfigurations()
    }
  } catch (error) {
    console.error('Error deleting configuration:', error)
    showToast('ลบไม่สำเร็จ', 'error')
  }
}
*/

const localSettings = ref({
  // Camera
  resolution: '1080p',
  fpsLimit: 30,
  showDepthMap: false,
  
  // Measurement
  measurementUnit: 'mm',
  minDepth: 300,
  maxDepth: 3000,
  autoCapture: true,
  
  // Detection
  confidenceThreshold: 0.5,
  minObjectSize: 50,
  showBoundingBoxes: true,
  
  // Calibration
  referenceSize: 100,
  
  ...props.settings
})

// Camera list management
const cameras = ref([])
const currentDeviceId = ref(null)
const loadingCameras = ref(false)

const loadCameras = async () => {
  loadingCameras.value = true
  try {
    const response = await axios.get('/api/cameras/list')
    if (response.data.success) {
      cameras.value = response.data.cameras || []
      currentDeviceId.value = response.data.current_device_id
      console.log(`📹 Found ${cameras.value.length} camera(s)`, cameras.value)
    }
  } catch (error) {
    console.error('Error loading cameras:', error)
    showToast('โหลดรายการกล้องไม่สำเร็จ', 'error')
    cameras.value = []
  } finally {
    loadingCameras.value = false
  }
}

const refreshCameras = async () => {
  showToast('กำลังค้นหากล้อง...', 'info')
  await loadCameras()
  if (cameras.value.length > 0) {
    showToast(`พบกล้อง ${cameras.value.length} ตัว`, 'success')
  } else {
    showToast('ไม่พบกล้อง Luxonis', 'warning')
  }
}

const formatMxId = (mxid) => {
  // Format MxID to be more readable (show first 8 chars)
  return mxid ? `${mxid.substring(0, 8)}...` : 'Unknown'
}




const saveSettings = () => {
  emit('update-settings', localSettings.value)
  emit('close')
}

const resetToDefaults = () => {
  localSettings.value = {
    resolution: '1080p',
    fpsLimit: 30,
    showDepthMap: false,
    measurementUnit: 'mm',
    minDepth: 300,
    maxDepth: 3000,
    autoCapture: true,
    confidenceThreshold: 0.5,
    minObjectSize: 50,
    showBoundingBoxes: true
  }
}

// ✅ Load configurations on mount
onMounted(() => {
  loadCameras()
  // loadConfigurations() // ✅ COMMENTED OUT - use ConfigurationManager instead
})
</script>

<style scoped>
.settings-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100001;
  animation: fadeIn 0.2s ease-out;
}

.settings-panel {
  background: var(--bg-card);
  border-radius: 16px;
  width: 90%;
  max-width: 700px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--border-color);
  animation: slideUp 0.3s ease-out;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.settings-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 28px;
  border-bottom: 1px solid var(--border-color);
}

.settings-title {
  font-size: 24px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 12px;
}

.close-button {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.close-button:hover {
  background: var(--bg-card-hover);
  color: var(--text-primary);
}

.settings-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px 28px;
}

.settings-section {
  margin-bottom: 32px;
}

.settings-section:last-child {
  margin-bottom: 0;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-primary);
}

.section-icon {
  font-size: 18px;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
  border-bottom: 1px solid var(--border-color);
}

.setting-item:last-child {
  border-bottom: none;
}

.setting-label {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.setting-description {
  font-size: 12px;
  font-weight: 400;
  color: var(--text-secondary);
}

.setting-input,
.setting-select {
  width: 200px;
  padding: 8px 12px;
  background: var(--bg-dark);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 14px;
  transition: all 0.2s;
}

.setting-input:focus,
.setting-select:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(var(--primary-rgb), 0.1);
}

.setting-range {
  width: 200px;
  height: 6px;
  border-radius: 3px;
  background: var(--border-color);
  outline: none;
  -webkit-appearance: none;
  cursor: pointer;
}

.setting-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--primary-color);
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.setting-range::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--primary-color);
  cursor: pointer;
  border: none;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.range-labels {
  display: flex;
  justify-content: space-between;
  width: 200px;
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.toggle-switch {
  position: relative;
  width: 52px;
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
  inset: 0;
  background: var(--border-color);
  border-radius: 28px;
  transition: all 0.3s;
}

.toggle-slider::before {
  content: '';
  position: absolute;
  width: 22px;
  height: 22px;
  left: 3px;
  top: 3px;
  background: white;
  border-radius: 50%;
  transition: all 0.3s;
}

.toggle-switch input:checked + .toggle-slider {
  background: var(--primary-color);
}

.toggle-switch input:checked + .toggle-slider::before {
  transform: translateX(24px);
}

.settings-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 28px;
  border-top: 1px solid var(--border-color);
}

.footer-actions {
  display: flex;
  gap: 12px;
}

.btn {
  padding: 10px 20px;
  border-radius: 8px;
  border: none;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-dark);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn:hover {
  background: var(--bg-card-hover);
}

.btn-primary {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: white;
}

.btn-primary:hover {
  background: var(--primary-dark);
}

.btn-secondary {
  background: transparent;
  color: var(--text-secondary);
}

.mt-2 {
  margin-top: 8px;
}

.depth-analysis {
  background: var(--bg-dark);
  padding: 15px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  margin-top: 10px;
}

.depth-info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
  font-size: 13px;
}

.depth-info-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.depth-info-row span {
  color: var(--text-secondary);
}

.depth-info-row strong {
  color: var(--primary-color);
  font-size: 14px;
}

/* Visualization Modal */
.visualization-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100002;
  animation: fadeIn 0.2s ease;
}

.visualization-content {
  background: var(--bg-card);
  border-radius: 12px;
  max-width: 90vw;
  max-height: 90vh;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  animation: slideUp 0.3s ease;
}

.visualization-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-dark);
}

.visualization-header h3 {
  margin: 0;
  font-size: 18px;
  color: var(--text-primary);
}

.close-btn {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 8px;
  border-radius: 6px;
  transition: all 0.2s;
}

.close-btn:hover {
  background: var(--bg-card-hover);
  color: var(--text-primary);
}

.visualization-body {
  padding: 20px;
  text-align: center;
}

.visualization-image {
  max-width: 100%;
  max-height: 70vh;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.visualization-hint {
  margin-top: 15px;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
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
    transform: translateY(30px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

/* Target Size Configurations Styles */
.config-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 15px;
}

.config-item-compact {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  transition: all 0.2s;
}

.config-item-compact:hover {
  background: var(--bg-card-hover);
  border-color: var(--primary);
}

.config-item-compact.editing {
  border-color: var(--warning);
  background: rgba(255, 193, 7, 0.1);
}

.config-info {
  flex: 1;
}

.config-name {
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.config-details {
  font-size: 12px;
  color: var(--text-secondary);
}

.config-actions {
  display: flex;
  gap: 8px;
}

.config-actions .icon-btn {
  padding: 6px 10px;
  font-size: 12px;
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 15px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  margin-bottom: 15px;
}

.config-form .input-group {
  margin-bottom: 0;
}

.config-form-actions {
  display: flex;
  gap: 10px;
  margin-top: 5px;
}

.config-form-actions .primary {
  flex: 1;
}

.config-form-actions .secondary {
  flex: 1;
}

.add-config-btn {
  width: 100%;
  padding: 10px;
  background: var(--success);
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.add-config-btn:hover {
  background: #28a745;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(40, 167, 69, 0.3);
}

/* Camera List Styles */
.camera-list {
  margin-top: 12px;
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 32px;
  color: var(--text-secondary);
  font-size: 14px;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 3px solid var(--border-color);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 32px;
  text-align: center;
  color: var(--text-secondary);
}

.empty-state svg {
  opacity: 0.5;
}

.empty-state p {
  margin: 0;
  font-size: 14px;
}

.camera-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.camera-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--bg-dark);
  border: 2px solid var(--border-color);
  border-radius: 10px;
  transition: all 0.2s;
}

.camera-item:hover {
  background: var(--bg-card-hover);
  border-color: var(--primary-color);
}

.camera-item.active {
  border-color: var(--primary-color);
  background: rgba(var(--primary-rgb), 0.1);
}

.camera-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  background: var(--primary-color);
  border-radius: 8px;
  color: white;
  flex-shrink: 0;
}

.camera-item.active .camera-icon {
  background: var(--success);
}

.camera-info {
  flex: 1;
  min-width: 0;
}

.camera-name {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.badge-active {
  display: inline-block;
  padding: 2px 8px;
  background: var(--success);
  color: white;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.camera-details {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary);
  flex-wrap: wrap;
}

.camera-id {
  font-family: var(--font-mono);
  background: var(--bg-card);
  padding: 2px 6px;
  border-radius: 4px;
}

.camera-protocol {
  padding: 2px 6px;
  background: var(--primary-color);
  color: white;
  border-radius: 4px;
  font-weight: 600;
}

.camera-state {
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
  text-transform: uppercase;
}

.camera-state.state-bootloader,
.camera-state.state-unbooted {
  background: var(--success);
  color: white;
}

.camera-state.state-booted {
  background: var(--primary-color);
  color: white;
}

.camera-state.state-unknown {
  background: var(--text-secondary);
  color: white;
}

.refresh-btn {
  margin-top: 12px;
  width: 100%;
  justify-content: center;
}

.btn-sm {
  padding: 8px 16px;
  font-size: 13px;
}
</style>
