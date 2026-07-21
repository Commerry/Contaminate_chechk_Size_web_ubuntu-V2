<template>
  <div class="machine-manager-panel">
    <div class="panel-wrapper">
      <div class="panel-header">
        <h2 class="panel-title">
          <IconSvg name="settings" :size="24" />
          Machine Manager
          <span class="subtitle">จัดการเครื่องจักร</span>
        </h2>
        <button class="close-btn" @click="$emit('close')">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>

      <div class="panel-content">
      <!-- Create/Edit Form (อยู่บนสุด) -->
      <div class="machine-form-section">
        <h3>{{ editingMachine ? 'แก้ไข' : 'เพิ่ม' }} เครื่องจักร</h3>
        
        <div class="form-group">
          <label>รหัสเครื่องจักร <span class="required">*</span></label>
          <input 
            v-model="formData.id" 
            type="text" 
            class="form-input"
            placeholder="เช่น MC-01, LINE-A-01"
            :disabled="!!editingMachine"
          />
        </div>

        <div class="form-group">
          <label>ชื่อเครื่องจักร <span class="required">*</span></label>
          <input 
            v-model="formData.name" 
            type="text" 
            class="form-input"
            placeholder="เช่น Machine 01"
          />
        </div>

        <div class="form-group">
          <label>รายละเอียด</label>
          <textarea 
            v-model="formData.description" 
            class="form-textarea"
            rows="3"
            placeholder="รายละเอียดเครื่องจักร..."
          ></textarea>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>สถานที่ตั้ง</label>
            <input 
              v-model="formData.location" 
              type="text" 
              class="form-input"
              placeholder="เช่น สายการผลิต A"
            />
          </div>

          <div class="form-group">
            <label>สถานะ</label>
            <select v-model="formData.status" class="form-select">
              <option value="active">ใช้งาน (Active)</option>
              <option value="inactive">ไม่ใช้งาน (Inactive)</option>
              <option value="maintenance">ซ่อมบำรุง (Maintenance)</option>
            </select>
          </div>
        </div>

        <!-- ✅ Configuration Section (Inline) -->
        <div class="config-section">
          <h4 class="section-subtitle">
            <IconSvg name="settings" :size="18" />
            การตั้งค่าขนาดพื้นที่ (Area Configuration)
          </h4>
          
          <div class="form-row">
            <div class="form-group">
              <label>พื้นที่ต่ำสุด (mm²) <span class="required">*</span></label>
              <input 
                v-model.number="formData.target_area_min" 
                type="number" 
                class="form-input"
                min="0"
                step="10"
                placeholder="เช่น 500"
              />
            </div>

            <div class="form-group">
              <label>พื้นที่สูงสุด (mm²) <span class="required">*</span></label>
              <input 
                v-model.number="formData.target_area_max" 
                type="number" 
                class="form-input"
                min="0"
                step="10"
                placeholder="เช่น 1000"
              />
            </div>
          </div>

          <div class="form-group">
            <label>ความคลาดเคลื่อนที่ยอมรับ (±mm²) <span class="required">*</span></label>
            <input 
              v-model.number="formData.tolerance" 
              type="number" 
              class="form-input"
              min="0"
              step="5"
              placeholder="เช่น 50"
            />
          </div>

          <div class="config-preview">
            <div class="preview-label">ช่วงพื้นที่ที่ยอมรับได้:</div>
            <div class="preview-value">
              <span class="value-highlight">
                {{ formData.target_area_min - formData.tolerance }} mm²
              </span>
              <span class="separator">~</span>
              <span class="value-highlight">
                {{ formData.target_area_max + formData.tolerance }} mm²
              </span>
            </div>
            <div class="preview-sublabel">
              (เป้าหมาย: {{ formData.target_area_min }}-{{ formData.target_area_max }} mm² ±{{ formData.tolerance }} mm²)
            </div>
          </div>
        </div>

        <div class="form-actions">
          <button class="btn btn-secondary" @click="cancelForm">
            ยกเลิก
          </button>
          <button 
            class="btn btn-primary" 
            @click="saveMachine"
            :disabled="!formData.id || !formData.name"
          >
            <IconSvg name="check" :size="16" />
            {{ editingMachine ? 'บันทึก' : 'เพิ่มเครื่องจักร' }}
          </button>
        </div>
      </div>

      <!-- Machine List (อยู่ล่าง) -->
      <div class="machine-list-section">
        <div class="section-header">
          <h3>รายการเครื่องจักร</h3>
        </div>

        <div class="machine-list">
          <div 
            v-for="machine in machines" 
            :key="machine.id"
            class="machine-item"
          >
            <div class="machine-info">
              <div class="machine-name">{{ machine.name }}</div>
              <div class="machine-details">
                <span class="badge badge-info">{{ machine.id }}</span>
                <span v-if="machine.location" class="location">📍 {{ machine.location }}</span>
                <span 
                  class="status-badge" 
                  :class="statusClass(machine.status)"
                >
                  {{ statusText(machine.status) }}
                </span>
              </div>
              <!-- ✅ แสดง Configuration -->
              <div v-if="machine.config" class="machine-config">
                <span class="config-label">📏 พื้นที่:</span>
                <span class="config-value">
                  {{ machine.config.target_area_min }}-{{ machine.config.target_area_max }} mm²
                  <span class="tolerance">±{{ machine.config.tolerance }}</span>
                </span>
              </div>
              <div v-if="machine.description" class="machine-description">
                {{ machine.description }}
              </div>
            </div>
            <div class="machine-actions">
              <button class="btn-icon" @click="editMachine(machine)">
                <IconSvg name="edit" :size="16" />
              </button>
              <button class="btn-icon danger" @click="deleteMachine(machine.id)">
                <IconSvg name="trash" :size="16" />
              </button>
            </div>
          </div>

          <div v-if="machines.length === 0" class="empty-state">
            <IconSvg name="folder" :size="48" style="opacity: 0.3; margin-bottom: 16px;" />
            <p>ยังไม่มีเครื่องจักร</p>
          </div>
        </div>
      </div>
    </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import IconSvg from './IconSvg.vue'
import { useToast } from '../composables/useToast'

const emit = defineEmits(['close', 'updated'])
const { showToast } = useToast()

const machines = ref([])
const editingMachine = ref(null)
const formData = ref({
  id: '',
  name: '',
  description: '',
  location: '',
  status: 'active',
  target_area_min: 500,
  target_area_max: 1000,
  tolerance: 50
})

const statusClass = (status) => {
  return {
    'status-active': status === 'active',
    'status-inactive': status === 'inactive',
    'status-maintenance': status === 'maintenance'
  }
}

const statusText = (status) => {
  const texts = {
    active: 'ใช้งาน',
    inactive: 'ไม่ใช้งาน',
    maintenance: 'ซ่อมบำรุง'
  }
  return texts[status] || status
}

const loadMachines = async () => {
  try {
    const response = await fetch('/api/machines')
    const data = await response.json()
    
    if (data.success) {
      machines.value = data.machines || []
    } else {
      showToast(data.message || 'โหลดข้อมูลเครื่องจักรไม่สำเร็จ', 'error')
    }
  } catch (error) {
    console.error('Error loading machines:', error)
    showToast('เชื่อมต่อ backend ไม่ได้', 'error')
  }
}

const editMachine = (machine) => {
  editingMachine.value = machine
  formData.value = {
    id: machine.id,
    name: machine.name,
    description: machine.description || '',
    location: machine.location || '',
    status: machine.status || 'active',
    target_area_min: machine.config?.target_area_min || 500,
    target_area_max: machine.config?.target_area_max || 1000,
    tolerance: machine.config?.tolerance || 50
  }
  showCreateForm.value = false
}

const cancelForm = () => {
  editingMachine.value = null
  formData.value = {
    id: '',
    name: '',
    description: '',
    location: '',
    status: 'active',
    target_area_min: 500,
    target_area_max: 1000,
    tolerance: 50
  }
}

const saveMachine = async () => {
  if (!formData.value.id || !formData.value.name) {
    showToast('กรุณากรอกข้อมูลที่จำเป็น', 'warning')
    return
  }

  try {
    const url = editingMachine.value 
      ? `/api/machines/${editingMachine.value.id}` 
      : '/api/machines'
    
    const method = editingMachine.value ? 'PUT' : 'POST'

    // Send target-area fields flat; the backend nests them into machine.config.*
    const response = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData.value)
    })
    
    const data = await response.json()
    
    if (data.success) {
      showToast(
        editingMachine.value ? 'แก้ไขเครื่องจักรสำเร็จ' : 'เพิ่มเครื่องจักรสำเร็จ',
        'success'
      )
      cancelForm()
      await loadMachines()
      emit('updated')
    } else {
      showToast(data.message || 'บันทึกไม่สำเร็จ', 'error')
    }
  } catch (error) {
    console.error('Error saving machine:', error)
    showToast('เกิดข้อผิดพลาดในการบันทึก', 'error')
  }
}

const deleteMachine = async (machineId) => {
  if (!confirm(`คุณต้องการลบเครื่องจักร ${machineId} หรือไม่?`)) {
    return
  }

  try {
    const response = await fetch(`/api/machines/${machineId}`, {
      method: 'DELETE'
    })
    
    const data = await response.json()
    
    if (data.success) {
      showToast('ลบเครื่องจักรสำเร็จ', 'success')
      await loadMachines()
      emit('updated')
    } else {
      showToast(data.message || 'ลบไม่สำเร็จ', 'error')
    }
  } catch (error) {
    console.error('Error deleting machine:', error)
    showToast('เกิดข้อผิดพลาดในการลบ', 'error')
  }
}

onMounted(() => {
  loadMachines()
})
</script>

<style scoped>
.machine-manager-panel {
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

.machine-list-section {
  margin-bottom: 24px;
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

.machine-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.machine-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: var(--bg-dark-secondary);
  border: 2px solid transparent;
  border-radius: 8px;
  transition: all 0.2s;
}

.machine-item:hover {
  background: var(--bg-card-hover);
  border-color: var(--primary-color);
}

.machine-info {
  flex: 1;
}

.machine-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.machine-details {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 4px;
}

.machine-description {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 8px;
  line-height: 1.5;
}

.badge {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}

.badge-info {
  background: #dbeafe;
  color: var(--primary-dark);
}

.location {
  font-size: 12px;
  color: var(--text-secondary);
}

.status-badge {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.status-active {
  background: #d1fae5;
  color: var(--primary-dark);
}

.status-inactive {
  background: #f3f4f6;
  color: #6b7280;
}

.status-maintenance {
  background: #fef3c7;
  color: #b45309;
}

.machine-actions {
  display: flex;
  gap: 8px;
}

.btn-icon {
  background: var(--bg-dark-secondary);
  border: none;
  border-radius: 8px;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.btn-icon:hover {
  background: #dbeafe;
  color: var(--primary-dark);
}

.btn-icon.danger:hover {
  background: #fee2e2;
  color: #dc2626;
}

.empty-state {
  text-align: center;
  padding: 48px 24px;
  color: var(--text-tertiary);
}

.empty-state p {
  margin: 0 0 16px 0;
  font-size: 14px;
  color: var(--text-secondary);
}

.machine-form-section {
  background: var(--bg-dark-secondary);
  border-radius: 12px;
  padding: 24px;
  border: 1px solid var(--border-color);
}

.machine-form-section h3 {
  color: var(--text-primary);
  font-size: 16px;
  margin: 0 0 20px 0;
  font-weight: 600;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  color: var(--text-secondary);
  font-size: 13px;
  margin-bottom: 8px;
  font-weight: 500;
}

.required {
  color: #dc2626;
}

.form-input,
.form-textarea,
.form-select {
  width: 100%;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 10px 12px;
  color: var(--text-primary);
  font-size: 14px;
  transition: all 0.2s;
}

.form-input:focus,
.form-textarea:focus,
.form-select:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(var(--primary-rgb), 0.1);
}

.form-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: var(--bg-dark-secondary);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.form-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-primary {
  background: var(--gradient-primary);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--gradient-primary);
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(var(--primary-rgb), 0.3);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--bg-dark-secondary);
  color: var(--text-secondary);
}

.btn-secondary:hover {
  background: var(--bg-card-hover);
}

/* ✅ Configuration Section Styles */
.config-section {
  margin-top: 24px;
  padding: 20px;
  background: linear-gradient(135deg, rgba(var(--primary-rgb), 0.05), rgba(var(--primary-rgb), 0.05));
  border: 2px solid rgba(var(--primary-rgb), 0.2);
  border-radius: 12px;
  transition: all 0.3s ease;
}

.config-section:hover {
  border-color: rgba(var(--primary-rgb), 0.4);
  box-shadow: 0 4px 12px rgba(var(--primary-rgb), 0.1);
}

.section-subtitle {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--primary-color);
  margin: 0 0 16px 0;
}

.config-preview {
  margin-top: 16px;
  padding: 16px;
  background: var(--bg-card);
  border: 2px solid var(--border-color);
  border-radius: 10px;
}

.preview-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.preview-value {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 6px;
}

.value-highlight {
  color: var(--primary-color);
  font-size: 20px;
  font-weight: 700;
}

.separator {
  color: var(--text-tertiary);
  font-weight: 400;
}

.preview-sublabel {
  font-size: 12px;
  color: var(--text-tertiary);
  font-style: italic;
}

.machine-config {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  padding: 8px 12px;
  background: linear-gradient(135deg, rgba(var(--primary-rgb), 0.08), rgba(var(--primary-rgb), 0.08));
  border: 1px solid rgba(var(--primary-rgb), 0.15);
  border-radius: 6px;
  font-size: 13px;
}

.config-label {
  font-weight: 500;
  color: var(--text-secondary);
}

.config-value {
  font-weight: 600;
  color: var(--primary-color);
}

.tolerance {
  font-size: 12px;
  color: var(--primary-color);
  margin-left: 4px;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
  flex: 1;
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-color);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(var(--primary-rgb), 0.3);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--bg-dark-secondary);
  color: var(--text-secondary);
}

.btn-secondary:hover {
  background: var(--bg-card-hover);
}

.btn-sm {
  padding: 8px 16px;
  font-size: 13px;
}
</style>
