<template>
  <div class="measurement-display">
    <!-- 🎯 3-Zone Mode: แสดงการวัด 3 ช่องแยกกัน -->
    <div v-if="threeZoneMode" class="zone-measurements-container">
      <div v-for="zoneId in [1, 2, 3]" :key="zoneId" class="zone-card">
        <div class="zone-header">
          <h3 class="zone-title">ZONE {{ zoneId }}</h3>
          <span v-if="zoneMeasurements[zoneId]" class="badge badge-success">
            Detected
          </span>
          <span v-else class="badge badge-warning">
            Empty
          </span>
        </div>
        
        <div v-if="zoneMeasurements[zoneId]" class="zone-measurements">
          <div class="zone-measurement-row">
            <span class="zone-label">W:</span>
            <span class="zone-value">{{ formatValue(zoneMeasurements[zoneId].width) }}</span>
            <span class="zone-unit">mm</span>
          </div>
          <div class="zone-measurement-row">
            <span class="zone-label">H:</span>
            <span class="zone-value">{{ formatValue(zoneMeasurements[zoneId].height) }}</span>
            <span class="zone-unit">mm</span>
          </div>
        </div>
        
        <div v-else class="zone-empty">
          <p>No object detected</p>
        </div>
      </div>
    </div>

    <!-- Active Setup + Stats Card (โหมดปกติ) -->
    <div v-else class="card measurement-card">
      <!-- 🔧 Active Setup Panel — แสดงการตั้งค่าที่เลือกบนหน้าโปรแกรม -->
      <div class="card-header">
        <h2 class="card-title">
          <IconSvg name="target" :size="20" />
          Contour Detection
        </h2>
        <span v-if="activeSetup.machineId" class="badge badge-success">Active</span>
        <span v-else-if="activeSetup.config" class="badge badge-info">Contour ON</span>
        <span v-else class="badge badge-warning">Waiting</span>
      </div>

      <!-- 🖥️ Web control: pick machine (= target) to start detection + capture to DB -->
      <div class="detect-controls">
        <label class="detect-label">Machine (Target)</label>
        <select
          class="detect-select"
          :value="selectedMachineId"
          @change="$emit('select-machine', $event.target.value)"
        >
          <option value="">— ไม่เลือก / หยุดตรวจจับ —</option>
          <option v-for="m in machines" :key="m.id" :value="m.id">
            {{ m.name }}<template v-if="m.config"> ({{ m.config.target_area_min }}–{{ m.config.target_area_max }} mm²)</template>
          </option>
        </select>
        <button
          class="btn btn-primary capture-btn"
          :disabled="!isMeasuring"
          @click="$emit('capture')"
          title="ถ่ายภาพพร้อมกรอบ ROI แล้วบันทึกลงฐานข้อมูล"
        >
          <IconSvg name="capture" :size="18" />
          ถ่าย + บันทึก DB
        </button>
      </div>

      <div class="setup-info-grid">
        <div class="setup-info-row">
          <span class="setup-info-label">เครื่องจักร</span>
          <span class="setup-info-value">{{ activeSetup.machineName || '—' }}</span>
        </div>
        <div class="setup-info-row">
          <span class="setup-info-label">Configuration</span>
          <span class="setup-info-value">{{ activeSetup.config?.name || '—' }}</span>
        </div>
        <div v-if="activeSetup.config" class="setup-info-row">
          <span class="setup-info-label">Target Area</span>
          <span class="setup-info-value setup-info-highlight">
            {{ activeSetup.config.target_area_min }} – {{ activeSetup.config.target_area_max }} mm²
          </span>
        </div>
        <div v-if="activeSetup.config" class="setup-info-row">
          <span class="setup-info-label">Tolerance</span>
          <span class="setup-info-value">±{{ activeSetup.config.tolerance }} mm²</span>
        </div>
        <div class="setup-info-row">
          <span class="setup-info-label">LOT</span>
          <span class="setup-info-value">{{ activeSetup.lotName || '—' }}</span>
        </div>
      </div>

      <!-- 📊 3-Tier Detection Stats -->
      <div v-if="detectionStats.total > 0" class="stats-tier-wrapper">
        <div class="stats-tier-grid">
          <div class="stat-tier-card total-tier">
            <div class="stat-tier-number">{{ detectionStats.total }}</div>
            <div class="stat-tier-label">Total</div>
          </div>
          <div class="stat-tier-card pass-tier">
            <div class="stat-tier-number">{{ detectionStats.pass }}</div>
            <div class="stat-tier-label">✓ Pass</div>
          </div>
          <div class="stat-tier-card near-tier">
            <div class="stat-tier-number">{{ detectionStats.nearPass }}</div>
            <div class="stat-tier-label">▲ Near</div>
          </div>
          <div class="stat-tier-card fail-tier">
            <div class="stat-tier-number">{{ detectionStats.fail }}</div>
            <div class="stat-tier-label">✗ Fail</div>
          </div>
        </div>
      </div>
      <div v-else class="setup-waiting">
        <p>{{ activeSetup.machineId ? '⏳ รอวัตถุ...' : activeSetup.config ? '⏳ รอเริ่มการวัด (กด Start บนหน้าโปรแกรม)...' : '⏳ รอเลือก Configuration บนหน้าโปรแกรม...' }}</p>
      </div>
    </div> <!-- ✅ Close measurement-card -->

    <!-- Camera Vision Preview Cards -->
    <div class="preview-cards">
      <!-- Contour Detection Visualization -->
      <div v-if="contourMask" class="card preview-card">
        <div class="card-header">
          <h2 class="card-title">
            <IconSvg name="target" :size="18" />
            Contour Detection
          </h2>
        </div>
        <div class="preview-container">
          <img v-if="contourMask" :src="'data:image/jpeg;base64,' + contourMask.image" alt="Contour Mask" class="preview-image" />
          <div class="preview-label">Background Subtraction</div>
        </div>
        <div class="depth-info">
          <small>🔴 Hot = Objects | 🔵 Cold = Background</small>
        </div>
      </div>
    </div>

    <!-- System Log Card -->
    <div class="card stats-card log-card">
      <div class="card-header">
        <h2 class="card-title">
          <IconSvg name="activity" :size="20" />
          System Log
        </h2>
        <button class="clear-log-btn" @click="clearLogs" title="Clear Logs">
          <IconSvg name="rotate-ccw" :size="16" />
        </button>
      </div>

      <div class="log-container">
        <div v-if="systemLogs.length === 0" class="log-empty">
          <IconSvg name="info" :size="32" style="opacity: 0.3; margin-bottom: 8px;" />
          <p>No logs yet</p>
        </div>
        <div v-else class="log-list">
          <div 
            v-for="(log, index) in systemLogs" 
            :key="index" 
            class="log-entry"
            :class="`log-${log.type}`"
          >
            <div class="log-time">{{ log.time }}</div>
            <div class="log-icon">
              <IconSvg v-if="log.type === 'success'" name="check" :size="16" />
              <IconSvg v-else-if="log.type === 'error'" name="alert" :size="16" />
              <IconSvg v-else-if="log.type === 'warning'" name="alert-triangle" :size="16" />
              <IconSvg v-else name="info" :size="16" />
            </div>
            <div class="log-message">{{ log.message }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Export Button -->
    <button class="btn btn-primary export-btn" @click="exportData">
      <IconSvg name="download" :size="18" />
      Export Data
    </button>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import IconSvg from './IconSvg.vue'

const props = defineProps({
  measurements: {
    type: Object,
    default: () => ({
      width: 0,
      height: 0,
      depth: 0,
      volume: 0,
      hasObject: false
    })
  },
  zoneMeasurements: {
    type: Object,
    default: () => ({ 1: null, 2: null, 3: null })
  },
  threeZoneMode: {
    type: Boolean,
    default: false
  },
  contrastFrame: {
    type: String,
    default: null
  },
  depthFrame: {
    type: String,
    default: null
  },
  contourMask: {
    type: Object,
    default: null
  },
  depthColorScheme: {
    type: String,
    default: 'gray'
  },
  unit: {
    type: String,
    default: 'mm'
  },
  detectionStats: {
    type: Object,
    default: () => ({
      total: 0,
      inRange: 0,
      outRange: 0,
      pass: 0,
      nearPass: 0,
      fail: 0,
      smallest: 0,
      largest: 0
    })
  },
  activeSetup: {
    type: Object,
    default: () => ({
      machineId: null,
      machineName: '',
      lotId: null,
      lotName: '',
      config: null
    })
  },
  machines: {
    type: Array,
    default: () => []
  },
  selectedMachineId: {
    type: [String, Number],
    default: ''
  },
  isMeasuring: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['select-machine', 'capture'])

const statistics = ref({
  totalMeasurements: 0,
  avgWidth: 0,
  avgHeight: 0,
  avgDepth: 0
})

const volumeUnit = computed(() => {
  switch (props.unit) {
    case 'mm': return 'mm³'
    case 'cm': return 'cm³'
    case 'm': return 'm³'
    case 'in': return 'in³'
    default: return 'mm³'
  }
})

const formatValue = (value) => {
  if (!value || value === 0) return '0.0'
  return value.toFixed(1)
}

const formatVolume = (value) => {
  if (!value || value === 0) return '0.0'
  if (value > 1000000) {
    return (value / 1000000).toFixed(2)
  }
  return value.toFixed(1)
}

// Calculate scaled dimensions for 3D box
const get3DBoxDimensions = () => {
  // If no object detected or measurements are all zero, use placeholder values
  if (!props.measurements.hasObject || 
      (props.measurements.width <= 0 && props.measurements.height <= 0 && props.measurements.depth <= 0)) {
    return {
      w: 80,
      h: 80,
      d: 80
    }
  }
  
  const width = Math.max(props.measurements.width, 1)
  const height = Math.max(props.measurements.height, 1)
  const depth = Math.max(props.measurements.depth, 1)
  
  const maxDim = Math.max(width, height, depth)
  const scale = maxDim > 0 ? 180 / maxDim : 1
  
  return {
    w: Math.max(30, width * scale),
    h: Math.max(30, height * scale),
    d: Math.max(30, depth * scale)
  }
}

// Container style with perspective
const get3DContainerStyle = () => {
  return {
    transformStyle: 'preserve-3d',
    perspective: '1000px',
    perspectiveOrigin: 'center center',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    width: '100%',
    height: '250px',
    position: 'relative'
  }
}

// Main box wrapper style
const get3DBoxStyle = () => {
  const dims = get3DBoxDimensions()
  return {
    position: 'relative',
    width: `${dims.w}px`,
    height: `${dims.h}px`,
    transformStyle: 'preserve-3d',
    transform: 'rotateX(-20deg) rotateY(30deg)',
    transition: 'all 0.3s ease-in-out'
  }
}

// Front face style
const getBoxFrontStyle = () => {
  const dims = get3DBoxDimensions()
  return {
    position: 'absolute',
    left: 0,
    top: 0,
    width: `${dims.w}px`,
    height: `${dims.h}px`,
    margin: 0,
    background: 'rgba(var(--primary-rgb), 0.7)',
    border: '2px solid rgba(var(--primary-rgb), 1)',
    transformOrigin: 'left top',
    transform: `translateZ(${dims.d}px)`,
    backfaceVisibility: 'hidden',
    transition: 'all 0.3s ease-in-out'
  }
}

// Back face style
const getBoxBackStyle = () => {
  const dims = get3DBoxDimensions()
  return {
    position: 'absolute',
    left: 0,
    top: 0,
    width: `${dims.w}px`,
    height: `${dims.h}px`,
    margin: 0,
    background: 'rgba(var(--primary-rgb), 0.3)',
    border: '2px solid rgba(var(--primary-rgb), 0.6)',
    transformOrigin: 'left top',
    transform: `translateZ(${-dims.d}px) rotateY(180deg)`,
    backfaceVisibility: 'hidden',
    transition: 'all 0.3s ease-in-out'
  }
}

// Right face style
const getBoxRightStyle = () => {
  const dims = get3DBoxDimensions()
  return {
    position: 'absolute',
    left: 0,
    top: 0,
    width: `${dims.d}px`,
    height: `${dims.h}px`,
    margin: 0,
    background: 'rgba(34, 197, 94, 0.7)',
    border: '2px solid rgba(34, 197, 94, 1)',
    transformOrigin: 'left top',
    transform: `translateX(${dims.w}px) rotateY(90deg)`,
    backfaceVisibility: 'hidden',
    transition: 'all 0.3s ease-in-out'
  }
}

// Left face style
const getBoxLeftStyle = () => {
  const dims = get3DBoxDimensions()
  return {
    position: 'absolute',
    left: 0,
    top: 0,
    width: `${dims.d}px`,
    height: `${dims.h}px`,
    margin: 0,
    background: 'rgba(34, 197, 94, 0.3)',
    border: '2px solid rgba(34, 197, 94, 0.6)',
    transformOrigin: 'left top',
    transform: `rotateY(-90deg)`,
    backfaceVisibility: 'hidden',
    transition: 'all 0.3s ease-in-out'
  }
}

// Top face style
const getBoxTopStyle = () => {
  const dims = get3DBoxDimensions()
  return {
    position: 'absolute',
    left: 0,
    top: 0,
    width: `${dims.w}px`,
    height: `${dims.d}px`,
    margin: 0,
    background: 'rgba(var(--accent-rgb), 0.7)',
    border: '2px solid rgba(var(--accent-rgb), 1)',
    transformOrigin: 'left top',
    transform: `rotateX(-90deg) translateY(${-dims.d}px)`,
    backfaceVisibility: 'visible',
    transition: 'all 0.3s ease-in-out'
  }
}

// Bottom face style
const getBoxBottomStyle = () => {
  const dims = get3DBoxDimensions()
  return {
    position: 'absolute',
    left: 0,
    top: 0,
    width: `${dims.w}px`,
    height: `${dims.d}px`,
    margin: 0,
    background: 'rgba(var(--accent-rgb), 0.3)',
    border: '2px solid rgba(var(--accent-rgb), 0.6)',
    transformOrigin: 'left top',
    transform: `translateY(${dims.h}px) rotateX(90deg)`,
    backfaceVisibility: 'hidden',
    transition: 'all 0.3s ease-in-out'
  }
}

// System Logs
const systemLogs = ref([])
const maxLogs = 100

const addLog = (message, type = 'info') => {
  const log = {
    time: new Date().toLocaleTimeString('th-TH'),
    message,
    type // 'success', 'error', 'warning', 'info'
  }
  systemLogs.value.unshift(log)
  if (systemLogs.value.length > maxLogs) {
    systemLogs.value.pop()
  }
}

const clearLogs = () => {
  systemLogs.value = []
}

// Watch for detection changes to log
import { watch } from 'vue'

watch(() => props.detectionStats.total, (newVal, oldVal) => {
  if (newVal > 0 && newVal !== oldVal) {
    const inRange = props.detectionStats.inRange
    const outRange = props.detectionStats.outRange
    addLog(`Detected ${newVal} objects: ${inRange} in range, ${outRange} out of range`, 'success')
  }
})

watch(() => props.measurements.hasObject, (hasObject) => {
  if (hasObject) {
    const w = props.measurements.width.toFixed(1)
    const h = props.measurements.height.toFixed(1)
    addLog(`Object detected: ${w}×${h} mm`, 'info')
  }
})

const exportData = () => {
  const data = {
    timestamp: new Date().toISOString(),
    measurements: props.measurements,
    statistics: statistics.value,
    logs: systemLogs.value,
    unit: props.unit
  }
  
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `measurements_${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
  addLog('Data exported successfully', 'success')
}

// Expose addLog to parent
defineExpose({ addLog })

</script>

<style scoped>
.measurement-display {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
  overflow-y: auto;
}

/* 🎯 3-Zone Measurements Layout */
.zone-measurements-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 8px;
}

.zone-card {
  background: var(--bg-card);
  border-radius: 12px;
  padding: 16px;
  border: 3px solid #ff0000;
  box-shadow: 0 4px 12px rgba(255, 0, 0, 0.2);
}

.zone-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.zone-title {
  font-size: 18px;
  font-weight: bold;
  color: #ff0000;
  margin: 0;
}

.zone-measurements {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: rgba(0, 0, 0, 0.3);
  padding: 12px;
  border-radius: 8px;
}

.zone-measurement-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
}

.zone-label {
  font-weight: bold;
  color: #888;
  min-width: 30px;
}

.zone-value {
  font-size: 20px;
  font-weight: bold;
  color: var(--text-primary);
}

.zone-unit {
  font-size: 14px;
  color: #888;
}

.zone-empty {
  text-align: center;
  padding: 20px;
  color: #888;
  font-style: italic;
}

.card {
  background: var(--bg-card);
  border-radius: 12px;
  padding: 20px;
  box-shadow: var(--shadow);
  border: 1px solid var(--border-color);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 8px;
}

.card-title {
  font-size: 18px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-primary);
  font-family: var(--font-display);
  letter-spacing: -0.3px;
}

.header-badges {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.badge-ai {
  background: linear-gradient(135deg, var(--primary-color), var(--primary-color));
  color: white;
  font-weight: 600;
  font-size: 13px;
}

.measurement-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.measurement-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: var(--bg-dark);
  border-radius: 8px;
  border: 1px solid var(--border-color);
  transition: all 0.2s;
}

.measurement-item:hover {
  border-color: var(--primary-color);
  transform: translateX(4px);
}

.volume-item {
  grid-column: 1;
  background: linear-gradient(135deg, rgba(var(--primary-rgb), 0.1), rgba(var(--primary-rgb), 0.1));
}

.measurement-icon {
  font-size: 32px;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-card);
  border-radius: 8px;
}

.measurement-info {
  flex: 1;
}

.measurement-label {
  font-size: 12px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}

.measurement-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  font-family: var(--font-mono);
}

.measurement-unit {
  font-size: 14px;
  color: var(--text-secondary);
  font-weight: 500;
  margin-left: 4px;
}

.visualization-container {
  position: relative !important;
  height: 250px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  perspective: 1500px !important;
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
  border-radius: 8px !important;
  overflow: visible !important;
}

.box-3d {
  position: relative !important;
  width: var(--box-width, 120px) !important;
  height: var(--box-height, 120px) !important;
  transform-style: preserve-3d !important;
  transform: rotateX(-20deg) rotateY(30deg) !important;
  animation: rotate3d 8s infinite ease-in-out !important;
}

@keyframes rotate3d {
  0%, 100% {
    transform: rotateX(-20deg) rotateY(30deg);
  }
  50% {
    transform: rotateX(-30deg) rotateY(60deg);
  }
}

.box-face {
  position: absolute !important;
  left: 0 !important;
  top: 0 !important;
  background: rgba(var(--primary-rgb), 0.3) !important;
  border: 2px solid var(--primary-color) !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  font-size: 12px !important;
  font-weight: 600 !important;
  color: white !important;
  backdrop-filter: blur(4px) !important;
  backface-visibility: visible !important;
  box-sizing: border-box !important;
}

.box-front {
  width: var(--box-width, 120px) !important;
  height: var(--box-height, 120px) !important;
  transform: rotateY(0deg) translateZ(calc(var(--box-depth, 120px) / 2)) !important;
}

.box-back {
  width: var(--box-width, 120px) !important;
  height: var(--box-height, 120px) !important;
  transform: rotateY(180deg) translateZ(calc(var(--box-depth, 120px) / 2)) !important;
}

.box-right {
  width: var(--box-depth, 120px) !important;
  height: var(--box-height, 120px) !important;
  transform: rotateY(90deg) translateZ(calc(var(--box-width, 120px) / 2)) !important;
}

.box-left {
  width: var(--box-depth, 120px) !important;
  height: var(--box-height, 120px) !important;
  transform: rotateY(-90deg) translateZ(calc(var(--box-width, 120px) / 2)) !important;
}

.box-top {
  width: var(--box-width, 120px) !important;
  height: var(--box-depth, 120px) !important;
  transform: rotateX(90deg) translateZ(calc(var(--box-height, 120px) / 2)) !important;
  background: rgba(var(--primary-rgb), 0.5) !important;
}

/* SVG axis overlay */
.axis-overlay {
  z-index: 10;
}

.axis-overlay text {
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.8);
}

.box-bottom {
  width: var(--box-width, 120px) !important;
  height: var(--box-depth, 120px) !important;
  transform: rotateX(-90deg) translateZ(calc(var(--box-height, 120px) / 2)) !important;
}

.dimension-label {
  font-size: 11px;
  padding: 4px 8px;
  background: rgba(0, 0, 0, 0.7);
  border-radius: 4px;
}

.stats-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: var(--bg-dark);
  border-radius: 6px;
  font-size: 13px;
}

.stat-label {
  color: var(--text-secondary);
}

.stat-value {
  font-weight: 600;
  color: var(--text-primary);
  font-family: var(--font-mono);
}

.export-btn {
  width: 100%;
  justify-content: center;
}

/* Preview Cards */
.preview-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.preview-card .card-header {
  padding: 12px 16px;
}

.preview-card .card-title {
  font-size: 14px;
  gap: 8px;
}

.preview-container {
  position: relative;
  width: 100%;
  height: 200px;
  background: #0f172a;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.preview-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: rgba(255, 255, 255, 0.5);
  text-align: center;
}

.preview-placeholder p {
  margin: 0;
  font-size: 13px;
  font-weight: 500;
}

.preview-label {
  position: absolute;
  bottom: 8px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  backdrop-filter: blur(4px);
}

.depth-info {
  padding: 8px 12px;
  background: rgba(15, 23, 42, 0.5);
  border-radius: 0 0 8px 8px;
  margin-top: -8px;
}

.depth-info small {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.7);
  line-height: 1.4;
}

/* Dimension Labels - ข้างขวาโมเดล 3D */
.dimension-labels {
  position: absolute;
  right: -150px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  flex-direction: column;
  gap: 16px;
  pointer-events: none;
}

.dimension-label {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.8);
  border-radius: 6px;
  border-left: 3px solid;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(4px);
}

.width-label {
  border-color: var(--primary-color);
}

.height-label {
  border-color: var(--primary-light);
}

.depth-label {
  border-color: #22c55e;
}

.label-key {
  font-size: 13px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.7);
  min-width: 20px;
}

.label-value {
  font-size: 15px;
  font-weight: 700;
  color: white;
  font-family: var(--font-mono);
  white-space: nowrap;
}

/* 🖥️ Web detection controls */
.detect-controls {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.detect-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-secondary);
}

.detect-select {
  width: 100%;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--border-color);
  background: var(--bg-dark-secondary);
  color: var(--text-primary);
  font-size: 14px;
  font-family: var(--font-body);
  cursor: pointer;
  transition: border-color 0.2s ease;
}

.detect-select:hover,
.detect-select:focus {
  border-color: var(--primary-color);
  outline: none;
}

.detect-select option {
  background: var(--bg-card);
  color: var(--text-primary);
}

.capture-btn {
  width: 100%;
  justify-content: center;
}

/* 🔧 Active Setup Info Panel */
.setup-info-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  background: var(--bg-dark-secondary);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  margin-bottom: 4px;
}

.setup-info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px 2px;
  border-bottom: 1px solid var(--border-color);
}

.setup-info-row:last-child {
  border-bottom: none;
}

.setup-info-label {
  font-size: 11px;
  color: var(--text-secondary, #94a3b8);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: flex;
  align-items: center;
}

.setup-info-value {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary, #e2e8f0);
  text-align: right;
  max-width: 60%;
  word-break: break-word;
}

.setup-info-highlight {
  color: var(--primary-light);
}

.setup-waiting {
  text-align: center;
  padding: 16px;
  color: var(--text-secondary, #94a3b8);
  font-size: 12px;
}

/* 📊 3-Tier Stats Grid */
.stats-tier-wrapper {
  margin-top: 10px;
}

.stats-tier-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.stat-tier-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 10px 6px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.stat-tier-card.total-tier  { background: rgba(100, 116, 139, 0.2); border-color: #64748b; }
.stat-tier-card.pass-tier   { background: rgba(22, 163, 74, 0.2);  border-color: #16a34a; }
.stat-tier-card.near-tier   { background: rgba(202, 138, 4, 0.2);  border-color: #ca8a04; }
.stat-tier-card.fail-tier   { background: rgba(220, 38, 38, 0.2);  border-color: #dc2626; }

.stat-tier-number {
  font-size: 22px;
  font-weight: 700;
  line-height: 1;
}

.total-tier .stat-tier-number { color: #94a3b8; }
.pass-tier  .stat-tier-number { color: #4ade80; }
.near-tier  .stat-tier-number { color: #facc15; }
.fail-tier  .stat-tier-number { color: #f87171; }

.stat-tier-label {
  font-size: 10px;
  margin-top: 4px;
  color: var(--text-secondary, #94a3b8);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* 🎯 Statistics Summary Styles */
.stats-summary {
  width: 100%;
  margin-bottom: 20px;
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  padding: 16px;
  background: linear-gradient(135deg, rgba(var(--primary-rgb), 0.05) 0%, rgba(5, 150, 105, 0.05) 100%);
  border-radius: 12px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: white;
  border-radius: 12px;
  border: 2px solid #d9ede4;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  min-width: 0;
  overflow: visible;
  box-shadow: 0 2px 8px rgba(var(--primary-rgb), 0.08);
}

.stat-card:hover {
  background: #f0f9f4;
  border-color: var(--primary-color);
  transform: translateY(-3px);
  box-shadow: 0 8px 16px rgba(var(--primary-rgb), 0.15);
}

.stat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 12px;
  flex-shrink: 0;
}

.stat-icon svg {
  width: 28px;
  height: 28px;
}

.stat-card.in-range .stat-icon {
  background: linear-gradient(135deg, rgba(var(--primary-rgb), 0.15), rgba(var(--primary-rgb), 0.25));
  color: var(--primary-color);
}

.stat-card.out-range .stat-icon {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(239, 68, 68, 0.25));
  color: #ef4444;
}

.stat-card.smallest .stat-icon {
  background: linear-gradient(135deg, rgba(var(--primary-rgb), 0.15), rgba(var(--primary-rgb), 0.25));
  color: var(--primary-color);
}

.stat-card.largest .stat-icon {
  background: linear-gradient(135deg, rgba(var(--primary-rgb), 0.15), rgba(var(--primary-rgb), 0.25));
  color: var(--primary-color);
}

.stat-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  flex: 1;
  overflow: visible;
}

.stat-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-secondary);
  white-space: nowrap;
  line-height: 1.2;
  font-family: var(--font-display);
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  font-family: var(--font-display);
  white-space: nowrap;
  line-height: 1.1;
  letter-spacing: -0.5px;
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.stat-unit {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
}

/* System Log Styles */
.log-card {
  min-height: 400px;
  max-height: 600px;
  display: flex;
  flex-direction: column;
}

.log-card .card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.clear-log-btn {
  padding: 6px 12px;
  background: var(--bg-card-hover);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.3s;
  font-size: 12px;
  color: var(--text-secondary);
}

.clear-log-btn:hover {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}

.log-container {
  flex: 1;
  overflow-y: auto;
  background: var(--bg-dark-secondary);
  border-radius: 8px;
  padding: 12px;
}

.log-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-secondary);
  opacity: 0.6;
}

.log-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.log-entry {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  background: var(--bg-card);
  border-left: 3px solid var(--border-color);
  border-radius: 6px;
  font-size: 13px;
  transition: all 0.2s;
}

.log-entry:hover {
  background: var(--bg-card-hover);
  transform: translateX(2px);
}

.log-entry.log-success {
  border-left-color: var(--success-color);
}

.log-entry.log-error {
  border-left-color: var(--danger-color);
  background: rgba(239, 68, 68, 0.05);
}

.log-entry.log-warning {
  border-left-color: var(--warning-color);
  background: rgba(245, 158, 11, 0.05);
}

.log-entry.log-info {
  border-left-color: var(--primary-color);
}

.log-time {
  font-size: 11px;
  color: var(--text-secondary);
  font-family: var(--font-mono);
  white-space: nowrap;
  min-width: 70px;
}

.log-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  margin-top: 2px;
}

.log-success .log-icon {
  color: var(--success-color);
}

.log-error .log-icon {
  color: var(--danger-color);
}

.log-warning .log-icon {
  color: var(--warning-color);
}

.log-info .log-icon {
  color: var(--primary-color);
}

.log-message {
  flex: 1;
  color: var(--text-primary);
  line-height: 1.5;
  word-break: break-word;
}

</style>
