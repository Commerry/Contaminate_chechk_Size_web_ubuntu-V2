<template>
  <div class="camera-view-container">
    <div class="card camera-card">
      <div class="card-header">
        <h2 class="card-title">
          <IconSvg name="video" :size="20" />
          Live Camera Feed
        </h2>
        <div class="card-actions">
          <span v-if="isActive" class="badge badge-success pulse">
            <span class="record-dot"></span>
            LIVE
          </span>
          <span v-else class="badge badge-warning">STANDBY</span>
        </div>
      </div>

      <div class="camera-viewport">
        <!-- Camera Canvas -->
        <canvas 
          ref="canvasRef" 
          class="camera-canvas"
          :class="{ 'inactive': !isActive && !frameData?.image }"
        ></canvas>

        <!-- Prediction Status Badge -->
        <div v-if="isActive" class="prediction-status" :class="{ active: isPredicting || isContourDetecting }">
          <span class="status-dot"></span>
          <template v-if="isContourDetecting">Contour Mode Active</template>
          <template v-else-if="isPredicting">Prediction Active</template>
          <template v-else>Detection Paused</template>
        </div>

        <!-- Placeholder when camera is off AND no frame is available -->
        <div v-if="!isActive && !frameData?.image" class="camera-placeholder">
          <div class="placeholder-content">
            <IconSvg name="camera" :size="64" style="opacity: 0.4; margin-bottom: 16px;" />
            <p class="placeholder-text">{{ !isActive ? 'Camera Standby' : (isConnected ? 'Waiting for Camera Feed' : 'Camera Not Connected') }}</p>
            <p class="placeholder-subtext">{{ statusMessage }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Depth Map View (Optional) -->
    <div v-if="showDepthMap" class="card depth-card">
      <div class="card-header">
        <h2 class="card-title">
          <IconSvg name="layers" :size="20" />
          Depth Map
        </h2>
      </div>
      <div class="depth-viewport">
        <canvas ref="depthCanvasRef" class="depth-canvas"></canvas>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import IconSvg from './IconSvg.vue'

const props = defineProps({
  isActive: {
    type: Boolean,
    default: false
  },
  isConnected: {
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
  threeZoneMode: {
    type: Boolean,
    default: false
  },
  detections: {
    type: Array,
    default: () => []
  },
  frameData: {
    type: Object,
    default: null
  },
  statusMessage: {
    type: String,
    default: 'Click "Start Camera" to begin'
  },
  showDepthMap: {
    type: Boolean,
    default: false
  }
})

const canvasRef = ref(null)
const depthCanvasRef = ref(null)
const currentFps = ref(30)
const resolution = ref('1920x1080')

// Update canvas with frame data
watch(() => props.frameData, (newFrame) => {
  if (newFrame && canvasRef.value) {
    drawFrame(newFrame)
  }
}, { deep: true })

// Re-draw when detections change
watch(() => props.detections, () => {
  if (props.frameData && canvasRef.value) {
    drawFrame(props.frameData)
  }
}, { deep: true })

// ✅ Re-draw เมื่อสถานะ detection เปลี่ยน (เพื่อล้างกรอบทันที)
watch(() => props.isContourDetecting, () => {
  if (props.frameData && canvasRef.value) {
    drawFrame(props.frameData)
  }
})

watch(() => props.isPredicting, () => {
  if (props.frameData && canvasRef.value) {
    drawFrame(props.frameData)
  }
})

const drawFrame = (frameData) => {
  const canvas = canvasRef.value
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  
  // Check if frame data is valid
  if (!frameData || !frameData.image) {
    // Draw placeholder when no image
    ctx.fillStyle = '#1e293b'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.fillStyle = '#64748b'
    ctx.font = '24px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText('Waiting for camera feed...', canvas.width / 2, canvas.height / 2)
    return
  }
  
  // Validate image data format
  const imageData = frameData.image || frameData.data
  if (!imageData || typeof imageData !== 'string') {
    console.warn('Invalid frame data format')
    return
  }
  
  // Create image from base64
  const img = new Image()
  img.onload = () => {
    canvas.width = img.width
    canvas.height = img.height
    ctx.drawImage(img, 0, 0)
    
    // 🎯 วาดเส้นแบ่ง 3 zones ถ้าอยู่โหมด 3-zone
    if (props.threeZoneMode && (props.isPredicting || props.isContourDetecting)) {
      drawZoneDividers(ctx, canvas.width, canvas.height)
    }
    
    // ✅ วาดกรอบ ROI เฉพาะเมื่อ Contour หรือ Prediction ทำงาน AND มี detections
    const shouldDrawBoxes = (props.isPredicting === true || props.isContourDetecting === true) && 
                           props.detections && 
                           Array.isArray(props.detections) && 
                           props.detections.length > 0
    
    if (shouldDrawBoxes) {
      console.log('🎨 Drawing', props.detections.length, 'detection boxes')
      drawDetectionBoxes(ctx, canvas.width, canvas.height)
    } else {
      console.log('⏭️ Skipping boxes - isPredicting:', props.isPredicting, 'isContour:', props.isContourDetecting, 'detections:', props.detections?.length || 0)
    }
  }
  
  img.onerror = () => {
    console.error('Failed to load frame image')
    // Draw error placeholder
    ctx.fillStyle = '#1e293b'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.fillStyle = '#ef4444'
    ctx.font = '20px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText('Error loading frame', canvas.width / 2, canvas.height / 2)
  }
  
  // Set image source with validation
  if (imageData.startsWith('data:image/')) {
    img.src = imageData
  } else if (imageData.length > 0) {
    img.src = 'data:image/jpeg;base64,' + imageData
  }
}

// 🎯 วาดเส้นแบ่ง 3 zones
const drawZoneDividers = (ctx, canvasWidth, canvasHeight) => {
  const zoneWidth = canvasWidth / 3
  
  // เส้นแบ่งโซน 1-2
  ctx.strokeStyle = '#ff0000'  // สีแดง
  ctx.lineWidth = 4
  ctx.setLineDash([10, 5])  // เส้นประ
  ctx.beginPath()
  ctx.moveTo(zoneWidth, 0)
  ctx.lineTo(zoneWidth, canvasHeight)
  ctx.stroke()
  
  // เส้นแบ่งโซน 2-3
  ctx.beginPath()
  ctx.moveTo(zoneWidth * 2, 0)
  ctx.lineTo(zoneWidth * 2, canvasHeight)
  ctx.stroke()
  ctx.setLineDash([])  // รีเซ็ตเส้นประ
  
  // วาดข้อความ Zone 1, 2, 3
  ctx.fillStyle = '#ff0000'
  ctx.font = 'bold 24px Arial'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'top'
  
  // Background สำหรับข้อความ
  ctx.globalAlpha = 0.7
  ctx.fillStyle = '#000000'
  ctx.fillRect(zoneWidth / 2 - 60, 10, 120, 40)
  ctx.fillRect(zoneWidth + zoneWidth / 2 - 60, 10, 120, 40)
  ctx.fillRect(zoneWidth * 2 + zoneWidth / 2 - 60, 10, 120, 40)
  ctx.globalAlpha = 1.0
  
  ctx.fillStyle = '#ff0000'
  ctx.fillText('ZONE 1', zoneWidth / 2, 20)
  ctx.fillText('ZONE 2', zoneWidth + zoneWidth / 2, 20)
  ctx.fillText('ZONE 3', zoneWidth * 2 + zoneWidth / 2, 20)
}

const drawDetectionBoxes = (ctx, canvasWidth, canvasHeight) => {
  console.log('🖌️ drawDetectionBoxes called with', props.detections.length, 'detections')
  
  // ⭐ สีสำหรับหลายวัตถุ (เมื่อไม่มี in_range)
  const defaultColors = [
    { stroke: '#00ff00', fill: 'rgba(0, 255, 0, 0.1)' },      // เขียว
    { stroke: '#ff0000', fill: 'rgba(255, 0, 0, 0.1)' },      // แดง
    { stroke: '#0000ff', fill: 'rgba(0, 0, 255, 0.1)' },      // น้ำเงิน
    { stroke: '#ffff00', fill: 'rgba(255, 255, 0, 0.1)' },    // เหลือง
    { stroke: '#ff00ff', fill: 'rgba(255, 0, 255, 0.1)' }     // ม่วง
  ]
  
  // ✅ สีสำหรับ Small Object Mode (ตาม in_range)
  const inRangeColor = { stroke: '#00ff00', fill: 'rgba(0, 255, 0, 0.15)' }   // เขียว = เข้าเกณฑ์
  const outRangeColor = { stroke: '#ff0000', fill: 'rgba(255, 0, 0, 0.15)' }  // แดง = ไม่เข้าเกณฑ์
  
  props.detections.forEach((detection, index) => {
    const bbox = detection.bbox
    if (!bbox || bbox.length !== 4) {
      console.warn('⚠️ Invalid bbox for detection', index, detection)
      return
    }
    
    const [x, y, w, h] = bbox
    console.log(`📦 Drawing box ${index}: [${x}, ${y}, ${w}, ${h}]`)
    const confidence = detection.confidence || 0
    const label = detection.label || 'Object'
    
    // 🎨 3-tier color system: pass (green), near_pass (yellow), fail (red)
    let color
    const status = detection.status || null
    
    if (status === 'pass') {
      color = { stroke: '#00ff00', fill: 'rgba(0, 255, 0, 0.15)' }  // เขียว - ผ่าน
    } else if (status === 'near_pass') {
      color = { stroke: '#ffff00', fill: 'rgba(255, 255, 0, 0.15)' }  // เหลือง - ใกล้เคียงผ่าน
    } else if (status === 'fail') {
      color = { stroke: '#ff0000', fill: 'rgba(255, 0, 0, 0.15)' }  // แดง - ไม่ผ่าน
    } else if (detection.in_range !== null && detection.in_range !== undefined) {
      // Fallback: Small Object Mode (backward compatibility)
      color = detection.in_range ? inRangeColor : outRangeColor
    } else {
      // No config loaded: gray
      color = { stroke: '#888888', fill: 'rgba(136, 136, 136, 0.10)' }
    }
    
    // Draw bounding box
    ctx.strokeStyle = color.stroke
    ctx.lineWidth = 1.5
    ctx.strokeRect(x, y, w, h)
    
    // Draw semi-transparent fill
    ctx.fillStyle = color.fill
    ctx.fillRect(x, y, w, h)
    
    // ⭐ แสดงขนาด WIDTH x HEIGHT บนกรอบ (เฉพาะ mm เท่านั้น)
    const widthMm = detection.width_mm || 0
    const heightMm = detection.height_mm || 0
    
    if (widthMm > 0 && heightMm > 0) {
      // วาดขนาดที่กลางกรอบ (แสดงเฉพาะ mm) - ตัวอักษรเล็กลงอีก
      const sizeText = `W:${Math.round(widthMm)} H:${Math.round(heightMm)}`
      ctx.font = 'bold 11px Arial'
      ctx.fillStyle = '#ffffff'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      
      // Background สำหรับข้อความ
      const textMetrics = ctx.measureText(sizeText)
      const textWidth = textMetrics.width + 8
      const textHeight = 16
      const textX = x + w / 2
      const textY = y + h / 2
      
      // Background สีดำเข้มกว่า
      ctx.fillStyle = 'rgba(0, 0, 0, 0.85)'
      ctx.fillRect(textX - textWidth/2, textY - textHeight/2, textWidth, textHeight)
      
      // ข้อความสีขาว
      ctx.fillStyle = '#ffffff'
      ctx.fillText(sizeText, textX, textY)
    }
    
    // Draw label background (บนซ้าย) - ตัวอักษรเล็กลงอีก
    const labelText = `#${index + 1} ${label} ${(confidence * 100).toFixed(1)}%`
    ctx.font = 'bold 10px Arial'
    ctx.textAlign = 'left'
    const textMetrics = ctx.measureText(labelText)
    const textWidth = textMetrics.width
    const textHeight = 14
    const padding = 3
    
    // Background for label
    ctx.fillStyle = color.stroke
    ctx.globalAlpha = 0.9
    ctx.fillRect(x, y - textHeight - padding * 2, textWidth + padding * 2, textHeight + padding * 2)
    ctx.globalAlpha = 1.0
    
    // Draw label text
    ctx.fillStyle = '#000000'
    ctx.textBaseline = 'top'
    ctx.fillText(labelText, x + padding, y - textHeight - padding)
    
    // Draw corner markers for better visibility
    const cornerLength = 20
    ctx.strokeStyle = color.stroke
    ctx.lineWidth = 2
    
    // Top-left corner
    ctx.beginPath()
    ctx.moveTo(x, y + cornerLength)
    ctx.lineTo(x, y)
    ctx.lineTo(x + cornerLength, y)
    ctx.stroke()
    
    // Top-right corner
    ctx.beginPath()
    ctx.moveTo(x + w - cornerLength, y)
    ctx.lineTo(x + w, y)
    ctx.lineTo(x + w, y + cornerLength)
    ctx.stroke()
    
    // Bottom-left corner
    ctx.beginPath()
    ctx.moveTo(x, y + h - cornerLength)
    ctx.lineTo(x, y + h)
    ctx.lineTo(x + cornerLength, y + h)
    ctx.stroke()
    
    // Bottom-right corner
    ctx.beginPath()
    ctx.moveTo(x + w - cornerLength, y + h)
    ctx.lineTo(x + w, y + h)
    ctx.lineTo(x + w, y + h - cornerLength)
    ctx.stroke()
  })
}

onMounted(() => {
  // Initialize canvas
  if (canvasRef.value) {
    const canvas = canvasRef.value
    canvas.width = 1920
    canvas.height = 1080

    const ctx = canvas.getContext('2d')
    ctx.fillStyle = '#1e293b'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
  }
  // Real FPS is provided by the parent via the `fps` prop; no fake timer here.
})
</script>

<style scoped>
.camera-view-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.camera-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.depth-card {
  height: 200px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-actions {
  display: flex;
  gap: 8px;
}

.record-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--success-color);
  margin-right: 4px;
  animation: pulse 2s ease-in-out infinite;
}

.camera-viewport {
  flex: 1;
  position: relative;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.camera-canvas {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.camera-canvas.inactive {
  display: none;
}

.camera-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(26, 26, 26, 0.88) 0%, rgba(15, 15, 15, 0.96) 100%);
  backdrop-filter: blur(2px);
  animation: fadeIn 0.5s ease;
}

.camera-placeholder::before {
  content: '';
  position: absolute;
  width: 200px;
  height: 200px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(var(--primary-rgb), 0.1) 0%, transparent 70%);
  animation: pulse 2s ease-in-out infinite;
}

.placeholder-content {
  text-align: center;
  position: relative;
  z-index: 1;
  animation: float 3s ease-in-out infinite;
}

.placeholder-icon {
  font-size: 64px;
  display: block;
  margin-bottom: 16px;
  opacity: 0.5;
}

.placeholder-text {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.placeholder-subtext {
  font-size: 14px;
  color: var(--text-secondary);
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
  box-shadow: var(--glow-primary), inset 0 0 20px rgba(var(--primary-rgb), 0.1);
  animation: fadeIn 0.3s ease-out, boxPulse 2s ease-in-out infinite;
  background: rgba(var(--primary-rgb), 0.05);
}

@keyframes boxPulse {
  0%, 100% {
    box-shadow: var(--glow-primary), inset 0 0 20px rgba(var(--primary-rgb), 0.1);
    border-color: var(--primary-color);
  }
  50% {
    box-shadow: 0 0 30px rgba(var(--primary-rgb), 0.7), inset 0 0 30px rgba(var(--primary-rgb), 0.2);
    border-color: var(--primary-light);
  }
}

.detection-label {
  position: absolute;
  top: -32px;
  left: 0;
  background: var(--primary-color);
  color: white;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.detection-confidence {
  opacity: 0.9;
  margin-left: 4px;
}

.info-overlay {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-item {
  background: rgba(26, 26, 26, 0.9);
  backdrop-filter: blur(8px);
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.info-icon {
  font-size: 14px;
}

.depth-viewport {
  height: 100%;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}

.depth-canvas {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(0.95);
  }
}

/* Responsive Design */
@media (max-width: 1024px) {
  .camera-viewport, .depth-viewport {
    border-radius: 6px;
  }
  
  .info-item {
    padding: 5px 10px;
    font-size: 11px;
  }
}

@media (max-width: 768px) {
  .camera-card {
    min-height: 300px;
  }
  
  .depth-card {
    height: 150px;
  }
  
  .card-title {
    font-size: 16px;
  }
  
  .info-overlay {
    top: 8px;
    right: 8px;
    gap: 6px;
  }
  
  .detection-label {
    font-size: 10px;
    padding: 3px 8px;
    top: -26px;
  }
}

@media (max-width: 480px) {
  .camera-card {
    min-height: 250px;
  }
  
  .depth-card {
    display: none;
  }
  
  .card-title {
    font-size: 14px;
    gap: 6px;
  }
  
  .info-item {
    padding: 4px 8px;
    font-size: 10px;
  }
}

/* Prediction Status Badge */
.prediction-status {
  position: absolute;
  top: 16px;
  right: 16px;
  padding: 8px 16px;
  background: rgba(239, 68, 68, 0.9);
  color: white;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  backdrop-filter: blur(10px);
  z-index: 10;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.prediction-status.active {
  background: rgba(var(--primary-rgb), 0.9);
}

.prediction-status .status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: white;
  animation: pulse-dot 2s infinite;
}

@keyframes pulse-dot {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(1.2);
  }
}
</style>
