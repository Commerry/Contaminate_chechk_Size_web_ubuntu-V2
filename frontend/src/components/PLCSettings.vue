<template>
  <div class="plc-settings">
    <div class="section-header">
      <h2 class="section-title">
        <IconSvg name="cpu" :size="24" />
        PLC Settings
        <span class="subtitle">การตั้งค่า PLC</span>
      </h2>
    </div>

    <div class="section-content">
      <!-- PLC Status Card -->
      <div class="status-card" :class="{ 'connected': plcStatus.connected }">
        <div class="status-header">
          <div class="status-icon" :class="plcStatus.connected ? 'connected' : 'disconnected'">
            <IconSvg name="cpu" :size="32" />
          </div>
          <div class="status-info">
            <h3>{{ plcStatus.connected ? 'Connected' : 'Disconnected' }}</h3>
            <p>{{ plcStatus.connected ? `Mode: ${plcStatus.mode}` : 'PLC is not connected' }}</p>
          </div>
        </div>
        <div class="status-details" v-if="plcStatus.enabled">
          <div class="detail-row">
            <span class="label">IP Address:</span>
            <span class="value">{{ plcStatus.address || 'N/A' }}</span>
          </div>
          <div class="detail-row">
            <span class="label">DB Number:</span>
            <span class="value">{{ plcStatus.db_num || 'N/A' }}</span>
          </div>
          <div class="detail-row">
            <span class="label">Mode:</span>
            <span class="value mode" :class="plcStatus.mode">
              {{ plcStatus.mode === 'debug' ? 'Debug (Simulated)' : 'Production (Real PLC)' }}
            </span>
          </div>
        </div>
      </div>

      <!-- PLC Controls -->
      <div class="control-section">
        <h3 class="control-title">Control Panel</h3>
        
        <div class="button-group">
          <button 
            class="control-btn connect" 
            @click="connectPLC"
            :disabled="plcStatus.connected || loading"
          >
            <IconSvg name="wifi" :size="20" />
            Connect PLC
          </button>
          
          <button 
            class="control-btn disconnect" 
            @click="disconnectPLC"
            :disabled="!plcStatus.connected || loading"
          >
            <IconSvg name="wifi-off" :size="20" />
            Disconnect PLC
          </button>
        </div>

        <div class="button-group" v-if="plcStatus.mode === 'debug'">
          <button 
            class="control-btn debug" 
            @click="triggerDebug"
            :disabled="!plcStatus.connected || loading"
          >
            <IconSvg name="zap" :size="20" />
            Debug Trigger (Manual)
          </button>
        </div>
      </div>

      <!-- PLC Configuration Form -->
      <div class="config-section">
        <h3 class="config-title">Configuration</h3>
        
        <div class="form-grid">
          <div class="form-group">
            <label>Mode</label>
            <select v-model="config.plc_mode" :disabled="plcStatus.connected">
              <option value="debug">Debug (Simulated)</option>
              <option value="production">Production (Real PLC)</option>
            </select>
            <small>Debug mode สำหรับทดสอบโดยไม่ต้องมี PLC จริง</small>
          </div>

          <div class="form-group" v-if="config.plc_mode === 'production'">
            <label>PLC IP Address</label>
            <input 
              type="text" 
              v-model="config.plc_address"
              :disabled="plcStatus.connected"
              placeholder="192.168.1.100"
            />
          </div>

          <div class="form-group" v-if="config.plc_mode === 'production'">
            <label>DB Number</label>
            <input 
              type="number" 
              v-model.number="config.plc_db_num"
              :disabled="plcStatus.connected"
              placeholder="100"
            />
          </div>

          <div class="form-group">
            <label class="checkbox-label">
              <input 
                type="checkbox" 
                v-model="config.plc_enabled"
                :disabled="plcStatus.connected"
              />
              <span>Enable PLC Integration</span>
            </label>
            <small>เปิดใช้งานระบบ PLC สำหรับ trigger กล้องอัตโนมัติ</small>
          </div>
        </div>

        <div class="form-actions">
          <button 
            class="save-btn" 
            @click="saveConfig"
            :disabled="plcStatus.connected || loading"
          >
            <IconSvg name="save" :size="18" />
            Save Configuration
          </button>
        </div>
      </div>

      <!-- Debug Info -->
      <div class="debug-info" v-if="plcStatus.mode === 'debug'">
        <h4>ℹ️ Debug Mode Information</h4>
        <ul>
          <li>Debug mode ใช้ PLC จำลองสำหรับการทดสอบ</li>
          <li>ไม่ต้องมี Siemens PLC จริง หรือ python-snap7 library</li>
          <li>PLC จำลองจะส่ง trigger อัตโนมัติทุก 10 วินาที</li>
          <li>สามารถกด "Debug Trigger" เพื่อ trigger ด้วยตนเองได้</li>
          <li>เหมาะสำหรับการทดสอบระบบ และ development</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import IconSvg from './IconSvg.vue'

const emit = defineEmits(['updated'])

const loading = ref(false)
const plcStatus = ref({
  enabled: false,
  connected: false,
  mode: 'debug',
  address: '',
  db_num: 100
})

const config = ref({
  plc_enabled: false,
  plc_mode: 'debug',
  plc_address: '192.168.1.100',
  plc_db_num: 100
})

// Fetch PLC status
const fetchStatus = async () => {
  try {
    const response = await fetch('/api/plc/status')
    const data = await response.json()
    if (data.success) {
      plcStatus.value = {
        enabled: data.enabled,
        connected: data.connected,
        mode: data.mode || 'debug',
        address: data.address || '',
        db_num: data.db_num || 100
      }
      
      // Update config form
      config.value = {
        plc_enabled: data.enabled,
        plc_mode: data.mode || 'debug',
        plc_address: data.address || '192.168.1.100',
        plc_db_num: data.db_num || 100
      }
    }
  } catch (error) {
    console.error('Failed to fetch PLC status:', error)
  }
}

// Connect PLC
const connectPLC = async () => {
  loading.value = true
  try {
    const response = await fetch('/api/plc/connect', { method: 'POST' })
    const data = await response.json()
    
    if (data.success) {
      await fetchStatus()
      emit('updated')
    } else {
      alert('Failed to connect PLC: ' + (data.error || 'Unknown error'))
    }
  } catch (error) {
    console.error('Failed to connect PLC:', error)
    alert('Failed to connect PLC: ' + error.message)
  } finally {
    loading.value = false
  }
}

// Disconnect PLC
const disconnectPLC = async () => {
  loading.value = true
  try {
    const response = await fetch('/api/plc/disconnect', { method: 'POST' })
    const data = await response.json()
    
    if (data.success) {
      await fetchStatus()
      emit('updated')
    } else {
      alert('Failed to disconnect PLC: ' + (data.error || 'Unknown error'))
    }
  } catch (error) {
    console.error('Failed to disconnect PLC:', error)
    alert('Failed to disconnect PLC: ' + error.message)
  } finally {
    loading.value = false
  }
}

// Debug trigger
const triggerDebug = async () => {
  loading.value = true
  try {
    const response = await fetch('/api/plc/trigger-debug', { method: 'POST' })
    const data = await response.json()
    
    if (data.success) {
      alert('Debug trigger sent! Camera will capture measurement.')
    } else {
      alert('Failed to trigger: ' + (data.message || data.error || 'Unknown error'))
    }
  } catch (error) {
    console.error('Failed to trigger debug:', error)
    alert('Failed to trigger: ' + error.message)
  } finally {
    loading.value = false
  }
}

// Save configuration
const saveConfig = async () => {
  loading.value = true
  try {
    const response = await fetch('/api/plc/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config.value)
    })
    const data = await response.json()
    
    if (data.success) {
      await fetchStatus()
      emit('updated')
      alert('Configuration saved successfully!')
    } else {
      alert('Failed to save configuration: ' + (data.error || 'Unknown error'))
    }
  } catch (error) {
    console.error('Failed to save configuration:', error)
    alert('Failed to save configuration: ' + error.message)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchStatus()
  // Poll status every 5 seconds
  setInterval(fetchStatus, 5000)
})
</script>

<style scoped>
.plc-settings {
  width: 100%;
  height: 100%;
  overflow-y: auto;
}

.section-header {
  margin-bottom: 24px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.subtitle {
  font-size: 14px;
  font-weight: 400;
  color: var(--text-secondary);
  margin-left: auto;
}

.section-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* Status Card */
.status-card {
  background: linear-gradient(135deg, var(--bg-card) 0%, var(--bg-card-hover) 100%);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 24px;
  transition: all 0.3s ease;
}

.status-card.connected {
  border-color: var(--primary-color);
  box-shadow: 0 0 20px rgba(var(--primary-rgb), 0.2);
}

.status-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.status-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-dark-secondary);
  color: var(--text-secondary);
  transition: all 0.3s ease;
}

.status-icon.connected {
  background: rgba(var(--primary-rgb), 0.2);
  color: var(--primary-color);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(var(--primary-rgb), 0.7); }
  50% { box-shadow: 0 0 0 10px rgba(var(--primary-rgb), 0); }
}

.status-info h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
}

.status-info p {
  margin: 4px 0 0 0;
  font-size: 14px;
  color: var(--text-secondary);
}

.status-details {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-row .label {
  font-size: 14px;
  color: var(--text-secondary);
}

.detail-row .value {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.detail-row .value.mode {
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 13px;
}

.detail-row .value.mode.debug {
  background: rgba(251, 191, 36, 0.2);
  color: #fbbf24;
}

.detail-row .value.mode.production {
  background: rgba(var(--primary-rgb), 0.2);
  color: var(--primary-color);
}

/* Control Section */
.control-section {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
}

.control-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 16px 0;
}

.button-group {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}

.button-group:last-child {
  margin-bottom: 0;
}

.control-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.control-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.control-btn.connect {
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  color: white;
}

.control-btn.connect:not(:disabled):hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(var(--primary-rgb), 0.3);
}

.control-btn.disconnect {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: white;
}

.control-btn.disconnect:not(:disabled):hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(239, 68, 68, 0.3);
}

.control-btn.debug {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: white;
}

.control-btn.debug:not(:disabled):hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(245, 158, 11, 0.3);
}

/* Config Section */
.config-section {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
}

.config-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 16px 0;
}

.form-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.form-group input,
.form-group select {
  padding: 10px 14px;
  background: var(--bg-dark-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 14px;
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: var(--primary-color);
}

.form-group small {
  font-size: 12px;
  color: var(--text-secondary);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  width: auto;
}

.form-actions {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.save-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-color) 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.save-btn:not(:disabled):hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(var(--primary-rgb), 0.3);
}

.save-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Debug Info */
.debug-info {
  background: rgba(251, 191, 36, 0.1);
  border: 1px solid rgba(251, 191, 36, 0.3);
  border-radius: 12px;
  padding: 16px;
}

.debug-info h4 {
  margin: 0 0 12px 0;
  color: #fbbf24;
  font-size: 16px;
}

.debug-info ul {
  margin: 0;
  padding-left: 20px;
  color: var(--text-primary);
}

.debug-info li {
  margin-bottom: 8px;
  font-size: 14px;
  line-height: 1.6;
}

.debug-info li:last-child {
  margin-bottom: 0;
}
</style>
