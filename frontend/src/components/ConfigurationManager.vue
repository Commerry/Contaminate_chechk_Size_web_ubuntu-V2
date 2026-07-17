<template>
  <div class="config-manager-panel">
    <div class="panel-wrapper">
      <div class="panel-header">
        <h2 class="panel-title">
          <IconSvg name="settings" :size="24" />
          Configuration Manager
          <span class="subtitle">กำหนดพื้นที่เป้าหมาย (Area-based)</span>
        </h2>
        <button class="close-btn" @click="$emit('close')">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>

      <div class="panel-content">
      <!-- Configuration List -->
      <div class="config-list-section">
        <div class="section-header">
          <h3>รายการ Configurations</h3>
          <button class="btn btn-primary btn-sm" @click="showCreateForm = true">
            <IconSvg name="plus" :size="16" />
            เพิ่ม Configuration
          </button>
        </div>

        <div class="config-list">
          <div 
            v-for="config in configurations" 
            :key="config.id"
            class="config-item"
            :class="{ 'active': selectedConfig?.id === config.id }"
          >
            <div class="config-info">
              <div class="config-name">{{ config.name }}</div>
              <div class="config-details">
                <span class="badge badge-info">
                  {{ config.target_area_min }} - {{ config.target_area_max }} mm²
                </span>
                <span class="tolerance">±{{ config.tolerance }} mm²</span>
              </div>
            </div>
            <div class="config-actions">
              <button 
                class="btn-icon" 
                @click="selectConfig(config)"
                :class="{ 'active': selectedConfig?.id === config.id }"
              >
                <IconSvg name="check" :size="16" />
              </button>
              <button class="btn-icon" @click="editConfig(config)">
                <IconSvg name="edit" :size="16" />
              </button>
              <button class="btn-icon danger" @click="deleteConfig(config.id)">
                <IconSvg name="trash" :size="16" />
              </button>
            </div>
          </div>

          <div v-if="configurations.length === 0" class="empty-state">
            <IconSvg name="folder" :size="48" style="opacity: 0.3; margin-bottom: 16px;" />
            <p>ยังไม่มี Configuration</p>
            <button class="btn btn-primary" @click="showCreateForm = true">
              เพิ่ม Configuration แรก
            </button>
          </div>
        </div>
      </div>

      <!-- Create/Edit Form -->
      <div v-if="showCreateForm || editingConfig" class="config-form-section">
        <h3>{{ editingConfig ? 'แก้ไข' : 'เพิ่ม' }} Configuration</h3>
        
        <div class="form-group">
          <label>ชื่อ Configuration</label>
          <input 
            v-model="formData.name" 
            type="text" 
            class="form-input"
            placeholder="เช่น Small Object (500-1000 mm²)"
          />
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>พื้นที่ต่ำสุด (mm²)</label>
            <input 
              v-model.number="formData.target_area_min" 
              type="number" 
              class="form-input"
              min="0"
              step="10"
            />
          </div>

          <div class="form-group">
            <label>พื้นที่สูงสุด (mm²)</label>
            <input 
              v-model.number="formData.target_area_max" 
              type="number" 
              class="form-input"
              min="0"
              step="10"
            />
          </div>
        </div>

        <div class="form-group">
          <label>ความคลาดเคลื่อนที่ยอมรับ (±mm²)</label>
          <input 
            v-model.number="formData.tolerance" 
            type="number" 
            class="form-input"
            min="0"
            step="5"
          />
        </div>

        <div class="form-preview">
          <div class="preview-label">ตัวอย่างช่วงพื้นที่:</div>
          <div class="preview-value">
            {{ formData.target_area_min - formData.tolerance }} mm² 
            ~ 
            {{ formData.target_area_max + formData.tolerance }} mm²
          </div>
        </div>

        <div class="form-actions">
          <button class="btn" @click="cancelForm">ยกเลิก</button>
          <button class="btn btn-primary" @click="saveConfig">
            {{ editingConfig ? 'บันทึกการแก้ไข' : 'เพิ่ม Configuration' }}
          </button>
        </div>
      </div>
    </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import IconSvg from './IconSvg.vue'
import axios from 'axios'

const emit = defineEmits(['close', 'config-selected'])

const configurations = ref([])
const selectedConfig = ref(null)
const showCreateForm = ref(false)
const editingConfig = ref(null)

const formData = ref({
  name: '',
  target_area_min: 500,
  target_area_max: 1000,
  tolerance: 50,
  enabled: true
})

onMounted(() => {
  loadConfigurations()
})

async function loadConfigurations() {
  try {
    const response = await axios.get('/api/configurations')
    if (response.data.success) {
      configurations.value = response.data.configurations
    }
  } catch (error) {
    console.error('Failed to load configurations:', error)
    alert('ไม่สามารถโหลด Configuration ได้')
  }
}

function selectConfig(config) {
  selectedConfig.value = config
  emit('config-selected', config)
}

function editConfig(config) {
  editingConfig.value = config
  formData.value = { ...config }
  showCreateForm.value = false
}

async function saveConfig() {
  try {
    if (editingConfig.value) {
      // Update existing
      const response = await axios.put(
        `/api/configurations/${editingConfig.value.id}`,
        formData.value
      )
      if (response.data.success) {
        await loadConfigurations()
        cancelForm()
        alert('แก้ไข Configuration สำเร็จ')
      }
    } else {
      // Create new
      const response = await axios.post(
        '/api/configurations/create',
        formData.value
      )
      if (response.data.success) {
        await loadConfigurations()
        cancelForm()
        alert('เพิ่ม Configuration สำเร็จ')
      }
    }
  } catch (error) {
    console.error('Failed to save configuration:', error)
    alert('ไม่สามารถบันทึก Configuration ได้')
  }
}

async function deleteConfig(id) {
  if (!confirm('คุณต้องการลบ Configuration นี้หรือไม่?')) return

  try {
    const response = await axios.delete(
      `/api/configurations/${id}`
    )
    if (response.data.success) {
      await loadConfigurations()
      if (selectedConfig.value?.id === id) {
        selectedConfig.value = null
      }
      alert('ลบ Configuration สำเร็จ')
    }
  } catch (error) {
    console.error('Failed to delete configuration:', error)
    alert('ไม่สามารถลบ Configuration ได้')
  }
}

function cancelForm() {
  showCreateForm.value = false
  editingConfig.value = null
  formData.value = {
    name: '',
    target_area_min: 500,
    target_area_max: 1000,
    tolerance: 50,
    enabled: true
  }
}
</script>

<style scoped>
.config-manager-panel {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100001;
  padding: 20px;
}

.panel-wrapper {
  background: var(--bg-card);
  border-radius: 12px;
  max-width: 900px;
  width: 100%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-xl);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 24px;
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  flex-direction: column;
  align-items: flex-start;
}

.subtitle {
  font-size: 14px;
  font-weight: 400;
  color: var(--text-secondary);
  margin-top: 4px;
}

.close-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 8px;
  border-radius: 6px;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.close-btn:hover {
  background: var(--bg-dark-secondary);
  color: var(--text-primary);
}

.panel-content {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.config-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.config-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: var(--bg-dark-secondary);
  border: 2px solid transparent;
  border-radius: 8px;
  transition: all 0.2s;
}

.config-item:hover {
  background: var(--bg-card-hover);
}

.config-item.active {
  border-color: var(--primary-color);
  background: rgba(var(--primary-rgb), 0.12);
}

.config-info {
  flex: 1;
}

.config-name {
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.config-details {
  display: flex;
  gap: 12px;
  align-items: center;
}

.tolerance {
  font-size: 13px;
  color: var(--text-secondary);
}

.config-actions {
  display: flex;
  gap: 8px;
}

.btn-icon {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  padding: 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-icon:hover {
  background: var(--bg-card-hover);
}

.btn-icon.active {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: white;
}

.btn-icon.danger:hover {
  background: #fef2f2;
  border-color: #ef4444;
  color: #ef4444;
}

.empty-state {
  text-align: center;
  padding: 48px 24px;
  color: var(--text-secondary);
  display: flex;
  flex-direction: column;
  align-items: center;
}

.config-form-section {
  margin-top: 24px;
  padding: 24px;
  background: var(--bg-dark-secondary);
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.config-form-section h3 {
  margin-top: 0;
  margin-bottom: 20px;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: var(--text-secondary);
  font-size: 14px;
}

.form-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-size: 14px;
  transition: all 0.2s;
}

.form-input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(var(--primary-rgb), 0.1);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.form-preview {
  padding: 16px;
  background: var(--bg-card);
  border-radius: 8px;
  margin-bottom: 20px;
  border: 1px solid var(--border-color);
}

.preview-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.preview-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--primary-color);
}

.form-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.btn {
  padding: 10px 20px;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  color: var(--text-secondary);
}

.btn:hover {
  background: var(--bg-card-hover);
}

.btn-primary {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}

.btn-primary:hover {
  background: var(--primary-dark);
}

.btn-sm {
  padding: 6px 12px;
  font-size: 13px;
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.badge-info {
  background: #dbeafe;
  color: #1e40af;
}
</style>
