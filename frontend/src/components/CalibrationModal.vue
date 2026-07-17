<template>
  <div class="calibration-overlay" @click.self="$emit('close')">
    <div class="calibration-modal">
      <div class="calibration-header">
        <h2 class="calibration-title">
          <IconSvg name="target" :size="28" />
          Camera Calibration (Auto)
        </h2>
        <button class="close-button" @click="$emit('close')">
          <IconSvg name="close" :size="20" />
        </button>
      </div>

      <div class="calibration-content">
        <div v-if="step === 1" class="calibration-step">
          <div class="step-header">
            <div class="step-number">Step 1</div>
            <h3 class="step-title">Prepare Reference Objects</h3>
          </div>
          <div class="step-content">
            <div class="instruction-box">
              <IconSvg name="ruler" :size="48" style="opacity: 0.6; margin-bottom: 16px;" />
              <p class="instruction-text">
                Place TWO reference objects in front of the camera:
              </p>
              <p class="instruction-subtext">
                📦 Object 1: <strong>50 × 50 mm</strong><br>
                📦 Object 2: <strong>20 × 20 mm</strong>
              </p>
              <p class="instruction-subtext" style="margin-top: 12px;">
                Both objects should be clearly visible within the camera's field of view.
              </p>
            </div>
            
            <!-- Camera Preview -->
            <div class="camera-preview">
              <div class="preview-frame" v-if="!cameraStream">
                <IconSvg name="camera" :size="64" style="opacity: 0.3;" />
                <p style="margin-top: 16px; opacity: 0.7;">Loading camera...</p>
              </div>
              <img v-else :src="cameraStream" class="camera-feed" alt="Camera feed" />
              
              <!-- Detection overlay -->
              <div v-if="detectedObjects" class="detection-overlay">
                <div 
                  v-for="(obj, key) in detectedObjects" 
                  :key="key"
                  class="detection-box"
                  :style="{
                    left: obj.bbox[0] + 'px',
                    top: obj.bbox[1] + 'px',
                    width: obj.bbox[2] + 'px',
                    height: obj.bbox[3] + 'px'
                  }"
                >
                  <span class="detection-label">{{ obj.reference }}</span>
                </div>
              </div>
            </div>
          </div>
          
          <div class="step-actions">
            <button class="btn btn-primary" @click="startAutoCalibration" :disabled="calibrating">
              <IconSvg v-if="!calibrating" name="target" :size="16" style="margin-right: 8px;" />
              <span v-if="calibrating" class="spinner"></span>
              {{ calibrating ? 'Calibrating...' : 'Start Auto-Calibration' }}
            </button>
          </div>
        </div>

        <div v-else-if="step === 2" class="calibration-step">
          <div class="step-header">
            <div class="step-number">Step 2</div>
            <h3 class="step-title">🎯 Review Calibration Results</h3>
            <p class="step-subtitle">ตรวจสอบผลลัพธ์ก่อนบันทึก</p>
          </div>
          <div class="step-content">
            
            <!-- 🎨 แสดงภาพผลลัพธ์พร้อม ROI box (เด่นที่สุด) -->
            <div v-if="resultImage" class="result-image-preview-main">
              <h4 class="preview-title">📸 ภาพผลลัพธ์การตรวจจับ</h4>
              <div class="image-container">
                <img :src="resultImage" alt="Calibration Result" class="calibration-result-image" />
              </div>
              <div class="preview-legend">
                <div class="legend-item">
                  <span class="legend-box" style="background: rgba(0, 255, 0, 0.3); border: 2px solid #00ff00;"></span>
                  <span>วัตถุใหญ่ (50×50mm)</span>
                </div>
                <div class="legend-item">
                  <span class="legend-box" style="background: rgba(255, 200, 0, 0.3); border: 2px solid #ffc800;"></span>
                  <span>วัตถุเล็ก (20×20mm)</span>
                </div>
              </div>
              <div class="preview-hint">
                ✅ ตรวจสอบว่ากรอบและขนาดถูกต้องหรือไม่ ถ้าไม่ถูกต้องให้กด Retry
              </div>
            </div>

            <div class="calibration-results">
              <!-- Detected Objects Info -->
              <div class="result-section" v-if="calibrationData.detected_objects">
                <h5 class="result-section-title">📦 ขนาดที่ตรวจวัดได้</h5>
                <div class="detected-objects-grid">
                  <div class="detected-object-card large-object">
                    <div class="object-label">🟢 วัตถุใหญ่ (50×50mm)</div>
                    <div class="object-details">
                      <div class="detail-row">
                        <span class="detail-label">พิกเซล:</span>
                        <span class="detail-value">{{ calibrationData.detected_objects.large.width_px }} × {{ calibrationData.detected_objects.large.height_px }} px</span>
                      </div>
                      <div class="detail-row highlight">
                        <span class="detail-label">ผลลัพธ์:</span>
                        <span class="detail-value">{{ calibrationData.detected_objects.large.width_mm }} × {{ calibrationData.detected_objects.large.height_mm }} mm</span>
                      </div>
                    </div>
                  </div>
                  <div class="detected-object-card small-object">
                    <div class="object-label">🔵 วัตถุเล็ก (20×20mm)</div>
                    <div class="object-details">
                      <div class="detail-row">
                        <span class="detail-label">พิกเซล:</span>
                        <span class="detail-value">{{ calibrationData.detected_objects.small.width_px }} × {{ calibrationData.detected_objects.small.height_px }} px</span>
                      </div>
                      <div class="detail-row highlight">
                        <span class="detail-label">ผลลัพธ์:</span>
                        <span class="detail-value">{{ calibrationData.detected_objects.small.width_mm }} × {{ calibrationData.detected_objects.small.height_mm }} mm</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              
                
              <div class="result-section">
                <h5 class="result-section-title">🎯 Calibration Factors</h5>
                <div class="result-item">
                  <span class="result-label">Width Factor:</span>
                  <span class="result-value">{{ calibrationData.calibration_width }}</span>
                </div>
                <div class="result-item">
                  <span class="result-label">Height Factor:</span>
                  <span class="result-value">{{ calibrationData.calibration_height }}</span>
                </div>
                <div class="result-item">
                  <span class="result-label">Average Factor:</span>
                  <span class="result-value">{{ calibrationData.calibration_factor }}</span>
                </div>
                <div class="result-item">
                  <span class="result-label">Accuracy:</span>
                  <span class="result-value accuracy">{{ calibrationData.accuracy }}%</span>
                </div>
              </div>
              
              <div class="result-section collapsed">
                <details>
                  <summary class="result-section-title">📐 Calibration Formula (คลิกเพื่อดู)</summary>
                  <div class="formula-box">
                    <div class="formula-item">
                      <code>{{ calibrationData.formula_width }}</code>
                    </div>
                    <div class="formula-item">
                      <code>{{ calibrationData.formula_height }}</code>
                    </div>
                    <div class="formula-item highlight">
                      <code>{{ calibrationData.formula_average }}</code>
                    </div>
                  </div>
                </details>
              </div>
            </div>
          </div>
          
          <div class="step-actions">
            <button class="btn btn-secondary" @click="resetCalibration">
              <IconSvg name="arrow-h" :size="16" style="margin-right: 8px; transform: rotate(180deg);" />
              🔄 Retry Calibration
            </button>
            <button class="btn btn-primary btn-save" @click="saveCalibration" :disabled="saving">
              <IconSvg v-if="!saving" name="check" :size="16" style="margin-right: 8px;" />
              <span v-if="saving" class="spinner"></span>
              {{ saving ? 'กำลังบันทึก...' : '✅ Save & Apply' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import IconSvg from './IconSvg.vue'
import { useMeasurementStore } from '../stores/measurementStore'

const emit = defineEmits(['close', 'calibration-complete'])

const apiBaseUrl = window.location.origin  // ใช้ origin ที่เปิดหน้าเว็บ (จะได้ port ถูกต้อง)

const step = ref(1)
const cameraStream = ref('')
const calibrating = ref(false)
const saving = ref(false)
const detectedObjects = ref(null)

// measurement store (so main views can show the same detection boxes)
const measurementStore = useMeasurementStore()
const resultImage = ref('')  // ภาพผลลัพธ์ที่มี ROI
const calibrationData = ref({
  calibration_width: 0,
  calibration_height: 0,
  calibration_factor: 0,
  formula_width: '',
  formula_height: '',
  formula_average: '',
  accuracy: 0,
  detected_objects: null
})

let streamInterval = null

// Start camera stream with ROI detection
const startCameraStream = () => {
  streamInterval = setInterval(async () => {
    try {
      // ใช้ calibration preview endpoint ที่มี ROI detection
      // เพิ่ม timestamp เป็น cache buster เพื่อให้ได้ภาพใหม่ทุกครั้ง
      const response = await fetch(`${apiBaseUrl}/api/calibration/preview?t=${Date.now()}`)
      if (response.ok) {
        const blob = await response.blob()
        // Revoke previous URL to prevent memory leak
        if (cameraStream.value) {
          URL.revokeObjectURL(cameraStream.value)
        }
        cameraStream.value = URL.createObjectURL(blob)
      }
    } catch (error) {
      console.error('Failed to fetch camera stream:', error)
    }
  }, 200) // Update every 200ms (ลดความถี่ลงเพื่อ performance)
}

// Stop camera stream
const stopCameraStream = () => {
  if (streamInterval) {
    clearInterval(streamInterval)
    streamInterval = null
  }
}

// Start auto-calibration
const startAutoCalibration = async () => {
  calibrating.value = true
  detectedObjects.value = null
  
  try {
    const response = await fetch(`${apiBaseUrl}/api/calibration/auto-detect`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    })
    
    const result = await response.json()
    
    if (result.success) {
      calibrationData.value = result.data
      detectedObjects.value = result.data.detected_objects

      // Map detected_objects into an array for the global store so main views show boxes
      try {
        const detectionsArray = []
        const dobj = result.data.detected_objects || {}
        Object.keys(dobj).forEach((k) => {
          const o = dobj[k]
          if (!o) return
          const bbox = o.bbox || o.bounding_box || o.box || null
          if (!Array.isArray(bbox) || bbox.length !== 4) return
          detectionsArray.push({
            bbox: bbox,
            label: o.reference || o.label || k,
            confidence: o.confidence || 1,
            width_px: o.width_px || bbox[2],
            height_px: o.height_px || bbox[3],
            width_mm: o.width_mm || o.detected_width_mm || null,
            height_mm: o.height_mm || o.detected_height_mm || null,
            status: o.status || null
          })
        })

        measurementStore.detections = detectionsArray
      } catch (e) {
        console.warn('Failed to map detected_objects to store.detections', e)
      }

      // เก็บภาพผลลัพธ์ที่มี ROI box
      if (result.data.result_image) {
        resultImage.value = 'data:image/jpeg;base64,' + result.data.result_image
      }
      
      // Stop live stream and show result
      stopCameraStream()
      
      // Show result step
      setTimeout(() => {
        step.value = 2
      }, 500)
    } else {
      alert('Auto-calibration failed: ' + result.message)
    }
  } catch (error) {
    console.error('Auto-calibration error:', error)
    alert('Failed to perform auto-calibration. Please try again.')
  } finally {
    calibrating.value = false
  }
}

// Save calibration
const saveCalibration = async () => {
  saving.value = true
  
  try {
    const response = await fetch(`${apiBaseUrl}/api/calibration/save`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        calibration_width: calibrationData.value.calibration_width,
        calibration_height: calibrationData.value.calibration_height,
        calibration_factor: calibrationData.value.calibration_factor
      })
    })
    
    const result = await response.json()
    
    if (result.success) {
      emit('calibration-complete', {
        calibrationFactor: calibrationData.value.calibration_factor,
        calibrationWidth: calibrationData.value.calibration_width,
        calibrationHeight: calibrationData.value.calibration_height,
        accuracy: calibrationData.value.accuracy
      })
    } else {
      alert('Failed to save calibration: ' + result.message)
    }
  } catch (error) {
    console.error('Save calibration error:', error)
    alert('Failed to save calibration. Please try again.')
  } finally {
    saving.value = false
  }
}

// Reset calibration
const resetCalibration = () => {
  step.value = 1
  detectedObjects.value = null
  calibrating.value = false
  resultImage.value = ''  // Clear result image
  // Clear global detections so main view removes boxes
  try { measurementStore.detections = [] } catch (e) { /* ignore */ }
  startCameraStream()  // Restart live stream
}

onMounted(() => {
  startCameraStream()
})

onUnmounted(() => {
  stopCameraStream()
})
</script>

<style scoped>
.calibration-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100001;
  animation: fadeIn 0.2s ease-out;
}

.calibration-modal {
  background: var(--bg-card);
  border-radius: 16px;
  width: 90%;
  max-width: 700px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-xl);
  border: 1px solid var(--border-color);
  animation: slideUp 0.3s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
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

.calibration-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 28px;
  border-bottom: 1px solid var(--border-color);
}

.calibration-title {
  font-size: 24px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--text-primary);
}

.close-button {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
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

.calibration-content {
  flex: 1;
  overflow-y: auto;
  padding: 28px;
}

.calibration-step {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.step-header {
  text-align: center;
}

.step-number {
  display: inline-block;
  padding: 6px 16px;
  background: var(--primary-color);
  color: white;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}

.step-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.step-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.instruction-box {
  background: var(--bg-dark);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 24px;
  text-align: center;
}

.instruction-text {
  font-size: 15px;
  color: var(--text-primary);
  margin: 0 0 8px 0;
  font-weight: 500;
}

.instruction-subtext {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.6;
}

.camera-preview {
  background: var(--bg-dark);
  border: 2px dashed var(--border-color);
  border-radius: 12px;
  min-height: 300px;
  max-height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.preview-frame {
  text-align: center;
  color: var(--text-secondary);
}

.camera-feed {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.detection-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.detection-box {
  position: absolute;
  border: 3px solid var(--primary-color);
  border-radius: 4px;
  box-shadow: 0 0 10px rgba(var(--primary-rgb), 0.5);
}

.detection-label {
  position: absolute;
  top: -25px;
  left: 0;
  background: var(--primary-color);
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.success-box {
  background: linear-gradient(135deg, rgba(var(--primary-rgb), 0.1), rgba(var(--primary-rgb), 0.05));
  border: 1px solid rgba(var(--primary-rgb), 0.3);
  border-radius: 12px;
  padding: 32px;
  text-align: center;
}

.success-icon {
  margin-bottom: 16px;
  color: var(--success-color);
}

.success-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.success-text {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0 0 24px 0;
}

.calibration-results {
  display: flex;
  flex-direction: column;
  gap: 20px;
  text-align: left;
}

.result-section {
  background: var(--bg-dark);
  border-radius: 8px;
  padding: 16px;
  border: 1px solid var(--border-color);
}

.result-section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 12px 0;
}

/* 🎨 Result Image Preview with ROI */
.result-image-preview {
  margin: 20px 0;
  padding: 16px;
  background: var(--bg-dark);
  border: 2px solid var(--border-color);
  border-radius: 12px;
}

.calibration-result-image {
  width: 100%;
  max-height: 400px;
  object-fit: contain;
  border-radius: 8px;
  margin-top: 12px;
}

.result-hint {
  font-size: 12px;
  color: var(--text-secondary);
  text-align: center;
  margin: 8px 0 0 0;
  font-style: italic;
}

/* 🎨 Main Result Image Preview (ภาพผลลัพธ์หลัก) */
.result-image-preview-main {
  margin: 0 0 24px 0;
  padding: 20px;
  background: linear-gradient(135deg, rgba(var(--primary-rgb), 0.05), rgba(var(--primary-rgb), 0.05));
  border: 2px solid var(--primary-color);
  border-radius: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.preview-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 16px 0;
  text-align: center;
}

.image-container {
  background: #000;
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 12px;
}

.image-container .calibration-result-image {
  width: 100%;
  height: auto;
  display: block;
  max-height: 450px;
  object-fit: contain;
}

.preview-legend {
  display: flex;
  justify-content: center;
  gap: 24px;
  margin: 12px 0;
  padding: 12px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-primary);
}

.legend-box {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  display: inline-block;
}

.preview-hint {
  text-align: center;
  font-size: 14px;
  color: var(--success-color);
  padding: 10px;
  background: rgba(var(--primary-rgb), 0.1);
  border-radius: 8px;
  border: 1px solid rgba(var(--primary-rgb), 0.3);
}

.step-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 4px 0 0 0;
  font-weight: normal;
}

/* ปรับปรุง Detected Object Cards */
.detected-object-card {
  background: rgba(var(--primary-rgb), 0.05);
  border: 2px solid var(--border-color);
  border-radius: 12px;
  padding: 16px;
  transition: all 0.3s ease;
}

.detected-object-card:hover {
  border-color: var(--primary-color);
  box-shadow: 0 4px 12px rgba(var(--primary-rgb), 0.2);
}

.detected-object-card.large-object {
  border-color: rgba(0, 255, 0, 0.4);
}

.detected-object-card.small-object {
  border-color: rgba(255, 200, 0, 0.4);
}

.object-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--primary-color);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-color);
}

.object-details {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.8;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
}

.detail-row.highlight {
  background: rgba(var(--primary-rgb), 0.1);
  padding: 8px;
  border-radius: 6px;
  margin-top: 6px;
  font-weight: 600;
}

.detail-label {
  color: var(--text-secondary);
}

.detail-value {
  color: var(--text-primary);
  font-family: var(--font-mono);
}

.detail-row.highlight .detail-value {
  color: var(--success-color);
  font-size: 13px;
}

/* Collapsible Formula Section */
.result-section.collapsed details {
  cursor: pointer;
}

.result-section.collapsed summary {
  list-style: none;
  cursor: pointer;
  user-select: none;
}

.result-section.collapsed summary::-webkit-details-marker {
  display: none;
}

.result-section.collapsed summary::after {
  content: ' ▼';
  font-size: 10px;
  margin-left: 8px;
  opacity: 0.6;
}

.result-section.collapsed[open] summary::after {
  content: ' ▲';
}

/* ปรับปรุงปุ่ม */
.btn-secondary {
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover {
  background: var(--bg-dark);
  border-color: var(--primary-color);
}

.btn-save {
  font-weight: 600;
  padding: 14px 32px;
}

.formula-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.formula-item {
  background: rgba(var(--primary-rgb), 0.1);
  border: 1px solid rgba(var(--primary-rgb), 0.3);
  border-radius: 6px;
  padding: 10px 14px;
}

.formula-item.highlight {
  background: rgba(var(--primary-rgb), 0.1);
  border-color: rgba(var(--primary-rgb), 0.4);
}

.formula-item code {
  color: var(--text-primary);
  font-size: 13px;
  font-family: var(--font-mono);
}

.result-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
}

.result-item:last-child {
  border-bottom: none;
}

.result-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.result-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  font-family: var(--font-mono);
}

.result-value.accuracy {
  color: var(--success-color);
}

.detected-objects-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.detected-object-card {
  background: rgba(var(--primary-rgb), 0.05);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 12px;
}

.object-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--primary-color);
  margin-bottom: 8px;
}

.object-details {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.step-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  padding-top: 8px;
}

.btn {
  padding: 12px 24px;
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

.btn:hover:not(:disabled) {
  background: var(--bg-card-hover);
  transform: translateY(-1px);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-dark);
  box-shadow: var(--glow-primary);
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.success-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.success-text {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0 0 24px 0;
}

.calibration-results {
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: var(--bg-dark);
  border-radius: 8px;
  padding: 16px;
}

.result-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
}

.result-item:last-child {
  border-bottom: none;
}

.result-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.result-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  font-family: var(--font-mono);
}

.step-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  padding-top: 8px;
}

.btn {
  padding: 12px 24px;
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

.btn:hover:not(:disabled) {
  background: var(--bg-card-hover);
  transform: translateY(-1px);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-dark);
  box-shadow: var(--glow-primary);
}
</style>
