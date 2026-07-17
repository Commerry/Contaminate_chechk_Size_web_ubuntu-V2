<template>
  <div class="database-control" v-if="databaseEnabled">
    <!-- Session Active -->
    <div v-if="sessionActive" class="session-active">
      <div class="session-header">
        <div class="session-icon pulsing">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <circle cx="12" cy="12" r="10"/>
          </svg>
        </div>
        <div class="session-info">
          <div class="session-title">Recording Session</div>
          <div class="session-subtitle">{{ sessionData.object_name || 'Waiting for detection...' }}</div>
        </div>
      </div>

      <div class="session-progress">
        <div class="progress-info">
          <span>{{ sessionData.current_count || 0 }} / {{ sessionData.max_triggers || 0 }}</span>
          <span class="progress-percentage">{{ Math.round((sessionData.progress || 0) * 100) }}%</span>
        </div>
        <div class="progress-bar">
          <div 
            class="progress-fill" 
            :style="{ width: ((sessionData.progress || 0) * 100) + '%' }"
          ></div>
        </div>
      </div>

      <div class="session-actions">
        <button class="btn-complete" @click="completeSession" :disabled="isProcessing">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
            <polyline points="22 4 12 14.01 9 11.01"></polyline>
          </svg>
          Complete
        </button>
        <button class="btn-cancel" @click="cancelSession" :disabled="isProcessing">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
          Cancel
        </button>
      </div>

      <!-- Recent Measurements in Session -->
      <div v-if="sessionData.measurements && sessionData.measurements.length > 0" class="recent-measurements">
        <div class="measurements-title">Recent Measurements:</div>
        <div class="measurements-list">
          <div 
            v-for="(m, i) in sessionData.measurements.slice(-3).reverse()" 
            :key="i"
            class="measurement-item"
          >
            <span class="measurement-index">#{{ sessionData.measurements.length - i }}</span>
            <span class="measurement-value">{{ m.size.toFixed(2) }} mm</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Session Not Active -->
    <div v-else class="session-idle">
      <button class="btn-start-session" @click="showStartDialog = true">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
          <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path>
          <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path>
        </svg>
        <span>Start Database Session</span>
      </button>
    </div>

    <!-- Start Session Dialog -->
    <div v-if="showStartDialog" class="dialog-overlay" @click.self="showStartDialog = false">
      <div class="dialog">
        <div class="dialog-header">
          <h3>Start Measurement Session</h3>
          <button class="close-btn" @click="showStartDialog = false">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        <div class="dialog-body">
          <div class="form-group">
            <label>Object Name <span class="required">*</span></label>
            <input 
              type="text" 
              v-model="startForm.object_name" 
              placeholder="e.g., Contaminate_A"
              @keyup.enter="startSession"
            >
            <p class="help-text">Object name must match detected objects</p>
          </div>

          <div class="form-group">
            <label>LOT Number</label>
            <input 
              type="text" 
              v-model="startForm.lot" 
              placeholder="Optional"
            >
          </div>

          <div class="form-group">
            <label>Product Type</label>
            <input 
              type="text" 
              v-model="startForm.product_type" 
              placeholder="Optional"
            >
          </div>

          <div class="form-group">
            <label>Measurement Count</label>
            <input 
              type="number" 
              v-model.number="startForm.max_triggers" 
              min="1"
              max="100"
              :disabled="startForm.unlimited"
            >
            <label class="checkbox-label">
              <input type="checkbox" v-model="startForm.unlimited">
              <span>Unlimited (manual completion)</span>
            </label>
          </div>
        </div>

        <div class="dialog-footer">
          <button class="btn-secondary" @click="showStartDialog = false">Cancel</button>
          <button 
            class="btn-primary" 
            @click="startSession" 
            :disabled="!startForm.object_name || isProcessing"
          >
            {{ isProcessing ? 'Starting...' : 'Start Session' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Status Messages -->
    <div v-if="statusMessage" class="status-message" :class="statusMessage.type">
      {{ statusMessage.text }}
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'DatabaseControl',
  data() {
    return {
      databaseEnabled: false,
      sessionActive: false,
      sessionData: {},
      showStartDialog: false,
      isProcessing: false,
      statusMessage: null,
      startForm: {
        object_name: '',
        lot: '',
        product_type: '',
        max_triggers: 10,
        unlimited: false
      }
    }
  },
  mounted() {
    this.checkDatabaseStatus()
    // Poll session status every 2 seconds
    this.statusInterval = setInterval(() => {
      if (this.databaseEnabled) {
        this.checkSessionStatus()
      }
    }, 2000)
  },
  beforeUnmount() {
    if (this.statusInterval) {
      clearInterval(this.statusInterval)
    }
  },
  methods: {
    async checkDatabaseStatus() {
      try {
        const response = await axios.get('/api/database/config')
        if (response.data.success) {
          this.databaseEnabled = response.data.config.enabled
        }
      } catch (error) {
        console.error('Failed to check database status:', error)
      }
    },
    async checkSessionStatus() {
      try {
        const response = await axios.get('/api/database/session/status')
        if (response.data.success) {
          this.sessionActive = response.data.active
          this.sessionData = response.data.session || {}
        }
      } catch (error) {
        console.error('Failed to check session status:', error)
      }
    },
    async startSession() {
      if (!this.startForm.object_name) {
        this.showStatus('Please enter object name', 'error')
        return
      }

      this.isProcessing = true
      
      try {
        const payload = {
          object_name: this.startForm.object_name,
          lot: this.startForm.lot,
          product_type: this.startForm.product_type
        }

        if (!this.startForm.unlimited) {
          payload.max_triggers = this.startForm.max_triggers
        } else {
          payload.max_triggers = 999999
        }

        const response = await axios.post('/api/database/session/start', payload)
        
        if (response.data.success) {
          this.showStatus('Session started successfully', 'success')
          this.showStartDialog = false
          this.sessionActive = true
          this.checkSessionStatus()
          
          // Reset form
          this.startForm = {
            object_name: '',
            lot: '',
            product_type: '',
            max_triggers: 10,
            unlimited: false
          }
        } else {
          this.showStatus(response.data.message || 'Failed to start session', 'error')
        }
      } catch (error) {
        this.showStatus(error.response?.data?.message || 'Failed to start session', 'error')
      } finally {
        this.isProcessing = false
      }
    },
    async completeSession() {
      if (!confirm('Complete this session and save the maximum measurement to database?')) {
        return
      }

      this.isProcessing = true
      
      try {
        const response = await axios.post('/api/database/session/complete')
        
        if (response.data.success) {
          const maxData = response.data.max_measurement
          this.showStatus(
            `Session completed! Saved: ${maxData.obj} = ${maxData.size.toFixed(2)}mm`,
            'success'
          )
          this.sessionActive = false
          this.sessionData = {}
        } else {
          this.showStatus(response.data.message || 'Failed to complete session', 'error')
        }
      } catch (error) {
        this.showStatus(error.response?.data?.message || 'Failed to complete session', 'error')
      } finally {
        this.isProcessing = false
      }
    },
    async cancelSession() {
      if (!confirm('Cancel this session? All measurements will be discarded.')) {
        return
      }

      this.isProcessing = true
      
      try {
        const response = await axios.post('/api/database/session/cancel')
        
        if (response.data.success) {
          this.showStatus('Session cancelled', 'success')
          this.sessionActive = false
          this.sessionData = {}
        } else {
          this.showStatus('Failed to cancel session', 'error')
        }
      } catch (error) {
        this.showStatus('Failed to cancel session', 'error')
      } finally {
        this.isProcessing = false
      }
    },
    showStatus(text, type) {
      this.statusMessage = { text, type }
      setTimeout(() => {
        this.statusMessage = null
      }, 3000)
    }
  }
}
</script>

<style scoped>
.database-control {
  margin-top: 16px;
}

.session-active {
  background: linear-gradient(135deg, rgba(234, 179, 8, 0.1) 0%, rgba(234, 179, 8, 0.05) 100%);
  border: 2px solid rgba(234, 179, 8, 0.3);
  border-radius: 12px;
  padding: 16px;
}

.session-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.session-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #facc15;
}

.session-icon.pulsing svg {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(1.1);
  }
}

.session-info {
  flex: 1;
}

.session-title {
  font-size: 16px;
  font-weight: 600;
  color: #facc15;
  margin-bottom: 2px;
}

.session-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
}

.session-progress {
  margin-bottom: 12px;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
  font-size: 13px;
  color: var(--text-tertiary);
}

.progress-percentage {
  font-weight: 600;
  color: #facc15;
}

.progress-bar {
  height: 8px;
  background: rgba(100, 100, 120, 0.2);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #facc15, #fbbf24);
  transition: width 0.3s ease;
  border-radius: 4px;
}

.session-actions {
  display: flex;
  gap: 8px;
}

.btn-complete,
.btn-cancel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-complete {
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.3);
  color: #4ade80;
}

.btn-complete:hover:not(:disabled) {
  background: rgba(34, 197, 94, 0.2);
  border-color: #4ade80;
}

.btn-cancel {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #f87171;
}

.btn-cancel:hover:not(:disabled) {
  background: rgba(239, 68, 68, 0.2);
  border-color: #f87171;
}

.btn-complete:disabled,
.btn-cancel:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.recent-measurements {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(234, 179, 8, 0.2);
}

.measurements-title {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 8px;
  font-weight: 500;
}

.measurements-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.measurement-item {
  display: flex;
  justify-content: space-between;
  padding: 6px 8px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
  font-size: 13px;
}

.measurement-index {
  color: var(--text-secondary);
}

.measurement-value {
  color: var(--text-primary);
  font-weight: 600;
}

.session-idle {
  display: flex;
  justify-content: center;
}

.btn-start-session {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 24px;
  background: var(--gradient-primary);
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-start-session:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(var(--primary-rgb), 0.4);
}

/* Dialog styles */
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100001;
}

.dialog {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  width: 90%;
  max-width: 500px;
  box-shadow: var(--shadow-xl);
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid var(--border-color);
}

.dialog-header h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: 18px;
}

.close-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-dark-secondary);
  border: none;
  border-radius: 6px;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all 0.2s;
}

.close-btn:hover {
  background: var(--bg-card-hover);
  color: var(--text-primary);
}

.dialog-body {
  padding: 20px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  color: var(--text-tertiary);
  font-size: 14px;
  font-weight: 500;
}

.required {
  color: #f87171;
}

.form-group input[type="text"],
.form-group input[type="number"] {
  width: 100%;
  padding: 10px 12px;
  background: var(--bg-dark-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 14px;
}

.form-group input:focus {
  outline: none;
  border-color: var(--primary-color);
  background: var(--bg-dark-secondary);
}

.form-group input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.help-text {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-secondary);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  cursor: pointer;
  user-select: none;
}

.checkbox-label input {
  width: auto;
}

.dialog-footer {
  display: flex;
  gap: 12px;
  padding: 20px;
  border-top: 1px solid var(--border-color);
}

.btn-primary,
.btn-secondary {
  flex: 1;
  padding: 12px 20px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: var(--gradient-primary);
  border: none;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(var(--primary-rgb), 0.4);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--bg-dark-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-tertiary);
}

.btn-secondary:hover {
  background: var(--bg-card-hover);
}

.status-message {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 13px;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    transform: translateY(-10px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.status-message.success {
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.3);
  color: #4ade80;
}

.status-message.error {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #f87171;
}
</style>
