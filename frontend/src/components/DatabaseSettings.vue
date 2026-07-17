<template>
  <div class="database-settings">
    <div class="settings-header">
      <h3>
        <svg class="icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
          <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path>
          <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path>
        </svg>
        SQL Server Database
      </h3>
      <p class="settings-description">
        Configure database connection and measurement session settings
      </p>
    </div>

    <!-- Connection Status -->
    <div class="connection-status" :class="statusClass">
      <div class="status-indicator"></div>
      <span>{{ connectionStatus }}</span>
    </div>

    <!-- Enable/Disable Database -->
    <div class="form-group">
      <label class="checkbox-label">
        <input type="checkbox" v-model="config.enabled" @change="handleEnableChange">
        <span>Enable Database Storage</span>
      </label>
      <p class="help-text">Save measurement data to SQL Server database</p>
    </div>

    <div v-if="config.enabled" class="database-form">
      <!-- Connection Settings -->
      <div class="form-section">
        <h4>Connection Settings</h4>
        
        <div class="form-group">
          <label>Host / IP Address</label>
          <input 
            type="text" 
            v-model="config.host" 
            placeholder="10.0.191.15"
            :disabled="!config.enabled"
          >
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>Port</label>
            <input 
              type="number" 
              v-model.number="config.port" 
              placeholder="1433"
              :disabled="!config.enabled"
            >
          </div>
          
          <div class="form-group">
            <label>Database Name</label>
            <input 
              type="text" 
              v-model="config.database" 
              placeholder="OT-test"
              :disabled="!config.enabled"
            >
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>Username</label>
            <input 
              type="text" 
              v-model="config.username" 
              placeholder="testchecksize"
              autocomplete="off"
              :disabled="!config.enabled"
            >
          </div>
          
          <div class="form-group">
            <label>Password</label>
            <input 
              type="password" 
              v-model="config.password" 
              placeholder="Enter password"
              autocomplete="new-password"
              :disabled="!config.enabled"
            >
          </div>
        </div>

        <div class="form-group">
          <label>Table Name</label>
          <input 
            type="text" 
            v-model="config.table" 
            placeholder="tbl_testchecksize"
            :disabled="!config.enabled"
          >
        </div>

        <!-- Test Connection Button -->
        <button 
          class="btn-test" 
          @click="testConnection"
          :disabled="isTestingConnection || !config.enabled"
        >
          <svg v-if="!isTestingConnection" class="icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
            <polyline points="22 4 12 14.01 9 11.01"></polyline>
          </svg>
          <svg v-else class="icon spinning" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
          </svg>
          {{ isTestingConnection ? 'Testing...' : 'Test Connection' }}
        </button>

        <div v-if="testResult" class="test-result" :class="testResult.success ? 'success' : 'error'">
          {{ testResult.message }}
        </div>

        <!-- Database Schema Guide -->
        <div class="schema-guide">
          <button class="schema-toggle" @click="showSchema = !showSchema">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="16" x2="12" y2="12"></line>
              <line x1="12" y1="8" x2="12.01" y2="8"></line>
            </svg>
            <span>Database Schema / Table Structure</span>
            <svg class="chevron" :class="{ 'open': showSchema }" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </button>

          <div v-if="showSchema" class="schema-content">
            <p class="schema-description">
              คัดลอก SQL script ด้านล่างเพื่อสร้างตารางในฐานข้อมูล SQL Server ของคุณ
            </p>

            <div class="code-block">
              <div class="code-header">
                <span>SQL Script</span>
                <button class="copy-btn" @click="copySchema" :class="{ 'copied': schemaCopied }">
                  <svg v-if="!schemaCopied" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                  </svg>
                  <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                  {{ schemaCopied ? 'Copied!' : 'Copy' }}
                </button>
              </div>
              <pre class="code-content">{{ schemaSQL }}</pre>
            </div>

            <div class="schema-notes">
              <h5>📋 Table Columns Explained:</h5>
              <ul>
                <li><code>id</code> - Auto-increment primary key</li>
                <li><code>machine_code</code> - Machine identifier (nullable)</li>
                <li><code>object_name</code> - Name of measured object</li>
                <li><code>width_mm</code>, <code>height_mm</code> - Measured dimensions in millimeters</li>
                <li><code>area_mm2</code> - Calculated area (width × height)</li>
                <li><code>lot_number</code>, <code>product_type</code> - Product tracking info</li>
                <li><code>timestamp</code> - Measurement date and time</li>
                <li><code>session_id</code>, <code>max_value_in_session</code> - Session tracking</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <!-- Session Settings -->
      <div class="form-section">
        <h4>Measurement Session Settings</h4>

        <div class="form-group">
          <label>
            Measurement Triggers per Session
            <span class="label-badge">{{ config.unlimited_mode ? 'UNLIMITED' : config.measurement_triggers }}</span>
          </label>
          <input 
            type="range" 
            v-model.number="config.measurement_triggers" 
            min="1" 
            max="100"
            :disabled="!config.enabled || config.unlimited_mode"
          >
          <p class="help-text">
            System will measure {{ config.measurement_triggers }} times and save only the MAXIMUM value
          </p>
        </div>

        <div class="form-group">
          <label class="checkbox-label">
            <input type="checkbox" v-model="config.unlimited_mode" :disabled="!config.enabled">
            <span>Unlimited Mode</span>
          </label>
          <p class="help-text">Allow unlimited measurements until manually completed</p>
        </div>

        <div class="form-group">
          <label class="checkbox-label">
            <input type="checkbox" v-model="config.auto_save" :disabled="!config.enabled">
            <span>Auto-save on completion</span>
          </label>
          <p class="help-text">Automatically save to database when session completes</p>
        </div>
      </div>

      <!-- Product Information -->
      <div class="form-section">
        <h4>Product Information (Optional)</h4>

        <div class="form-group">
          <label>LOT Number</label>
          <input 
            type="text" 
            v-model="config.lot" 
            placeholder="LOT-001"
            :disabled="!config.enabled"
          >
        </div>

        <div class="form-group">
          <label>Product Type</label>
          <input 
            type="text" 
            v-model="config.product_type" 
            placeholder="TYPE-A"
            :disabled="!config.enabled"
          >
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="form-actions">
        <button class="btn-secondary" @click="loadConfig">
          <svg class="icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/>
          </svg>
          Reset
        </button>
        <button class="btn-primary" @click="saveConfig" :disabled="isSaving">
          <svg v-if="!isSaving" class="icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
            <polyline points="17 21 17 13 7 13 7 21"></polyline>
            <polyline points="7 3 7 8 15 8"></polyline>
          </svg>
          <svg v-else class="icon spinning" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
          </svg>
          {{ isSaving ? 'Saving...' : 'Save Configuration' }}
        </button>
      </div>
    </div>

    <!-- Session Control (if active) -->
    <div v-if="sessionStatus && sessionStatus.active" class="session-control">
      <h4>Active Session</h4>
      <div class="session-info">
        <div class="info-item">
          <span class="label">Object:</span>
          <span class="value">{{ sessionStatus.session.object_name }}</span>
        </div>
        <div class="info-item">
          <span class="label">Progress:</span>
          <span class="value">{{ sessionStatus.session.current_count }} / {{ sessionStatus.session.max_triggers }}</span>
        </div>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: (sessionStatus.session.progress * 100) + '%' }"></div>
        </div>
      </div>
      <button class="btn-cancel" @click="cancelSession">Cancel Session</button>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'DatabaseSettings',
  data() {
    return {
      config: {
        enabled: false,
        host: '',
        username: '',
        password: '',
        database: '',
        table: 'tbl_testchecksize',
        port: 1433,
        measurement_triggers: 10,
        unlimited_mode: false,
        auto_save: false,
        lot: '',
        product_type: ''
      },
      isTestingConnection: false,
      isSaving: false,
      testResult: null,
      connectionStatus: 'Not Connected',
      sessionStatus: null,
      statusClass: 'disconnected',
      showSchema: false,
      schemaCopied: false,
      schemaSQL: `-- Create measurement table for PSE Vision System
CREATE TABLE tbl_testchecksize (
    id INT IDENTITY(1,1) PRIMARY KEY,
    machine_code NVARCHAR(50) NULL,
    object_name NVARCHAR(100) NOT NULL,
    width_mm DECIMAL(10, 2) NOT NULL,
    height_mm DECIMAL(10, 2) NOT NULL,
    area_mm2 DECIMAL(15, 2) NULL,
    lot_number NVARCHAR(50) NULL,
    product_type NVARCHAR(50) NULL,
    timestamp DATETIME DEFAULT GETDATE(),
    session_id NVARCHAR(100) NULL,
    max_value_in_session BIT DEFAULT 0,
    notes NVARCHAR(MAX) NULL
);

-- Create indexes for better query performance
CREATE INDEX idx_timestamp ON tbl_testchecksize(timestamp);
CREATE INDEX idx_lot_number ON tbl_testchecksize(lot_number);
CREATE INDEX idx_machine_code ON tbl_testchecksize(machine_code);
CREATE INDEX idx_session_id ON tbl_testchecksize(session_id);

-- Example query to get recent measurements
-- SELECT TOP 100 * FROM tbl_testchecksize ORDER BY timestamp DESC;`
    }
  },
  mounted() {
    this.loadConfig()
    this.checkSessionStatus()
    // Poll session status every 2 seconds
    this.sessionInterval = setInterval(() => {
      if (this.config.enabled) {
        this.checkSessionStatus()
      }
    }, 2000)
  },
  beforeUnmount() {
    if (this.sessionInterval) {
      clearInterval(this.sessionInterval)
    }
  },
  methods: {
    async loadConfig() {
      try {
        const response = await axios.get('/api/database/config')
        if (response.data.success) {
          // Merge loaded config with defaults
          this.config = { ...this.config, ...response.data.config }
          this.updateConnectionStatus()
        }
      } catch (error) {
        console.error('Failed to load database config:', error)
      }
    },
    async saveConfig() {
      this.isSaving = true
      this.testResult = null
      
      try {
        const response = await axios.post('/api/database/config/update', this.config)
        
        if (response.data.success) {
          this.testResult = {
            success: true,
            message: 'Configuration saved successfully'
          }
          this.updateConnectionStatus()
        } else {
          this.testResult = {
            success: false,
            message: response.data.message || 'Failed to save configuration'
          }
        }
      } catch (error) {
        this.testResult = {
          success: false,
          message: error.response?.data?.message || error.message
        }
      } finally {
        this.isSaving = false
      }
    },
    async testConnection() {
      this.isTestingConnection = true
      this.testResult = null
      
      try {
        const response = await axios.post('/api/database/test')
        
        this.testResult = {
          success: response.data.success,
          message: response.data.message
        }
        
        if (response.data.success) {
          this.connectionStatus = 'Connected'
          this.statusClass = 'connected'
        }
      } catch (error) {
        this.testResult = {
          success: false,
          message: error.response?.data?.message || 'Connection test failed'
        }
        this.connectionStatus = 'Connection Failed'
        this.statusClass = 'error'
      } finally {
        this.isTestingConnection = false
      }
    },
    async checkSessionStatus() {
      try {
        const response = await axios.get('/api/database/session/status')
        if (response.data.success) {
          this.sessionStatus = response.data
        }
      } catch (error) {
        console.error('Failed to get session status:', error)
      }
    },
    async cancelSession() {
      try {
        const response = await axios.post('/api/database/session/cancel')
        if (response.data.success) {
          this.sessionStatus = null
          this.testResult = {
            success: true,
            message: 'Session cancelled'
          }
        }
      } catch (error) {
        this.testResult = {
          success: false,
          message: 'Failed to cancel session'
        }
      }
    },
    handleEnableChange() {
      if (!this.config.enabled) {
        this.connectionStatus = 'Not Connected'
        this.statusClass = 'disconnected'
        this.testResult = null
      }
    },
    updateConnectionStatus() {
      if (this.config.enabled) {
        this.connectionStatus = 'Configured (Not Tested)'
        this.statusClass = 'configured'
      } else {
        this.connectionStatus = 'Not Connected'
        this.statusClass = 'disconnected'
      }
    },
    copySchema() {
      navigator.clipboard.writeText(this.schemaSQL).then(() => {
        this.schemaCopied = true
        setTimeout(() => {
          this.schemaCopied = false
        }, 2000)
      }).catch(err => {
        console.error('Failed to copy:', err)
        alert('Failed to copy to clipboard')
      })
    }
  }
}
</script>

<style scoped>
.database-settings {
  padding: 0;
  background: transparent;
}

.settings-header h3 {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 0 8px 0;
  color: var(--primary-color);
  font-size: 18px;
  font-weight: 600;
}

.settings-description {
  margin: 0 0 20px 30px;
  color: var(--text-secondary);
  font-size: 14px;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 20px;
  font-size: 14px;
  font-weight: 500;
}

.connection-status.disconnected {
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  color: #64748b;
}

.connection-status.configured {
  background: #fef3c7;
  border: 1px solid #fbbf24;
  color: #d97706;
}

.connection-status.connected {
  background: #dcfce7;
  border: 1px solid #4ade80;
  color: #16a34a;
}

.connection-status.error {
  background: #fee2e2;
  border: 1px solid #f87171;
  color: #dc2626;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.database-form {
  margin-top: 20px;
}

.form-section {
  margin-bottom: 30px;
  padding: 20px;
  background: var(--bg-dark-secondary);
  border-radius: 10px;
  border: 1px solid var(--border-color);
}

.form-section h4 {
  margin: 0 0 16px 0;
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 600;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 500;
}

.label-badge {
  display: inline-block;
  padding: 2px 8px;
  background: #dbeafe;
  border-radius: 4px;
  color: var(--primary-color);
  font-size: 12px;
  font-weight: 600;
  margin-left: 8px;
}

.form-group input[type="text"],
.form-group input[type="password"],
.form-group input[type="number"] {
  width: 100%;
  padding: 10px 12px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 14px;
  transition: all 0.2s;
}

.form-group input[type="text"]:focus,
.form-group input[type="password"]:focus,
.form-group input[type="number"]:focus {
  outline: none;
  border-color: var(--primary-color);
  background: var(--bg-card);
  box-shadow: 0 0 0 3px rgba(var(--primary-rgb), 0.1);
}

.form-group input[type="text"]:disabled,
.form-group input[type="password"]:disabled,
.form-group input[type="number"]:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.form-group input[type="range"] {
  width: 100%;
  height: 6px;
  background: var(--border-color);
  border-radius: 3px;
  outline: none;
}

.form-group input[type="range"]::-webkit-slider-thumb {
  width: 18px;
  height: 18px;
  background: var(--primary-color);
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
}

.checkbox-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.help-text {
  margin: 6px 0 0 0;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.4;
}

.btn-test {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: var(--bg-card);
  border: 1px solid var(--primary-color);
  border-radius: 6px;
  color: var(--primary-color);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  margin-top: 12px;
}

.btn-test:hover:not(:disabled) {
  background: var(--primary-color);
  color: white;
  box-shadow: 0 2px 8px rgba(var(--primary-rgb), 0.3);
}

.btn-test:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.test-result {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 13px;
}

.test-result.success {
  background: #dcfce7;
  border: 1px solid #4ade80;
  color: #16a34a;
}

.test-result.error {
  background: #fee2e2;
  border: 1px solid #f87171;
  color: #dc2626;
}

.form-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}

.btn-primary,
.btn-secondary {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 20px;
  border-radius: 8px;
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
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.btn-secondary:hover {
  background: var(--bg-card-hover);
  border-color: var(--border-color);
  border-color: rgba(100, 100, 120, 0.5);
}

.session-control {
  margin-top: 20px;
  padding: 20px;
  background: rgba(234, 179, 8, 0.05);
  border: 1px solid rgba(234, 179, 8, 0.2);
  border-radius: 10px;
}

.session-control h4 {
  margin: 0 0 16px 0;
  color: #facc15;
  font-size: 16px;
}

.session-info {
  margin-bottom: 16px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 14px;
}

.info-item .label {
  color: var(--text-secondary);
}

.info-item .value {
  color: var(--text-primary);
  font-weight: 600;
}

.progress-bar {
  height: 8px;
  background: rgba(100, 100, 120, 0.2);
  border-radius: 4px;
  overflow: hidden;
  margin-top: 12px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #facc15, #fbbf24);
  transition: width 0.3s ease;
}

.btn-cancel {
  width: 100%;
  padding: 10px;
  background: var(--bg-card);
  border: 1px solid #ef4444;
  border-radius: 6px;
  color: #dc2626;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel:hover {
  background: #ef4444;
  color: white;
}

/* Schema Guide Styles */
.schema-guide {
  margin-top: 20px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
  background: var(--bg-card);
}

.schema-toggle {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 12px 16px;
  background: var(--bg-dark-secondary);
  border: none;
  color: var(--primary-color);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.schema-toggle:hover {
  background: var(--bg-card-hover);
}

.schema-toggle .chevron {
  margin-left: auto;
  transition: transform 0.2s;
}

.schema-toggle .chevron.open {
  transform: rotate(180deg);
}

.schema-content {
  padding: 16px;
  background: var(--bg-dark-secondary);
  animation: slideDown 0.2s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.schema-description {
  margin: 0 0 16px 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.5;
}

.code-block {
  margin-bottom: 16px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  overflow: hidden;
}

.code-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: var(--bg-dark-secondary);
  border-bottom: 1px solid var(--border-color);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
}

.copy-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--bg-card);
  border: 1px solid var(--primary-color);
  border-radius: 4px;
  color: var(--primary-color);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.copy-btn:hover {
  background: var(--primary-color);
  color: white;
}

.copy-btn.copied {
  background: #dcfce7;
  border-color: #4ade80;
  color: #16a34a;
}

.code-content {
  margin: 0;
  padding: 16px;
  background: #1e293b;
  color: #e2e8f0;
  font-family: 'Consolas', 'Monaco', var(--font-mono);
  font-size: 12px;
  line-height: 1.6;
  overflow-x: auto;
  white-space: pre;
}

.schema-notes {
  padding: 14px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 6px;
}

.schema-notes h5 {
  margin: 0 0 12px 0;
  color: var(--primary-color);
  font-size: 13px;
  font-weight: 600;
}

.schema-notes ul {
  margin: 0;
  padding-left: 20px;
  list-style: none;
}

.schema-notes li {
  margin-bottom: 6px;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.5;
  position: relative;
}

.schema-notes li::before {
  content: "▸";
  position: absolute;
  left: -15px;
  color: var(--primary-color);
}

.schema-notes code {
  padding: 2px 6px;
  background: #dbeafe;
  border-radius: 3px;
  color: #1e40af;
  font-family: 'Consolas', 'Monaco', var(--font-mono);
  font-size: 11px;
}

.icon {
  flex-shrink: 0;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
